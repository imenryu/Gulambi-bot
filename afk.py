import time
from typing import Optional, Dict

from loguru import logger
from telethon import events

import constants

class AFKManager:
    """Manages the AFK feature for the userbot."""

    def __init__(self, client):
        self.client = client
        self.afk_status = False
        self.afk_message = "I'm AFK."
        self.afk_start_time: Optional[float] = None
        self.afk_reason: Optional[str] = None
        self.last_replied: Dict[int, float] = {}  # Track last reply time to each user

    async def afk_command(self, event) -> None:
        """Handle the .afk command."""
        if self.afk_status:
            await event.edit("I am already AFK!")
            return

        # Check if a custom message is provided
        custom_message = event.pattern_match.group(1)
        if custom_message:
            self.afk_message = "I'm AFK."
            self.afk_reason = custom_message
        else:
            self.afk_message = "I'm AFK."
            self.afk_reason = None

        # Enable AFK
        self.afk_status = True
        self.afk_start_time = time.time()
        await event.edit(f"I am now AFK: {self.afk_message}")
        logger.info(f"AFK enabled. Reason: {self.afk_reason}")

    async def unafk_command(self, event) -> None:
        """Handle the .unafk command."""
        if not self.afk_status:
            await event.edit("I am not AFK!")
            return

        # Disable AFK
        self.afk_status = False
        self.afk_start_time = None
        self.afk_reason = None
        await event.edit("I am no longer AFK!")
        logger.info("AFK disabled.")

    async def handle_afk_messages(self, event) -> None:
        """Handle incoming messages when AFK is enabled."""
        if not self.afk_status:
            return

        # Ignore messages from yourself
        if event.sender_id == (await self.client.get_me()).id:
            return

        # Check if the message is in a group and the bot is not mentioned
        if event.is_group and not event.mentioned:
            return

        # Prevent multiple AFK replies to the same user in a short period
        current_time = time.time()
        last_reply_time = self.last_replied.get(event.sender_id, 0)
        if current_time - last_reply_time < 60:  # 60 seconds cooldown
            return

        # Calculate AFK duration
        afk_duration = int(current_time - self.afk_start_time)
        hours, remainder = divmod(afk_duration, 3600)
        minutes, seconds = divmod(remainder, 60)
        duration_text = f"{hours}h {minutes}m {seconds}s"

        # Prepare AFK reply
        reply_message = "I'm AFK."
        if self.afk_reason:
            reply_message += f"\nReason: {self.afk_reason}"
        reply_message += f"\nTotal time since AFK: {duration_text}"

        # Send AFK reply
        await event.reply(reply_message)
        self.last_replied[event.sender_id] = current_time  # Update last reply time
        logger.info(f"Sent AFK reply to {event.sender_id}")

    def get_event_handlers(self) -> list:
        """Returns a list of AFK-related event handlers."""
        return [
            {'callback': self.afk_command, 'event': events.NewMessage(pattern=constants.AFK_COMMAND_REGEX, outgoing=True)},
            {'callback': self.unafk_command, 'event': events.NewMessage(pattern=constants.UNAFK_COMMAND_REGEX, outgoing=True)},
            {'callback': self.handle_afk_messages, 'event': events.NewMessage(incoming=True)}
        ]
