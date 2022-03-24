# fastapi-bot

A simple implementation of a GatewayBot that interacts with a separate FastAPI instance.

## What is this project?

A demonstration of how you can use FastAPI endpoints to trigger actions
on your Hikari bot to send messages in channels etc.

This example has a basic static site that a user fills in their discord
user ID and their github link, and an admin on the server can either
approve or deny their request.

Based on approval or denial the bot will send the user a DM with a link
to the server.

## Running the bot

```bash
# Clone the repo
git clone https://github.com/Jonxslays/fastapi-bot.git

# Install dependencies with poetry
poetry shell && poetry install --no-dev

# Run the bot
python -m fastapi-bot
```

## License

This project is licensed under the
[MIT License](https://github.com/Jonxslays/fastapi-bot/blob/master/LICENSE).
