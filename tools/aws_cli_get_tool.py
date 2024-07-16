from typing import Any, Type, Optional

from langchain_core.callbacks import CallbackManagerForToolRun
from pydantic import BaseModel, Field

from tools.base_aws_cli_tool import AWSCLITool


class AWSCLIGetToolParams(BaseModel):
    aws_cli_command: str = Field(..., description="AWS CLI command to retrieve data, e.g., 'ec2 describe-instances'")
    additional_args: Optional[str] = Field(None, description="Additional arguments to pass to the AWS CLI command")


class AWSCLIGetTool(AWSCLITool):
    name: str = "aws_cli_get_tool"
    description: str = ("This tool retrieves data from your AWS account using AWS CLI commands. "
                        "Use the format `aws <command> <subcommand> [parameters]` to specify the data you want to retrieve.")
    args_schema: Type[AWSCLIGetToolParams] = AWSCLIGetToolParams

    def _run(
            self,
            aws_cli_command: str,
            additional_args: Optional[str] = None,
            run_manager: Optional[CallbackManagerForToolRun] = None,
            **kwargs: Any,
    ) -> Any:
        if not aws_cli_command.startswith("aws "):
            aws_cli_command = f"aws {aws_cli_command}"
        if additional_args:
            aws_cli_command += f" {additional_args}"
        return super()._run(aws_cli_command, run_manager, **kwargs)
