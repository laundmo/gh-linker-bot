from gh_linker.bot import bot

from dotenv import load_dotenv
import os
load_dotenv()  

extensions = [
    "bot.cogs.info",
    "bot.cogs.code_snippets"
]

for ext in extensions:
    bot.load_extension(ext)

token = os.getenv("BOT_TOKEN")
if token:
    bot.run()