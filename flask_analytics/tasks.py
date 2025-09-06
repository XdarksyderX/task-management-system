# tasks.py
import os, json, uuid, logging
from sqlalchemy import select, func, text
from init_db import init_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def report_job(payload_json, db_url, reports_dir):
    try:
        logger.info(f"Starting report job with payload: {payload_json}")
        
        payload = json.loads(payload_json)
        DB = init_db(db_url)
        Session = DB["Session"]
        Task = DB["Task"]

        with Session() as s:
            stmt = select(
                Task.id, Task.title, Task.status, Task.priority,
                Task.created_at, Task.updated_at, Task.due_date,
                Task.estimated_hours, Task.actual_hours, Task.is_archived
            )
            
            query_type = payload.get("query", "all_tasks")
            
            if query_type == "done_last_30d":
                stmt = stmt.where(
                    Task.status == "done",
                    Task.updated_at >= func.now() - text("interval '30 days'")
                )
            elif query_type == "all_tasks":
                # No additional filtering for all tasks
                pass
            else:
                # Default to all tasks if unknown query type
                pass
                
            rows = s.execute(stmt).all()

        os.makedirs(reports_dir, exist_ok=True)
        rid = str(uuid.uuid4())
        path = os.path.join(reports_dir, f"{rid}.csv")
        
        with open(path, "w", encoding="utf-8") as f:
            f.write("id,title,status,priority,created_at,updated_at,due_date,estimated_hours,actual_hours,is_archived\n")
            for r in rows:
                f.write(",".join([
                    str(r.id),
                    '"' + (r.title or "").replace('"','""') + '"',
                    str(r.status or ""), str(r.priority or ""),
                    r.created_at.isoformat() if r.created_at else "",
                    r.updated_at.isoformat() if r.updated_at else "",
                    r.due_date.isoformat() if r.due_date else "",
                    str(r.estimated_hours or ""), str(r.actual_hours or ""),
                    "true" if r.is_archived else "false",
                ]) + "\n")
        
        logger.info(f"Report generated successfully: {rid} with {len(rows)} rows")
        
        return {
            "report_id": rid, 
            "count": len(rows),
            "query": query_type,
            "filename": f"{rid}.csv"
        }
        
    except Exception as e:
        logger.error(f"Error in report_job: {str(e)}", exc_info=True)
        raise