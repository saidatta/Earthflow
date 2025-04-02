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