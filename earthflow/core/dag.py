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