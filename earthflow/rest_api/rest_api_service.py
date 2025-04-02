from fastapi import FastAPI, Depends, HTTPException, status
from datetime import datetime
from typing import List
import uvicorn

from earthflow.models.base import SessionLocal, init_db
from earthflow.models.dag_model import DAGModel
from earthflow.models.dag_run_model import DAGRunModel
from earthflow.models.task_instance_model import TaskInstanceModel

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/dags", tags=["DAGs"])
def list_dags(db=Depends(get_db)):
    return db.query(DAGModel).all()

@app.get("/dags/{dag_id}", tags=["DAGs"])
def get_dag(dag_id: str, db=Depends(get_db)):
    dag = db.query(DAGModel).filter_by(dag_id=dag_id).one_or_none()
    if not dag:
        raise HTTPException(status_code=404, detail="DAG not found")
    return dag

@app.post("/dags/{dag_id}/trigger", tags=["DAGs"])
def trigger_dag(dag_id: str, db=Depends(get_db)):
    dag = db.query(DAGModel).filter_by(dag_id=dag_id).one_or_none()
    if not dag:
        raise HTTPException(status_code=404, detail="DAG not found")

    run_id = f"{dag_id}_{datetime.utcnow().isoformat()}"
    dag_run = DAGRunModel(dag_id=dag_id, run_id=run_id, state="queued", start_time=datetime.utcnow())
    db.add(dag_run)
    db.commit()
    # Optionally push a message to the scheduler or run immediately
    return {"message": f"Triggered DAG {dag_id} with run_id {run_id}"}

@app.get("/dag_runs/{dag_id}", tags=["DAG Runs"])
def get_dag_runs(dag_id: str, db=Depends(get_db)):
    runs = db.query(DAGRunModel).filter_by(dag_id=dag_id).all()
    return runs

@app.get("/tasks/{dag_run_id}", tags=["Task Instances"])
def get_task_instances(dag_run_id: int, db=Depends(get_db)):
    tasks = db.query(TaskInstanceModel).filter_by(dag_run_id=dag_run_id).all()
    return tasks

# Additional endpoints: logs retrieval, kill run, etc.

if __name__ == "__main__":
    uvicorn.run("rest_api_service:app", host="0.0.0.0", port=8000, reload=True)