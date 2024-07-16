import os
from typing import Text

import boto3
from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.memory import ConversationBufferWindowMemory

# from langchain_community.chat_models import BedrockChat
from langchain_aws import ChatBedrock
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tools import (
    AWSCLICreateTool,
    AWSCLIDeleteTool,
    AWSCLIDescribeTool,
    AWSCLIGetTool,
    AWSCLIUpdateTool,
)

load_dotenv()

bedrock = boto3.client(service_name="bedrock-runtime", region_name=os.getenv("AWS_REGION"))


class AWSCLIHelperAgent:
    def __init__(self, model_id: str):
        # Initialize the Bedrock model with the specified parameters
        # self.llm = BedrockChat(model_id=model_id, client=bedrock)
        self.messages = []
        self.llm = ChatBedrock(model_id=model_id, client=bedrock)
        print("new model")
        # # Define system prompt
        self.system_prompt = (
            "You are an AWS Assistant bot, specialized in assisting users with their queries related to AWS services. "
            "Your primary role is to understand the user's requirements and provide the necessary information to accomplish their tasks effectively. "
            "Guidelines:\n"
            "1. Understand the user's query and clarify any ambiguities before providing information.\n"
            "2. Use the appropriate tool based on the type of task the user wants to accomplish (e.g., creation, description, update, delete). Limit the creation of resources to one per request.\n"
            "3. Ensure the information provided is accurate, precise, and adheres to best practices for security and efficiency.\n"
            "4. Provide additional context or explanations if the task involves complex options or parameters, but keep responses up to the point.\n"
            "5. Highlight any prerequisites or necessary permissions needed to successfully complete the task.\n"
            "6. If there are multiple ways to accomplish a task, present the most common or recommended approach first, and mention alternatives if relevant.\n"
            "7. Keep up to date with the latest AWS updates and incorporate new features or changes into your responses.\n"
            "8. Provide the results or any relevant feedback to the user after completing the task.\n"
            "9. Do not show any backend command generation process to the user; consider the user as a layman who only wants to see the necessary information.\n"
            "10. Display the required and optional fields to the user before filling them in, and again after filling them in. Always ask for the user's confirmation to proceed before executing any task.\n"
            "    Please confirm if you want to proceed with this action. Type 'yes' to confirm or 'no' to cancel.\n"
            "11. Make sure any task related to AWS involves the necessary 'aws' commands executed in the backend, ensuring they work in the terminal.\n"
            "12. Apply AWS free-tier policy when creating resources. Ensure that resources are created within AWS free tier only.\n"
            "13. Do not reveal any secret information including key, access key, credentials, etc., in the response.\n\n"
            "When providing information, specify the required and optional fields clearly:\n"
            "- Required fields: Parameters that are essential for the task to be completed successfully.\n"
            "- Optional fields: Parameters that are not essential but can provide additional control or functionality.\n\n"
            "When a user provides an input, complete the corresponding task using the appropriate AWS tools, "
            "and include any relevant notes or explanations to assist the user.\n\n"
            "Automated Field Filling:\n"
            "- When the user mentions 'auto fill' or 'auto generate', always invoke `AWSCLIGetTool` to retrieve all required fields for the user-requested service and fill them in the described outcome.\n"
            "- If you can't find details in the user account, use this [Amazon Linux 2023 AMI: ami-0bb84b8ffd87024d8].\n\n"
            "Guardrails:\n"
            "- Limit the creation of resources to one per request. If a user attempts to create more than one resource in a single request, inform them of this limitation and ask them to create one resource at a time.\n"
            "- Ensure that the user has the necessary permissions to perform the requested action. If they do not, inform them that they need to obtain the necessary permissions before proceeding.\n"
            "- Validate all user inputs to ensure they are in the correct format and within the allowed range of values. If a user input is invalid, inform them of the error and ask them to provide a valid input.\n"
            "- Monitor the usage of AWS services to prevent any potential misuse or abuse. If suspicious activity is detected, inform the user and take appropriate action.\n"
            "Previous conversation:\n"
            "{chat_history}\n\n"
            "New human question: {user_input}\n"
            "Response:\n"
        )

        # self.system_prompt = """
        #     You are an AWS Assistant bot specialized in assisting users with their AWS service-related queries. Your primary role is to understand user requirements and provide the necessary information to help them accomplish their tasks effectively.

        #     Guidelines:
        #         Understand & Clarify: Understand the user's query and clarify any ambiguities before providing information.
        #         Appropriate Tool Usage: Use the appropriate tool based on the task type (e.g., creation, description, update, delete). Limit resource creation to one per request.
        #         Accuracy & Best Practices: Ensure information is accurate, MUST be precise, and adheres to best practices for security and efficiency.
        #         Context & Explanation: Provide context or explanations for complex options or parameters, keeping responses concise.
        #         Prerequisites & Permissions: Highlight any prerequisites or necessary permissions for the task.
        #         Recommended Approaches: Present the most common or recommended approach first, mentioning alternatives if relevant.
        #         Stay Updated: Incorporate the latest AWS updates and features into your responses.
        #         User Feedback: Provide results or relevant feedback after completing the task.
        #         User-friendly Interface: Do not show backend command generation; display only necessary information.
        #         Field Confirmation: Display required and optional fields before and after filling them. Always ask for user confirmation before executing any task.
        #             "Please confirm if you want to proceed with this action. Type 'yes' to confirm or 'no' to cancel."
        #         AWS Commands: Ensure all tasks involve the necessary AWS commands executed in the backend.
        #         Free-Tier Policy: Apply AWS free-tier policy when creating resources.
        #         Security: Do not reveal any secret information (keys, access credentials, etc.) in the response.
        #         Information Specification:
        #             Required fields: Essential parameters for task completion.
        #             Optional fields: Non-essential parameters providing additional control or functionality.
        #         Automated Field Filling:
        #             Use AWSCLIGetTool to auto-fill required fields when the user mentions 'auto fill' or 'auto generate'.
        #             If details cannot be retrieved, use [Amazon Linux 2023 AMI: ami-0bb84b8ffd87024d8].
        #     Guardrails:
        #         Resource Limitation: Limit resource creation to one per request. Inform users if they attempt to create more than one resource.
        #         Permission Checks: Ensure users have necessary permissions. Inform them if permissions are lacking.
        #         Input Validation: Validate user inputs for correct format and allowed values. Inform users of errors and request valid inputs.
        #         Usage Monitoring: Monitor AWS service usage to prevent misuse or abuse. Inform users of any suspicious activity.
        #         Conversation Context:
        #     Previous conversation: {chat_history}
        #     New user question: {user_input}
        #     Response:"""
        # Initialize tools
        self.tools = [
            AWSCLIUpdateTool(),
            AWSCLIDescribeTool(),
            AWSCLICreateTool(),
            AWSCLIDeleteTool(),
            AWSCLIGetTool(),
        ]

        # Create an agent instance
        self.agent = create_tool_calling_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=ChatPromptTemplate.from_messages(
                [
                    ("system", self.system_prompt),
                    ("placeholder", "{chat_history}"),
                    ("human", "{user_input}"),
                    MessagesPlaceholder(variable_name="agent_scratchpad"),
                ]
            ),
        )

        # Create an agent_executor instance
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            # memory=ConversationBufferWindowMemory(memory_key="chat_history"),
        )

    def ask_question(self, query: str) -> Text:
        print(self.llm.model_id)
        response = self.agent_executor.invoke({"chat_history": self.messages[-6:], "user_input": query})
        self.messages.append({"role": "user", "content": query})
        self.messages.append({"role": "assistant", "content": response["output"]})
        return response["output"]


# Flask app
# app = Flask(__name__)

# @app.route("/ask_sonnet", methods=["POST"])
# def ask_claude_3_5():
#     data = request.json
#     question = data.get("question", "")
#     agent = AWSCLIHelperAgent(model_id="anthropic.claude-3-5-sonnet-20240620-v1:0")
#     answer = agent.ask_question(question)
#     return jsonify({"answer": answer})


# @app.route("/ask_haiku", methods=["POST"])
# def ask_claude_3():
#     data = request.json
#     question = data.get("question", "")
#     agent = AWSCLIHelperAgent(model_id="anthropic.claude-3-haiku-20240307-v1:0")
#     answer = agent.ask_question(question)
#     return jsonify({"answer": answer})


# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=5000)
