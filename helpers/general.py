import discord


async def send_error_message(ctx, content):
    embed = discord.Embed(color=0xff2929)
    embed.add_field(
        name="❌", value=content, inline=False)
    if not ctx.message:
        await ctx.respond(embed=embed, delete_after=15.0)
    else:
        await ctx.send(embed=embed, delete_after=15.0)


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
