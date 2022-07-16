from contextlib import suppress
from aiohttp import ClientSession
from discord.ext import commands
from discord.ext.commands import Cog
from discord import Forbidden, Thread


class Bot(commands.Bot):
    """
    Base bot instance.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.http_session = ClientSession()

    @Cog.listener()
    async def on_thread_join(self, thread: Thread) -> None:
        """
        Try to join newly created threads.
        Despite the event name being misleading, this is dispatched when new threads are created.
        We want our bots to automatically join threads in order to answer commands using their prefixes.
        """
        if thread.me:
            # Already in this thread, return early
            return

        with suppress(Forbidden):
            await thread.join()


bot = Bot(command_prefix="?")
