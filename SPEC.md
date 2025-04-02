Below is a **conceptual** Python 3.12 code skeleton illustrating how you might structure your EarthFlow MVP (inspired by Airflow LocalExecutor). It is not a fully functional system yet—it outlines the architecture, core modules, and key classes to help you get started in a maintainable way.

---
## High-Level Architecture

1. **Directory with Python DAG files**  
   - Users place/update Python files defining DAGs (BashOperators, dependencies, schedule, etc.) in a configurable directory (`DAGS_FOLDER`).
   - Example DAG file (`example_dag.py`) might look like:
     ```python
     from earthflow import DAG, BashOperator

     with DAG(dag_id="example_dag", schedule="0 9 * * *", version="1.0") as dag:
         t1 = BashOperator(task_id="task1", bash_command="echo 'Task 1'")
         t2 = BashOperator(task_id="task2", bash_command="echo 'Task 2'")

         t1 >> t2  # define dependency
     ```

2. **PostgreSQL Database**  
   - Stores DAG metadata (dag_id, version, schedule, etc.), DAG run history, task instances (states, start time, end time, etc.), and logs references.
   - Acts as the communication hub between services.

3. **Scheduler Service** (`scheduler_service.py`)  
   - A process that:
     1. Scans the `DAGS_FOLDER` for Python files.
     2. Dynamically imports each DAG definition.
     3. Updates DAG metadata in PostgreSQL (including version).
     4. Sets up cron-based scheduling logic (manually or via a library like `APScheduler`).
     5. Executes tasks locally when a DAG is triggered (on cron or on-demand).
     6. Writes task logs to local files and updates statuses in PostgreSQL.

4. **REST API Service** (`rest_api_service.py`)  
   - A process (Flask / FastAPI / etc.) that exposes endpoints to:
     1. **List** DAGs, tasks, runs, logs, etc.
     2. **Trigger** a DAG run manually.
     3. **Stop/cancel** running DAG (optional).
     4. **Retrieve** real-time task statuses and logs.
     5. Provide basic authentication/authorization (even if minimal token-based for MVP).
   - Reads/writes data to PostgreSQL.

5. **Executor / Worker Model**  
   - For MVP, everything runs on the **same pod/node** (local executor).
   - In future, you might introduce a distributed executor (KubernetesExecutor, CeleryExecutor, etc.).

6. **File-Based Logging**  
   - Each task logs to a file, e.g. `/var/log/earthflow/<dag_id>/<task_id>/<execution_date>.log`.
   - You store references to these logs in PostgreSQL for quick retrieval.

---

## Folder Structure

A possible project structure:

```
earthflow/
  ├── dag_parser/
  │   └── parser.py                 # logic to scan folder, import DAGs
  ├── models/
  │   ├── base.py                   # SQLAlchemy base, session creation
  │   ├── dag_model.py              # DAG ORM model
  │   ├── dag_run_model.py          # DAGRun ORM model
  │   ├── task_instance_model.py    # TaskInstance ORM model
  │   └── ...
  ├── operators/
  │   └── bash_operator.py          # BashOperator definition
  ├── scheduler/
  │   └── scheduler_service.py      # main scheduler logic
  ├── rest_api/
  │   └── rest_api_service.py       # main REST service
  ├── core/
  │   ├── dag.py                    # DAG class definition
  │   ├── task.py                   # Base Task operator
  │   └── ...
  ├── utils/
  │   ├── logging_utils.py          # handle file-based logging
  │   ├── cron_utils.py             # parse cron expressions
  │   └── ...
  ├── DAGS/                         # folder with user-defined DAG files
  │   └── example_dag.py
  └── requirements.txt
```

---

## Database Models (SQLAlchemy Example)

### `models/base.py`
```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+psycopg2://user:password@hostname:5432/earthflow"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    Base.metadata.create_all(bind=engine)
```

### `models/dag_model.py`
```python
from sqlalchemy import Column, String, Integer, DateTime
from .base import Base

class DAGModel(Base):
    __tablename__ = "dag"

    id = Column(Integer, primary_key=True, index=True)
    dag_id = Column(String, unique=True)
    schedule = Column(String)            # e.g., cron expression
    version = Column(String, default="") # version tracking
    last_parsed = Column(DateTime)       # for debugging or last parse time
    # Add more fields as needed
```

### `models/dag_run_model.py`
```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base

class DAGRunModel(Base):
    __tablename__ = "dag_run"

    id = Column(Integer, primary_key=True, index=True)
    dag_id = Column(String)  # could also be ForeignKey to DAGModel.dag_id
    run_id = Column(String)  # unique identifier for the run
    state = Column(String)   # e.g., "running", "success", "failed"
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    # relationship("TaskInstanceModel", back_populates="dag_run")
```

