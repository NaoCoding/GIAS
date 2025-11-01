import os
import sys
from dataclasses import dataclass

from dotenv import load_dotenv
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openrouter import OpenRouterProvider

from agent.prompt.root_agent import system_prompt
from tool import github_tool

load_dotenv()


@dataclass
class run_deps:
    repo: str


class root_agent:

    def __init__(self):
        self._model = OpenAIChatModel(
            os.getenv("MODEL_NAME"),
            provider=OpenRouterProvider(api_key=os.getenv("OPEN_ROUTER_API_KEY")),
        )
        self._agent = Agent(
            model=self._model,
            system_prompt=system_prompt,
            deps_type=run_deps,
        )

        @self._agent.tool
        def get_repo(ctx: RunContext[run_deps]):
            """Get a GitHub repository by its name."""
            return github_tool.get_repo(ctx.deps.repo)

    async def run(self, user_input: str):
        result = await self._agent.run(user_input, deps=run_deps("plait-board/drawnix"))
        return result
