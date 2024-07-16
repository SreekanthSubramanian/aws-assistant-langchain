import os
import subprocess
from typing import Any, Type, Optional

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


class AWSCLIToolParams(BaseModel):
    aws_cli_command: str = Field(..., description="AWS CLI command")


class AWSCLITool(BaseTool):
    args_schema: Type[AWSCLIToolParams] = AWSCLIToolParams

    def _run(
            self,
            aws_cli_command: str,
            run_manager: Optional[CallbackManagerForToolRun] = None,
            **kwargs: Any,
    ) -> dict:
        my_process = subprocess.Popen(aws_cli_command + f" --profile {os.environ.get('CURRENT_PROFILE')}", shell=True,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = my_process.communicate()
        stdout = stdout.decode('utf-8') if stdout else ""
        stderr = stderr.decode('utf-8') if stderr else ""
        if my_process.returncode != 0:
            return {"status": "error", "message": stderr}
        else:
            return {"status": "success", "message": stdout}
