import asyncio
import html
import sys
import traceback
from typing import List, Dict, Any, Callable

import aiofiles
from loguru import logger
from meval import meval
from telethon import events

import constants
from utility import delete_if_exists

class ExpressionEvaluator:
    """
    A class to encapsulate the code evaluation functionality, 
    including namespace handling, code cleanup, expression evaluation, 
    and output handling.
    """

    __slots__ = ('_client',)

    def __init__(self, client) -> None:
        self._client = client

    def start(self) -> None:
        """Starts the Evaluator."""
        logger.info('Initializing Evaluator')

        for handler in self.event_handlers:
            callback = handler.get('callback')
            event = handler.get('event')
            self._client.add_event_handler(
               callback=callback, event=event
            )
            logger.info(f'[{self.__class__.__name__}] Added event handler: `{callback.__name__}`')

    async def _get_namespaces(self, event) -> dict:
        """
        Provides namespaces for code evaluation.

        Args:
            event: The event object (e.g., message event).

        Returns:
            dict: A dictionary containing namespaces.
        """
        return {
            "client": self._client,
            "event": event,
            "reply": await event.get_reply_message()
        }

    def _cleanup_code(self, expression: str) -> str:
        """
        Cleans up code by removing backticks and newlines from code blocks.

        Args:
            expression: The code expression string.

        Returns:
            str: Cleaned code expression.
        """
        if expression.startswith('```') and expression.endswith('```'):
            return '\n'.join(expression.split('\n')[1:-1])
        return expression.strip('` \n')

    async def _evaluate_expression(self, expression: str, namespaces: dict) -> Any:
        """
        Evaluates a Python code expression in a separate thread.

        Args:
            expression: The Python code expression to evaluate.
            namespaces: Dictionary containing namespaces for evaluation.

        Returns:
            Any: The result of the evaluated expression.
        """
        task = asyncio.create_task(meval(expression, globals(), **locals(), **namespaces))
        return await task

    async def _handle_output(self, event, output: Any, expression: str) -> None:
        """
        Handles the output of the evaluated expression by sending it as a document.

        Args:
            event: The event object (e.g., message event).
            output: The output from the evaluated expression.
            expression: The original code expression.
        """
        if output is None:
            await event.reply(message='No output.')
            return

        output_str = str(output)
        filename = 'evaluate.txt'
        try:
            async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
                await f.write(output_str)
            await event.reply(
                file=filename,
                message=f'<code>{html.escape(expression)}</code>'
            )
        finally:
            delete_if_exists(filename)

    async def eval_command(self, event) -> None:
        """
        Evaluates a Python expression sent by a sudo user.

        This method orchestrates the entire evaluation process, from 
        namespace creation to output handling, using the class's methods.

        Args:
            event: The event object (e.g., message event) containing the 
                   command and expression to evaluate.
        """
        message_parts = event.raw_text.split(maxsplit=1)
        if len(message_parts) < 2:
            await event.reply('No expression provided.')
            return

        namespaces = await self._get_namespaces(event)
        expression = self._cleanup_code(message_parts[1])

        try:
            output = await self._evaluate_expression(expression, namespaces)
        except Exception as e:
            etype, value, tb = sys.exc_info()
            if not (etype and value and tb):
                _formatted_exc = traceback.format_exc()
            else:
                _formatted_exc = traceback.format_exception(etype, value, tb)

            formatted_exc = (
                ''.join(_formatted_exc)
                if isinstance(_formatted_exc, list)
                else _formatted_exc
            )
            output = f'{e}\n\n{formatted_exc}'

        await self._handle_output(event, output, expression)

    @property
    def event_handlers(self) -> List[Dict[str, Callable | events.NewMessage]]:
        """Returns a list of event handlers."""
        return [
            {'callback': self.eval_command, 'event': events.NewMessage(pattern=constants.EVAL_COMMAND_REGEX, outgoing=True)}
        ]
