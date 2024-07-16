from typing import Optional, Any

from langchain_core.callbacks import CallbackManagerForToolRun
from pydantic import BaseModel, Field

from tools.base_aws_cli_tool import AWSCLITool


class AWSCLIDeleteToolParams(BaseModel):
    command: str = Field(..., description="AWS CLI command to delete resources, e.g., 'aws ec2 terminate-instances'")


class AWSCLIDeleteTool(AWSCLITool):
    name: str = "aws_cli_delete_tool"
    description: str = ("This tool handles AWS delete commands. Use AWS CLI format like 'aws ec2 terminate-instances'. "
                        "Ensure the command is correctly formatted to delete resources and prefixed with 'aws'.")

    def _run(
            self,
            aws_cli_command: str,
            run_manager: Optional[CallbackManagerForToolRun] = None,
            **kwargs: Any,
    ) -> Any:
        if not aws_cli_command.startswith("aws "):
            aws_cli_command = f"aws {aws_cli_command}"
        return super()._run(aws_cli_command, run_manager, **kwargs)
