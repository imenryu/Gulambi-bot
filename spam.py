import asyncio
from telethon import events
from telethon.errors import MessageDeleteForbiddenError

class Spam:
    """Handles spam commands like .spam, .delayspam, and .stopspam."""

    def __init__(self, client):
        self.client = client
        self.spamming = {}  # Dictionary to track spam per chat

    async def spam_message(self, chat_id, message, count, event=None):
        """Spams a message multiple times."""
        if event:
            try:
                await event.delete()  # Delete the trigger message
            except MessageDeleteForbiddenError:
                await event.reply(" I don't have permission to delete messages here.")

        self.spamming[chat_id] = True  # Start tracking spam
        for _ in range(count):
            if not self.spamming.get(chat_id, False):  # Stop if .stopspam is used
                break
            await self.client.send_message(chat_id, message)
        self.spamming[chat_id] = False  # Reset spam status after completion

    async def delayspam_message(self, chat_id, message, count, delay, event=None):
        """Spams a message multiple times with a delay."""
        if event:
            try:
                await event.delete()  # Delete the trigger message
            except MessageDeleteForbiddenError:
                await event.reply(" I don't have permission to delete messages here.")

        self.spamming[chat_id] = True  # Start tracking spam
        for _ in range(count):
            if not self.spamming.get(chat_id, False):  # Stop if .stopspam is used
                break
            await self.client.send_message(chat_id, message)
            await asyncio.sleep(delay)
        self.spamming[chat_id] = False  # Reset spam status after completion

    async def stop_spam(self, event):
        """Stops any ongoing spam in the current chat."""
        chat_id = event.chat_id
        self.spamming[chat_id] = False
        await event.respond("Stopped all ongoing spam.")
