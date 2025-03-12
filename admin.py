from telethon import events
from telethon.tl.functions.channels import GetParticipantRequest, EditBannedRequest, EditAdminRequest
from telethon.tl.types import ChatBannedRights, ChatAdminRights
from telethon.errors import MessageNotModifiedError
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Store chat-specific data
chat_data = {}

class AdminManager:
    """Handles admin commands like mute, unmute, ban, unban, promote, demote, and kick."""

    def __init__(self, client):
        self.client = client

    async def _get_chat_data(self, chat_id):
        """Returns the data for a specific chat, initializing if necessary."""
        if chat_id not in chat_data:
            chat_data[chat_id] = {"muted_users": set(), "banned_users": set(), "admins": set()}
        return chat_data[chat_id]

    async def _get_target_user(self, event):
        """Helper method to get the target user from a reply or user ID."""
        if event.is_reply:
            reply = await event.get_reply_message()
            if reply and reply.sender_id:
                return reply.sender_id
        args = event.raw_text.split()
        if len(args) == 2 and args[1].isdigit():
            return int(args[1])
        return None

    async def _edit_message(self, event, text):
        """Helper method to edit a message with error handling."""
        try:
            await event.edit(text)
        except MessageNotModifiedError:
            # Ignore if the message was not modified
            pass
        except Exception as e:
            logger.error(f"Failed to edit message: {e}")

    async def mute_user(self, event):
        """Mutes a user by deleting their messages in the chat."""
        chat_id = event.chat_id
        user_id = await self._get_target_user(event)

        if not user_id:
            return await self._edit_message(event, "Reply to a user or provide a user ID to mute them!")

        chat_info = await self._get_chat_data(chat_id)
        chat_info["muted_users"].add(user_id)

        await self._edit_message(event, "Muted!!!")

    async def unmute_user(self, event):
        """Unmutes a user by stopping message deletion."""
        chat_id = event.chat_id
        user_id = await self._get_target_user(event)

        if not user_id:
            return await self._edit_message(event, "Reply to a user or provide a user ID to unmute them!")

        chat_info = await self._get_chat_data(chat_id)

        if user_id not in chat_info["muted_users"]:
            return await self._edit_message(event, "This user is not muted!")

        chat_info["muted_users"].discard(user_id)
        await self._edit_message(event, "Unmuted!!!")

    async def delete_muted_messages(self, event):
        """Deletes messages sent by muted users."""
        chat_id = event.chat_id
        chat_info = await self._get_chat_data(chat_id)

        logger.info(f"Checking if user {event.sender_id} is muted in chat {chat_id}...")

        if event.sender_id in chat_info["muted_users"]:
            logger.info(f"User {event.sender_id} is muted. Attempting to delete their message...")
            try:
                await event.delete()
                logger.info(f"Deleted message from muted user {event.sender_id}")
            except Exception as e:
                logger.error(f"Failed to delete message from muted user {event.sender_id}: {e}")
        else:
            logger.info(f"User {event.sender_id} is not muted.")

    async def ban_user(self, event):
        """Bans a user from the chat."""
        chat_id = event.chat_id
        user_id = await self._get_target_user(event)

        if not user_id:
            return await self._edit_message(event, "Reply to a user or provide a user ID to ban them!")

        try:
            await self.client(EditBannedRequest(chat_id, user_id, ChatBannedRights(view_messages=True)))
            chat_info = await self._get_chat_data(chat_id)
            chat_info["banned_users"].add(user_id)
            await self._edit_message(event, "Banned!!!")
        except Exception as e:
            logger.error(f"Failed to ban user {user_id}: {e}")
            await self._edit_message(event, "Failed to ban the user.")

    async def unban_user(self, event):
        """Unbans a user from the chat."""
        chat_id = event.chat_id
        user_id = await self._get_target_user(event)

        if not user_id:
            return await self._edit_message(event, "Reply to a user or provide a user ID to unban them!")

        chat_info = await self._get_chat_data(chat_id)

        if user_id not in chat_info["banned_users"]:
            return await self._edit_message(event, "This user is not banned!")

        try:
            await self.client(EditBannedRequest(chat_id, user_id, ChatBannedRights()))
            chat_info["banned_users"].discard(user_id)
            await self._edit_message(event, "Unbanned!!!")
        except Exception as e:
            logger.error(f"Failed to unban user {user_id}: {e}")
            await self._edit_message(event, "Failed to unban the user.")

    async def kick_user(self, event):
        """Kicks a user from the chat."""
        chat_id = event.chat_id
        user_id = await self._get_target_user(event)

        if not user_id:
            return await self._edit_message(event, "Reply to a user or provide a user ID to kick them!")

        try:
            await self.client(EditBannedRequest(chat_id, user_id, ChatBannedRights(view_messages=True)))
            await self.client(EditBannedRequest(chat_id, user_id, ChatBannedRights()))
            await self._edit_message(event, "Kicked!!!")
        except Exception as e:
            logger.error(f"Failed to kick user {user_id}: {e}")
            await self._edit_message(event, "Failed to kick the user.")

    async def promote_user(self, event):
        """Promotes a user to admin."""
        chat_id = event.chat_id
        user_id = await self._get_target_user(event)

        if not user_id:
            return await self._edit_message(event, "Reply to a user or provide a user ID to promote them!")

        rights = ChatAdminRights(
            post_messages=True,
            delete_messages=True,
            ban_users=True,
            invite_users=True,
            change_info=True,
            pin_messages=True
        )

        try:
            await self.client(EditAdminRequest(chat_id, user_id, rights, rank="Admin"))
            chat_info = await self._get_chat_data(chat_id)
            chat_info["admins"].add(user_id)
            await self._edit_message(event, "Promoted!!!")
        except Exception as e:
            logger.error(f"Failed to promote user {user_id}: {e}")
            await self._edit_message(event, "Failed to promote the user.")

    async def demote_user(self, event):
        """Demotes an admin back to a normal user."""
        chat_id = event.chat_id
        user_id = await self._get_target_user(event)

        if not user_id:
            return await self._edit_message(event, "Reply to a user or provide a user ID to demote them!")

        chat_info = await self._get_chat_data(chat_id)

        if user_id not in chat_info["admins"]:
            return await self._edit_message(event, "This user is not an admin!")

        try:
            rights = ChatAdminRights()
            await self.client(EditAdminRequest(chat_id, user_id, rights, rank=""))
            chat_info["admins"].discard(user_id)
            await self._edit_message(event, "Demoted!!!")
        except Exception as e:
            logger.error(f"Failed to demote user {user_id}: {e}")
            await self._edit_message(event, "Failed to demote the user.")

    def get_event_handlers(self):
        """Returns event handlers for admin commands."""
        return [
            {"callback": self.mute_user, "event": events.NewMessage(pattern=r"\.mute(?: (\d+))?$", outgoing=True)},
            {"callback": self.unmute_user, "event": events.NewMessage(pattern=r"\.unmute(?: (\d+))?$", outgoing=True)},
            {"callback": self.ban_user, "event": events.NewMessage(pattern=r"\.ban(?: (\d+))?$", outgoing=True)},
            {"callback": self.unban_user, "event": events.NewMessage(pattern=r"\.unban(?: (\d+))?$", outgoing=True)},
            {"callback": self.kick_user, "event": events.NewMessage(pattern=r"\.kick(?: (\d+))?$", outgoing=True)},
            {"callback": self.promote_user, "event": events.NewMessage(pattern=r"\.promote(?: (\d+))?$", outgoing=True)},
            {"callback": self.demote_user, "event": events.NewMessage(pattern=r"\.demote(?: (\d+))?$", outgoing=True)},
            {"callback": self.delete_muted_messages, "event": events.NewMessage(incoming=True)}
        ]
