import asyncio
import json
from typing import List, Dict, Callable, Optional

from loguru import logger
from telethon import events
from telethon.tl.types import PhotoStrippedSize

import constants
from utility import delete_if_exists


IDENTIFICATION_TRIGGER_REGEX = r"^Who's that pokemon\?$"
POKEMON_REVEAL_REGEX = r'^(Nobody|The)(.+|\s)pokemon was (.+)'
SUCCESSFULL_IDENTIFICATION_REGEX = r'(.+) guessed in (.+)\s+The pokemon was (.+)'

TELEMETRY_REPORT = """Telemetry Report:
  - /guess dispatched: {0.messages_sent}
  - Responses processed: {0.responses_received}
  - Successful identifications: {0.successful_identifications}
  - Unsuccessful identifications: {0.unsuccessful_identifications}
  - Pokè Dollar (PD) accrued: {1}"""


class AutomationOrchestrator:
    """Manages the lifecycle and operational state of the automated identification process."""

    __slots__ = ('_is_active',)

    def __init__(self):
        self._is_active: bool = False

    def activate_automation(self) -> None:
        """Initiates the automated identification process."""
        self._is_active = True

    def deactivate_automation(self, activity_monitor: 'ActivityMonitor') -> None:
        """Terminates automated identification and resets the associated activity metrics."""
        activity_monitor.reset_metrics()
        self._is_active = False

    @property
    def is_automation_active(self) -> bool:
        """Returns the current automation state (active or inactive)."""
        return self._is_active

class ActivityMonitor:
    """Monitors and meticulously records key performance indicators of the identification process."""

    __slots__ = (
        '_messages_sent',
        '_responses_received',
        '_successful_identifications',
        '_unsuccessful_identifications'
    )
    
    def __init__(self):
        self._messages_sent: int = 0
        self._responses_received: int = 0
        self._successful_identifications: int = 0
        self._unsuccessful_identifications: int = 0

    def record_activity(
      self,
      message_sent: bool = False,
      response_received: bool = False,
      successful_identification: bool = False,
      unsuccessful_identification: bool = False
    ) -> None:
        """Records specific activity events, incrementing the corresponding counters."""
        if message_sent:
            self._messages_sent += 1
        if response_received:
            self._responses_received += 1
        if successful_identification:
            self._successful_identifications += 1
        if unsuccessful_identification:
            self._unsuccessful_identifications += 1

    def reset_metrics(self) -> None:
        """Resets all recorded performance metrics to their initial zero values."""
        self._messages_sent = 0
        self._responses_received = 0
        self._successful_identifications = 0
        self._unsuccessful_identifications = 0

    @property
    def messages_sent(self) -> int:
        return self._messages_sent

    @property
    def responses_received(self) -> int:
        return self._responses_received

    @property
    def successful_identifications(self) -> int:
        return self._successful_identifications

    @property
    def unsuccessful_identifications(self) -> int:
        return self._unsuccessful_identifications


class ImageMetadataCache:
    """Maintains a cache of metadata associated with recently processed images for subsequent correlation with identification results."""

    __slots__ = ('_metadata',)

    def __init__(self):
        self._metadata: Optional[list[str]] = None

    def store_metadata(self, dimensions: list[str]) -> None:
        """Stores image metadata, including dimensions and the associated message identifier."""
        self._metadata = dimensions

    def retrieve_metadata(self) -> Optional[str]:
        """Retrieves the stored image metadata and subsequently clears the cache to prevent stale data."""
        metadata = self._metadata
        self._metadata = None
        return metadata


