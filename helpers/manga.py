import re
from pymongo.collection import Collection
from bson.objectid import ObjectId
from discord import Message, Embed


async def get_manga_info(db: Collection, yomiyasu_id: str):
    res = db.aggregate([
        {
            '$match': {
                '_id': ObjectId(yomiyasu_id)
            }
        }, {
            '$lookup': {
                'from': 'books',
                'localField': '_id',
                'foreignField': 'serie',
                'as': 'books'
            }
        }, {
            '$unwind': {
                'path': '$books'
            }
        }, {
            '$group': {
                '_id': {
                    '_id': '$_id',
                    'visibleName': '$visibleName',
                    'difficulty': '$difficulty',
                    'bookCount': '$bookCount',
                    'summary': '$summary'
                },
                'characters': {
                    '$sum': '$books.characters'
                }
            }
        }, {
            '$project': {
                "_id": "$_id._id",
                "visibleName": "$_id.visibleName",
                "difficulty": "$_id.difficulty",
                "bookCount": "$_id.bookCount",
                "summary": "$_id.summary",
                "characters": 1
            }
        }
    ])
    return res.next()


async def send_yomiyasu_embed(message: Message, db: Collection, yomiyasu_db: Collection):
    if "manga.ajr.moe/app/series" in message.content and len(message.embeds) > 0:
        await message.edit(suppress=True)
        url_pattern = r'https?://\S+|www\.\S+'
        urls = re.findall(url_pattern, message.content)
        embeds = []
        for url in urls:
            if "manga.ajr.moe/app/series" in message.content:
                manga_id = url.split("/series/")[1]

                result = await get_manga_info(yomiyasu_db.series, manga_id)
                manga_result = db.find_one({"yomiyasuId": manga_id})

                serie_embed = Embed(
                    title=f"**{result['visibleName']}**", description=result["summary"], url=url, color=0x24b14d)
                serie_embed.set_author(
                    name="Yomiyasu", url="https://manga.ajr.moe/")
                if result["difficulty"] > 0:
                    serie_embed.add_field(
                        name="Dificultad", value=result["difficulty"])
                serie_embed.add_field(
                    name="Nº de volúmenes", value=result["bookCount"])
                serie_embed.add_field(
                    name="Nº de caracteres", value=result["characters"])
                serie_embed.set_image(url=manga_result["thumbnail"])
                embeds.append(serie_embed)
        return embeds
    return None
