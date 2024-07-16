import os
from typing import Text, Optional

from dotenv import load_dotenv
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.memory import ConversationBufferWindowMemory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from prompts.aws_agent_prompt import prompt_template
from tools import AWSCLICreateTool, AWSCLIDeleteTool, AWSCLIDescribeTool, AWSCLIUpdateTool, AWSCLIGetTool

load_dotenv()


class AWSCLIHelperAgent:
    def __init__(self, temperature: float = 0, model_name: Text = "gpt-4o",
                 openai_api_key: Optional[Text] = None):
        # Load the API key from environment if not provided
        if openai_api_key is None:
            openai_api_key = os.getenv("OPENAI_API_KEY")

        # Initialize the ChatOpenAI model with the specified parameters
        self.llm = ChatOpenAI(model=model_name, temperature=temperature, openai_api_key=openai_api_key, max_tokens=225)

        # Initialize tools
        self.tools = [AWSCLIUpdateTool(), AWSCLIDescribeTool(), AWSCLICreateTool(), AWSCLIDeleteTool(), AWSCLIGetTool()]

        # Define system prompt
        self.system_prompt = prompt_template

        # Initialize memory for the conversation
        self.memory = ConversationBufferWindowMemory(
            memory_key="chat_history"
        )

        # Create an agent instance
        self.agent = create_tool_calling_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=ChatPromptTemplate.from_messages([
                ("system", self.system_prompt),
                ("human", "{user_input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ])
        )

        # Create an agent_executor instance
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            memory=self.memory
        )

    def ask_question(self, query: str) -> Text:
        response = self.agent_executor.invoke({
            "user_input": query
        })
        return response['output']
