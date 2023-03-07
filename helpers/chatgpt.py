import os

from helpers.general import send_response
from revChatGPT.V1 import Chatbot
import functools
import asyncio
import typing


def to_thread(func: typing.Callable) -> typing.Coroutine:
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        wrapped = functools.partial(func, *args, **kwargs)
        return await loop.run_in_executor(None, wrapped)
    return wrapper


@to_thread
def official_handle_response(message, conversation=None) -> str:
    offical_chatbot = Chatbot(
        config={"email": os.getenv("GPT_EMAIL"), "password": os.getenv("GPT_PASS")}, conversation_id=conversation)

    prev_text = ""
    for data in offical_chatbot.ask(message):
        message = data["message"][len(prev_text):]
        prev_text = data["message"]

    return prev_text


async def send_prompt(ctx, message, conversation=None, try_num=0):
    if ctx.message:
        author = ctx.message.author.id
    else:
        author = ctx.author.id
    try:
        response = '> **' + message + '** - <@' + \
            str(author) + '> \n\n'
        if ctx.message and not conversation:
            temp_message = await send_response(ctx, "Generando respuesta... Espere por favor")
        async with ctx.typing():
            response = f"{response}{await official_handle_response(message,conversation)}"
        char_limit = 1900
        if len(response) > char_limit:
            # Split the response into smaller chunks of no more than 1900 characters each(Discord limit is 2000 per chunk)
            if "```" in response:
                # Split the response if the code block exists
                parts = response.split("```")

                for i in range(0, len(parts)):
                    if i % 2 == 0:  # indices that are even are not code blocks
                        await send_response(ctx, parts[i])

                    # Send the code block in a seperate message
                    else:  # Odd-numbered parts are code blocks
                        code_block = parts[i].split("\n")
                        formatted_code_block = ""
                        for line in code_block:
                            while len(line) > char_limit:
                                # Split the line at the 50th character
                                formatted_code_block += line[:char_limit] + "\n"
                                line = line[char_limit:]
                            formatted_code_block += line + "\n"  # Add the line and seperate with new line

                        # Send the code block in a separate message
                        if (len(formatted_code_block) > char_limit + 100):
                            code_block_chunks = [formatted_code_block[i:i + char_limit]
                                                 for i in range(0, len(formatted_code_block), char_limit)]
                            for chunk in code_block_chunks:
                                await send_response(ctx, "```" + chunk + "```")
                        else:
                            await send_response(ctx, "```" + formatted_code_block + "```")

            else:
                response_chunks = [response[i:i + char_limit]
                                   for i in range(0, len(response), char_limit)]
                for chunk in response_chunks:
                    await send_response(ctx, chunk)
        else:
            await send_response(ctx, response)
        if ctx.message and not conversation:
            await temp_message.delete()
    except Exception as e:
        print(e)
        if ctx.message and not conversation:
            await temp_message.delete()
        if try_num < 2:
            try_num += 1
            await send_prompt(ctx, message, conversation=conversation, try_num=try_num)
        else:
            await send_response(ctx, "> **Error: Los servidores de ChatGPT están petados, repite la pregunta más tarde**", delete_after=10.0)
