import os
import json
import types
import uuid
from pathlib import Path
import pytest

class FakeTimedelta:
	def __init__(self, seconds=0):
		self._seconds = seconds
	def total_seconds(self):
		return self._seconds

class FakeInt(int):
	def total_seconds(self):
		return float(self)

class FakeMappings(list):
	def mappings(self):
		return self
	def all(self):
		return self

class FakeColumn:
	def __init__(self, name):
		self.name = name
	def __eq__(self, other):
		return True
	def __ne__(self, other):
		return False
	def __ge__(self, other):
		return True
	def __le__(self, other):
		return True
	def __gt__(self, other):
		return True
	def __lt__(self, other):
		return True
	def __add__(self, other):
		return FakeColumn(f"{self.name}_add")
	def __sub__(self, other):
		return FakeColumn(f"{self.name}_sub")
	def __mul__(self, other):
		return FakeColumn(f"{self.name}_mul")
	def __truediv__(self, other):
		return FakeColumn(f"{self.name}_div")
	def label(self, name):
		return FakeColumn(name)

class FakeTable:
	def __init__(self, name):
		self.name = name
		self.id = FakeColumn("id")
		self.status = FakeColumn("status")
		self.priority = FakeColumn("priority")
		self.is_archived = FakeColumn("is_archived")
		self.created_by_id = FakeColumn("created_by_id")
		self.assigned_team_id = FakeColumn("assigned_team_id")
		self.updated_at = FakeColumn("updated_at")
		self.created_at = FakeColumn("created_at")
		self.actual_hours = FakeColumn("actual_hours")
		self.task_id = FakeColumn("task_id")
		self.user_id = FakeColumn("user_id")
		self.author_id = FakeColumn("author_id")
		self.tag_id = FakeColumn("tag_id")
		self.team_id = FakeColumn("team_id")
		self.name_col = FakeColumn("name")
	def __eq__(self, other):
		return True
	def __ne__(self, other):
		return False

class FakeSelect:
	def __init__(self, *args, **kwargs):
		pass
	def select_from(self, *args, **kwargs):
		return self
	def where(self, *args, **kwargs):
		return self
	def join(self, *args, **kwargs):
		return self
	def group_by(self, *args, **kwargs):
		return self
	def order_by(self, *args, **kwargs):
		return self
	def limit(self, *args, **kwargs):
		return self

class FakeFunc:
	def count(self, *args, **kwargs):
		result = FakeColumn("count")
		result.label = lambda name: FakeColumn(name)
		return result
	def sum(self, *args, **kwargs):
		result = FakeColumn("sum")
		result.label = lambda name: FakeColumn(name)
		return result
	def coalesce(self, *args, **kwargs):
		result = FakeColumn("coalesce")
		result.label = lambda name: FakeColumn(name)
		return result
	def avg(self, *args, **kwargs):
		result = FakeColumn("avg")
		result.label = lambda name: FakeColumn(name)
		return result
	def now(self, *args, **kwargs):
		result = FakeColumn("now")
		result.label = lambda name: FakeColumn(name)
		return result
	def date_trunc(self, *args, **kwargs):
		result = FakeColumn("date_trunc")
		result.label = lambda name: FakeColumn(name)
		return result

def fake_select(*args, **kwargs):
	return FakeSelect(*args, **kwargs)

def fake_text(text_val):
	return FakeColumn(text_val)

def fake_cast(expr, type_):
	return FakeColumn("cast_result")

class FakeJob:
	def __init__(self, job_id="job-123", result=None, status="started"):
		self.id = job_id
		self._result = result
		self._status = status
	def get_status(self):
		return self._status
	@property
	def result(self):
		return self._result

class FakeQueue:
	def __init__(self, *a, **k):
		self.jobs = {}
	def enqueue(self, fn, *args, **kwargs):
		job_id = "job-" + uuid.uuid4().hex[:8]
		result = fn(*args, **kwargs) if callable(fn) else {"report_id": job_id}
		job = FakeJob(job_id=job_id, result=result, status="finished")
		self.jobs[job_id] = job
		return job
	def fetch_job(self, job_id):
		return self.jobs.get(job_id)

