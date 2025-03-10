import discord
import os # default module
import github_issues as issues
from dotenv import load_dotenv

load_dotenv() # load all the variables from the env file
bot = discord.Bot()

GUILD_ID = os.getenv('GUILD_ID')
THREAD_ID = -1

issues_group = bot.create_group("issues", "Manage Github issues")

class IssueView(discord.ui.View):
    def __init__(self, title: str, body: str, ctx : discord.context.ApplicationContext) -> None:
        super().__init__()
        self.title = title
        self.body = body
        self.ctx = ctx
        self.disabled = False


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
                label="Feature",
                description="A request for a new feature!"
            )
        ]
    )
    async def select_callback(self, select, interaction: discord.Interaction):
        if (self.disabled):
            return

        label = select.values[0]
        if (label == "Bug"):
            label = "bug"
        if (label == "Feature"):
            label = "enhancement"

        created = issues.create_issue(issues.OWNER, issues.REPO, self.title, self.body, labels=[label])
    
        await interaction.respond("Done!", ephemeral=True)
        await self.ctx.respond(content=f"[Created Issue]({issues.get_issue_url(created)})")
        self.disable_all_items()
        self.disabled = True

    async def on_timeout(self): 
        self.disable_all_items() 
        self.disabled = True
        await self.ctx.respond(content="Issue Creation Timed Out.")

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

async def get_thread_id() -> int:
    '''
        Returns the id of the thread this bot operates in
        Throws an exception if the thread/guild is not found
    '''

    # Attempt to find the thread
    global THREAD_ID
    guild = bot.get_guild(int(GUILD_ID))
    if (guild == None):
        raise Exception("Guild not found")
    for channel in guild.text_channels:
        if (channel.name == "github-issues"):
            THREAD_ID = channel.id
            return THREAD_ID
    
    # Try to create the thread
    thread = await guild.create_forum_channel("github-issues")
    THREAD_ID = thread.id
    return THREAD_ID

@issues_group.command(guild_ids=[GUILD_ID])
async def create(ctx : discord.context.ApplicationContext):
    '''
        Create a new issue
    '''
    modal = IssueModal(title="Create an Issue", ctx=ctx)
    await ctx.send_modal(modal)

bot.run(os.getenv('DISCORD_TOKEN')) # run the bot with the token