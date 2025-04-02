import subprocess
from earthflow.core.task import BaseOperator

class BashOperator(BaseOperator):
    def __init__(self, task_id: str, bash_command: str):
        super().__init__(task_id)
        self.bash_command = bash_command

    def execute(self, context=None):
        # context can hold run_id, params, etc.
        # For MVP, just run the command
        process = subprocess.Popen(
            self.bash_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()
        return_code = process.returncode
        return return_code, stdout.decode(), stderr.decode()