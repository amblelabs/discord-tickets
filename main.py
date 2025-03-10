import discord
import os # default module
import github_issues as issues
from dotenv import load_dotenv

load_dotenv() # load all the variables from the env file
bot = discord.Bot()

GUILD_ID = os.getenv('GUILD_ID')
FORUM_ID = -1

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
        if (self.disabled):
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

async def get_forum_id() -> int:
    '''
        Returns the id of the forum this bot operates in
        Throws an exception if the forum/guild is not found
    '''

    # Attempt to find the forum
    global FORUM_ID
    guild = bot.get_guild(int(GUILD_ID))
    if (guild == None):
        raise Exception("Guild not found")
    for channel in guild.forum_channels:
        if (channel.name == "github-issues"):
            FORUM_ID = channel.id
            return FORUM_ID
    
    # Try to create the forum
    forum = await guild.create_forum_channel("github-issues")
    FORUM_ID = forum.id
    return FORUM_ID

async def create_issue(title: str, body: str, label: list[str] = [], blame: str = None) -> tuple[dict, discord.Thread]:
    '''
        Create an issue in the GitHub repository and the Discord forum
    '''

    # Get the forum id
    if (FORUM_ID == -1):
        await get_forum_id()

    body += f"\n\nCreated By: `{blame}`" if blame else ""

    # Create the issue
    created = issues.create_issue(issues.OWNER, issues.REPO, title, body, labels=label)

    # Create the forum message
    forum = bot.get_channel(FORUM_ID)
    thread = await forum.create_thread(name=title, content=f"{body}\n\n[Created Issue]({issues.get_issue_url(created)})", applied_tags=get_tags(forum, label))
    
    return created, thread

def get_tags(forum: discord.ForumChannel, tags: list[str]) -> list[discord.ForumTag]:
    '''
        Get a tag from a forum channel
    '''

    found = []
    for t in forum.available_tags:
        if (t.name in tags):
            found.append(t)
    return found

@issues_group.command(guild_ids=[GUILD_ID])
async def create(ctx : discord.context.ApplicationContext):
    '''
        Create a new issue
    '''
    modal = IssueModal(title="Create an Issue", ctx=ctx)
    await ctx.send_modal(modal)

bot.run(os.getenv('DISCORD_TOKEN')) # run the bot with the token