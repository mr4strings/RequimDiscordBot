import discord
import os
from dotenv import load_dotenv
import asyncio # Required for running async discord.py code within Flask

# --- Flask Imports ---
from flask import Flask, jsonify, request # jsonify to send JSON responses, request for query parameters

load_dotenv()



BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Define a LIST of TARGET CHANNEL IDs
# Replace these example IDs with your actual channel IDs, each as a string within the list.
TARGET_CHANNEL_IDS = [
    "1308488868252614687",      # Adventure Log
    "1308488287576653895",      # Characters
    "1308488702917476443",      # Inventory
    "1317209630367154249",      # Locations
    "1308488839811039353",      # NPCs
    "1364267090294607973",      # Requiem Trading Consortium
    "1308488427158634547",      # Stonebreak Manor
    
]
# --- Basic Validation (copied from before) ---
if BOT_TOKEN is None:
    print("Error: DISCORD_BOT_TOKEN not found. Make sure you have a .env file with the token.")
    exit()
if not TARGET_CHANNEL_IDS or any(id_val in ["YOUR_FIRST_CHANNEL_ID_HERE", "YOUR_SECOND_CHANNEL_ID_HERE"] for id_val in TARGET_CHANNEL_IDS):
    print(f"Error: TARGET_CHANNEL_IDS list is empty or contains placeholder IDs in your bot.py file. Please update it.")
    exit()
for channel_id in TARGET_CHANNEL_IDS:
    if not isinstance(channel_id, str) or not channel_id.isdigit():
        print(f"Error: Invalid channel ID '{channel_id}' found. All IDs must be strings of numbers.")
        exit()

# --- Flask App Initialization ---
app = Flask(__name__)

# --- Discord Client Setup (for persistent bot - WILL NOT RUN in this API-focused version) ---
# We define these but won't call client.run() in this version.
# The API will create its own short-lived client instances.
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
# persistent_bot_client = discord.Client(intents=intents)

# @persistent_bot_client.event
# async def on_ready():
#     print(f'Persistent bot logged in as {persistent_bot_client.user}')
#     print('This part is for the continuous listening bot, not directly used by the API in this version.')

# @persistent_bot_client.event
# async def on_message(message):
#     if message.author == persistent_bot_client.user:
#         return
#     if str(message.channel.id) in TARGET_CHANNEL_IDS:
#         print(f"Persistent Bot: Message in {message.channel.name} from {message.author.name}: {message.content}")


# --- Helper function to fetch messages (Async) ---
async def fetch_discord_messages(channel_id_to_fetch: str, num_messages: int = 10):
    temp_client = discord.Client(intents=intents) # Create a temporary client
    messages_data = []
    try:
        await temp_client.login(BOT_TOKEN)
        # print(f"Temporary client logged in for channel {channel_id_to_fetch}") # Debug print
        channel = await temp_client.fetch_channel(int(channel_id_to_fetch)) # Channel ID must be int here
        # print(f"Fetched channel: {channel.name}") # Debug print

        async for historical_message in channel.history(limit=num_messages):
            messages_data.append({
                "id": str(historical_message.id),
                "author": str(historical_message.author.name),
                "author_id": str(historical_message.author.id),
                "content": str(historical_message.content),
                "timestamp": str(historical_message.created_at)
            })
        # print(f"Fetched {len(messages_data)} messages.") # Debug print
    except discord.errors.NotFound:
        print(f"Error: Channel with ID {channel_id_to_fetch} not found or bot doesn't have access.")
        return {"error": "Channel not found or inaccessible"}, 404
    except discord.errors.Forbidden:
        print(f"Error: Bot does not have permissions to fetch history for channel ID {channel_id_to_fetch}.")
        return {"error": "Bot forbidden from accessing channel history"}, 403
    except Exception as e:
        print(f"An unexpected error occurred while fetching messages: {e}")
        return {"error": f"An internal error occurred: {e}"}, 500
    finally:
        if temp_client.is_ready(): # Check if logout is necessary
            await temp_client.close()
        # print("Temporary client logged out.") # Debug print
    return messages_data, 200


# --- API Endpoint Definition ---
@app.route('/get_messages', methods=['GET'])
async def get_messages_api(): # Flask 2.0+ supports async route handlers
    """
    API endpoint to get messages from a specific Discord channel.
    Query Parameters:
    - channel_id (str, required): The ID of the Discord channel.
    - limit (int, optional, default=10): Number of messages to fetch.
    """
    channel_id_param = request.args.get('channel_id')
    try:
        limit_param = int(request.args.get('limit', 10)) # Default to 10 messages
        if limit_param <= 0 or limit_param > 100: # Add a reasonable cap
            limit_param = 10
    except ValueError:
        return jsonify({"error": "Invalid limit parameter. Must be an integer."}), 400

    if not channel_id_param:
        return jsonify({"error": "channel_id query parameter is required."}), 400

    if channel_id_param not in TARGET_CHANNEL_IDS:
        # Optional: Only allow fetching from pre-approved channels
        # return jsonify({"error": f"Channel ID {channel_id_param} is not in the allowed list."}), 403
        # For now, let's allow fetching any channel ID passed, but print a warning if not in TARGET_CHANNEL_IDS
        print(f"Warning: API request for channel ID {channel_id_param} which is not in pre-configured TARGET_CHANNEL_IDS.")
        # If you want to restrict, uncomment the return jsonify line above and remove this print.

    # Run the async Discord fetching function
    # Because Flask's default dev server might not run an asyncio event loop
    # in a way that `asyncio.run` can be called directly in a threaded context,
    # and `await` in the route requires Flask 2.0+ and an async context.
    # Assuming Flask 2.0+ for direct await in async route.
    result, status_code = await fetch_discord_messages(channel_id_param, limit_param)

    if status_code == 200:
        return jsonify({"channel_id": channel_id_param, "messages": result}), status_code
    else:
        return jsonify(result), status_code


# --- Main execution for Flask app ---
if __name__ == '__main__':
    # Note: The persistent discord bot (client.run(BOT_TOKEN)) is NOT started here.
    # This script now only runs the Flask web server.
    # For development, Flask's built-in server is fine.
    # For production, you'd use a proper WSGI/ASGI server like Gunicorn or Uvicorn/Hypercorn.
    print("Starting Flask API server...")
    print(f"To get messages, open your browser or use a tool like Postman to access:")
    print(f"http://127.0.0.1:5000/get_messages?channel_id=YOUR_CHANNEL_ID_HERE&limit=5")
    app.run(debug=True, host='0.0.0.0', port=5000) # Runs on http://127.0.0.1:5000/
                                            # host='0.0.0.0' makes it accessible on your local network
