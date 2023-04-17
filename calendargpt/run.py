from langchain.agents import Tool
from langchain.llms import OpenAI
from langchain import LLMChain
from functools import partial
from langchain.agents import ZeroShotAgent, Tool, AgentExecutor
from calendargpt.tools.google_calendar import GoogleCalendar
from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    AIMessagePromptTemplate,
    HumanMessagePromptTemplate,
)


def create_prompt(
    tools,
    prefix,
    format_instructions,
):
    tool_strings = "\n".join([f"{tool.name}: {tool.description}" for tool in tools])
    tool_names = ", ".join([tool.name for tool in tools])
    format_instructions = format_instructions.format(tool_names=tool_names)
    template = "\n\n".join([prefix, tool_strings, format_instructions])

    system_message_prompt = SystemMessagePromptTemplate.from_template(template)
    human_message_prompt = HumanMessagePromptTemplate.from_template("{input}")
    ai_message_prompt = AIMessagePromptTemplate.from_template("{agent_scratchpad}")

    return ChatPromptTemplate.from_messages(
        [system_message_prompt, human_message_prompt, ai_message_prompt]
    )


google_calendar = GoogleCalendar()
USER_EMAIL = "shuyangg@gmail.com"
USER_NAME = "Shuyang Gao"

PREFIX = f"""You are going to manage user({USER_NAME}, {USER_EMAIL})'s calendar and email based on natural language instructions.
Please coordinate with everyone over email based on user's request. Today's Date is 2023-04-16, Sunday. 
In the message, please propose some time ranges for the recipients to choose from if no time specified by the user.
You have access to the following tools:"""


FORMAT_INSTRUCTIONS = """Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question"""


list_events_tool = Tool(
    name="list_events",
    description=f"This tool would allow you to retrieve all the events scheduled for user {USER_EMAIL} in a given date, "
    f"The input to this tool must be of format 'YYYY-MM-dd'.",
    func=partial(google_calendar.list_events, USER_EMAIL),
)

send_email_tool = Tool(
    name="send_email",
    description="this tool would allow you to send an email to given recipients with a given subject and message.\n"
    "The input to this tool should be a json dictionary, containing the following three keys:\n"
    "recipients, subject and message.\n"
    "When send emails, please assume you are user's assistant, and send emails in the tone of a personal assistant.",
    func=lambda x: "Email Sent Successfully",
)

tools = [send_email_tool, list_events_tool]
prompt = create_prompt(
    tools=tools,
    prefix=PREFIX,
    format_instructions=FORMAT_INSTRUCTIONS,
)

llm_chain = LLMChain(llm=OpenAI(temperature=0), prompt=prompt)

agent = ZeroShotAgent(llm_chain=llm_chain, allowed_tools=[tool.name for tool in tools])
agent_executor = AgentExecutor.from_agent_and_tools(
    agent=agent, tools=tools, verbose=True
)

agent_executor.run(
    "schedule a meeting with bodiyuan@berkeley.edu and jindi930617@gmail.com for a hour next week."
)