### `models/task_instance_model.py`
```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base

class TaskInstanceModel(Base):
    __tablename__ = "task_instance"

    id = Column(Integer, primary_key=True, index=True)
    dag_run_id = Column(Integer, ForeignKey("dag_run.id"))
    task_id = Column(String)
    state = Column(String)      # "queued", "running", "success", "failed"
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    log_file_path = Column(String, nullable=True)
    # relationship("DAGRunModel", back_populates="task_instances")
```

---

## Core Classes

### `core/dag.py`
```python
from typing import List
from earthflow.core.task import BaseOperator

class DAG:
    def __init__(self, dag_id: str, schedule: str, version: str = "latest"):
        self.dag_id = dag_id
        self.schedule = schedule
        self.version = version
        self.tasks: List[BaseOperator] = []

    def add_task(self, task: BaseOperator):
        self.tasks.append(task)
        task.dag = self

    def __enter__(self):
        # allow `with DAG() as dag: ...` syntax
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
```

### `core/task.py`
```python
class BaseOperator:
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.dag = None
        self.upstream_tasks = []
        self.downstream_tasks = []

    def set_upstream(self, task):
        self.upstream_tasks.append(task)
        task.downstream_tasks.append(self)

    def set_downstream(self, task):
        self.downstream_tasks.append(task)
        task.upstream_tasks.append(self)
```

### `operators/bash_operator.py`
```python
import subprocess
from earthflow.core.task import BaseOperator

class BashOperator(BaseOperator):
    def __init__(self, task_id: str, bash_command: str):
        super().__init__(task_id)
        self.bash_command = bash_command

    def execute(self, context=None):
        # context can hold run_id, params, etc.
        # For MVP, just run the command
        process = subprocess.Popen(
            self.bash_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()
        return_code = process.returncode
        return return_code, stdout.decode(), stderr.decode()
```

---

## DAG File Example

```python
# earthflow/DAGS/example_dag.py

from earthflow.core.dag import DAG
from earthflow.operators.bash_operator import BashOperator

with DAG(dag_id="example_dag", schedule="0 9 * * *", version="1.0") as dag:
    t1 = BashOperator(task_id="print_hello", bash_command="echo Hello from t1")
    t2 = BashOperator(task_id="print_world", bash_command="echo World from t2")

    t1 >> t2
```

---

## Parsing and Registering DAGs (`dag_parser/parser.py`)

```python
import importlib
import os
import sys
import glob
from datetime import datetime

from earthflow.models.base import SessionLocal
from earthflow.models.dag_model import DAGModel

def discover_and_register_dags(dag_folder: str):
    """
    1. Dynamically import all .py files in the dag_folder.
    2. Extract `DAG` objects and register in DB.
    """
    sys.path.append(dag_folder)  # so we can import them as modules

    session = SessionLocal()

    try:
        for file_path in glob.glob(os.path.join(dag_folder, "*.py")):
            module_name = os.path.splitext(os.path.basename(file_path))[0]
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # This executes the DAG file

            # The DAG file uses 'with DAG(...) as dag:' syntax.
            # You might store a global reference in the module, e.g. mod.dag
            for attribute_name in dir(mod):
                attribute = getattr(mod, attribute_name)
                # We check if it's a DAG instance
                if hasattr(attribute, "dag_id") and hasattr(attribute, "tasks"):
                    register_dag_in_db(session, attribute)
    finally:
        session.close()

def register_dag_in_db(session, dag):
    # Upsert logic
    existing_dag = session.query(DAGModel).filter_by(dag_id=dag.dag_id).one_or_none()
    if existing_dag:
        existing_dag.schedule = dag.schedule
        existing_dag.version = dag.version
        existing_dag.last_parsed = datetime.utcnow()
        # Update other fields as needed
    else:
        new_dag_model = DAGModel(
            dag_id=dag.dag_id,
            schedule=dag.schedule,
            version=dag.version,
            last_parsed=datetime.utcnow(),
        )
        session.add(new_dag_model)
    session.commit()
```

---

## Scheduler Service (`scheduler/scheduler_service.py`)

