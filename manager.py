import time
from typing import List, Dict, Callable

from loguru import logger
from telethon import events

import constants
from evaluate import ExpressionEvaluator
from guesser import PokemonIdentificationEngine
from hunter import PokemonHuntingEngine
from afk import AFKManager
from alive import AliveHandler
from release import PokemonReleaseManager
from admin import AdminManager
from purge import PurgeManager
from spam import Spam  # Import the Spam class

HELP_MESSAGE = """**Help Menu**

**Pokémon Commands**
• `.pokemon` - Show Pokémon-related commands

**Utility Commands**
• `.ping` - Pong
• `.alive` - Bot status
• `.help` - Help menu
• `.afk` (message) - Set AFK status
• `.unafk` - Disable AFK status

**Admin Commands**
• `.admin` - Admin commands
• `.mute` - Mute a user
• `.unmute` - Unmute a user
• `.ban` - Ban a user
• `.unban` - Unban a user
• `.promote` - Promote a user to admin
• `.demote` - Demote an admin
• `.kick` - Kick a user

**Purge Commands**
• `.purge` - Delete all messages in a chat
• `.purge (count)` - Delete a specific number of messages

**Spam Commands**
• `.spam` - Spam commands menu
"""

POKEMON_HELP = """**Pokémon Commands**

• `.guess` (on/off/stats) - Guess Pokémon
• `.hunt` (on/off/stats) - Hunt for Pokémon
• `.list <category>` - List Pokémon by category
• `.release` - Pokémon release menu
"""

RELEASE_HELP = """**Release Commands**

• `.release on` - Start auto-releasing Pokémon
• `.release off` - Stop auto-releasing Pokémon
• `.release add <name>` - Add a Pokémon to the release list
• `.release remove <name>` - Remove a Pokémon from the release list
• `.release list` - Show the Pokémon in the release list
"""

ADMIN_HELP = """**Admin Commands**

• `.mute` - Mute a user
• `.unmute` - Unmute a user
• `.ban` - Ban a user
• `.unban` - Unban a user
• `.promote` - Promote a user to admin
• `.demote` - Demote an admin
• `.kick` - Kick a user
"""

PURGE_HELP = """**Purge Commands**

• `.purge` - Delete all messages in a chat
• `.purge (count)` - Delete a specific number of messages
"""

SPAM_HELP = """**Spam Commands**

• `.spam <count> <message>` - Spam a message multiple times.
• `.delayspam <count> <delay> <message>` - Spam a message with a delay between each message.
• `.stopspam` - Stop all ongoing spam in the current chat.
"""


