from __future__ import annotations

import asyncio
import regex
from typing import TYPE_CHECKING, List, Dict, Callable, Optional, Tuple
from enum import Enum, auto
import time

from loguru import logger
from telethon import events
from telethon.errors import DataInvalidError, MessageIdInvalidError

import constants

if TYPE_CHECKING:
    from telethon.tl import BotCallbackAnswer, Message

TELEMETRY_REPORT = """
 ✨ Hunting Report 📊
---------------------
{report_lines}
---------------------
💰 Pokè Dollar (PD) Earned: {poke_dollars_accrued} PD
⏱️  Time Active: {formatted_duration}
⚡ PD per Hour (Estimate): {pd_per_hour:.2f} PD/hour
"""

TELEMETRY_REPORT_LINE = "  {metric_name}: {value}"

METRIC_NAMES = {
    "hunt_commands_sent": "🏹 /hunt commands sent",
    "responses_processed": "✅ Responses processed",
    "responses_skipped": "🚫 Responses skipped",
    "successful_encounters": "🏆 Successful encounters",
    "unsuccessful_encounters": "❌ Unsuccessful encounters",
    "skipped_encounters": "回避 Skipped encounters",
    "skipped_trainers": "🏃‍♂️ Skipped trainers",
    "pokemon_switched": "🔄 Pokemon switched",
    "encounter_success_rate": "🎯 Encounter success rate",
    "response_skip_rate": " пропускать Response skip rate",
    "items_found": "📦 Items found",
    "pokeball_usage": "⚽ Pokeball Usage",
}

POKEBALL_BUTTON_TEXT_MAP = {
    "Nest",
    "Repeat",
    "Ultra",
    "Great",
    "Regular"
}


class AutomationOrchestrator:
    """Manages automation lifecycle and state."""

    __slots__ = ('_is_active', '_start_time')

    def __init__(self):
        self._is_active: bool = False
        self._start_time: Optional[float] = None

    def activate_automation(self) -> None:
        """Activates automation, recording start time."""
        if self._is_active:
            logger.warning("Automation is already active.")
            return
        self._is_active = True
        self._start_time = time.time()
        logger.info("Automation activated.")

    def deactivate_automation(self, activity_monitor: 'ActivityMonitor') -> None:
        """Deactivates automation and resets metrics."""
        if not self._is_active:
            logger.warning("Automation is already inactive.")
            return
        activity_monitor.reset_metrics()
        self._is_active = False
        self._start_time = None
        logger.info("Automation deactivated and metrics reset.")

    @property
    def is_automation_active(self) -> bool:
        """Returns automation status."""
        return self._is_active

    @property
    def start_time(self) -> Optional[float]:
        """Returns automation start time."""
        return self._start_time


class ActivityType(Enum):
    MESSAGE_SENT = auto()
    RESPONSE_RECEIVED = auto()
    RESPONSE_SKIPPED = auto()
    SUCCESSFUL_ENCOUNTER = auto()
    UNSUCCESSFUL_ENCOUNTER = auto()
    SKIPPED_ENCOUNTER = auto()
    SKIPPED_TRAINER = auto()
    SWITCHED_POKEMON = auto()
    POKE_DOLLARS_ACCRUED = auto()
    ITEM_FOUND = auto()
    POKEBALL_USED = auto()


