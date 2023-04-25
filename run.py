from langchain.agents import Tool
from langchain.llms import OpenAI
from langchain import LLMChain
from functools import partial
from langchain.agents import ZeroShotAgent, Tool, AgentExecutor
from tools.google_services import GoogleServices
from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    AIMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
import os

os.environ["OPENAI_API_KEY"] = ''


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

USER_EMAIL = "emily.jarvis.assistant@gmail.com"
USER_NAME = "Emily Paris"
ASSISTANT_EMAIL = "emily.jarvis.assistant@gmail.com"
ASSISTANT_NAME = "Jarvis"
user_google_services = GoogleServices(email=USER_EMAIL, credentials_path='tools/emily_gmail_cred.json')
assistant_google_services = GoogleServices(email=ASSISTANT_EMAIL, credentials_path='tools/emily_gmail_cred.json')

PREFIX = f"""You are going to manage user({USER_NAME}, {USER_EMAIL})'s calendar and email based on natural language instructions.
Please coordinate with everyone over emails based on user's request. 
You need to first check the user's calendar and then determine the available time slots to provide.
In the message, please propose some time ranges for the recipients to choose from if no time specified by the user.
You must send out confirmation emails to all attendees after sending the calendar invitation.
You have access to the following tools:"""


FORMAT_INSTRUCTIONS = """Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}], do not put in arguments in action name
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question"""


list_events_tool = Tool(
    name="list_events",
    description=f"This tool would allow you to retrieve all the events scheduled for user {USER_EMAIL} in given dates.\n"
    """The input to this tool is the dates we would like to retrieve events for. Each date must be of format "YYYY-MM-DD" and different dates can be put together separated by comma.\n"""
    """For example, if I want to retrieve events for three dates: 04/24/2023, 04/26/2023, and 04/27/2023, the input format is "2023-04-24,2023-04-26,2023-04-27".""",
    func=user_google_services.list_events,
)

create_events_tool = Tool(
    name="create_events",
    description=f"This tool would allow you to send calendar invitation for the user {USER_NAME} ({USER_EMAIL}) to other recipients.\n"
    """The input to this tool should be a json dictionary with all property names enclosed in double quotes, containing the following five keys: recipients, event_summary, event_description, event_start_time, event_end_time. The recipients should be a list.\n"""
    """The event_start_time and event_end_time should be in the format of "YYYY-MM-DDTHH:MM:SS".""",
    func=user_google_services.create_events,
)

send_email_tool = Tool(
    name="send_email",
    description="This tool would allow you to send an email to given recipients with a given subject and body.\n"
    "The input to this tool should be a json dictionary with all property names enclosed in double quotes, containing the following three keys: recipients, subject, body. The recipients should be a list.\n"
    "Please send an email to each recipient individually when there are multiple recipients.\n"
    "When sending emails, please assume you are the user's assistant, and send emails in the tone of a personal assistant named as Jarvis. And you should claim that your are the user's assistant\n"
    "When applicable, please provide several available time slots for the recipients to choose.\n"
    "Please make the email formal, well-formatted, clear, and easy to read.",
    func=assistant_google_services.send_email,
)

tools = [send_email_tool, list_events_tool, create_events_tool]
prompt = create_prompt(
    tools=tools,
    prefix=PREFIX,
    format_instructions=FORMAT_INSTRUCTIONS,
)

llm_chain = LLMChain(llm=OpenAI(model_name='gpt-3.5-turbo', temperature=0), prompt=prompt)

agent = ZeroShotAgent(llm_chain=llm_chain, allowed_tools=[tool.name for tool in tools])
agent_executor = AgentExecutor.from_agent_and_tools(
    agent=agent, tools=tools, verbose=True
)

agent_executor.run(
    "Emily: schedule a meeting with jindi930617@gmail.com for a hour next Monday. (Today's Date is 04/24/2023, Monday.)\n\n"
    "Assistant Jarvis: Dear Jindi,\n\nI am Emily's assistant, Jarvis. Emily is available for a meeting with you next Monday. Please let us know your preferred time slot between 10am-12pm or 2pm-4pm. If these time slots do not work for you, please suggest an alternative time.\n\nBest regards,\nJarvis\n\n"
    "Jindi: I prefer the morning time.\n\n"
    "Assistnat Jarvis: Dear Jindi,\n\nI am Emily's assistant, Jarvis. Emily is available for a meeting with you next Monday from 10am-12pm. Please let us know if this time works for you. If not, please suggest an alternative time.\n\nBest regards,\nJarvis\n\n"
    "Jindi: 10am-11am works for me!\n\n"
)
