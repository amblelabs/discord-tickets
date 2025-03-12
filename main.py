import typing

from dotenv import load_dotenv
load_dotenv() # load all the variables from the env file

import discord
import os # default module
import github_issues as issues
import tracking
import notification as notifier
import asyncio

bot = discord.Bot()

forum: typing.Optional[discord.ForumChannel] = None
webhook: typing.Optional[discord.Webhook] = None

GUILD_ID = os.getenv("GUILD_ID")

issues_group = bot.create_group("issues", "Manage Github issues")

class IssueView(discord.ui.View):
    def __init__(self, title: str, body: str, ctx : discord.context.ApplicationContext) -> None:
        super().__init__(timeout=10)

        self.title = title
        self.body = body
        self.disabled = False
        self.ctx = ctx

    @discord.ui.select( # the decorator that lets you specify the properties of the select menu
        placeholder = "Issue Type", # the placeholder text that will be displayed if nothing is selected
        min_values = 1, # the minimum number of values that must be selected by the users
        max_values = 1, # the maximum number of values that can be selected by the users
        options = [ # the list of options from which users can choose, a required field
            discord.SelectOption(
                label="Bug",
                description="A bug report!"
            ),
            discord.SelectOption(
                label="Enhancement",
                description="A request for a new feature!"
            )
        ]
    )
    async def select_callback(self, select, interaction: discord.Interaction):
        if self.disabled:
            return

        label = select.values[0].lower()

        created, thread = await create_issue(self.title, self.body, label=[label], blame=interaction.user.name)

        await interaction.respond("Done!", ephemeral=True)
        await self.ctx.respond(content=f"[Created Thread]({thread.jump_url})")
        self.disable_all_items()
        self.disabled = True

    async def on_timeout(self): 
        self.disable_all_items() 
        self.disabled = True
        await self.ctx.respond(content="Issue Creation Timed Out.", ephemeral=True)

