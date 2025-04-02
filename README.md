# EarthFlow

EarthFlow is an MVP (Minimum Viable Product) version of a workflow orchestration system inspired by Apache Airflow, built for Python 3.12. It provides a simplified implementation of DAG (Directed Acyclic Graph) based workflow execution with local executor functionality.

## Features

- Create and schedule Python-based DAG workflows
- Execute tasks in a deterministic order based on dependencies
- PostgreSQL backend for metadata storage and communication
- REST API for DAG management and monitoring
- File-based logging system
- Support for BashOperator tasks

## System Requirements

- Python 3.12+
- PostgreSQL
- Dependencies listed in `requirements.txt`

## Installation

1. Clone the repository:

```bash
git clone https://github.com/saidatta/Earthflow.git
cd Earthflow
```

2. Set up a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. Install the dependencies:

```bash
pip install -r earthflow/requirements.txt
```

4. Configure the PostgreSQL connection in `earthflow/models/base.py` by updating the `DATABASE_URL` variable with your database credentials.

## Usage

### Creating a DAG

Create a Python file in the `earthflow/DAGS` directory. Here's an example:

```python
from earthflow.core.dag import DAG
from earthflow.operators.bash_operator import BashOperator

with DAG(dag_id="example_dag", schedule="0 9 * * *", version="1.0") as dag:
    t1 = BashOperator(task_id="print_hello", bash_command="echo Hello from t1")
    t2 = BashOperator(task_id="print_world", bash_command="echo World from t2")

    # Define task dependencies
    t1.set_downstream(t2)  # This can also be written as t1 >> t2
```

### Running the Scheduler

```bash
python -m earthflow.scheduler.scheduler_service
```

### Running the REST API

```bash
python -m earthflow.rest_api.rest_api_service
```

### API Endpoints

- `GET /dags` - List all DAGs
- `GET /dags/{dag_id}` - Get a specific DAG
- `POST /dags/{dag_id}/trigger` - Trigger a DAG run
- `GET /dag_runs/{dag_id}` - Get runs for a specific DAG
- `GET /tasks/{dag_run_id}` - Get task instances for a specific DAG run

## Project Structure

```
earthflow/
  ├── dag_parser/        # DAG discovery and registration
  ├── models/            # Database models
  ├── operators/         # Task operators
  ├── scheduler/         # Scheduler service
  ├── rest_api/          # REST API service
  ├── core/              # Core components
  ├── utils/             # Utility functions
  ├── DAGS/              # Directory for user-defined DAG files
  └── requirements.txt   # Project dependencies
```

## Development Notes

This is an MVP implementation with the following limitations:

1. All execution is local (no distributed execution)
2. Limited error handling and recovery
3. Basic scheduling with croniter 
4. Minimal security features

For a production system, consider adding:
- Distributed execution (KubernetesExecutor, CeleryExecutor)
- Better error handling and task retries
- Web UI for monitoring
- Advanced security features
- Enhanced logging and monitoring
