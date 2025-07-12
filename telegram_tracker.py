from telethon.sync import TelegramClient
import asyncio

# ✅ Your Telegram credentials
api_id = 29271301
api_hash = '5efce68568312af5e01eea891cc75778'
phone_number = '+254769255782'  # Your full phone number with +254

# ✅ Session name (saves your login)
client = TelegramClient('lead_session', api_id, api_hash)

async def main():
    await client.start(phone=phone_number)
    print("✅ Connected to Telegram")

    # ✅ Example: Read messages from a public group
    group_username = 'kenyajobs'  # or 'realestatekenya', 'tutorke', etc.

    async for message in client.iter_messages(group_username, limit=10):
        print(f"📩 {message.sender_id}: {message.text}")

with client:
    client.loop.run_until_complete(main())
