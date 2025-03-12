import asyncio
from telethon import events
from telethon.errors import ChatAdminRequiredError, MessageDeleteForbiddenError
from loguru import logger

class PurgeManager:
    """Handles message purging functionality."""

    def __init__(self, client):
        self._client = client

    async def purge_messages(self, event):
        """Handles the `.purge <count>` and `.purge` (in reply) commands."""
        logger.info(f"Purge command received: {event.raw_text}")
        args = event.raw_text.split()
        reply_msg = await event.get_reply_message()

        if reply_msg:
            logger.info("Purging up to replied message...")
            await self._purge_up_to_reply(event, reply_msg)
        elif len(args) == 2 and args[1].isdigit():
            count = int(args[1])
            logger.info(f"Purging {count} of your messages...")
            await self._purge_own_messages(event, count)
        else:
            logger.warning("Invalid purge command usage.")
            await event.reply("Usage: `.purge <count>` (your messages) or reply with `.purge` (delete all till replied message)")

    async def _purge_up_to_reply(self, event, reply_msg):
        """Deletes all messages from the replied message up to the latest message."""
        chat = event.chat_id
        to_delete = []
        deleted_count = 0

        try:
            async for message in self._client.iter_messages(chat, min_id=reply_msg.id - 1, reverse=True):
                to_delete.append(message.id)
                deleted_count += 1
                if len(to_delete) >= 100:
                    await self._client.delete_messages(chat, to_delete)
                    to_delete.clear()
                    await asyncio.sleep(1)  # Prevents rate limiting

            if to_delete:
                await self._client.delete_messages(chat, to_delete)

            confirmation = await event.respond(f" Deleted {deleted_count} messages up to the replied message.")
            await asyncio.sleep(3)
            await confirmation.delete()

        except (ChatAdminRequiredError, MessageDeleteForbiddenError):
            await event.reply("⚠️ Error: I need 'Delete Messages' permission!")

    async def _purge_own_messages(self, event, count):
        """Deletes only the user's own messages."""
        if count <= 0:
            return await event.reply("⚠️ Count must be greater than 0.")

        chat = event.chat_id
        to_delete = []
        deleted_count = 0

        try:
            async for message in self._client.iter_messages(chat, from_user=event.sender_id, limit=count):
                to_delete.append(message.id)
                deleted_count += 1
                if len(to_delete) >= 100:
                    await self._client.delete_messages(chat, to_delete)
                    to_delete.clear()
                    await asyncio.sleep(1)  # Prevents rate limiting

            if to_delete:
                await self._client.delete_messages(chat, to_delete)

            confirmation = await event.respond(f" Deleted {deleted_count} of your messages!")
            await asyncio.sleep(3)
            await confirmation.delete()

        except (ChatAdminRequiredError, MessageDeleteForbiddenError):
            await event.reply("⚠️ Error: I need 'Delete Messages' permission!")

    def get_event_handlers(self):
        """Returns event handlers for purge commands."""
        return [
            {"callback": self.purge_messages, "event": events.NewMessage(pattern=r"\.purge(?: |$)(\d*)", outgoing=True)},
        ]
