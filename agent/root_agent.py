import logging
import os

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI

from agent.prompt.root_agent import system_prompt

LLM_MODEL = "arcee-ai/trinity-large-preview:free"
load_dotenv()
openrouter_key = os.environ.get("OPEN_ROUTER_API_KEY")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class root_agent:
    def __init__(self, vectorstore, model_name: str = LLM_MODEL):
        self._llm = ChatOpenAI(
            model=model_name,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0.1,
            api_key=openrouter_key,
        )
        self._retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
        self._prompt = ChatPromptTemplate.from_template(system_prompt)
        self._rag_chain = (
            {"context": self._retriever, "question": RunnablePassthrough()}
            | self._prompt
            | self._llm
            | StrOutputParser()
        )
        logger.info("Root agent initialized successfully.")

    def run(self, user_input: str) -> str:
        result = self._rag_chain.invoke(
            {"context": self._retriever, "question": user_input}
        )
        return result
