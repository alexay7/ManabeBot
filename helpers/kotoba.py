import json
import discord

from helpers.certs import generate_certificate

with open("config/kotoba.json", encoding="utf8") as json_file:
    kotoba_config = json.load(json_file)
    noken_ranks = kotoba_config["noken_ranks"]
    kotoba_tests = kotoba_config["kotoba_tests"]


async def level_user(ctx, user, guild, level, currentroleid):
    requirements = kotoba_tests[level.strip(
    )]
    reqscorelimit, reqanswertime, reqfontsize, reqfont, newrankid, reqfailed, shortname, reqAntiOcr, reqStartIndex, reqEndIndex, image_name = requirements

    # MODO "PODER HACER EL N1 DE GOLPE"
    if currentroleid == newrankid:
        return

    # MODO "TENER QUE APROBAR TODO POCO A POCO"
    if (noken_ranks.index(currentroleid)+1 != noken_ranks.index(newrankid)):
        return

    #  Get level by position in the list
    if currentroleid != 0:
        current_level = noken_ranks.index(
            currentroleid)
        level = noken_ranks.index(
            newrankid)

        # If the current level is higher, stop
        if current_level > level:
            return

        # If the level is higher than 0, delete the previous rol
        if level > 0:
            previous_role = guild.get_role(
                currentroleid)
            await user.remove_roles(
                previous_role)

    # Add the role to the user
    newrole = guild.get_role(
        newrankid)
    await user.add_roles(newrole)

    # Get level by position in the list
    level = 5 - \
        noken_ranks.index(newrankid)
    generate_certificate(
        user.name, user.joined_at, "N"+str(level))
    image = discord.File(
        "temp/certificate.jpg", filename="certificate.jpg")
    image_name = "certificate.jpg"

    await ctx.send(f'<@!{user.id}> ha aprobado el examen de{shortname}!\n'
                   f'Escribe `.levelup` en <#796084920790679612> para ver los requisitos del siguiente nivel.', file=image if image_name else None)
