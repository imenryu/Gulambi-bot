import time
import platform
import psutil  # To get system details
from telethon import events
from platform import python_version
from telethon import version

import constants  # Import constants

class AliveHandler:
    def __init__(self, client):
        self._client = client

    async def alive_command(self, event):
        """Responds with bot status when `.alive` is used."""
        start_time = time.time()
        await event.edit("Checking...")
        ping_ms = (time.time() - start_time) * 1000

        # Get system info
        os_name = platform.system()
        os_version = platform.release()
        cpu_usage = psutil.cpu_percent()
        ram_usage = psutil.virtual_memory().percent

        alive_message = (
            "🔹 **__BOT STATUS__** 🔹\n\n"
            f"👤 **Owner:** `{constants.OWNER_NAME}`\n"
            f"⚡ **Uptime:** `{ping_ms:.2f}ms`\n"
            f"🐍 **Python:** `{python_version()}`\n"
            f"📡 **Telethon:** `{version.__version__}`\n"
            f"📌 **Bot Version:** `{constants.BOT_VERSION}`\n\n"
            f"🖥 **System:** `{os_name} {os_version}`\n"
            f"💾 **CPU Usage:** `{cpu_usage}%`\n"
            f"🧠 **RAM Usage:** `{ram_usage}%`\n"
            "➜ **Creator:** ``@Exryuh`` # credit hataya to gand mar lunga
        )

        await event.delete()  # Delete "Checking..." message
        await event.reply(alive_message, file=constants.ALIVE_IMG_PATH)  # Use image path from constants

    def register(self):
        """Registers the `.alive` command with the client."""
        self._client.add_event_handler(
            self.alive_command,
            events.NewMessage(pattern=r"^\.alive$", outgoing=True)
        )
