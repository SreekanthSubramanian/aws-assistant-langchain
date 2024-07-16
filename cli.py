from agents.aws_agent import AWSCLIHelperAgent

aws_agent = AWSCLIHelperAgent()

while True:
    query = input("enter your query: ")
    if query is None and query == "/bye":
        break
    response = aws_agent.ask_question(query)
    print(response)
