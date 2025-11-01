import asyncio
import sys

sys.path.append(sys.path[0].split("client")[0])
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma

from agent.root_agent import root_agent

OLLAMA_EMBEDDING_MODEL = "nomic-embed-text"
OLLAMA_BASE_URL = "http://localhost:11434"
CHROMA_DB_PATH = "../chroma_db"


async def main():
    embeddings = OllamaEmbeddings(
        model=OLLAMA_EMBEDDING_MODEL, base_url=OLLAMA_BASE_URL
    )
    vectorstore = Chroma(
        persist_directory=CHROMA_DB_PATH, embedding_function=embeddings
    )
    r = root_agent(vectorstore)
    while True:
        user_input = input("Enter your command: ")
        result = r.run(user_input)
        print(result)


asyncio.run(main())
