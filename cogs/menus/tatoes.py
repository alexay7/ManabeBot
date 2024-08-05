from discord import File, Interaction, ButtonStyle
from discord.ui import Button, View
from helpers.tatoes import gen_video_from_img_and_audio
from helpers.views import prepare_response


async def generate_response(tatoe):
    video_path = await gen_video_from_img_and_audio(
        tatoe["image"], tatoe["audio"])

    video = File(video_path, filename="video.mp4")
    embed = tatoe["embed"]

    return embed, video


class PrevButton(Button):
    def __init__(self):
        super().__init__(style=ButtonStyle.blurple, label="◀️")

        self.disabled = True

    async def callback(self, interaction: Interaction):
        await prepare_response(interaction, self.view)

        view = self.view
        view.page -= 1

        view.enable_all_items()

        if view.page == 1:
            self.disabled = True

        embed, file = await generate_response(view.tatoes[view.page-1])

        await interaction.edit_original_response(embed=embed, file=file, view=view)


class NextButton(Button):
    def __init__(self):
        super().__init__(style=ButtonStyle.blurple, label="▶️")

        self.disabled = False

    async def callback(self, interaction: Interaction):
        await prepare_response(interaction, self.view)

        view = self.view
        view.page += 1

        view.enable_all_items()

        if view.page == len(view.tatoes):
            self.disabled = True

        embed, file = await generate_response(view.tatoes[view.page-1])

        await interaction.edit_original_response(embed=embed, file=file, view=view)


class TatoesView(View):
    def __init__(self, tatoes, page=1):
        super().__init__()

        self.tatoes = tatoes
        self.page = page

        self.add_item(PrevButton())

        self.add_item(NextButton())

        if len(tatoes) == 1:
            self.disable_all_items()