class IssueModal(discord.ui.Modal):
    def __init__(self, ctx : discord.context.ApplicationContext, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.ctx = ctx

        self.add_item(discord.ui.InputText(label="Title"))
        self.add_item(discord.ui.InputText(label="Body", style=discord.InputTextStyle.long))

    async def callback(self, interaction: discord.Interaction):
        title = self.children[0].value
        body = self.children[1].value
        await interaction.respond(f"## Label the Issue", view=IssueView(title, body, self.ctx), ephemeral=True)

@bot.event
async def on_ready():
    print(f"{bot.user} is ready!")

    await setup_forum()

    async def send_reminders():
        while True:
            print("Sending reminders...")
            await notifier.remind_all_issues(bot, issues.OWNER, issues.REPO)
            await asyncio.sleep(300)

    async def update_issues():
        while True:
            print("Updating issues...")
            await track_all_issues()
            await asyncio.sleep(300)

    bot.loop.create_task(update_issues())
    bot.loop.create_task(send_reminders())

@bot.event
async def on_raw_thread_update(payload: discord.RawThreadUpdateEvent):
    # Check if thread is archived, if so close the issue and stop tracking it
    thread = None

    async for archived in forum.archived_threads():
        if archived.id == payload.thread_id:
            thread = archived
            break

    if thread: # must be archived then
        issue = tracking.get_issue(thread.id)

        if issue:
            issues.close_issue(issues.OWNER, issues.REPO, issue.get("issue_number"))
            tracking.untrack_issue(issues.OWNER, issues.REPO, issue.get("issue_number"))
            print("Untracked & Closed issue", issue.get("issue_number"))
            await thread.send("Issue closed, will no longer be tracked (permanently).")
            await thread.edit(locked=True, archived=True)

async def track_all_issues():
    """
        Track all the issues in the GitHub repository
    """

    gh_issues = issues.get_issues(issues.OWNER, issues.REPO)

    for issue in gh_issues:
        # Check if the issue is already being tracked
        if tracking.get_thread_id(issues.OWNER, issues.REPO, issue.get("number")) != -1:
            continue

        user = issue.get("user")
        login = user.get("login")
        avatar = user.get("avatar_url")

        body = issue.get("body") or "No Description"

        # ensure < 2000 characters
        if len(body) > 2000:
            body = body[:2000]

        label = issue.get("labls").get("name")

        thread: discord.Thread = await forum.create_thread(name=issue.get("title"), content="# Created By: `{login}`", applied_tags=get_tags(forum, label))
        tracking.track_issue(issues.OWNER, issues.REPO, issue.get("number"), thread.id)

        await webhook.send(content=body, username=login, avatar_url=avatar)

# TODO - Implement the on_message event, not sure if i liked it so i commented it out
# @bot.event
# async def on_message(message: discord.Message):
#     if (message.author == bot.user):
#         return

#     # Check if the message is in a thread
#     if isinstance(message.channel, discord.Thread):
#         issue = tracking.get_issue(message.channel.id)
#         if (issue):
#             body = f"# From Discord \n\n **{message.author.name}** says \"{message.content}\""

#             issues.send_comment(issues.OWNER, issues.REPO, issue.get("issue_number"), body)
#             print("Sent comment to issue", issue.get("issue_number"), body)

#             # Validate the issue
#             if (await tracking.validate(issue) == False):
#                 await message.channel.send("Issue has been closed, will no longer be tracked.")
#                 await message.channel.edit(locked=True, archived=True)

async def create_issue(title: str, body: str, label: list[str] = [], blame: str = None) -> tuple[dict, discord.Thread]:
    """
        Create an issue in the GitHub repository and the Discord forum
    """
    body += f"\n\n# Created By: `{blame}`" if blame else ""

    # Create the issue
    created = issues.create_issue(issues.OWNER, issues.REPO, title, body, labels=label)

    # Create the forum message
    thread = await forum.create_thread(name=title, content=f"{body}\n\n[Created Issue]({issues.get_issue_url(created)})", applied_tags=get_tags(forum, label))
    
    # start tracking
    tracking.track_issue(issues.OWNER, issues.REPO, created.get("number"), thread.id)

    return created, thread


@issues_group.command(guild_ids=[GUILD_ID])
async def create(ctx : discord.context.ApplicationContext):
    """
        Create a new issue
    """
    modal = IssueModal(title="Create an Issue", ctx=ctx)
    await ctx.send_modal(modal)


@issues_group.command(guild_ids=[GUILD_ID])
async def comment(ctx: discord.context.ApplicationContext, message: str, issue_number: int = None):
    """
        Comment on an issue
    """
    if issue_number is None:
        # Get the issue number from the thread
        issue = tracking.get_issue(ctx.channel.id)

        if issue:
            issue_number = issue.get("issue_number")
        else:
            await ctx.respond("This is not a tracked issue.", ephemeral=True)
            return
    
    await ctx.defer()

    body = f"# From Discord \n\n **{ctx.author.name}** says \"{message}\""
    issues.send_comment(issues.OWNER, issues.REPO, issue_number, body)
    await ctx.followup.send(f"New Comment:\n **{ctx.author.name}** says \"{message}\"")
    print("Sent comment to issue", issue_number, ctx.author.name, message)


# @issues_group.command(guild_ids=[GUILD_ID])
# @discord.commands.default_permissions(manage_channels=True)
# async def close(ctx: discord.context.ApplicationContext, issue_number: int = None):
#     '''
#         Close an issue
#     '''

#     await ctx.defer()

#     if (issue_number == None):
#         # Get the issue number from the thread
#         issue = tracking.get_issue(ctx.channel.id)
#         if (issue):
#             issue_number = issue.get("issue_number")
#         else:
#             await ctx.send_followup("This is not a tracked issue.", ephemeral=True)
#             return


#     thread_id = tracking.get_thread_id(issues.OWNER, issues.REPO, issue_number)
#     thread = bot.get_channel(thread_id)

#     if (thread):
#         await thread.send("Issue closed, will no longer be tracked.")
#         await thread.edit(locked=True, archived=True)

#     issues.close_issue(issues.OWNER, issues.REPO, issue_number)
#     tracking.untrack_issue(issues.OWNER, issues.REPO, issue_number)

#     issues.send_comment(issues.OWNER, issues.REPO, issue_number, f"Issue closed by {ctx.author.name} from Discord.")
#     print("Untracked & Closed issue", issue_number)
#     await ctx.send_followup("Issue closed!")


def get_tags(forum: discord.ForumChannel, tags: list[str]) -> list[discord.ForumTag]:
    """
        Get a tag from a forum channel
    """
    return [t for t in forum.available_tags if t.name in tags]


async def setup_forum():
    """
        Returns the id of the forum this bot operates in
        Throws an exception if the forum/guild is not found
    """

    # Attempt to find the forum
    channel = None
    guild = bot.get_guild(int(GUILD_ID))

    if not guild:
        raise Exception("Guild not found")

    for c in guild.forum_channels:
        if c.name == "github-issues":
            channel = c
            break

    # Try to create the forum
    if not channel:
        channel = await guild.create_forum_channel("github-issues")

    if not channel or not isinstance(channel, discord.ForumChannel):
        raise Exception("FORUM_ID should point to a forum channel!")

    global forum
    forum = channel

    global webhook
    webhooks = await forum.webhooks()

    if not webhooks:
        webhook = await forum.create_webhook(name="Github Issues")
    else:
        webhook = (await forum.webhooks())[-1]

bot.run(os.getenv("DISCORD_TOKEN")) # run the bot with the token