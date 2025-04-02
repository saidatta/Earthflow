import os
import logging
from datetime import datetime

def setup_task_logger(dag_id, task_id, execution_date):
    """
    Sets up logging for a task instance.
    
    Args:
        dag_id (str): The ID of the DAG
        task_id (str): The ID of the task
        execution_date (datetime): The execution date of the DAG run
    
    Returns:
        logger: A configured logger instance
        log_file_path: The path to the log file
    """
    # Create log directory structure
    log_dir = os.path.join('/var/log/earthflow', dag_id, task_id)
    os.makedirs(log_dir, exist_ok=True)
    
    # Generate log file name based on execution date
    log_file_name = f"{execution_date.isoformat()}.log"
    log_file_path = os.path.join(log_dir, log_file_name)
    
    # Set up logger
    logger = logging.getLogger(f"{dag_id}.{task_id}")
    logger.setLevel(logging.INFO)
    
    # Create file handler
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    
    return logger, log_file_path