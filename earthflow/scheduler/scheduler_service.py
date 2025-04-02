import time
import threading
import traceback
import os
import importlib
from datetime import datetime

from earthflow.models.base import SessionLocal, init_db
from earthflow.dag_parser.parser import discover_and_register_dags
from earthflow.models.dag_model import DAGModel
from earthflow.models.dag_run_model import DAGRunModel
from earthflow.models.task_instance_model import TaskInstanceModel
from earthflow.utils.cron_utils import is_cron_time
from earthflow.utils.logging_utils import setup_task_logger

# Set DAGS_FOLDER to a relative path within the project
DAGS_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "DAGS")

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
# Note: We removed the is_cron_time function because we're now importing it from utils.cron_utils
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
    """
    Executes the tasks for a DAG run locally.
    
    This is a simplified implementation that:
    1. Rediscovers the DAG from the DAGS folder
    2. Gets the tasks from the DAG
    3. Performs a simple topological sort based on dependencies
    4. Executes each task in order, updating its state in the database
    """
    # Find the DAG file that contains the DAG with dag_id = dag_run.dag_id
    found_dag = None
    
    for file_path in os.listdir(DAGS_FOLDER):
        if file_path.endswith('.py'):
            module_name = os.path.splitext(file_path)[0]
            spec = importlib.util.spec_from_file_location(
                module_name,
                os.path.join(DAGS_FOLDER, file_path)
            )
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            
            # Check if this module contains our DAG
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if hasattr(attr, 'dag_id') and attr.dag_id == dag_run.dag_id:
                    found_dag = attr
                    break
            
            if found_dag:
                break
    
    if not found_dag:
        print(f"Could not find DAG with id {dag_run.dag_id}")
        dag_run.state = "failed"
        session.commit()
        return
    
    # Simple topological sort (this is a naive implementation)
    # In a real system, you'd handle cycles, multiple paths, etc.
    def get_sorted_tasks(dag):
        tasks = list(dag.tasks)
        result = []
        
        # Add tasks with no dependencies first
        no_deps = [t for t in tasks if not t.upstream_tasks]
        result.extend(no_deps)
        
        # Add the rest based on dependencies
        remaining = [t for t in tasks if t not in no_deps]
        while remaining:
            for task in list(remaining):
                if all(up in result for up in task.upstream_tasks):
                    result.append(task)
                    remaining.remove(task)
        
        return result
    
    sorted_tasks = get_sorted_tasks(found_dag)
    
    # Execute each task
    execution_date = dag_run.start_time
    
    for task in sorted_tasks:
        # Create a task instance
        task_instance = TaskInstanceModel(
            dag_run_id=dag_run.id,
            task_id=task.task_id,
            state="running",
            start_time=datetime.utcnow()
        )
        session.add(task_instance)
        session.commit()
        
        try:
            # Set up logging
            logger, log_file_path = setup_task_logger(
                dag_run.dag_id,
                task.task_id,
                execution_date
            )
            
            # Update log file path
            task_instance.log_file_path = log_file_path
            session.commit()
            
            # Execute the task
            logger.info(f"Executing task {task.task_id}")
            result = task.execute({"execution_date": execution_date, "dag_run": dag_run})
            
            # Log the result
            return_code, stdout, stderr = result
            logger.info(f"Task completed with return code {return_code}")
            logger.info(f"STDOUT: {stdout}")
            if stderr:
                logger.error(f"STDERR: {stderr}")
            
            # Update task state
            task_instance.state = "success" if return_code == 0 else "failed"
            task_instance.end_time = datetime.utcnow()
            session.commit()
            
            # If task failed, mark the DAG run as failed and exit
            if return_code != 0:
                logger.error(f"Task {task.task_id} failed, marking DAG as failed")
                dag_run.state = "failed"
                dag_run.end_time = datetime.utcnow()
                session.commit()
                return
                
        except Exception as e:
            print(f"Error executing task {task.task_id}: {str(e)}")
            task_instance.state = "failed"
            task_instance.end_time = datetime.utcnow()
            session.commit()
            
            # Mark the DAG run as failed
            dag_run.state = "failed"
            dag_run.end_time = datetime.utcnow()
            session.commit()
            return
    
    # All tasks completed successfully
    dag_run.state = "success"
    dag_run.end_time = datetime.utcnow()
    session.commit()

def start_scheduler():
    init_db()
    scheduler_thread = threading.Thread(target=schedule_loop, daemon=True)
    scheduler_thread.start()
    scheduler_thread.join()

if __name__ == "__main__":
    start_scheduler()