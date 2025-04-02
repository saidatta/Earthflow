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