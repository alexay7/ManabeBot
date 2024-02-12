import asyncio
import discord


async def send_error_message(ctx, content, delete_after=15.0):
    embed = discord.Embed(color=0xff2929)
    embed.add_field(
        name="❌", value=content, inline=False)
    if hasattr(ctx, "message") and not ctx.message:
        await ctx.respond(embed=embed, delete_after=delete_after)
    else:
        await ctx.send(embed=embed, delete_after=delete_after)


def intToMonth(number):
    if number == 1:
        return "Enero"
    if number == 2:
        return "Febrero"
    if number == 3:
        return "Marzo"
    if number == 4:
        return "Abril"
    if number == 5:
        return "Mayo"
    if number == 6:
        return "Junio"
    if number == 7:
        return "Julio"
    if number == 8:
        return "Agosto"
    if number == 9:
        return "Septiembre"
    if number == 10:
        return "Octubre"
    if number == 11:
        return "Noviembre"
    return "Diciembre"


def intToWeekday(number):
    if number == 1:
        return "火"
    if number == 2:
        return "水"
    if number == 3:
        return "木"
    if number == 4:
        return "金"
    if number == 5:
        return "土"
    if number == 6:
        return "日"
    return "月"


async def send_message_for_other(ctx, username, avatar, content):
    webhook = await ctx.channel.create_webhook(name=username)
    await webhook.send(
        content, username=username, avatar_url=avatar)

    webhooks = await ctx.channel.webhooks()
    for webhook in webhooks:
        await webhook.delete()


async def send_response(ctx, content=None, view=None, embed=None, file=None, ephemeral=None, delete_after=None):
    if ctx.message:
        params = {
            "content": content,
            "view": view,
            "embed": embed,
            "file": file,
            "delete_after": delete_after
        }
        not_none_params = {k: v for k, v in params.items() if v is not None}
        return await ctx.send(**not_none_params)
    else:
        params = {
            "content": content,
            "view": view,
            "embed": embed,
            "file": file,
            "ephemeral": ephemeral,
            "delete_after": delete_after
        }
        not_none_params = {k: v for k, v in params.items() if v is not None}
        return await ctx.respond(**not_none_params)


async def set_processing(ctx):
    if not ctx.message:
        await ctx.defer()


async def get_clock_emoji(hour, minute):
    if hour == 0 or hour == 12:
        if minute < 15:
            return "🕛"
        elif minute < 45:
            return "🕧"
        else:
            return "🕐"
    if hour == 1 or hour == 13:
        if minute < 15:
            return "🕐"
        elif minute < 45:
            return "🕜"
        else:
            return "🕑"
    if hour == 2 or hour == 14:
        if minute < 15:
            return "🕑"
        elif minute < 45:
            return "🕝"
        else:
            return "🕒"
    if hour == 3 or hour == 15:
        if minute < 15:
            return "🕒"
        elif minute < 45:
            return "🕞"
        else:
            return "🕓"
    if hour == 4 or hour == 16:
        if minute < 15:
            return "🕓"
        elif minute < 45:
            return "🕟"
        else:
            return "🕔"
    if hour == 5 or hour == 17:
        if minute < 15:
            return "🕔"
        elif minute < 45:
            return "🕠"
        else:
            return "🕕"
    if hour == 6 or hour == 18:
        if minute < 15:
            return "🕕"
        elif minute < 45:
            return "🕡"
        else:
            return "🕖"
    if hour == 7 or hour == 19:
        if minute < 15:
            return "🕖"
        elif minute < 45:
            return "🕢"
        else:
            return "🕗"
    if hour == 8 or hour == 20:
        if minute < 15:
            return "🕗"
        elif minute < 45:
            return "🕣"
        else:
            return "🕘"
    if hour == 9 or hour == 21:
        if minute < 15:
            return "🕘"
        elif minute < 45:
            return "🕤"
        else:
            return "🕙"
    if hour == 10 or hour == 22:
        if minute < 15:
            return "🕙"
        elif minute < 45:
            return "🕥"
        else:
            return "🕚"
    if hour == 11 or hour == 23:
        if minute < 15:
            return "🕚"
        elif minute < 45:
            return "🕦"
        else:
            return "🕛"


async def send_message_with_buttons(self, ctx, content):
    pages = len(content)
    cur_page = 1
    message = await ctx.send(f"```\n{content[cur_page-1]}\nPág {cur_page} de {pages}\n```")
    if pages > 1:
        await message.add_reaction("◀️")
        await message.add_reaction("▶️")
        while True:
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=180)
                if not user.bot:
                    # waiting for a reaction to be added - times out after x seconds, 60 in this
                    # example

                    if str(reaction.emoji) == "▶️" and cur_page != pages:
                        cur_page += 1
                        await message.edit(content=f"```{content[cur_page-1]}\nPág {cur_page} de {pages}```")
                        try:
                            await message.remove_reaction(reaction, user)
                        except discord.errors.Forbidden:
                            await send_error_message(ctx, "‼️ Los mensajes con páginas no funcionan bien en DM!")

                    elif str(reaction.emoji) == "◀️" and cur_page > 1:
                        cur_page -= 1
                        await message.edit(content=f"```{content[cur_page-1]}\nPág {cur_page} de {pages}```")
                        try:
                            await message.remove_reaction(reaction, user)
                        except discord.errors.Forbidden:
                            await send_error_message(self, ctx, "‼️ Los mensajes con páginas no funcionan bien en DM!")

                    else:
                        try:
                            await message.remove_reaction(reaction, user)
                        except discord.errors.Forbidden:
                            await send_error_message(self, ctx, "‼️ Los mensajes con páginas no funcionan bien en DM!")
                        # removes reactions if the user tries to go forward on the last page or
                        # backwards on the first page
            except asyncio.TimeoutError:
                try:
                    await message.delete()
                except discord.errors.Forbidden:
                    await send_error_message(self, ctx, "‼️ Los mensajes con páginas no funcionan bien en DM!")
                break
                # ending the loop if user doesn't react after x seconds
