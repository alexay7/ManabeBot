import discord
from discord.ext import commands

import json
import random
import requests

from helpers.general import send_error_message
from termcolor import cprint, COLORS

SMALLROWKATAKANA = 'ァィゥェォヵㇰヶㇱㇲㇳㇴㇵㇶㇷㇷ゚ㇸㇹㇺャュョㇻㇼㇽㇾㇿヮ'

# ================ GENERAL VARIABLES ================
with open("config/kotoba.json", encoding="utf8") as json_file:
    kotoba_config = json.load(json_file)
    kotoba_channels = kotoba_config["kotoba_channels"]
# ====================================================


def accent_output(word, accent):
    output = ""
    mora = 0
    i = 0
    while i < len(word):
        output += word[i]

        i += 1
        mora += 1

        while i < len(word) and word[i] in SMALLROWKATAKANA:
            output += word[i]
            i += 1

        if mora == accent:
            output += "＼"

    return output


def accents_for_array(accents):
    result = []
    for accent in accents:
        aux = []
        pitch_accents = []
        for a in accent["accent"]:
            aux.append(accent_output(a["pronunciation"], a["pitchAccent"]))
            pitch_accents.append(str(a["pitchAccent"]))
        # Join all the elements of the aux array with ・
        output = "・".join(aux)

        result.append(
            f" ・[［{' ・'.join(pitch_accents)}］{output}](https://kez.io/nhk/audio/{accent['soundFile']})")
    return result


def accents_for_simple_array(accents):
    result = []
    for accent in accents:
        aux = []
        pitch_accents = []
        for a in accent:
            aux.append(accent_output(a["pronunciation"], a["pitchAccent"]))
            pitch_accents.append(str(a["pitchAccent"]))
        # Join all the elements of the aux array with ・
        output = "・".join(aux)

        result.append(f" ・［{' ・'.join(pitch_accents)}］{output}")
    return result


class Pitch(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot: discord.bot.Bot = bot

        # Import json file from dicts/nhk.json
        with open("dicts/nhk.json", "r", encoding="utf8") as f:
            self.nhk = json.load(f)

    @commands.Cog.listener()
    async def on_ready(self):
        cprint("- [✅] Cog de pitch accent cargado con éxito",
               random.choice(list(COLORS.keys())))

    @commands.command(aliases=["acento", "pitch"])
    async def accent(self, ctx: commands.Context, word: str):
        if ctx.channel.id not in kotoba_channels:
            await send_error_message(ctx,
                                     "Este comando solo puede ser usado en <#796084920790679612>.")
            return

        search_word = word.strip()

        # Filter the nhk dict by the search word
        nhk_results = list(filter(
            lambda x: x["kana"] == search_word or search_word in x["kanji"], self.nhk))

        combined_accents = []
        for result in nhk_results:
            array_slice = slice(1)
            simple_accents = accents_for_simple_array(
                result["conjugations"][array_slice])
            normal_accents = accents_for_array(result["accents"])

            subentries_slice = slice(0, 25)
            subentries = result["subentries"][subentries_slice]
            subentries_accents = []
            for entry in subentries:
                subentries_accents += entry["accents"]

            flattened_subentries = [
                item for sub_list in subentries_accents for item in sub_list]

            # Merge all arrays
            accents = simple_accents + normal_accents + flattened_subentries

            kanji_output = f"【 {'、'.join(result['kanji'])}】" if len(
                result["kanji"]) > 0 else ""
            usage_output = f"【{result['usage']}】" if "usage" in result else ""
            accents_str = '\n'.join(accents)
            combined_accents.append(
                f"{result['kana']}{kanji_output}{usage_output}\n{accents_str}")

        title = f"Pitch accent de: {word}"
        output = ""
        footer = ""

        if len(nhk_results) == 0:
            # Hacer petición post
            response = requests.request("POST", "https://kotu.io/api/dictionary/parse", headers={
                                        'Content-Type': 'text/plain'}, data=word.encode('utf-8'))

            sentences = response.json()

            accent_phrases = []
            for sentence in sentences:
                accent_phrases.append(sentence["accentPhrases"])

            # Flatten the array
            flattened_phrases = [
                item for sub_list in accent_phrases for item in sub_list]

            guesses = []
            for phrase in flattened_phrases:
                guesses.append(accent_output(
                    phrase["pronunciation"], phrase["pitchAccent"]["mora"]))
            guesses_str = "　".join(guesses)

            output = f"Lo que creo que es\n{guesses_str}"
            footer = "Drops are indicated by ＼. Phrases are seperated by spaces. Phrases without drops are flat."
        else:
            output = "\n\n".join(combined_accents)

        wait_msg = await ctx.send("Dame un sec que estoy pensando")

        if len(output) <= 2048:
            embed = discord.Embed(
                title=title, description=output, color=0x00ff00)
            embed.set_footer(text=footer)

            # Find context channel
            found_channel: discord.TextChannel = await self.bot.fetch_channel(ctx.channel.id)

            # Find user by id
            found_user = await self.bot.fetch_user(219588857136414720)

            webhook = await found_channel.create_webhook(name=found_user.name)
            await webhook.send(embed=embed, username=found_user.display_name, avatar_url=found_user.display_avatar)

            webhooks = await found_channel.webhooks()
            for webhook in webhooks:
                await wait_msg.delete()
                await webhook.delete()
            return


def setup(bot):
    bot.add_cog(Pitch(bot))
