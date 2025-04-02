class BaseOperator:
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.dag = None
        self.upstream_tasks = []
        self.downstream_tasks = []

    def set_upstream(self, task):
        self.upstream_tasks.append(task)
        task.downstream_tasks.append(self)

    def set_downstream(self, task):
        self.downstream_tasks.append(task)
        task.upstream_tasks.append(self)