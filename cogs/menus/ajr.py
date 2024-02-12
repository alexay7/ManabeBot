import calendar
import math
import discord
import helpers.mongo as mongo

from datetime import datetime
from matplotlib import pyplot as plt

from helpers.views import prepare_response


async def ajr_command(horas):
    pipeline = [
        {
            "$match": {
                "timestamp": {
                    "$gte": int(datetime(2022, 1, 1, 0, 0, 0).timestamp()),
                }
            }
        },
        {
            '$group': {
                '_id': {
                    'userId': '$userId',
                    'year': {'$year': {'$toDate': {'$multiply': ['$timestamp', 1000]}}},
                    'month': {'$month': {'$toDate': {'$multiply': ['$timestamp', 1000]}}}
                },
                'totalPuntos': {'$sum': '$puntos'},
                'totalBonusPuntos': {
                    '$sum': {
                        '$cond': {
                            'if': {'$eq': ['$bonus', True]},
                            'then': {'$divide': ['$puntos', 1.4]},
                            'else': '$puntos'
                        }
                    }
                }
            }
        },
        {
            '$sort': {'_id.year': 1, '_id.month': 1}
        }, {
            '$lookup': {
                'from': 'users',
                'localField': '_id.userId',
                'foreignField': 'userId',
                'as': 'userInfo'
            }
        }, {
            '$unwind': {
                'path': '$userInfo'
            }
        }, {
            '$project': {
                '_id.month': 1,
                '_id.year': 1,
                '_id.userId': '$userInfo.username',
                'puntos': {
                    '$cond': {
                        'if': {'$eq': ['$bonus', True]},
                        'then': '$totalBonusPuntos',
                        'else': '$totalPuntos'
                    }
                }
            }
        }
    ]

    # Run the pipeline and get the results
    results = list(mongo.db.logs.aggregate(pipeline))

    # Create a dictionary to store the data for each user
    user_data = {}
    max_points = 0
    max_month = None

    # Loop through the results and group the data by user
    for result in results:
        user_id = result['_id']['userId'].replace("_", "")
        year = result['_id']['year']
        month = result['_id']['month']
        month_name = calendar.month_name[month]
        puntos = result['puntos']

        # Check if the user data exists in the dictionary, and add it if it doesn't
        if user_id not in user_data:
            user_data[user_id] = {'x': [], 'y': [], 'label': user_id}

        # Add the data point to the user's data
        user_data[user_id]['x'].append(f"{year}/{str(month).zfill(2)}")
        if horas:
            user_data[user_id]['y'].append(puntos / 27)
        else:
            user_data[user_id]['y'].append(puntos)

    # Find the common set of x-axis labels and sort them by year and month
    x_labels = list(
        set([x_val for user_id, data in user_data.items() for x_val in data['x']]))
    x_labels.sort()

    # Create a dictionary to hold the filled-in data
    filled_data = {}

    # Loop through each user's data and fill in missing data with zeros
    for user_id, data in user_data.items():
        filled_data[user_id] = {'x': x_labels, 'y': []}
        for x_label in x_labels:
            if x_label in data['x']:
                filled_data[user_id]['y'].append(
                    data['y'][data['x'].index(x_label)])
            else:
                filled_data[user_id]['y'].append(0)
        # Copy the label from the user_data dictionary to the filled_data dictionary
        filled_data[user_id]['label'] = data['label']

    month_points = {}
    for x_label in x_labels:
        total_points = sum([data['y'][idx] for user_id, data in filled_data.items(
        ) for idx, x_val in enumerate(data['x']) if x_val == x_label])
        month_points[x_label] = total_points

    # Find the month with the highest points
    for month, points in month_points.items():
        if points > max_points:
            max_month = month
            max_points = points
        if (month == f"{datetime.now().year}/{str(datetime.now().month).zfill(2)}"):
            current_month = month
            current_month_points = points

    colors = ["#000", "#556b2f", "#7f0000", "#191970", "#5f9ea0", "#9acd32", "#ff0000", "#ff8c00", "#ffd700",
              "#0000cd", "#ba55d3", "#00fa9a", "#00ffff", "#f08080", "#ff00ff", "#1e90ff", "#dda0dd",
              "#ff1493", "#f5deb3"]

    # Create a stacked area chart using Matplotlib
    fig, ax = plt.subplots(figsize=(15, 10))

    # Combine the y values for each user and plot them together as a stacked area chart
    stacked_y = [filled_data[user_id]['y']
                 for user_id, data in filled_data.items()]
    stack_coll = ax.stackplot(x_labels, stacked_y, labels=[
        data['label'] for user_id, data in filled_data.items()])

    for i in range(len(stack_coll)):  # Itera sobre las partes del stackplot
        # Asigna un hatch diferente a cada parte
        stack_coll[i].set_color(
            colors[(i - 1) % len(colors)])

    bbox_props = dict(boxstyle="round,pad=0.3",
                      edgecolor="black", facecolor="white")

    ax.text(max_month, max_points,
            f"{math.ceil(max_points)}", ha='center', va='bottom', fontsize=12, bbox=bbox_props, color="black")

    if max_month != month:
        # Add text annotation for current month points
        ax.text(current_month, current_month_points,
                f"{math.ceil(current_month_points)}", ha='center', va='center', bbox=bbox_props, color="black")

    # Set the x-axis label
    ax.set_xlabel('Meses')

    # Set the y-axis label
    if horas:
        ax.set_ylabel('Horas')
    else:
        ax.set_ylabel('Puntos')

    # Set the title
    ax.set_title('Inmersión en AJR')

    # Create the legend outside the plot
    ax.legend([filled_data[user_id]['label'] for user_id, data in filled_data.items(
    )], loc='upper left', bbox_to_anchor=(1.02, 1), fontsize='large')

    handles, labels = ax.get_legend_handles_labels()
    legend = ax.legend(reversed(handles), reversed(labels),
                       title='Usuarios', loc='upper left')

    ax.set_facecolor('#36393f')  # Color de fondo similar al de Discord
    fig.set_facecolor('#36393f')

    ax.title.set_color('white')
    ax.xaxis.label.set_color('white')
    ax.yaxis.label.set_color('white')
    ax.tick_params(axis='x', colors='white')  # Change tick labels color
    ax.tick_params(axis='y', colors='white')  # Change tick labels color

    for text in legend.get_texts():
        text.set_color("black")

    plt.rcParams.update(
        {'text.color': 'white', 'axes.labelcolor': 'white'})

    plt.xticks(rotation=45)
    plt.savefig("temp/image.png", bbox_inches="tight")
    plt.close()
    file = discord.File("temp/image.png", filename="image.png")
    return {"file": file, "view": AJRView(horas)}


class PointsButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="🌟 Ver Puntos",
                         style=discord.ButtonStyle.green, custom_id="points")

    async def callback(self, interaction: discord.Interaction):
        await prepare_response(interaction, self.view)

        response = await ajr_command(False)

        # Delete this button
        self.view.clear_items()
        self.view.add_item(HorasButton())

        await interaction.edit_original_response(files=[response["file"]], view=self.view, embeds=[])


class HorasButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="🕛 Ver Horas",
                         style=discord.ButtonStyle.green, custom_id="horas")

    async def callback(self, interaction: discord.Interaction):
        await prepare_response(interaction, self.view)

        response = await ajr_command(True)

        # Delete this button
        self.view.clear_items()
        self.view.add_item(PointsButton())

        await interaction.edit_original_response(files=[response["file"]], view=self.view, embeds=[])


class AJRView(discord.ui.View):
    def __init__(self, horas):
        super().__init__()

        if horas:
            self.add_item(PointsButton())
        else:
            self.add_item(HorasButton())
