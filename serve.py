import os
import subprocess
import time
import boto3
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import traceback

from agents.aws_agent import AWSCLIHelperAgent
from agents.aws_claude_agent import AWSCLIHelperAgent as AWSCLIHelperAgentClaude

STS_TOKEN_TIME_LIMIT = int(os.environ.get("STS_TOKEN_TIME_LIMIT") or 3600)
print(f"STS_TOKEN_TIME_LIMIT: {STS_TOKEN_TIME_LIMIT}")

aws_agent = AWSCLIHelperAgent()
aws_claude_sonnet_agent = AWSCLIHelperAgentClaude(
    model_id="anthropic.claude-3-5-sonnet-20240620-v1:0"
)
aws_claude_haiku_agent = AWSCLIHelperAgentClaude(
    model_id="anthropic.claude-3-haiku-20240307-v1:0"
)
app = FastAPI()

credentials = {}

origins = ["http://localhost:5173", "https://hiaido.com"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_credentials_from_db(id: str, owner: str):
    """
    Retrieves credentials associated with the provided email from DynamoDB.
    """
    # id is just unique identifier for the user
    # can be email for member accounts or uuid for connected accounts
    session = boto3.Session(
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        region_name=os.environ.get("AWS_REGION"),
    )
    dynamodb = session.resource("dynamodb")
    if len(id) == 36:
        table = dynamodb.Table("connected-aws-accounts")
        response = table.get_item(Key={"externalId": id, "owner": owner})
        if "Item" in response:
            sts_client = boto3.client("sts")
            assumed_role = sts_client.assume_role(
                RoleArn=response["Item"]["role_arn"],
                RoleSessionName="AssumeroleSession",
                DurationSeconds=STS_TOKEN_TIME_LIMIT,
                ExternalId=id,
            )
            assumed_role["Credentials"]["timestamp"] = time.time()
            return assumed_role["Credentials"]
    else:
        table = dynamodb.Table("account-factory-test")
        response = table.get_item(Key={"email": id, "owner": owner})
        if "Item" in response:
            sts_client = boto3.client("sts")
            assumed_role = sts_client.assume_role(
                RoleArn=response["Item"]["role_arn"],
                RoleSessionName="AssumeroleSession",
                DurationSeconds=STS_TOKEN_TIME_LIMIT,
            )
            assumed_role["Credentials"]["timestamp"] = time.time()
            return assumed_role["Credentials"]
    return None


def configure_aws_cli(
    aws_access_key_id, aws_secret_access_key, session_token, region, profile
):
    subprocess.run(
        [
            "aws",
            "configure",
            "set",
            "aws_access_key_id",
            aws_access_key_id,
            "--profile",
            profile,
        ],
        check=True,
    )
    subprocess.run(
        [
            "aws",
            "configure",
            "set",
            "aws_secret_access_key",
            aws_secret_access_key,
            "--profile",
            profile,
        ],
        check=True,
    )
    subprocess.run(
        [
            "aws",
            "configure",
            "set",
            "aws_session_token",
            session_token,
            "--profile",
            profile,
        ],
        check=True,
    )
    subprocess.run(
        ["aws", "configure", "set", "region", region, "--profile", profile], check=True
    )

    subprocess.run(["aws", "configure", "list", "--profile", profile], check=True)


class Query(BaseModel):
    query: str


@app.get(
    "/", summary="Root path", description="Root path to check if service is running"
)
async def root(request: Request):
    """
    Root path
    """
    return JSONResponse({"running": "yes"})


@app.get(
    "/health",
    summary="Health check path",
    description="Path used by orcestration services to check container health.",
)
async def health(request: Request):
    """
    Path used by orcestration services to check container health.
    """
    return JSONResponse({"healthy": True})


def credentials_expired(email):
    if not credentials.get(email):
        return True
    else:
        current_timestamp = time.time()
        # print(
        #     "HERE: ",
        #     current_timestamp
        #     < credentials.get(email)["timestamp"] + STS_TOKEN_TIME_LIMIT - 800,
        # )
        # print(
        #     f"Time left: {credentials.get(email)['timestamp'] + STS_TOKEN_TIME_LIMIT -800- time.time()}"
        # )
        if (
            current_timestamp
            < credentials.get(email)["timestamp"] + STS_TOKEN_TIME_LIMIT - 180
        ):
            return False
        else:
            return True


# TODO authenticate user
@app.post(
    "/configure-cli",
    summary="Configure CLI",
    description="Configures the CLI with the credentials associated with the provided email.",
)
async def configure_cli(request: Request):
    """
    Configures the CLI with credentials associated with the provided email.
    """
    try:
        data = await request.json()
        email = data.get("email")
        owner = data.get("owner")

        global credentials
        # print(credentials)

        if not email:
            raise HTTPException(status_code=400, detail="email parameter is required")
        if not owner:
            raise HTTPException(status_code=400, detail="owner parameter is required")
        if credentials.get(email) and not credentials_expired(email):
            return JSONResponse({"status": "CLI_ALREADY_CONFIGURED"})
        credentials[email] = get_credentials_from_db(email, owner)
        if credentials[email] is None:
            raise HTTPException(status_code=400, detail="Failed to generate session.")
        if credentials.get(email):
            access_key_id = credentials[email]["AccessKeyId"]
            secret_access_key = credentials[email]["SecretAccessKey"]
            session_token = credentials[email]["SessionToken"]
            configure_aws_cli(
                access_key_id,
                secret_access_key,
                session_token,
                "us-east-1",
                email,
            )
            return JSONResponse({"status": "CLI configured successfully"})
    except Exception as e:
        print(traceback.print_exc())
        raise HTTPException(status_code=500, detail=str(e))


async def check_cli_configured(request: Request):
    """
    Checks if CLI is configured before accessing certain endpoints.
    """
    data = await request.json()
    email = data.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="User email required.")
    if not credentials.get(email):
        raise HTTPException(
            status_code=400,
            detail="CLI not configured. Please configure the CLI before accessing this endpoint.",
        )
    expired = credentials_expired(email)
    if expired:
        print("CREDENTIALS EXPIRED")
        raise HTTPException(
            status_code=400,
            detail="Session expired. CLI not configured. Please configure the CLI before accessing this endpoint.",
        )
    # print(
    #     f"Time left: {credentials.get(email)['timestamp'] + STS_TOKEN_TIME_LIMIT -800- time.time()}"
    # )
    return True