```python
import time
import threading
import traceback
from datetime import datetime

from earthflow.models.base import SessionLocal, init_db
from earthflow.dag_parser.parser import discover_and_register_dags
from earthflow.models.dag_model import DAGModel
from earthflow.models.dag_run_model import DAGRunModel, TaskInstanceModel
from earthflow.operators.bash_operator import BashOperator
# ... other imports e.g. APScheduler or a custom cron parser

DAGS_FOLDER = "/path/to/dags"

def schedule_loop():
    """
    1. Periodically discover new DAGs.
    2. Check if it's time to run them (based on cron).
    3. Trigger execution if scheduled.
    """
    while True:
        try:
            discover_and_register_dags(DAGS_FOLDER)
            schedule_and_run_dags()
        except Exception as e:
            print("Error in schedule loop:", e, traceback.format_exc())
        time.sleep(30)  # Sleep for 30s or so

def schedule_and_run_dags():
    session = SessionLocal()
    try:
        all_dags = session.query(DAGModel).all()
        for dag in all_dags:
            if is_cron_time(dag.schedule):
                # Check if not recently triggered
                create_and_run_dag_run(session, dag)
    finally:
        session.close()

def is_cron_time(cron_expr: str) -> bool:
    # parse the cron expression
    # for MVP, let's say it triggers once every time we check if it matches the current minute
    # use a library like croniter for more robust logic
    return True  # Simplified, for demonstration

def create_and_run_dag_run(session, dag_model):
    # Create a new DAGRun record
    run_id = f"{dag_model.dag_id}_{datetime.utcnow().isoformat()}"
    dag_run = DAGRunModel(dag_id=dag_model.dag_id, run_id=run_id, state="running", start_time=datetime.utcnow())
    session.add(dag_run)
    session.commit()

    # Actually run the DAG tasks in local executor style
    # We'll do a naive topological sort or sequential run
    run_dag_tasks_local(session, dag_run)

def run_dag_tasks_local(session, dag_run):
    # For MVP, re-import DAG definition to get tasks?
    # Or store the DAG structure in DB or somewhere. Let's do a naive approach:
    # Pseudocode: re-discover the DAG, find the matching dag_id, run tasks in order
    pass

def start_scheduler():
    init_db()
    scheduler_thread = threading.Thread(target=schedule_loop, daemon=True)
    scheduler_thread.start()
    scheduler_thread.join()

if __name__ == "__main__":
    start_scheduler()
```

**NOTE**: For actual DAG execution, you’d need logic to:
1. Load the DAG’s tasks from the Python file or from an in-memory structure.  
2. Perform a topological sort of tasks based on dependencies.  
3. For each task, create a `TaskInstanceModel`, run the task’s `execute()`, capture logs, store logs in a file, update task state in DB.  
4. Continue until all tasks are done or any fail.  

---

## REST API Service (Using FastAPI as an Example)

### `rest_api_service.py`
```python
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
```

---

## Notes & Next Steps

1. **Task Execution**:  
   - The above skeleton does not show the actual local execution loop in detail. In a real system, you’d have a queue (or some scheduling logic) that picks up tasks from the “queued” state, runs them, and updates them to “running”/“success”/“failed.”

2. **Cron Scheduling**:  
   - Use a robust library like `croniter` or `APScheduler` to evaluate `cron_expr` and trigger DAGs at the correct time. The code above has a placeholder `is_cron_time()` function.

3. **Real-Time Logs & Monitoring**:  
   - For real-time logs, you could store logs in files, then optionally stream them via websockets or an SSE endpoint.  
   - The database would store the path to the log file, and the REST API could serve them on-demand.

4. **Authentication**:  
   - For MVP, you might add a simple token-based or Basic Auth approach using FastAPI’s dependency injection.  

5. **Resource Constraints**:  
   - You can enforce memory/CPU constraints if your environment (Kubernetes, Docker) supports it. For example, run tasks in separate Docker containers with resource limits (that’s heading toward a more advanced executor model).

6. **Versioning**:  
   - The `version` field in the DAG can be updated whenever a DAG changes.  
   - The scheduler picks up new versions automatically on parse.

7. **Scaling**:  
   - For horizontal scaling: you could run multiple scheduler replicas, but you need to ensure they coordinate so only one instance triggers a DAG at a given time. This typically involves a DB-based locking mechanism or a specialized concurrency lock (e.g., Redlock in Redis).
   - For tasks, in the MVP, they’re local. Eventually, you’d integrate a distributed executor.

8. **Error Handling & Retries**:  
   - Add configurable retry logic for tasks if return_code != 0.  
   - Store attempt counts in the `TaskInstanceModel`.

9. **CLI**:  
   - If you want a CLI-based approach to trigger DAGs or see statuses, you can build a small CLI that calls these REST endpoints or queries the DB directly.

---

## Summary

This skeleton demonstrates:
- **Two separate processes**: A scheduler (which periodically scans DAG files, registers them, and triggers runs) and a REST API (for listing DAGs, triggering runs, reading statuses, logs, etc.).  
- **PostgreSQL** for shared state and metadata.  
- **Local Executor** style execution for simplicity.  
- **File-based logging** with references stored in DB.  

From here, you can flesh out each piece depending on your MVP requirements (e.g., implement a robust cron scheduler, complete the local execution logic, add more endpoints for logs, authentication, etc.). This approach provides a straightforward foundation that you can iterate upon as you add more advanced features (KubernetesExecutor, alerting, UI, etc.).