class Manager:
    """Manages automation for the Userbot."""

    __slots__ = (
        '_client',
        '_guesser',
        '_hunter',
        '_evaluator',
        '_afk_manager',
        '_alive_handler',
        '_release_manager',
        '_admin_manager',
        '_purge_manager',
        '_spam_manager',  # Add SpamManager
    )

    def __init__(self, client) -> None:
        self._client = client
        self._guesser = PokemonIdentificationEngine(client)
        self._hunter = PokemonHuntingEngine(client)
        self._evaluator = ExpressionEvaluator(client)
        self._afk_manager = AFKManager(client)
        self._alive_handler = AliveHandler(client)
        self._release_manager = PokemonReleaseManager(client)
        self._admin_manager = AdminManager(client)
        self._purge_manager = PurgeManager(client)
        self._spam_manager = Spam(client)  # Initialize SpamManager

    def start(self) -> None:
        """Starts the Userbot's automations."""
        logger.info('Initializing Userbot')
        self._guesser.start()
        self._hunter.start()
        self._evaluator.start()
        self._alive_handler.register()

        # Add AFK event handlers
        for handler in self._afk_manager.get_event_handlers():
            self._client.add_event_handler(handler['callback'], handler['event'])
            logger.debug(f'[{self.__class__.__name__}] Added AFK event handler: `{handler["callback"].__name__}`')

        # Register AdminManager event handlers
        for handler in self._admin_manager.get_event_handlers():
            self._client.add_event_handler(handler['callback'], handler['event'])
            logger.debug(f'[{self.__class__.__name__}] Added admin event handler: `{handler["callback"].__name__}`')

        # Register other event handlers
        for handler in self.event_handlers:
            self._client.add_event_handler(handler['callback'], handler['event'])
            logger.debug(f'[{self.__class__.__name__}] Added event handler: `{handler["callback"].__name__}`')

    async def ping_command(self, event) -> None:
        """Handles the `.ping` command."""
        start = time.time()
        await event.edit('...')
        ping_ms = (time.time() - start) * 1000
        await event.edit(f'Pong!!\n{ping_ms:.2f}ms')

    async def help_command(self, event) -> None:
        """Handles the `.help` command."""
        await event.edit(HELP_MESSAGE)

    async def pokemon_menu(self, event) -> None:
        """Shows the Pokémon-related commands menu."""
        await event.edit(POKEMON_HELP)

    async def release_menu(self, event) -> None:
        """Shows the `.release` menu."""
        await event.edit(RELEASE_HELP)

    async def admin_menu(self, event) -> None:
        """Shows the `.admin` menu."""
        await event.edit(ADMIN_HELP)

    async def purge_menu(self, event) -> None:
        """Shows the `.purge` menu."""
        await event.edit(PURGE_HELP)

    async def spam_menu(self, event) -> None:
        """Shows the `.spam` menu."""
        await event.edit(SPAM_HELP)

    async def handle_guesser_automation_control_request(self, event) -> None:
        """Handles user requests to enable/disable guesser automation."""
        await self._guesser.handle_automation_control_request(event)

    async def handle_hunter_automation_control_request(self, event) -> None:
        """Handles user requests to enable/disable hunter automation."""
        await self._hunter.handle_automation_control_request(event)

    async def list_pokemon(self, event) -> None:
        """Handles the `.list` command by showing Pokémon based on the specified category."""
        args = event.pattern_match.group(1)

        categories = {
            "regular": constants.REGULAR_BALL,
            "repeat": constants.REPEAT_BALL,
            "ultra": constants.ULTRA_BALL,
            "great": constants.GREAT_BALL,
            "nest": constants.NEST_BALL,
            "safari": constants.SAFARI
        }

        if not args:  
            await event.edit(
                "**Usage:** `.list <category>`\n\n"
                "**Available categories:**\n"
                "- `regular`\n"
                "- `repeat`\n"
                "- `ultra`\n"
                "- `great`\n"
                "- `nest`\n"
                "- `safari`"
            )
            return

        category = args.lower()
        if category not in categories:
            await event.edit(f"**Invalid category!**\nUse one of: {', '.join(categories.keys())}")
            return

        pokemon_list = categories[category]
        if not pokemon_list:
            await event.edit(f"No Pokémon found in `{category}` category.")
            return

        formatted_list = ", ".join(sorted(pokemon_list))  
        await event.edit(f"**{category.capitalize()} Ball Pokémon:**\n{formatted_list}")

    async def handle_spam_command(self, event):
        """
        Handles the .spam command.
        Usage: .spam <count> <message>
        Example: .spam 5 Hello, this is a spam message!
        """
        try:
            count = int(event.pattern_match.group(1))
            message = event.pattern_match.group(2)

            if count > 100:  # Limit to 100 messages
                await event.reply("Maximum spam limit is 100 messages.")
                return

            await self._spam_manager.spam_message(event.chat_id, message, count, event)
        except Exception as e:
            await event.reply(f"Error: {e}")

    async def handle_delayspam_command(self, event):
        """
        Handles the .delayspam command.
        Usage: .delayspam <count> <delay> <message>
        Example: .delayspam 5 1 Hello, this is a delayed spam message!
        """
        try:
            count = int(event.pattern_match.group(1))
            delay = int(event.pattern_match.group(2))
            message = event.pattern_match.group(3)

            if count > 100:  # Limit to 100 messages
                await event.reply("Maximum spam limit is 100 messages.")
                return

            await self._spam_manager.delayspam_message(event.chat_id, message, count, delay, event)
        except Exception as e:
            await event.reply(f"Error: {e}")

    @property
    def event_handlers(self) -> List[Dict[str, Callable | events.NewMessage]]:
        """Returns a list of event handlers, including admin, spam, and Pokémon commands."""
        return [
            # General commands
            {'callback': self.ping_command, 'event': events.NewMessage(pattern=constants.PING_COMMAND_REGEX, outgoing=True)},
            {'callback': self.help_command, 'event': events.NewMessage(pattern=constants.HELP_COMMAND_REGEX, outgoing=True)},
            {'callback': self.pokemon_menu, 'event': events.NewMessage(pattern=r"\.pokemon$", outgoing=True)},

            # Pokémon commands
            {'callback': self.handle_guesser_automation_control_request, 'event': events.NewMessage(pattern=constants.GUESSER_COMMAND_REGEX, outgoing=True)},
            {'callback': self.handle_hunter_automation_control_request, 'event': events.NewMessage(pattern=constants.HUNTER_COMMAND_REGEX, outgoing=True)},
            {'callback': self.list_pokemon, 'event': events.NewMessage(pattern=constants.LIST_COMMAND_REGEX, outgoing=True)},
            {'callback': self.release_menu, 'event': events.NewMessage(pattern=r"\.release$", outgoing=True)},
            {'callback': self._release_manager.start_releasing, 'event': events.NewMessage(pattern=r"\.release on", outgoing=True)},
            {'callback': self._release_manager.stop_releasing, 'event': events.NewMessage(pattern=r"\.release off", outgoing=True)},
            {'callback': self._release_manager.add_pokemon, 'event': events.NewMessage(pattern=r"\.release add (.+)", outgoing=True)},
            {'callback': self._release_manager.remove_pokemon, 'event': events.NewMessage(pattern=r"\.release remove (.+)", outgoing=True)},
            {'callback': self._release_manager.list_pokemon, 'event': events.NewMessage(pattern=r"\.release list", outgoing=True)},

            # Admin commands
            {'callback': self.admin_menu, 'event': events.NewMessage(pattern=r"\.admin$", outgoing=True)},
            {'callback': self._admin_manager.mute_user, 'event': events.NewMessage(pattern=r"\.mute(?: (\d+))?$", outgoing=True)},
            {'callback': self._admin_manager.unmute_user, 'event': events.NewMessage(pattern=r"\.unmute(?: (\d+))?$", outgoing=True)},
            {'callback': self._admin_manager.ban_user, 'event': events.NewMessage(pattern=r"\.ban(?: (\d+))?$", outgoing=True)},
            {'callback': self._admin_manager.unban_user, 'event': events.NewMessage(pattern=r"\.unban(?: (\d+))?$", outgoing=True)},
            {'callback': self._admin_manager.kick_user, 'event': events.NewMessage(pattern=r"\.kick(?: (\d+))?$", outgoing=True)},
            {'callback': self._admin_manager.promote_user, 'event': events.NewMessage(pattern=r"\.promote(?: (\d+))?$", outgoing=True)},
            {'callback': self._admin_manager.demote_user, 'event': events.NewMessage(pattern=r"\.demote(?: (\d+))?$", outgoing=True)},

            # Purge commands
            {'callback': self._purge_manager.purge_messages, 'event': events.NewMessage(pattern=r"\.purge(?: \d+)?$", outgoing=True)},

            # Spam commands
            {'callback': self.spam_menu, 'event': events.NewMessage(pattern=r"\.spam$", outgoing=True)},
            {'callback': self.handle_spam_command, 'event': events.NewMessage(pattern=r"\.spam (\d+) (.+)", outgoing=True)},
            {'callback': self.handle_delayspam_command, 'event': events.NewMessage(pattern=r"\.delayspam (\d+) (\d+) (.+)", outgoing=True)},
            {'callback': self._spam_manager.stop_spam, 'event': events.NewMessage(pattern=r"\.stopspam$", outgoing=True)},
        ]
