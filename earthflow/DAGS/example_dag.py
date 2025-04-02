# earthflow/DAGS/example_dag.py

from earthflow.core.dag import DAG
from earthflow.operators.bash_operator import BashOperator

with DAG(dag_id="example_dag", schedule="0 9 * * *", version="1.0") as dag:
    t1 = BashOperator(task_id="print_hello", bash_command="echo Hello from t1")
    t2 = BashOperator(task_id="print_world", bash_command="echo World from t2")

    # Define task dependencies
    t1.set_downstream(t2)  # This can also be written as t1 >> t2