class ActivityMonitor:
    """Monitors and records hunting activities."""

    __slots__ = (
        '_messages_sent',
        '_responses_received',
        '_responses_skipped',
        '_successful_encounter',
        '_unsuccessful_encounter',
        '_skipped_encounter',
        '_skipped_trainers',
        '_switched_pokemon',
        '_poke_dollars_accrued',
        '_items_found',
        '_pokeball_usage'
    )

    def __init__(self):
        self._messages_sent: int = 0
        self._responses_received: int = 0
        self._responses_skipped: int = 0
        self._successful_encounter: int = 0
        self._unsuccessful_encounter: int = 0
        self._skipped_encounter: int = 0
        self._skipped_trainers: int = 0
        self._switched_pokemon: int = 0
        self._poke_dollars_accrued: int = 0
        self._items_found: list = []
        self._pokeball_usage: Dict[str, int] = {}

    def record_activity(self, activity_type: ActivityType, value=None) -> None:
        """Records activity events, incrementing counters and handling values."""
        try:
            if activity_type == ActivityType.MESSAGE_SENT:
                self._messages_sent += 1
            elif activity_type == ActivityType.RESPONSE_RECEIVED:
                self._responses_received += 1
            elif activity_type == ActivityType.RESPONSE_SKIPPED:
                self._responses_skipped += 1
            elif activity_type == ActivityType.SUCCESSFUL_ENCOUNTER:
                self._successful_encounter += 1
            elif activity_type == ActivityType.UNSUCCESSFUL_ENCOUNTER:
                self._unsuccessful_encounter += 1
            elif activity_type == ActivityType.SKIPPED_ENCOUNTER:
                self._skipped_encounter += 1
            elif activity_type == ActivityType.SKIPPED_TRAINER:
                self._skipped_trainers += 1
            elif activity_type == ActivityType.SWITCHED_POKEMON:
                self._switched_pokemon += 1
            elif activity_type == ActivityType.POKE_DOLLARS_ACCRUED:
                if not isinstance(value, (int, float)):
                    raise ValueError(f"Value for {activity_type.name} must be numeric.")
                self._poke_dollars_accrued += int(value)
            elif activity_type == ActivityType.ITEM_FOUND:
                if not isinstance(value, str):
                    raise ValueError(f"Value for {activity_type.name} must be a string (item name).")
                self._items_found.append(value)
            elif activity_type == ActivityType.POKEBALL_USED:
                if not isinstance(value, str):
                    raise ValueError(f"Value for {activity_type.name} must be a string (ball name).")
                ball_name = value.strip()
                if not ball_name:
                    logger.warning(f"Empty pokeball name provided for recording.")
                    return
                self._pokeball_usage[ball_name] = self._pokeball_usage.get(ball_name, 0) + 1
            else:
                raise ValueError(f'Invalid ActivityType: {activity_type.name}')
        except ValueError as ve:
            logger.exception(f"Error recording activity {activity_type.name}: {ve}")
        except Exception as e:
            logger.exception(f"Unexpected error during activity recording for {activity_type.name}")


    def reset_metrics(self) -> None:
        """Resets all activity metrics."""
        self._messages_sent = 0
        self._responses_received = 0
        self._responses_skipped = 0
        self._successful_encounter = 0
        self._unsuccessful_encounter = 0
        self._skipped_encounter = 0
        self._skipped_trainers = 0
        self._switched_pokemon = 0
        self._poke_dollars_accrued = 0
        self._items_found = []
        self._pokeball_usage = {}
        logger.debug("Activity metrics reset.")


    def generate_telemetry_report(self, start_time: Optional[float]) -> str:
        """Generates formatted telemetry report with detailed metrics and calculations."""
        report_lines = []

        report_lines.append(
            TELEMETRY_REPORT_LINE.format(metric_name=METRIC_NAMES["hunt_commands_sent"], value=self._messages_sent)
        )
        report_lines.append(
            TELEMETRY_REPORT_LINE.format(metric_name=METRIC_NAMES["responses_processed"], value=self._responses_received)
        )
        report_lines.append(
            TELEMETRY_REPORT_LINE.format(metric_name=METRIC_NAMES["responses_skipped"], value=self._responses_skipped)
        )
        report_lines.append(
            TELEMETRY_REPORT_LINE.format(metric_name=METRIC_NAMES["successful_encounters"], value=self._successful_encounter)
        )
        report_lines.append(
            TELEMETRY_REPORT_LINE.format(metric_name=METRIC_NAMES["unsuccessful_encounters"], value=self._unsuccessful_encounter)
        )
        report_lines.append(
            TELEMETRY_REPORT_LINE.format(metric_name=METRIC_NAMES["skipped_encounters"], value=self._skipped_encounter)
        )
        report_lines.append(
            TELEMETRY_REPORT_LINE.format(metric_name=METRIC_NAMES["skipped_trainers"], value=self._skipped_trainers)
        )
        report_lines.append(
            TELEMETRY_REPORT_LINE.format(metric_name=METRIC_NAMES["pokemon_switched"], value=self._switched_pokemon)
        )

        if self._responses_received > 0:
            encounter_rate = (self._successful_encounter / self._responses_received) * 100
            report_lines.append(
                TELEMETRY_REPORT_LINE.format(metric_name=METRIC_NAMES["encounter_success_rate"], value=f"{encounter_rate:.2f}%")
            )
        else:
            report_lines.append(
                TELEMETRY_REPORT_LINE.format(metric_name=METRIC_NAMES["encounter_success_rate"], value="N/A")
            )

        if self._messages_sent > 0:
            response_skip_rate = (self._responses_skipped / self._messages_sent) * 100
            report_lines.append(
                TELEMETRY_REPORT_LINE.format(metric_name=METRIC_NAMES["response_skip_rate"], value=f"{response_skip_rate:.2f}%")
            )
        else:
            report_lines.append(
                TELEMETRY_REPORT_LINE.format(metric_name=METRIC_NAMES["response_skip_rate"], value="N/A")
            )

        if self._items_found:
            items_list = ", ".join(self._items_found)
            report_lines.append(
                TELEMETRY_REPORT_LINE.format(metric_name=METRIC_NAMES["items_found"], value=items_list)
            )
        else:
            report_lines.append(
                 TELEMETRY_REPORT_LINE.format(metric_name=METRIC_NAMES["items_found"], value="None")
            )

        pokeball_usage_lines = []
        for ball_name, count in self._pokeball_usage.items():
            pokeball_usage_lines.append(f"{ball_name}: {count}")
        pokeball_usage_str = ", ".join(pokeball_usage_lines) if pokeball_usage_lines else "None"
        report_lines.append(
            TELEMETRY_REPORT_LINE.format(metric_name=METRIC_NAMES["pokeball_usage"], value=pokeball_usage_str)
        )

        if start_time:
            duration_seconds = time.time() - start_time
            hours = int(duration_seconds // 3600)
            minutes = int((duration_seconds % 3600) // 60)
            seconds = int(duration_seconds % 60)
            formatted_duration = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

            if duration_seconds > 0 and self._poke_dollars_accrued > 0:
                pd_per_hour = (self._poke_dollars_accrued / duration_seconds) * 3600
            else:
                pd_per_hour = 0.0
        else:
            formatted_duration = "N/A"
            pd_per_hour = 0.0


        report_string = TELEMETRY_REPORT.format(
            report_lines="\n".join(report_lines),
            poke_dollars_accrued=self._poke_dollars_accrued,
            formatted_duration=formatted_duration,
            pd_per_hour=pd_per_hour
        )
        return report_string



class PokemonHuntingEngine:
    """Engine for Pokemon hunting automation."""

    __slots__ = (
        '_client',
        'automation_orchestrator',
        'activity_monitor'
    )

    def __init__(self, client) -> None:
        """Initializes the hunting engine."""
        self._client = client
        self.automation_orchestrator = AutomationOrchestrator()
        self.activity_monitor = ActivityMonitor()


    def start(self) -> None:
        """Starts the hunting engine and periodic tasks."""
        logger.info('Initializing Pokemon Hunting Engine...')
        asyncio.create_task(self._periodically_transmit_hunt_commands())
        logger.info(f'[{self.__class__.__name__}] Created task: `_periodically_transmit_hunt_commands`')
        self._register_event_handlers()
        logger.info('Pokemon Hunting Engine started.')


    def _register_event_handlers(self) -> None:
        """Registers event handlers to the client."""
        for handler in self.event_handlers:
            callback = handler.get('callback')
            event = handler.get('event')
            self._client.add_event_handler(
                callback=callback, event=event
            )
            logger.info(f'[{self.__class__.__name__}] Registered event handler: `{callback.__name__}`')


    def _calculate_health_percentage(self, max_hp: int, current_hp: int) -> int:
        """Calculates health percentage, handling potential errors."""
        if max_hp <= 0:
            raise ValueError("Total health must be greater than zero.")
        if current_hp < 0 or current_hp > max_hp:
            raise ValueError("Current health must be between 0 and the total health.")
        health_percentage = round((current_hp / max_hp) * 100)
        return health_percentage


    async def _reload_message(self, event) -> Optional[Message]:
        try:
            await asyncio.sleep(1)
            msg = await self._client.get_messages(constants.HEXA_BOT_ID, ids=event.id)
        except ValueError:
            return
        return msg

    async def _click_button(self, event, i=None, j=None, text=None, data=None) -> Optional[BotCallbackAnswer]:
        response = None
        count = 0
        while count <= 5:
            count += 1
            await asyncio.sleep(constants.COOLDOWN())
            response = await event.click(i=i, j=j, text=text, data=None)
            if not response:
               await asyncio.sleep(1)
               continue

            response_text = str(response.message).lower() if response and response.message else ""
            if any(
                   substring in response_text for substring
                   in ["none", "fled", "caught", "in battle", "catching", "failed", "choose", "go, "]
               ):
               break
            elif any(
                   substring in response_text for substring
                   in ["wait", "try again"]
               ):
               await asyncio.sleep(1)
            else:
               logger.debug(response)
        return response

    async def _transmit_hunt_command(self) -> None:
        """Transmits the /hunt command, handling potential connection issues."""
        try:
            await asyncio.sleep(constants.COOLDOWN())
            if self.automation_orchestrator.is_automation_active:
                await self._client.send_message(entity=constants.HEXA_BOT_ID, message='/hunt')
                self.activity_monitor.record_activity(activity_type=ActivityType.MESSAGE_SENT)
        except ConnectionError as ce:
            logger.warning(f"Connection error when sending /hunt command: {ce}")
        except Exception as e:
            logger.exception(f"Unexpected error during /hunt command transmission: {e}")


    async def _periodically_transmit_hunt_commands(self) -> None:
        """Periodically sends hunt commands while automation is active, with error handling."""
        while self._client.is_connected():
            try:
                await asyncio.sleep(constants.PERIODICALLY_HUNT_SECONDS)
                if self.automation_orchestrator.is_automation_active:
                    await self._transmit_hunt_command()
            except asyncio.CancelledError:
                logger.info("Periodic hunt command task cancelled.")
                break
            except ConnectionError:
                logger.warning("Connection error during periodic hunt command transmission. Retrying...")
            except Exception as e:
                logger.exception(f"Unexpected error in periodic hunt command task: {e}")


    async def handle_automation_control_request(self, event: events.NewMessage.Event) -> None:
        """Handles automation control commands (on/off/stats)."""
        command_parts = event.raw_text.split()
        if len(command_parts) != 2:
            await event.respond("Invalid command format. Use: `/automhunt on|off|stats`")
            return

        action = command_parts[1].lower()

        if action == 'on':
            self.automation_orchestrator.activate_automation()
            await event.edit('Automated hunting has been activated.')
        elif action == 'off':
            telemetry_report = self.activity_monitor.generate_telemetry_report(self.automation_orchestrator.start_time)
            message = f'Automated hunting has been deactivated.\n{telemetry_report}'
            self.automation_orchestrator.deactivate_automation(self.activity_monitor)
            await event.edit(message)
        elif action == 'stats':
            telemetry_report = self.activity_monitor.generate_telemetry_report(self.automation_orchestrator.start_time)
            await event.edit(telemetry_report)
        else:
            await event.respond("Invalid action. Use: `.hunt on|off|stats`")


    async def poki_list(self, event: events.NewMessage.Event) -> None:
        """Handles the poki_list command to display allowed pokemons."""
        pokemon = ', '.join(constants.REPEAT_BALL)
        await event.edit(f"Pokèmon List: {pokemon}")


    async def handle_daily_quota_exceeded(self, event: events.NewMessage.Event) -> None:
        """Handles daily quota exceeded messages, deactivating automation."""
        substring = 'daily hunt limit reached'
        if substring in event.raw_text.lower() and self.automation_orchestrator.is_automation_active:
            self.activity_monitor.record_activity(activity_type=ActivityType.RESPONSE_RECEIVED)
            warning = 'Daily hunt quota reached. Automated hunting deactivated.'
            telemetry_report = self.activity_monitor.generate_telemetry_report(self.automation_orchestrator.start_time)
            message = f"<a href='tg://user?id={self._client.me.id}'>{self._client.me.first_name}</a> {warning}\n{telemetry_report}"
            await self._client.send_message(entity=constants.CHAT_ID, message=message)
            self.automation_orchestrator.deactivate_automation(self.activity_monitor)
            logger.warning(f"[{self.__class__.__name__}] @{self._client.me.username}'s {warning}")



    async def hunt_or_pass(self, event: events.NewMessage.Event) -> None:
        """Handles wild Pokemon encounters, deciding to hunt or pass based on config."""
        if not self.automation_orchestrator.is_automation_active:
            return

        if ('shiny' in event.raw_text.lower() and
                event.raw_text.lower().endswith('found!')):
            self.activity_monitor.record_activity(activity_type=ActivityType.RESPONSE_RECEIVED)
            warning = 'Shiny Pokèmon found! Automated hunting deactivated.'
            telemetry_report = self.activity_monitor.generate_telemetry_report()
            message = f"<a href='tg://user?id={self._client.me.id}'>{self._client.me.first_name}</a> {warning}\n{telemetry_report}"
            await self._client.send_message(entity=constants.CHAT_ID, message=message)
            self.automation_orchestrator.deactivate_automation(self.activity_monitor)
            logger.warning(f"[{self.__class__.__name__}] @{self._client.me.username}'s {warning}")

        elif "A wild" in event.raw_text:
            self.activity_monitor.record_activity(activity_type=ActivityType.RESPONSE_RECEIVED)
            name_match = regex.search(r"A wild (.+?) \(", event.raw_text)
            pok_name = name_match.group(1).strip()
            logger.debug(f"Wild Pokemon encountered: {pok_name}")
            for ball_name in POKEBALL_BUTTON_TEXT_MAP:
                if pok_name in getattr(constants, f'{ball_name.upper()}_BALL', []):
                    await asyncio.sleep(constants.COOLDOWN())
                    try:
                        await self._click_button(event=event, i=0, j=0)
                        break
                    except (DataInvalidError, MessageIdInvalidError) as e:
                        logger.warning(f'Failed to click button for {pok_name}: {e}')
                    except Exception as e:
                        logger.exception(f"Unexpected error clicking button for {pok_name}: {e}")
            else:
                self.activity_monitor.record_activity(activity_type=ActivityType.SKIPPED_ENCOUNTER)
                await self._transmit_hunt_command()

    
    async def battlefirst(self, event):
        substring = 'Battle begins!'
        if substring in event.raw_text and self.automation_orchestrator.is_automation_active:
          wild_pokemon_name_match = regex.search(r"Wild ([^\[]+?)\s*\[.*\]\nLv\. \d+\s+•\s+HP \d+/\d+", event.raw_text)
          
          if wild_pokemon_name_match:
            pok_name = wild_pokemon_name_match.group(1).strip()
            
            wild_pokemon_hp_match = regex.search(r"Wild .* \[.*\]\nLv\. \d+\s+•\s+HP (\d+)/(\d+)", event.raw_text)

            if wild_pokemon_hp_match:
                wild_max_hp = int(wild_pokemon_hp_match.group(2))
                if wild_max_hp <= 90:
                    logger.debug(f"{pok_name} is low level (HP: {wild_max_hp}), using Poke Balls directly.")
                    await asyncio.sleep(constants.COOLDOWN())
                    try:
                        await event.click(text="Poke Balls")
                        logger.info('clicked on btn poke balls')
                    except (DataInvalidError, MessageIdInvalidError) as e:
                        logger.warning(f'Failed to click "Poke Balls" for {pok_name}: {e}')
                    except Exception as e:
                        logger.exception(f'Unexpected error clicking "Poke Balls" for {pok_name}: {e}')
                else:
                    await asyncio.sleep(2)
                    try:
                        await event.click(0, 0)
                    except (DataInvalidError, MessageIdInvalidError) as e:
                        logger.warning(f'Failed to click first option for high-level {pok_name}: {e}')
                    except Exception as e:
                        logger.exception(f'Unexpected error clicking first option for high-level {pok_name}: {e}')
            else:
                logger.warning(f"Wild Pokemon HP info not found in battle message for {pok_name}.")

    async def battle(self, event):
        substring = 'Wild'
        if substring in event.raw_text and self.automation_orchestrator.is_automation_active:
            wild_pokemon_name_match = regex.search(r"Wild ([^\[]+?)\s*\[.*\]\nLv\. \d+\s+•\s+HP \d+/\d+", event.raw_text)
            if wild_pokemon_name_match:
                pok_name = wild_pokemon_name_match.group(1).strip()
                wild_pokemon_hp_match = regex.search(r"Wild .* \[.*\]\nLv\. \d+  •  HP (\d+)/(\d+)", event.raw_text)
                if wild_pokemon_hp_match:
                    wild_max_hp = int(wild_pokemon_hp_match.group(2))
                    wild_current_hp = int(wild_pokemon_hp_match.group(1))
                    wild_health_percentage = (wild_current_hp / wild_max_hp) * 100

                    if wild_current_hp > 90:
                        await asyncio.sleep(1)
                        try:
                        # Click the first option 5 times
                            for _ in range(5):
                                await event.click(0, 0)
                                await asyncio.sleep(1)  # Add a small delay between clicks
                        except Exception as e:
                            if not isinstance(e, MessageIdInvalidError):  # Suppress MessageIdInvalidError
                                logger.warning(f'Failed to click first option for high-level {pok_name}: {e}')

                    if wild_current_hp <= 90:
                        await asyncio.sleep(1)
                        try:
                            # Click "Poke Balls" 5 times
                            for _ in range(5):
                                await event.click(text="Poke Balls")
                                await asyncio.sleep(1)  # Add a small delay between clicks

                            if pok_name in constants.REGULAR_BALL:
                                await asyncio.sleep(1)
                                # Click "Regular" 5 times
                                for _ in range(5):
                                    await event.click(text="Regular")
                                    await asyncio.sleep(1)  # Add a small delay between clicks

                            elif pok_name in constants.REPEAT_BALL:
                                await asyncio.sleep(1)
                                # Click "Repeat" 5 times
                                for _ in range(5):
                                    await event.click(text="Repeat")
                                    await asyncio.sleep(1)  # Add a small delay between clicks

                        except Exception as e:
                            if not isinstance(e, MessageIdInvalidError):  # Suppress MessageIdInvalidError
                                logger.exception(f"Failed to click buttons for {pok_name} with low health: {e}")

                    logger.info(f"{pok_name} health percentage: {wild_health_percentage}%")
                else:
                    logger.info(f"Wild Pokemon {pok_name} HP not found in the battle description.")
            else:
                logger.info("Wild Pokemon name not found in the battle description.")

   
    async def handle_after_battle(self, event: events.MessageEdited.Event) -> None:
        """Handles messages indicating encounter skipped (fled, caught, etc.), and records Pokeball usage on catch."""
        if not self.automation_orchestrator.is_automation_active:
            return

        if any(
              substring in event.raw_text for substring
              in ["fled", "💵", "You caught"]
           ):
            pd_match = regex.search(r"\+(\d+) 💵", event.raw_text)
            if pd_match:
                pd = pd_match.group(1)
                self.activity_monitor.record_activity(activity_type=ActivityType.POKE_DOLLARS_ACCRUED, value=int(pd))
            await self._transmit_hunt_command()
  
    async def skip(self, event: events.NewMessage.Event) -> None:
        """Handles trainer encounter skip."""
        if not self.automation_orchestrator.is_automation_active:
            return

        trainer_match = regex.search(r"expert trainer", event.raw_text.lower())
        tm_match = regex.search(r"TM(\d+) 💿 found!", event.raw_text)
        stone_match = regex.search(r"(.+) mega stone found!", event.raw_text.lower())

        if trainer_match:
            self.activity_monitor.record_activity(activity_type=ActivityType.SKIPPED_TRAINER)
            await self._transmit_hunt_command()
        elif tm_match:
            tm = tm_match.group(1)
            self.activity_monitor.record_activity(activity_type=ActivityType.ITEM_FOUND, value=f"TM{tm}")
            await self._transmit_hunt_command()
        elif stone_match:
            stone = stone_match.group(1)
            self.activity_monitor.record_activity(activity_type=ActivityType.ITEM_FOUND, value=f"{stone.capitalize()} stone")
            await self._transmit_hunt_command()

    async def pokeSwitch(self, event: events.MessageEdited.Event) -> None:
        """Handles Pokemon switch requests during battle."""
        substring = 'Choose your next pokemon.'
        if substring in event.raw_text and self.automation_orchestrator.is_automation_active:
            self.activity_monitor.record_activity(activity_type=ActivityType.SWITCHED_POKEMON)
            buttons_to_click: List[str] = []
            for row in event.reply_markup.rows:
                for button in row.buttons:
                    button_text = button.text.strip()
                    if button_text and button_text != '🔙' and not button.text.isspace():
                        buttons_to_click.append(button_text)
            if not buttons_to_click:
                warning = 'No available pokemon to switch to.'
                logger.warning(warning)
                await event.reply(message=warning)
                return
            button_clicked = buttons_to_click[0]
            logger.debug(f"Switching to Pokemon: {button_clicked}")
            try:
                await self._click_button(event=event, text=button_clicked)
            except (DataInvalidError, MessageIdInvalidError) as e:
                logger.warning(f'Failed to click button: `{button_clicked}`: {e}')
            except Exception as e:
                logger.exception(f'Unexpected error clicking Pokemon switch button `{button_clicked}`: {e}')

    @property
    def event_handlers(self) -> List[Dict[str, Callable | events.NewMessage]]:
        """Returns a list of event handler definitions."""
        return [
            {'callback': self.handle_daily_quota_exceeded, 'event': events.NewMessage(chats=constants.HEXA_BOT_ID)},
            {'callback': self.hunt_or_pass, 'event': events.NewMessage(chats=constants.HEXA_BOT_ID)},
            {'callback': self.battlefirst, 'event': events.NewMessage(chats=constants.HEXA_BOT_ID)},
            {'callback': self.battle, 'event': events.MessageEdited(chats=constants.HEXA_BOT_ID)},
            {'callback': self.handle_after_battle, 'event': events.MessageEdited(chats=constants.HEXA_BOT_ID)},
            {'callback': self.skip, 'event': events.NewMessage(chats=constants.HEXA_BOT_ID)},
            {'callback': self.pokeSwitch, 'event': events.MessageEdited(chats=constants.HEXA_BOT_ID)}
        ]
