import os
import typing

import aiohttp
import discord
import tracking
import github_issues as github
import asyncio

WEBHOOK_URL = os.getenv("WEBHOOK")


async def message(bot: discord.Client, channel_id: int, message: str) -> bool:
    """
    Remind a channel with a message
    Returns false in erroneous cases, true otherwise
    """

    channel = bot.get_channel(channel_id)

    if not channel:
        return False

    try:
        async with aiohttp.ClientSession() as session:
            await channel.send(message)
        return True
    except discord.Forbidden:
        return False


async def remind_issue(bot: discord.Client, owner: str, repo: str, issue_number: int) -> bool:
    """
    Remind a channel with the issue
    Returns false in erroneous cases, true otherwise
    """

    thread_id = tracking.get_thread_id(owner, repo, issue_number)

    if not thread_id:
        return False

    gh_issue = github.get_issue(owner, repo, issue_number)

    if not gh_issue:
        return False

    msg = f"Reminder: Issue {issue_number} in {owner}/{repo} is still open. {github.get_issue_url(gh_issue)}"
    return await message(bot, thread_id, msg)


async def remind_all_issues(bot: discord.Client, owner: str, repo: str) -> bool:
    """
    Remind a channel with all the issues
    Returns false in erroneous cases, true otherwise
    """

    issues = tracking.get_tracked_issues(owner, repo)
    if not issues:
        return False

    for issue in issues:
        if not await remind_issue(bot, owner, repo, issue.get("issue_number")):
            return False

