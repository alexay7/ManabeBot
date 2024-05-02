import asyncio
from datetime import datetime, timedelta
import json
import discord
from matplotlib.ticker import MaxNLocator

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import bar_chart_race as bcr

from helpers.general import intToMonth, intToWeekday, send_response
from helpers.immersion.logs import get_best_user_of_range

with open("config/immersion.json") as json_file:
    immersion_config = json.load(json_file)
    announces_channel = immersion_config["announces_channel"]


def generate_linear_graph(points, horas):
    aux = dict(points)
    labels = []
    values = []
    for x, y in aux.items():
        labels.append(x),
        values.append(y)
    plt.plot(labels, values)
    plt.title("Inmersión en Manabe")
    plt.xticks(rotation=45)
    plt.xlabel("Tiempo")
    if horas:
        plt.ylabel("Horas totales")
    else:
        plt.ylabel("Puntos totales")
    plt.fill_between(labels, values, color="#AAAAF0")
    plt.savefig("temp/image.png", bbox_inches="tight")
    plt.close()
    file = discord.File("temp/image.png", filename="image.png")
    return file


def my_autopct(pct):
    return ('%1.1f%%' % pct) if pct >= 4.99 else ''


def generate_graph(points, type, timelapse=None, total_points=None, position=None):
    aux = dict(points)
    if type == "piechart":
        for elem in list(aux):
            if aux[elem] == 0:
                aux.pop(elem)
        aux.pop("TOTAL")

        if "CLUB Manabe" in aux:
            aux.pop("CLUB Manabe")

        labels = []
        values = []

        for x, y in aux.items():
            labels.append(x),
            values.append(y)

        fig1, ax1 = plt.subplots()

        plt.pie(values, labels=labels,
                autopct=my_autopct, pctdistance=0.85, textprops={'color': "w"}, shadow=True, startangle=90)

        fig1.set_facecolor("#2F3136")
        # Equal aspect ratio ensures that pie is drawn as a circle.
        ax1.axis('equal')

        centre_circle = plt.Circle((0, 0), 0.70, fc='#2F3136')
        fig1 = plt.gcf()

        # Adding Circle in Pie chart
        fig1.gca().add_artist(centre_circle)

        sumstr = f"{total_points}"
        # String on the donut center
        bbox_props = dict(boxstyle="circle,pad=0.3",
                          edgecolor="#2F3136", facecolor="gold")
        ax1.text(0., 0.4, position, horizontalalignment='center',
                 verticalalignment='center_baseline', size=28, color="#2F3136", bbox=bbox_props)
        ax1.text(0., -0.1, sumstr, horizontalalignment='center',
                 verticalalignment='center', size=26, color="white")
        ax1.text(0., -0.35, "Puntos", horizontalalignment='center',
                 verticalalignment='center_baseline', size=18, color="white")

        plt.savefig("temp/image.png")
        plt.close()
        file = discord.File("temp/image.png", filename="image.png")
        return file
    elif type == "progress":
        labels = []
        values = []
        media = {"LIBRO": [], "LECTURA": [], "TIEMPOLECTURA": [], "OUTPUT": [], "ANIME": [], "MANGA": [], "VN": [],
                 "AUDIO": [], "VIDEO": [], "JUEGO": []}

        for x, y in aux.items():
            labels.append(x),
            values.append(y)
        fig1, ax = plt.subplots(figsize=(10, 5))
        max = 0

        for elem in values:
            media["LIBRO"].append(elem["LIBRO"])
            media["MANGA"].append(elem["MANGA"])
            media["VN"].append(elem["VN"])
            media["ANIME"].append(elem["ANIME"])
            media["LECTURA"].append(elem["LECTURA"])
            media["TIEMPOLECTURA"].append(elem["TIEMPOLECTURA"])
            media["OUTPUT"].append(elem["OUTPUT"])
            media["AUDIO"].append(elem["AUDIO"])
            media["VIDEO"].append(elem["VIDEO"])
            media["JUEGO"].append(elem["JUEGO"])
            total = elem["LIBRO"] + elem["MANGA"] + elem["VN"] + elem["ANIME"] +  \
                elem["LECTURA"] + elem["TIEMPOLECTURA"] + elem["OUTPUT"] +  \
                elem["AUDIO"] + elem["VIDEO"] + elem["JUEGO"]
            if total > max:
                max = total

        libro = np.array(media["LIBRO"])
        manga = np.array(media["MANGA"])
        vn = np.array(media["VN"])
        anime = np.array(media["ANIME"])
        lectura = np.array(media["LECTURA"])
        tiempolectura = np.array(media["TIEMPOLECTURA"])
        output = np.array(media["OUTPUT"])
        audio = np.array(media["AUDIO"])
        video = np.array(media["VIDEO"])
        juego = np.array(media["JUEGO"])
        read = np.sum([libro, lectura, tiempolectura], axis=0)
        plt.xticks(rotation=45)
        # plt.bar(labels, libro, color='#f3054d')
        # plt.bar(labels, lectura, bottom=libro, color='#f3054d')
        # plt.bar(labels, tiempolectura, bottom=(
        #     libro + lectura), color='#f3054d')
        plt.bar(labels, read, color='#f3054d')
        plt.bar(labels, anime, bottom=read, color='#ffae00')
        plt.bar(labels, manga,
                bottom=read + anime, color='#4Bd0fB')
        plt.bar(labels, vn,
                bottom=read + anime + manga, color='#ffa0ff')
        plt.bar(labels, audio,
                bottom=read + anime + manga + vn, color='#03D04B')
        plt.bar(labels, video,
                bottom=read + anime + manga + vn + audio, color='#0f5f0c')
        plt.bar(labels, output,
                bottom=read + anime + manga + vn + audio + video, color='#ff5f0c')
        plt.bar(labels, juego,
                bottom=read + anime + manga + vn + audio + video + output, color='#0073ff')
        plt.xlabel("FECHA")
        plt.gca().xaxis.set_major_locator(MaxNLocator(integer=True, prune='both'))
        plt.ylabel("PUNTOS")
        plt.ylim(0, max * 1.05)
        plt.legend(["LECTURA", "ANIME", "MANGA", "VN", "AUDIO",
                    "VIDEO", "OUTPUT", "JUEGO"], loc='upper center', bbox_to_anchor=(0.5, 1.25),
                   ncol=3, fancybox=True, shadow=True, labelcolor="black")

        ax.set_facecolor('#36393f')  # Color de fondo similar al de Discord
        fig1.set_facecolor('#36393f')

        ax.title.set_color('white')
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.tick_params(axis='x', colors='white')  # Change tick labels color
        ax.tick_params(axis='y', colors='white')  # Change tick labels color

        plt.savefig("temp/image.png", bbox_inches="tight")
        plt.close()
        file = discord.File("temp/image.png", filename="image.png")
        return file
    else:
        labels = []
        values = []
        start = datetime.today().replace(hour=0, minute=0, second=0) - timedelta(days=6)
        for x in range(0, 7):
            normaldate = start + timedelta(days=x)
            auxdate = str(normaldate
                          ).replace("-", "/").split(" ")[0]
            labels.append(auxdate + intToWeekday(normaldate.weekday()))
            if auxdate in points:
                values.append(points[auxdate])
            else:
                values.append(0)
        plt.rc('font', family='Noto Sans CJK JP')
        fig, ax = plt.subplots()
        ax.bar(labels, values, color='#24B14D')
        ax.set_ylabel('Puntos', color="white")
        ax.tick_params(axis='both', colors='white')
        fig.set_facecolor("#2F3136")
        fig.autofmt_xdate()
        plt.savefig("temp/image.png")
        plt.close()
        file = discord.File("temp/image.png", filename="image.png")
        return file


