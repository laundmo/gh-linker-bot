from gh_linker.bot import bot

from dotenv import load_dotenv
import os
import logging

logging.basicConfig(level=logging.INFO)

load_dotenv()

extensions = ["gh_linker.cogs.info", "gh_linker.cogs.code_snippets"]

for ext in extensions:
    bot.load_extension(ext)

token = os.getenv("BOT_TOKEN")
if token:
    bot.run(token)