class FakeRedis:
	def __init__(self, *a, **k):
		self.kv = {}
	def get(self, k):
		v = self.kv.get(k)
		return v if isinstance(v, (bytes, type(None))) else json.dumps(v).encode()
	def setex(self, k, ttl, val):
		self.kv[k] = val if isinstance(val, (bytes, str)) else json.dumps(val)
	def sismember(self, key, member):
		return False

class _ScalarQueue:
	def __init__(self, scalars=None, executes=None):
		self.scalars = list(scalars or [])
		self.executes = list(executes or [])
	def next_scalar(self):
		if not self.scalars:
			return FakeInt(0)
		return self.scalars.pop(0)
	def next_execute(self):
		if not self.executes:
			return FakeMappings([])
		return self.executes.pop(0)

class FakeSession:
	def __init__(self, q: _ScalarQueue):
		self.q = q
	def __enter__(self):
		return self
	def __exit__(self, *exc):
		return False
	def scalar(self, *a, **k):
		return self.q.next_scalar()
	def execute(self, *a, **k):
		return self.q.next_execute()

def passthrough_jwt_required(fn):
	from flask import g
	def wrapper(*args, **kwargs):
		if not hasattr(g, "user_id"):
			g.user_id = 1
		if not hasattr(g, "is_staff"):
			g.is_staff = True
		if not hasattr(g, "scopes"):
			g.scopes = []
		return fn(*args, **kwargs)
	wrapper.__name__ = fn.__name__
	return wrapper

def fake_init_db(_db_url):
	endpoint_data = {
		"dashboard": {
			"scalars": [FakeInt(10), FakeInt(4), FakeInt(3), FakeInt(1), 12.5],
			"executes": [
				FakeMappings([{"priority": "low", "c": 2}, {"priority": "medium", "c": 5}, {"priority": "high", "c": 3}]),
				FakeMappings([{"day": "2025-09-01", "c": 2}, {"day": "2025-09-02", "c": 1}])
			]
		},
		"tasks_distribution": {
			"scalars": [],
			"executes": [
				FakeMappings([{"status": "todo", "c": 5}, {"status": "done", "c": 2}]),
				FakeMappings([{"tag": "backend", "c": 4}])
			]
		},
		"user_stats": {
			"scalars": [FakeInt(7), FakeInt(5), FakeInt(9), FakeInt(21.0)],
			"executes": [FakeMappings([{"week": "2025-08-25", "done": 3}])]
		},
		"team_performance": {
			"scalars": [FakeInt(12), FakeInt(6), FakeInt(2), FakeTimedelta(88200)],
			"executes": [FakeMappings([{"week": "2025-09-01", "done": 3}])]
		}
	}
	call_count = [0]
	def Session():
		call_count[0] += 1
		endpoints = ["dashboard", "tasks_distribution", "user_stats", "team_performance", "team_performance"]
		endpoint_index = min(call_count[0] - 1, len(endpoints) - 1)
		endpoint = endpoints[endpoint_index]
		data = endpoint_data[endpoint]
		q = _ScalarQueue(scalars=list(data["scalars"]), executes=list(data["executes"]))
		return FakeSession(q)
	task_table = FakeTable("Task")
	tag_table = FakeTable("Tag")
	tag_table.name = FakeColumn("name")
	task_tag_table = FakeTable("TaskTag")
	task_assignment_table = FakeTable("TaskAssignment")
	comment_table = FakeTable("Comment")
	user_table = FakeTable("User")
	team_table = FakeTable("Team")
	team_members_table = FakeTable("TeamMembers")
	models = {
		"Session": Session,
		"Task": task_table,
		"Tag": tag_table,
		"TaskTag": task_tag_table,
		"TaskAssignment": task_assignment_table,
		"Comment": comment_table,
		"User": user_table,
		"Team": team_table,
		"users_team_members": team_members_table,
		"TeamMembers": team_members_table,
	}
	return models

@pytest.fixture(autouse=True)
def set_env(tmp_path, monkeypatch):
	monkeypatch.setenv("ANALYTICS_DATABASE_URL", "postgresql+psycopg://fake:fake@db/fake")
	monkeypatch.setenv("ANALYTICS_REDIS_URL", "redis://fake:6379/0")
	monkeypatch.setenv("REPORTS_DIR", str(tmp_path))
	monkeypatch.setenv("JWT_ISSUER", "https://issuer")
	monkeypatch.setenv("JWT_JWKS_URL", "https://issuer/.well-known/jwks.json")

