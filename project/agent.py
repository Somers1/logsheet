import logging
import os

from django.conf import settings
from django.utils.functional import cached_property
from langchain.agents import create_tool_calling_agent
from langchain_aws import ChatBedrock
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, MessagesPlaceholder, \
    HumanMessagePromptTemplate, PromptTemplate
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langfuse.callback import CallbackHandler
from langgraph.prebuilt import create_agent_executor

logger = logging.getLogger(__name__)


class LLM:
    @staticmethod
    def model_factory(model):
        if model == 'gpt-4o':
            logger.warning(f'Using OpenAI {model} model')
            return ChatOpenAI(model=model, temperature=0, model_kwargs={'seed': 42})
        if 'gpt' in model:
            logger.warning(f'Using AzureOpenAI {model} model')
            return AzureChatOpenAI(deployment_name=model, temperature=0, model_kwargs={'seed': 42})
        if '3-5-sonnet' in model:
            logger.warning(f'Using US WEST 1 {model} model')
            return ChatBedrock(model_id=model, region_name='us-east-1', model_kwargs={"temperature": 0})
        if model in ('gemma2:2b', 'llama3.1'):
            return ChatOllama(base_url='http://192.168.0.184', model=model, model_kwargs={"temperature": 0})
        logger.warning(f'Using AWS bedrock {model} model')
        return ChatBedrock(model_id=model, model_kwargs={"temperature": 0})

    @cached_property
    def strong(self):
        return self.model_factory(os.environ['STRONG_MODEL'])

    @cached_property
    def weak(self):
        return self.model_factory(os.environ['WEAK_MODEL'])

    @cached_property
    def agent_prompt(self):
        prompt = """You are an agent that creates a timesheet based on log event from various sources"""
        return ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate(prompt=PromptTemplate(template=prompt, input_variables=[])),
            MessagesPlaceholder(variable_name='chat_history', optional=True),
            HumanMessagePromptTemplate(prompt=PromptTemplate(input_variables=['input'], template='{input}')),
            MessagesPlaceholder(variable_name='agent_scratchpad')])


langfuse_callback = CallbackHandler(**settings.LANGFUSE_CONFIG)
llm = LLM()


class Agent:
    def __init__(self, input_tools):
        agent_runnable = create_tool_calling_agent(llm.strong, input_tools, llm.agent_prompt)
        self.executor = create_agent_executor(agent_runnable, input_tools)
        self.history = []

    def invoke(self, input_text):
        config = {"recursion_limit": 50, "callbacks": [langfuse_callback]}
        response = self.executor.invoke({"input": input_text, "chat_history": []}, config=config)
        self.history.append(response)
        return response['agent_outcome'].return_values['output']
