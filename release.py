import asyncio
from telethon import events
from loguru import logger

class PokemonReleaseManager:
    def __init__(self, client):
        self.client = client
        self.release_task = None
        self.running = False
        self.current_chat_id = None  # Stores the chat where `.release on` was used
        self.release_list = set()  # Pokémon to be released

    async def release_pokemon(self):
        """Releases Pokémon in the chat where `.release on` was used."""
        while self.running:
            try:
                if not self.current_chat_id:
                    logger.warning("No active chat ID for release. Stopping...")
                    self.running = False
                    return  

                for pokemon in list(self.release_list):  # Convert to list to avoid set mutation issues
                    logger.info(f"Releasing {pokemon} in chat {self.current_chat_id}...")
                    
                    while self.running:
                        await self.client.send_message(self.current_chat_id, f"/release {pokemon}")
                        await asyncio.sleep(2)  # Wait for bot response

                        async for message in self.client.iter_messages(self.current_chat_id, limit=1):
                            if message.buttons:
                                # Step 1: Select the first Pokémon if multiple exist
                                await message.click(0, 0)  # Click first button [1]
                                await asyncio.sleep(4)  # Wait for next bot response

                                # Step 2: Confirm release by clicking the first "Release" button
                                async for confirm_message in self.client.iter_messages(self.current_chat_id, limit=1):
                                    if confirm_message.buttons:
                                        for i, row in enumerate(confirm_message.buttons):
                                            for j, button in enumerate(row):
                                                if "Release" in button.text:
                                                    await confirm_message.click(i, j)  # Click the "Release" button
                                                    logger.info(f"{pokemon} released!")
                                                    break

                                await asyncio.sleep(2)  # Wait for confirmation
                                break  # Move to the next Pokémon

                        await asyncio.sleep(3)  # Wait before releasing the next Pokémon

                    self.release_list.remove(pokemon)  # Remove from list after releasing

            except Exception as e:
                logger.error(f"Error: {e}")
                await asyncio.sleep(5)  # Retry delay

    async def start_releasing(self, event):
        """Starts the auto-release process in the chat where the command was sent."""
        if not self.running:
            self.running = True
            self.current_chat_id = event.chat_id  # Store chat ID
            self.release_task = asyncio.create_task(self.release_pokemon())
            await event.edit("Pokémon auto-release started in this chat!")  
        else:
            await event.edit("Release is already running!")  

    async def stop_releasing(self, event):
        """Stops the release process."""
        if self.running:
            self.running = False
            if self.release_task:
                self.release_task.cancel()
                self.release_task = None
            self.current_chat_id = None  
            await event.edit("Pokémon auto-release stopped!")  
        else:
            await event.edit("No active release process.")  

    async def add_pokemon(self, event):
        """Adds a Pokémon to the release list."""
        args = event.pattern_match.group(1)
        if not args:
            await event.edit("**Usage:** `.release add <pokemon>`")
            return
        pokemon_name = args.strip().lower()
        self.release_list.add(pokemon_name)
        await event.edit(f"**{pokemon_name.capitalize()}** added to the release list!")

    async def remove_pokemon(self, event):
        """Removes a Pokémon from the release list."""
        args = event.pattern_match.group(1)
        if not args:
            await event.edit("**Usage:** `.release remove <pokemon>`")
            return
        pokemon_name = args.strip().lower()
        if pokemon_name in self.release_list:
            self.release_list.remove(pokemon_name)
            await event.edit(f"**{pokemon_name.capitalize()}** removed from the release list!")
        else:
            await event.edit(f"**{pokemon_name.capitalize()}** is not in the release list.")

    async def list_pokemon(self, event):
        """Shows the Pokémon set for release."""
        if not self.release_list:
            await event.edit("Your release list is empty!")
        else:
            release_list_str = ", ".join(sorted(self.release_list))
            await event.edit(f"**Pokémon set for release:**\n{release_list_str}")

    async def show_release_help(self, event):
        """Shows available release commands."""
        release_help_message = """**Release Pokémon Commands**
• `.release on` - Start auto-releasing Pokémon  
• `.release off` - Stop auto-releasing Pokémon  
• `.release add <pokemon>` - Add a Pokémon to the release list  
• `.release remove <pokemon>` - Remove a Pokémon from the release list  
• `.release list` - Show the list of Pokémon set for release  
"""
        await event.edit(release_help_message)
