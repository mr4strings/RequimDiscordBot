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
    "1377758265928188065",      # homebrew rules
    
]
# Basic Validation for BOT_TOKEN and TARGET_CHANNEL_IDS
if BOT_TOKEN is None:
    print("Error: DISCORD_BOT_TOKEN not found.")
    exit()

if not TARGET_CHANNEL_IDS or "YOUR_FIRST_CHANNEL_ID_HERE" in TARGET_CHANNEL_IDS : # Simple check for placeholder
    print(f"Error: TARGET_CHANNEL_IDS is not configured correctly in your bot.py file. Please add actual Channel IDs.")
    exit()
for cid_val in TARGET_CHANNEL_IDS:
    if not isinstance(cid_val, str) or not cid_val.isdigit():
        print(f"Error: Invalid channel ID '{cid_val}' found in TARGET_CHANNEL_IDS. All IDs must be strings of numbers.")
        exit()


app = Flask(__name__)
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True # Ensure this is enabled in your Discord Developer Portal for the bot

# --- Helper function to fetch messages (Async - unchanged from before) ---
async def fetch_discord_messages(channel_id_to_fetch: str, num_messages: int | None = 10):
    temp_client = discord.Client(intents=intents)
    messages_data = []
    channel_name = "Unknown Channel" # Default channel name
    actual_channel_id_str = str(channel_id_to_fetch) # Ensure it's a string

    try:
        await temp_client.login(BOT_TOKEN)
        # Fetch channel object to get its name
        try:
            channel_obj = await temp_client.fetch_channel(int(actual_channel_id_str))
            channel_name = channel_obj.name
        except Exception as e_fetch_channel:
            print(f"Warning: Could not fetch channel object for ID {actual_channel_id_str} to get name: {e_fetch_channel}")
            # Proceed with fetching messages if channel ID is valid, even if name fetch fails
        
        # Re-fetch channel object if needed or use the one from above if it's the same logic path
        # For simplicity, let's assume channel_obj is the one we use for history
        if 'channel_obj' not in locals() or not channel_obj: # If fetch_channel failed above, try again before history
             channel_obj = await temp_client.fetch_channel(int(actual_channel_id_str))
             channel_name = channel_obj.name # update name if it was unknown

        async for historical_message in channel_obj.history(limit=num_messages):
            messages_data.append({
                "id": str(historical_message.id),
                "author": str(historical_message.author.name),
                "author_id": str(historical_message.author.id),
                "content": str(historical_message.content),
                "timestamp": str(historical_message.created_at)
            })
    except discord.errors.NotFound:
        print(f"Error (fetch_discord_messages): Channel with ID {actual_channel_id_str} not found or bot doesn't have access.")
        return {"error": "Channel not found or inaccessible with the given ID", "channel_name": channel_name, "channel_id": actual_channel_id_str}, 404
    except discord.errors.Forbidden:
        print(f"Error (fetch_discord_messages): Bot does not have permissions for channel ID {actual_channel_id_str}.")
        return {"error": "Bot forbidden from accessing channel history for the given ID", "channel_name": channel_name, "channel_id": actual_channel_id_str}, 403
    except Exception as e:
        print(f"Error (fetch_discord_messages): An unexpected error occurred for channel ID {actual_channel_id_str}: {e}")
        return {"error": f"An internal error occurred: {type(e).__name__} - {e}", "channel_name": channel_name, "channel_id": actual_channel_id_str}, 500
    finally:
        if temp_client.is_ready():
            await temp_client.close()
    # Return channel_name and channel_id along with messages
    return {"channel_name": channel_name, "channel_id": actual_channel_id_str, "messages": messages_data}, 200


# --- API Endpoint to GET RECENT ACTIVITY FROM ALL CONFIGURED CHANNELS ---
@app.route('/get_recent_activity_from_all_channels', methods=['GET'])
async def get_all_channels_activity_api():
    MESSAGES_PER_CHANNEL_LIMIT = 15  # Fixed number of messages from each channel
    
    all_channel_data = []
    fetch_errors = []

    for channel_id_str in TARGET_CHANNEL_IDS:
        result_data, status_code = await fetch_discord_messages(channel_id_str, MESSAGES_PER_CHANNEL_LIMIT)
        
        if status_code == 200:
            # result_data already contains channel_name, channel_id, and messages
            all_channel_data.append(result_data)
        else:
            # result_data contains the error, channel_name (might be "Unknown"), and channel_id
            fetch_errors.append(result_data) # result_data is the error dict here
            print(f"Error fetching from channel ID {channel_id_str}: {result_data.get('error')}")

    response_data = {
        "all_channel_activity": all_channel_data
    }
    if fetch_errors:
        response_data["fetch_errors"] = fetch_errors

    return jsonify(response_data), 200


if __name__ == '__main__':
    print("Starting Flask API server...")
    print(f"Bot will scan the following Channel IDs: {', '.join(TARGET_CHANNEL_IDS)}")
    print(f"To get recent activity from all configured channels, use endpoint: /get_recent_activity_from_all_channels")
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