async def fin_de_mes_graph(self, ctx: discord.ApplicationContext, mes, year, promotions, demotions):
    # Generate monthly ranking animation
    df = pd.read_csv('temp/test.csv', index_col='date',
                     parse_dates=['date'])
    df.tail()
    plt.rc('font', family='Noto Sans JP')
    plt.rcParams['text.color'] = "#FFFFFF"
    plt.rcParams['axes.labelcolor'] = "#FFFFFF"
    plt.rcParams['xtick.color'] = "#FFFFFF"
    plt.rcParams['ytick.color'] = "#FFFFFF"
    plt.rcParams.update({'figure.autolayout': True})
    fig, ax = plt.subplots(figsize=(10, 5), dpi=300)
    ax.set_title(f"Ranking {intToMonth(mes)} Manabe")
    ax.set_facecolor("#36393F")
    fig.set_facecolor("#36393F")
    ax.set_xlabel('Puntos', color="white")
    ax.tick_params(axis='both', colors='white')
    bcr.bar_chart_race(df, 'temp/video.mp4', figsize=(20, 12), fig=fig, n_bars=10,
                       period_fmt="%d/%m/%Y", period_length=2000, steps_per_period=50, bar_size=0.7, interpolate_period=True)
    file = discord.File("temp/video.mp4", filename="ranking.mp4")
    mvp = await get_best_user_of_range("TOTAL", f"{year}/{mes}")
    newrole = discord.utils.get(ctx.guild.roles, name="先輩")
    for user in ctx.guild.members:
        if newrole in user.roles:
            await user.remove_roles(newrole)
    mvpuser = ctx.guild.get_member(mvp["id"])
    await mvpuser.add_roles(newrole)

    embed = discord.Embed(
        title=f"🎌 Manabe mes de {intToMonth(mes)} 🎌", color=0x1302ff, description="-----------------")
    embed.add_field(name="Usuario del mes",
                    value=mvp["username"], inline=False)
    if mvpuser is not None:
        embed.set_thumbnail(
            url=mvpuser.avatar)
    embed.add_field(name="Puntos conseguidos",
                    value=round(mvp["points"], 2), inline=False)
    message = f"🎉 Felicidades a {mvpuser.mention} por ser el usuario del mes de {intToMonth(mes)}!"

    channel = await self.bot.fetch_channel(announces_channel)
    await channel.send(embed=embed, content=message, file=file)

    # Announce promotions and demotions
    if len(promotions) > 0:
        message = "🎉 Felicidades a "
        for user in promotions:
            message += f"<@{user['userId']}>, "
        message = message[:-2]
        message += " por su ascenso a la Liga 学べ"
        await channel.send(content=message)
    if len(demotions) > 0:
        message = "😔 Lo siento por "
        for user in demotions:
            message += f"<@{user['userId']}>, "
        message = message[:-2]
        message += " por su descenso a la liga 上手"
        await channel.send(content=message)

    await send_response(ctx, "Gráfico generado con éxito")


def fin_de_mes_sync(self, ctx, mes, year, promotions, demotions):
    asyncio.run(fin_de_mes_graph(self, ctx, mes, year, promotions, demotions))