@app.post(
    "/get-response/claude-sonnet",
    summary="Get response from Claude Sonnet model",
    description="Processes a user query and returns a response from the Claude Sonnet model.",
    dependencies=[Depends(check_cli_configured)],
)
async def get_sonnet_response(request: Request):
    """
    Processes a user query and returns a response from the Claude Sonnet model.
    """
    try:
        data = await request.json()
        user_question = data.get("query")
        user_email = data.get("email")

        if not user_question:
            raise HTTPException(status_code=400, detail="Query parameter is required")
        if not user_email:
            raise HTTPException(status_code=400, detail="User email is required")

        # TODO IMPORTANT!!!: use some other method to set current profile
        os.environ["CURRENT_PROFILE"] = user_email
        response = aws_claude_sonnet_agent.ask_question(user_question)
        return JSONResponse({"response": response})

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/get-response/claude-haiku",
    summary="Get response from Claude Haiku model",
    description="Processes a user query and returns a response from the Claude Haiku model.",
    dependencies=[Depends(check_cli_configured)],
)
async def get_sonnet_response(request: Request):
    """
    Processes a user query and returns a response from the Claude Haiku model.
    """
    try:
        data = await request.json()
        user_question = data.get("query")
        user_email = data.get("email")

        if not user_question:
            raise HTTPException(status_code=400, detail="Query parameter is required")
        if not user_email:
            raise HTTPException(status_code=400, detail="User email is required")

        # TODO IMPORTANT!!!: use some other method to set current profile
        os.environ["CURRENT_PROFILE"] = user_email
        response = aws_claude_haiku_agent.ask_question(user_question)
        return JSONResponse({"response": response})

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# TODO authenticate user
@app.post(
    "/get-response",
    summary="Get Response",
    description="Processes a user query and returns a response from the AWS Agent.",
    dependencies=[Depends(check_cli_configured)],
)
async def get_response(request: Request):
    """
    Processes a user query and returns a response from the AWS Agent.
    """
    try:
        data = await request.json()
        user_question = data.get("query")
        user_email = data.get("email")
        if not user_question:
            raise HTTPException(status_code=400, detail="Query parameter is required")
        if not user_email:
            raise HTTPException(status_code=400, detail="User email is required")

        # TODO IMPORTANT!!!: use some other method to set current profile
        os.environ["CURRENT_PROFILE"] = user_email
        response = aws_agent.ask_question(user_question)
        return JSONResponse({"response": response})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("serve:app", host="0.0.0.0", port=8000)
