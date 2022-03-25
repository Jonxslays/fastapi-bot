from __future__ import annotations

import os
import datetime

import hikari
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import FileResponse
from fastapi.responses import RedirectResponse
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

load_dotenv()

# Create a new FastAPI instance
app = FastAPI()
# Mount the static directory to the app
app.mount("/static", StaticFiles(directory="static"), name="static")
# Create the Hikari GatewayBot instance
bot = hikari.GatewayBot(
    token=os.environ["TOKEN"],
    cache_settings=None,
    intents=hikari.Intents.ALL_UNPRIVILEGED | hikari.Intents.GUILD_MEMBERS,
)

# Grab the guild channel and admin role from the environment
CHANNEL = int(os.environ["CHANNEL"])
ADMIN_ROLE_ID = int(os.environ["ADMIN_ROLE_ID"])

# In the real world these should be stored in a database
pending_requests: list[int] = []
approved_members: list[int] = []


# Starts the bot when the server starts
@app.on_event("startup")
async def on_startup() -> None:
    await bot.start()


# Closes the bot when the server closes
@app.on_event("shutdown")
async def on_shutdown() -> None:
    await bot.close()


# Returns the index.html page
@app.get("/")
async def index() -> FileResponse:
    return FileResponse("static/index.html")


# Returns the oops.html page
@app.get("/oops")
async def oops() -> FileResponse:
    return FileResponse("static/oops.html")


# Validates an incoming submission on the index page form
@app.post("/access/request")
async def access_request(req: Request) -> Response:
    # Extract form data into variables
    form_data = await req.form()
    userid: int = int(form_data.get("userid"))
    github_link: str = form_data.get("github-link")

    if userid in pending_requests:
        # This user already submitted their info
        return RedirectResponse(
            "/oops?You already have a request pending.", status_code=302
        )

    # This user is now pending
    pending_requests.append(userid)

    # Build an action row with an approve and deny buttons
    action_row = (
        bot.rest.build_action_row()
        .add_button(hikari.ButtonStyle.PRIMARY, f"{userid}-approve-access")
        .set_label("Approve")
        .add_to_container()
        .add_button(hikari.ButtonStyle.DANGER, f"{userid}-deny-access")
        .set_label("Deny")
        .add_to_container()
    )

    # Build an embed to send to the channel
    embed = (
        hikari.Embed(
            title="New application to join",
            description=f"User: <@{userid}>",
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        .add_field("User ID", f"```{userid}```")
        .add_field("Github Link:", github_link)
        .add_field("Status", "```PENDING```")
    )

    # Send the embed to the channel
    await bot.rest.create_message(CHANNEL, embed, component=action_row)

    # Redirect the user on the site to the thanks.html page
    return FileResponse("static/thanks.html")


# If a member joins and they are not in approved members, ban them
@bot.listen(hikari.MemberCreateEvent)
async def on_member_create(event: hikari.MemberCreateEvent) -> None:
    if event.member.id not in approved_members:
        # This user never got approved - they've gone rogue!
        await event.member.ban()


# Listen for interactions (button clicks)
@bot.listen(hikari.InteractionCreateEvent)
async def on_interaction(event: hikari.InteractionCreateEvent) -> None:
    inter = event.interaction

    if not isinstance(inter, hikari.ComponentInteraction):
        # This interaction isn't related to buttons
        return None

    if inter.channel_id != CHANNEL:
        # This isn't the channel we send our requests to
        return None

    if inter.member and ADMIN_ROLE_ID not in inter.member.role_ids:
        # This user cant approve or deny other members
        return None

    try:
        userid, action, access = inter.custom_id.split("-")
    except ValueError:
        # This custom id does not match our format
        return None

    if access != "access":
        # This must be related to some other interactions, bail!
        return None

    if action == "deny":
        # Update the embed to denied
        embed = inter.message.embeds[0]
        embed.add_field("Status", f"```DENIED by {inter.user}```")

        # Create our response to the interaction
        await inter.create_initial_response(
            hikari.ResponseType.MESSAGE_UPDATE, embed, components=[]
        )

    elif action == "approve":
        # We want to approve them - someone clicked the approve button
        await do_approve_action(inter, int(userid))


async def do_approve_action(inter: hikari.ComponentInteraction, userid: int) -> None:
    # Create a new invite for this user to use
    invite = await bot.rest.create_invite(
        # This is the channel where the invite leads to
        # It should probably be some welcome or rules channel
        CHANNEL,
        max_age=datetime.timedelta(days=7),
        max_uses=1,
        reason=f"Approved by {inter.member}",
    )

    # Update the embed to approved
    embed = inter.message.embeds[0]
    embed.add_field("Status", f"```APPROVED by {inter.user}```")

    try:
        # Try to DM the user
        dm = await bot.rest.create_dm_channel(userid)
        await dm.send(
            "Hi were happy to inform you that you application has been accepted!"
            f" You, and only you, can join with the following link\n{invite}"
        )
    except hikari.ForbiddenError:
        # This can fail if the user has DM's closed
        # Make the embed red since we couldn't DM the user
        embed.color = hikari.Color(0xF00707)
        embed.add_field("DM failed", str(invite))

    # Create our response to the interaction
    await inter.create_initial_response(
        hikari.ResponseType.MESSAGE_UPDATE, embed, components=[]
    )

    # Remove the user from pending and add to approved
    pending_requests.remove(userid)
    approved_members.append(userid)


# Run the webserver
uvicorn.run(app, host="0.0.0.0")
