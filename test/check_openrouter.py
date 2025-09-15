from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openrouter import OpenRouterProvider


from dotenv import load_dotenv
import os

load_dotenv()

model = OpenAIChatModel(
    'deepseek/deepseek-chat-v3.1:free',
    provider=OpenRouterProvider(api_key=os.getenv("OPEN_ROUTER_API_KEY")),
)
agent = Agent(model=model)
result = agent.run_sync('Return me "Done"!')
print(result.output)