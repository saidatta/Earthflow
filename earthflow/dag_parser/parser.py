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