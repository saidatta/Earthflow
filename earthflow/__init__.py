"""
EarthFlow - A simple workflow orchestration system inspired by Airflow.

This package provides tools to define, schedule, and monitor workflows.
"""

from earthflow.core.dag import DAG
from earthflow.operators.bash_operator import BashOperator

__version__ = "0.1.0"