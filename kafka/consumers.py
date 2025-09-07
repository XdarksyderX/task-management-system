import os, json, logging, psycopg2, redis, signal, sys
from datetime import datetime
from dateutil.tz import tzutc
from confluent_kafka import Consumer, KafkaError

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
TOPICS = [
    t.strip()
    for t in os.getenv(
        "KAFKA_TOPICS",
        "user-activities,task-events,analytics-events,system-notifications",
    ).split(",")
    if t.strip()
]
GROUP_ID = os.getenv("KAFKA_GROUP_ID", "tms-role")
RESET = os.getenv("KAFKA_AUTO_OFFSET_RESET", "earliest")
ROLE = os.getenv("ROLE", "notifications")
PG_DSN = os.getenv("PG_DSN", "postgresql://postgres:postgres@postgres:5432/postgres")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/1")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(f"consumer-{ROLE}")

pg = None
rd = None
if ROLE in {"activity-feed", "search-index", "audit"}:
    pg = psycopg2.connect(PG_DSN)
    pg.autocommit = True
if ROLE in {"notifications", "analytics"}:
    rd = redis.from_url(REDIS_URL)

if ROLE == "activity-feed":
    with pg.cursor() as c:
        c.execute(
            """create table if not exists activity_feed(
            id bigserial primary key,
            user_id bigint,
            event_type text,
            entity text,
            entity_id bigint,
            ts timestamptz default now(),
            payload jsonb not null
        );"""
        )
if ROLE == "audit":
    with pg.cursor() as c:
        c.execute(
            """create table if not exists audit_logs(
            id bigserial primary key,
            user_id bigint,
            event_type text,
            ts timestamptz default now(),
            payload jsonb not null
        );"""
        )
if ROLE == "search-index":
    with pg.cursor() as c:
        c.execute(
            """
        create table if not exists search_index_tasks(
          task_id bigint primary key,
          search tsvector
        );
        """
        )


def ts_day(s):
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        d = datetime.now(tzutc())
    return d.strftime("%Y-%m-%d")


c = Consumer(
    {
        "bootstrap.servers": BOOTSTRAP,
        "group.id": GROUP_ID,
        "auto.offset.reset": RESET,
        "enable.auto.commit": True,
    }
)
c.subscribe(TOPICS)

_shutdown = False


def _graceful(*_):
    global _shutdown
    _shutdown = True


signal.signal(signal.SIGINT, _graceful)
signal.signal(signal.SIGTERM, _graceful)

log.info(f"role={ROLE} topics={TOPICS} group_id={GROUP_ID}")

while not _shutdown:
    msg = c.poll(1.0)
    if msg is None:
        continue
    if msg.error():
        if msg.error().code() != KafkaError._PARTITION_EOF:
            log.error(f"kafka error: {msg.error()}")
        continue
    key = msg.key().decode() if msg.key() else None
    try:
        v = json.loads(msg.value().decode())
    except Exception as e:
        log.error(f"bad json: {e}")
        continue
    et = v.get("event_type")
    uid = v.get("user_id")
    data = v.get("data", {})
    if ROLE == "notifications":
        rd.lpush(
            "notifications",
            json.dumps(
                {"topic": msg.topic(), "event_type": et, "user_id": uid, "data": data}
            ),
        )
        log.info(f"notif queued topic={msg.topic()} et={et} user_id={uid}")
    elif ROLE == "activity-feed":
        ent = "task" if "task_id" in data else "generic"
        ent_id = data.get("task_id")
        with pg.cursor() as cur:
            cur.execute(
                "insert into activity_feed(user_id,event_type,entity,entity_id,payload) values (%s,%s,%s,%s,%s)",
                (uid, et, ent, ent_id, json.dumps(v)),
            )
        log.info(f"feed insert et={et} entity={ent} id={ent_id}")
    elif ROLE == "analytics":
        day = ts_day(v.get("timestamp", ""))
        keyh = f"analytics:{day}"
        field = et or "unknown"
        rd.hincrby(keyh, field, 1)
        log.info(f"analytics {keyh} {field}+1")
    elif ROLE == "search-index":
        tid = data.get("task_id")
        if tid is not None:
            txt = f"{data.get('title','')} {data.get('description','')}"
            with pg.cursor() as cur:
                cur.execute(
                    """
				insert into search_index_tasks(task_id, search)
				values (%s, to_tsvector('simple', %s))
				on conflict (task_id) do update
				set search = excluded.search
				""",
                    (tid, txt),
                )
            log.info(f"reindex task_id={tid}")
        else:
            log.info("reindex skip no task_id")
    elif ROLE == "audit":
        with pg.cursor() as cur:
            cur.execute(
                "insert into audit_logs(user_id,event_type,payload) values (%s,%s,%s)",
                (uid, et, json.dumps(v)),
            )
        log.info(f"audit {et} user_id={uid}")

try:
    c.close()
except:
    pass
if pg:
    pg.close()
