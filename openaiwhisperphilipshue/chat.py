import os
from langchain.tools import BaseTool
from typing import Any, Dict, Union
from langchain_openai import ChatOpenAI
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

system = '''You are a general assistant chatbot. You can help with a variety
of tasks, such as answering questions, providing information,
and helping with tasks.
Use tools that are available to you to help you answer questions
and provide information. You can also ask for help from a human if you need.

Return in the same laguage as input.
'''

default_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        MessagesPlaceholder("chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ]
)


class Chat():
    def __init__(self, name='chat-conversational-react-description',
                 key: Union[str, None] = None,
                 model_name: Union[str, None] = None,
                 temperature: float = 0.0,
                 prompt=None):
        self.name = name
        _openai_api_key = key if key is not None \
            else os.getenv("OPENAI_API_KEY")
        _model_name = model_name if model_name is not None \
            else 'gpt-3.5-turbo-1106'
        _temperature = temperature
        self.llm = ChatOpenAI(
            openai_api_key=_openai_api_key,
            temperature=_temperature,
            model_name=_model_name
        )
        # initialize conversational memory
        self.conversational_memory = ConversationBufferWindowMemory(
            memory_key='chat_history',
            k=5,
            return_messages=True
        )
        if prompt is not None:
            self.prompt = prompt
        else:
            self.prompt = default_prompt

    def initialize_agent(self, tools: list[BaseTool], description: str):
        # initialize agent with tools
        agent = create_openai_tools_agent(self.llm, tools, self.prompt)
        self.agent = AgentExecutor(
            agent=agent,
            tools=tools,
            max_iterations=3,
            handle_parsing_errors=True,
            # verbose=True,
            memory=self.conversational_memory)
        self.tools_description = description

    def run(self, text: str) -> Dict[str, Any]:
        if self.agent is None:
            raise ValueError(
                "Agent not initialized."
                "Please call initialize_agent() method first.")
        if text == "":
            return "Please provide a valid input."

        # Create a dictionary with both input and tools
        inputs = {
            "input": text,
        }
        result = self.agent.invoke(inputs)
        return result

    def __call__(self, text: str) -> str:
        return self.run(text)['output']