class PokemonIdentificationEngine:
    """The core engine for identifying Pokemon and managing automation."""

    __slots__ = (
        '_client',
        'automation_orchestrator',
        'activity_monitor',
        'metadata_cache'
    )


    def __init__(self, client) -> None:
        self._client = client
        self.automation_orchestrator = AutomationOrchestrator()
        self.activity_monitor = ActivityMonitor()
        self.metadata_cache = ImageMetadataCache()

  
    def start(self) -> None:
        """Starts the Pokemon identification engine."""
        logger.info('Initializing Pokemon Identification Engine')

        asyncio.create_task(self._periodically_transmit_guess_commands())
        logger.info(f'[{self.__class__.__name__}] Created task: `_periodically_transmit_guess_commands`')

        for handler in self.event_handlers:
            callback = handler.get('callback')
            event = handler.get('event')
            self._client.add_event_handler(
               callback=callback, event=event
            )
            logger.info(f'[{self.__class__.__name__}] Added event handler: `{callback.__name__}`')

  
    async def _transmit_guess_command(self) -> None:
        """Transmits the guess command (/guess) to the designated chat."""
        await asyncio.sleep(constants.COOLDOWN())
        if self.automation_orchestrator.is_automation_active:
            await self._client.send_message(entity=constants.CHAT_ID, message='/guess')
            self.activity_monitor.record_activity(message_sent=True)

  
    async def _periodically_transmit_guess_commands(self) -> None:
        """Periodically transmits guess commands while automated identification is active."""
        while self._client.is_connected():
            try:
                await asyncio.sleep(constants.PERIODICALLY_GUESS_SECONDS)
                if self.automation_orchestrator.is_automation_active:
                    await self._transmit_guess_command()
            except (asyncio.CancelledError, ConnectionError) as e:
                logger.warning(f'[{self.__class__.__name__}] An error occurred during periodic command transmission: {e}', exc_info=True)

  
    async def handle_automation_control_request(self, event) -> None:
        """Handles user-initiated requests to control the automation process (on/off)."""
        action = event.raw_text.split()[-1]
        if action == 'on':
            if self.automation_orchestrator.is_automation_active:
                await event.edit('Automated identification already activate.')
            else:
                self.automation_orchestrator.activate_automation()
                await event.edit('Automated identification has been activated.')
        elif action == 'off':
            if self.automation_orchestrator.is_automation_active:
                telemetry_report = TELEMETRY_REPORT.format(self.activity_monitor, self.activity_monitor.successful_identifications * 5)
                message = f'Automated identification has been deactivated.\n{telemetry_report}'
                self.automation_orchestrator.deactivate_automation(self.activity_monitor)
                await event.edit(message)
            else:
              await event.edit('Automated identification already deactivate.')
        elif action == 'stats':
            telemetry_report = TELEMETRY_REPORT.format(self.activity_monitor, self.activity_monitor.successful_identifications * 5)
            await event.edit(telemetry_report)

  
    async def _handle_daily_quota_exceeded(self, event) -> None:
        """Handles the event of exceeding the daily identification quota, suspending automation."""
        if self.automation_orchestrator.is_automation_active:
            warning = 'daily guess allocation has been exhausted.\nAutomated identification procedures have been suspended.'
            telemetry_report = TELEMETRY_REPORT.format(self.activity_monitor, self.activity_monitor.successful_identifications * 5)
            message = f"{self._client.me.mention}'s {warning}\n{telemetry_report}"
            await self._client.send_message(entity=constants.CHAT_ID, message=message)
            self.automation_orchestrator.deactivate_automation(self.activity_monitor)
            logger.warning(f"[{self.__class__.__name__}] {self._client.me.mention}'s {'- @' + self._client.me.username if self._client.me.username else ''} {warning}")

  
    def _get_stripped_size(self, photo) -> str:
        try:
            return [str(size) for size in photo.sizes if isinstance(size, PhotoStrippedSize)][0]
        except IndexError as ie:
            logger.exception(f'cannot find stripped size: {ie}')
            return None


    async def process_received_imagery(self, event) -> None:
        """Processes received images to identify Pokemon."""
        if not self.automation_orchestrator.is_automation_active:
            return

        if not constants.POKEMON:
            logger.warning(f'[{self.__class__.__name__}] `constants.POKEMON` is not configured. Identification procedures cannot proceed.')
            return

        self.activity_monitor.record_activity(response_received=True)

        stripped_size = self._get_stripped_size(event.message.photo)
        if not stripped_size:
            await event.reply(message='something went wrong')
            return
        pokemon_name = None
        for name, expected_sizes in constants.POKEMON.items():
            if stripped_size == expected_sizes:
              pokemon_name = name
              break

        if pokemon_name is not None:
            await asyncio.sleep(constants.COOLDOWN())
            await event.reply(pokemon_name)
            self.activity_monitor.record_activity(successful_identification=True)
        else:
            self.metadata_cache.store_metadata(stripped_size)
            self.activity_monitor.record_activity(unsuccessful_identification=True)
            logger.warning(f'[{self.__class__.__name__}] pokemon name not matching')
            

    async def handle_pokemon_reveal_event(self, event) -> None:
        """Handles the "pokemon was" event, associating the revealed name with stored metadata."""
        revealed_name = event.raw_text.split()[-1]
        metadata = self.metadata_cache.retrieve_metadata()
        if metadata is not None:
            try:
                filename = 'new_pokemon.json'
                delete_if_exists(filename)
                NEW_POKEMON = constants.POKEMON
                NEW_POKEMON[revealed_name] = metadata
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(NEW_POKEMON, f, indent=4)
                await event.reply(file=filename)
                delete_if_exists(filename)
            except Exception as e:
                logger.warning(f'[{self.__class__.__name__}] An error occurred during sending metadata: {e}')

        await self._transmit_guess_command()

  
    async def handle_successfull_identification(self, event) -> None:
        if event.raw_text.endswith('💵'):
            await self._transmit_guess_command()
        else:
            await self._handle_daily_quota_exceeded(event)


    @property
    def event_handlers(self) -> List[Dict[str, Callable | events.NewMessage]]:
        """Returns a list of event handlers."""
        return [
            {'callback': self.process_received_imagery, 'event': events.NewMessage(pattern=IDENTIFICATION_TRIGGER_REGEX, from_users=constants.HEXA_BOT_ID, chats=constants.CHAT_ID)},
            {'callback': self.handle_successfull_identification, 'event': events.NewMessage(pattern=SUCCESSFULL_IDENTIFICATION_REGEX, from_users=constants.HEXA_BOT_ID, chats=constants.CHAT_ID)},
            {'callback': self.handle_pokemon_reveal_event, 'event': events.NewMessage(pattern=POKEMON_REVEAL_REGEX, from_users=constants.HEXA_BOT_ID, chats=constants.CHAT_ID)}
        ]
