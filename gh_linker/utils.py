# MIT License

# Copyright (c) 2018 Python Discord

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# These are various utils from the python-discord bots.
# Source repos:
#  - https://github.com/python-discord/sir-lancebot
#  - https://github.com/python-discord/bot
#  - https://github.com/python-discord/bot-core

import asyncio
from collections import abc
import contextlib
from functools import partial
import logging
from typing import Sequence
import typing
import discord
from discord.ext.commands import Context
from gh_linker.bot import bot

log = logging.getLogger(__name__)


class Channels:
    bot_commands = "497046178903490560"


class Colours:
    bright_green = 0x01D277
    soft_red = 0xCD6D6D


# I believe these emojis are from a private server.
# Should be accessible on any server by ID, hence this should still work.
class Emojis:
    # These icons are from Github's repo https://github.com/primer/octicons/
    issue_open = "<:IssueOpen:852596024777506817>"
    issue_closed = "<:IssueClosed:927326162861039626>"
    issue_draft = "<:IssueDraft:852596025147523102>"
    pull_request_open = "<:PROpen:852596471505223781>"
    pull_request_closed = "<:PRClosed:852596024732286976>"
    pull_request_draft = "<:PRDraft:852596025045680218>"
    pull_request_merged = "<:PRMerged:852596100301193227>"


async def invoke_help_command(ctx: Context) -> None:
    """Invoke the help command or default help command if help extensions is not loaded."""
    if "bot.exts.core.help" in ctx.bot.extensions:
        help_command = ctx.bot.get_command("help")
        await ctx.invoke(help_command, ctx.command.qualified_name)
        return
    await ctx.send_help(ctx.command)


TASK_RETURN = typing.TypeVar("TASK_RETURN")


def create_task(
    coro: abc.Coroutine[typing.Any, typing.Any, TASK_RETURN],
    *,
    suppressed_exceptions: tuple[type[Exception]] = (),
    event_loop: typing.Optional[asyncio.AbstractEventLoop] = None,
    **kwargs,
) -> asyncio.Task[TASK_RETURN]:
    """
    Wrapper for creating an :obj:`asyncio.Task` which logs exceptions raised in the task.
    If the ``event_loop`` kwarg is provided, the task is created from that event loop,
    otherwise the running loop is used.
    Args:
        coro: The function to call.
        suppressed_exceptions: Exceptions to be handled by the task.
        event_loop (:obj:`asyncio.AbstractEventLoop`): The loop to create the task from.
        kwargs: Passed to :py:func:`asyncio.create_task`.
    Returns:
        asyncio.Task: The wrapped task.
    """
    if event_loop is not None:
        task = event_loop.create_task(coro, **kwargs)
    else:
        task = asyncio.create_task(coro, **kwargs)
    task.add_done_callback(
        partial(_log_task_exception, suppressed_exceptions=suppressed_exceptions)
    )
    return task


def _log_task_exception(
    task: asyncio.Task, *, suppressed_exceptions: tuple[type[Exception]]
) -> None:
    """Retrieve and log the exception raised in ``task`` if one exists."""
    with contextlib.suppress(asyncio.CancelledError):
        exception = task.exception()
        # Log the exception if one exists.
        if exception and not isinstance(exception, suppressed_exceptions):
            log = logging.getLogger(__name__)
            log.error(
                f"Error in task {task.get_name()} {id(task)}!", exc_info=exception
            )


def reaction_check(
    reaction: discord.Reaction,
    user: discord.abc.User,
    *,
    message_id: int,
    allowed_emoji: Sequence[str],
    allowed_users: Sequence[int],
) -> bool:
    """
    Check if a reaction's emoji and author are allowed and the message is `message_id`.
    If the user is not allowed, remove the reaction. Ignore reactions made by the bot.
    If `allow_mods` is True, allow users with moderator roles even if they're not in `allowed_users`.
    """
    right_reaction = (
        user != bot.user
        and reaction.message.id == message_id
        and str(reaction.emoji) in allowed_emoji
    )
    if not right_reaction:
        return False

    if user.id in allowed_users:
        log.debug(f"Allowed reaction {reaction} by {user} on {reaction.message.id}.")
        return True
    else:
        log.debug(
            f"Removing reaction {reaction} by {user} on {reaction.message.id}:"
            " disallowed user."
        )
        create_task(
            reaction.message.remove_reaction(reaction.emoji, user),
            suppressed_exceptions=(discord.HTTPException,),
            name=f"remove_reaction-{reaction}-{reaction.message.id}-{user}",
        )
        return False


async def wait_for_deletion(
    message: discord.Message,
    user_ids: Sequence[int],
    deletion_emojis: Sequence[str] = ("<:trashcan:637136429717389331>",),
    timeout: float = 60 * 5,
    attach_emojis: bool = True,
) -> None:
    """
    Wait for any of `user_ids` to react with one of the `deletion_emojis` within `timeout` seconds to delete `message`.
    If `timeout` expires then reactions are cleared to indicate the option to delete has expired.
    An `attach_emojis` bool may be specified to determine whether to attach the given
    `deletion_emojis` to the message in the given `context`.
    An `allow_mods` bool may also be specified to allow anyone with a role in `MODERATION_ROLES` to delete
    the message.
    """
    if message.guild is None:
        raise ValueError("Message must be sent on a guild")

    if attach_emojis:
        for emoji in deletion_emojis:
            try:
                await message.add_reaction(emoji)
            except discord.NotFound:
                log.debug(
                    f"Aborting wait_for_deletion: message {message.id} deleted"
                    " prematurely."
                )
                return

    check = partial(
        reaction_check,
        message_id=message.id,
        allowed_emoji=deletion_emojis,
        allowed_users=user_ids,
    )

    try:
        try:
            await bot.wait_for("reaction_add", check=check, timeout=timeout)
        except asyncio.TimeoutError:
            await message.clear_reactions()
        else:
            await message.delete()
    except discord.NotFound:
        log.debug(f"wait_for_deletion: message {message.id} deleted prematurely.")
