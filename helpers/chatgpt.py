import os

from helpers.general import send_response
from revChatGPT.V1 import Chatbot


async def official_handle_response(message) -> str:
    offical_chatbot = Chatbot(
        config={"email": os.getenv("GPT_EMAIL"), "password": os.getenv("GPT_PASS")})
    responseMessage = offical_chatbot.ask(message)

    prev_text = ""
    for data in responseMessage:
        message = data["message"][len(prev_text):]
        prev_text = data["message"]

    return prev_text


async def send_prompt(ctx, message):
    if ctx.message:
        author = ctx.message.author.id
    else:
        author = ctx.author.id
    try:
        response = '> **' + message + '** - <@' + \
            str(author) + '> \n\n'
        if ctx.message:
            temp_message = await send_response(ctx, "Generando respuesta... Espere por favor")
        response = f"{response}{await official_handle_response(message)}"
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
        if ctx.message:
            await temp_message.delete()
    except Exception as e:
        print(e)
        await send_response(ctx, "> **Error: Something went wrong, please try again later!**")
