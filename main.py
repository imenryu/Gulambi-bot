import asyncio
import uvloop
from loguru import logger
from telethon import TelegramClient
from telethon.errors import ApiIdInvalidError, AuthKeyDuplicatedError, FloodError
from telethon.sessions import StringSession

import constants
import health_checker
from manager import Manager

async def main():
    while True:  # Keep the bot running
        try:
            # Initialize the Telegram client
            client = TelegramClient(
                session=StringSession(constants.SESSION),
                api_id=constants.API_ID,
                api_hash=constants.API_HASH,
                app_version=constants.__version__,
                auto_reconnect=True
            )

            # Start the client and fetch the bot's profile
            await client.start()
            me = await client.get_me()
            client.me = me
            client.parse_mode = 'html'

            # Initialize the Manager and start automations
            manager = Manager(client)
            manager.start()

            logger.info(f'Userbot Login successful: {me.first_name} - @{me.username} ({me.id})')

            # Keep the client running until disconnected
            await client.run_until_disconnected()

        except AuthKeyDuplicatedError:
            logger.error("AuthKeyDuplicatedError: Invalid session. Please update SESSION.")
            await asyncio.sleep(10)  # Prevent crash loops
            continue  # Restart the loop with a new session

        except (ApiIdInvalidError, FloodError) as e:
            logger.exception(f'Error occurred when logging in: {e}')
            await asyncio.sleep(10)  # Prevent crash loops
            continue

        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            await asyncio.sleep(10)  # Prevent crash loops
            continue

# Run health checker and start the bot
health_checker.check()
try:
    with asyncio.Runner(loop_factory=uvloop.new_event_loop) as runner:
        runner.run(main())
except KeyboardInterrupt:
    logger.info("Bot stopped manually.")
