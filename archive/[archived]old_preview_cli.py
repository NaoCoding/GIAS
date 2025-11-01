import asyncio
import sys

sys.path.append(sys.path[0].split("client")[0])
from agent.root_agent import root_agent


async def main():
    while True:
        user_input = input("Enter your command: ")
        result = await root_agent().run(user_input)
        print(result.output)


asyncio.run(main())
