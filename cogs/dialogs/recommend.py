import discord


class RecommendModal(discord.ui.Modal):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.add_item(discord.ui.InputText(
            label="Nombre", placeholder="Nombre de la obra (preferiblemente nombre nativo)", required=True))
        self.add_item(discord.ui.InputText(label="Nivel de Japonés",
                      placeholder="Nivel de JLPT o si eres nativo", required=True))
        self.add_item(discord.ui.InputText(label="Dificultad percibida",
                      placeholder="Lo dificil que te ha parecido la obra", required=True))
        self.add_item(discord.ui.InputText(
            label="Link", placeholder="Link de anilist/MAL/VNDB", required=False))
        self.add_item(discord.ui.InputText(label="Comentarios", placeholder="Comentarios adicionales",
                      required=False, style=discord.InputTextStyle.long))

    async def callback(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(1217567434182234252)

        # Send message to channel
        lines = [
            f"Nombre: {self.children[0].value}",
            f"Nivel de Japonés: {self.children[1].value}",
            f"Dificultad percibida: {self.children[2].value}"
        ]

        if self.children[4].value:
            lines.append(f"Comentarios: {self.children[4].value}")

        if self.children[3].value:
            lines.append(f"Link: {self.children[3].value}")

        # Get user that sent the message
        user = interaction.user

        webhook = await channel.create_webhook(name=user.name)
        await webhook.send(
            content="\n".join(lines), avatar_url=user.display_avatar)

        webhooks = await channel.webhooks()
        for webhook in webhooks:
            await webhook.delete()

        await interaction.response.send_message("Gracias por tu recomendación", ephemeral=True)