@pytest.fixture
def app_client(monkeypatch):
	import sqlalchemy.sql
	monkeypatch.setattr("sqlalchemy.select", fake_select)
	monkeypatch.setattr("sqlalchemy.func", FakeFunc())
	monkeypatch.setattr("sqlalchemy.text", fake_text)
	monkeypatch.setattr("sqlalchemy.cast", fake_cast)
	monkeypatch.setattr("sqlalchemy.Date", type("FakeDate", (), {}))
	monkeypatch.setattr("init_db.init_db", fake_init_db)
	import jwt_auth
	monkeypatch.setattr(jwt_auth, "jwt_required", passthrough_jwt_required)
	monkeypatch.setattr("redis.Redis.from_url", lambda *_a, **_k: FakeRedis())
	monkeypatch.setattr("rq.Queue", FakeQueue)
	from app import create_app
	app = create_app()
	app.testing = True
	return app.test_client(), app

def fake_report_job(data_json, db_url, reports_dir, **kwargs):
	import os
	report_id = uuid.uuid4().hex[:8]
	csv_path = os.path.join(reports_dir, f"{report_id}.csv")
	with open(csv_path, 'w') as f:
		f.write("task_id,status,created_at\n")
		f.write("1,done,2025-09-01\n")
		f.write("2,in_progress,2025-09-02\n")
	return {"report_id": report_id}

def auth_header():
	return {"Authorization": "Bearer testtoken"}

def test_healthz(app_client):
	client, _app = app_client
	r = client.get("/api/v1/analytics/healthz")
	assert r.status_code == 200
	assert r.get_json() == {"ok": True}

def test_dashboard_ok(app_client):
	client, _app = app_client
	r = client.get("/api/v1/analytics/dashboard", headers=auth_header())
	assert r.status_code == 200
	data = r.get_json()
	assert data["summary"]["total_tasks"] == 10
	assert data["summary"]["done_tasks"] == 4
	assert data["summary"]["in_progress_tasks"] == 3
	assert data["summary"]["blocked_tasks"] == 1
	assert data["summary"]["total_hours_done"] == 12.5
	assert isinstance(data["by_priority"], list)
	assert isinstance(data["last30_done"], list)

def test_tasks_distribution_ok(app_client):
	client, _app = app_client
	r = client.get("/api/v1/analytics/tasks/distribution", headers=auth_header())
	assert r.status_code == 200
	data = r.get_json()
	assert "by_status" in data
	assert "top_tags" in data
	assert isinstance(data["by_status"], list)
	assert isinstance(data["top_tags"], list)

def test_user_stats_ok(app_client):
	client, _app = app_client
	r = client.get("/api/v1/analytics/user/1/stats", headers=auth_header())
	assert r.status_code == 200
	data = r.get_json()
	assert data["user_id"] == 1
	assert "summary" in data
	assert "velocity" in data

def test_team_performance_ok_staff(app_client):
	client, _app = app_client
	r = client.get("/api/v1/analytics/team/10/performance", headers=auth_header())
	assert r.status_code == 200
	data = r.get_json()
	assert data["team_id"] == 10
	assert "metrics" in data
	assert "throughput" in data

def test_reports_flow(app_client, tmp_path, monkeypatch):
	client, app = app_client
	monkeypatch.setattr("tasks.report_job", fake_report_job)
	r = client.post("/api/v1/reports/generate", headers=auth_header(), json={"query": "done_last_30d"})
	assert r.status_code == 202
	job_id = r.get_json()["job_id"]
	assert job_id
	r = client.get(f"/api/v1/reports/{job_id}", headers=auth_header())
	assert r.status_code == 200
	status = r.get_json()
	assert status["status"] == "finished"
	report_id = "test_report"
	csv_path = tmp_path / f"{report_id}.csv"
	csv_path.write_text("task_id,status\n1,done\n2,in_progress\n")
	r = client.get(f"/api/v1/reports/{report_id}/download", headers=auth_header())
	assert r.status_code == 200
	assert "text/csv" in r.headers.get("Content-Type", "")
