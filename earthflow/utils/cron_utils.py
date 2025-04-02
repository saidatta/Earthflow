from datetime import datetime
from croniter import croniter

def is_cron_time(cron_expr: str, current_time: datetime = None) -> bool:
    """
    Determines if the current time matches the cron expression.
    
    Args:
        cron_expr (str): A cron expression (e.g., "0 9 * * *")
        current_time (datetime, optional): The time to check against. Defaults to now.
    
    Returns:
        bool: True if the current time matches the cron expression, False otherwise
    """
    if current_time is None:
        current_time = datetime.utcnow()
    
    # Create a croniter instance
    cron = croniter(cron_expr, current_time)
    
    # Get the previous and next scheduled times
    prev_time = cron.get_prev(datetime)
    next_time = cron.get_next(datetime)
    
    # If the previous scheduled time is within the last minute,
    # we consider it time to run the cron job
    time_diff = (current_time - prev_time).total_seconds()
    
    # If the difference is less than 60 seconds (1 minute),
    # it's time to run the job
    return time_diff < 60