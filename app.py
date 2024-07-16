import chainlit as cl

from agents.aws_agent import AWSCLIHelperAgent

aws_agent = AWSCLIHelperAgent()


@cl.on_chat_start
async def on_chat_start():
    cl.user_session.set("aws_agent", aws_agent)
    await cl.Message(content="Agent Initialized").send()


@cl.on_message
async def main(message: cl.Message):
    agent = cl.user_session.get("aws_agent")
    response = agent.ask_question(message.content)
    await cl.Message(
        content=response,
    ).send()
