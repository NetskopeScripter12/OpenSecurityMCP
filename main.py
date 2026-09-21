import argparse
import asyncio
from dotenv import load_dotenv
from core.cli import CliApp
from core.runtime import ROOT, open_chat


async def main():
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="SecurityMCP with Ollama")
    parser.add_argument("server_scripts", nargs="*", help="Trusted local MCP Python scripts")
    parser.add_argument("--allow-edits", action="store_true", help="Enable mutating MCP tools")
    args = parser.parse_args()
    async with open_chat(args.allow_edits, args.server_scripts) as chat:
        cli = CliApp(chat)
        await cli.initialize()
        await cli.run()


if __name__ == "__main__":
    asyncio.run(main())
