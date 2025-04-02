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