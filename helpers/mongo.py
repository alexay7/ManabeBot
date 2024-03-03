import os

from pymongo import MongoClient, errors

from termcolor import cprint
from dotenv import load_dotenv


def init_mongo(uri, name):
    try:
        # Initialize the mongo client
        client = MongoClient(uri)

        # Printea un mensaje guay si la conexión ha sido exitosa
        cprint(
            f"🐍 Conexión con la base de datos {name} establecida", "cyan", attrs=["bold"])

        # Return the ajrlogs database
        return client
    except errors.ServerSelectionTimeoutError:
        cprint("❌ Ha ocurrido un error intentando conectar con la base de datos",
               "red", attrs=["bold"])
        exit(1)


print("\n\n===============================================")

cprint(
    f"\n🤖 Iniciando AJRBot 3.0\n", "blue", attrs=["bold"])
load_dotenv(".env", override=True)

print("=========== CARGANDO BASES DE DATOS ===========\n")
ajr_client = init_mongo(os.getenv("MONGOURL"), "principal")
yomiyasu_client = init_mongo(os.getenv("YOMIYASUURL"), "de yomiyasu")

logs_db = ajr_client.ajrlogs
kotoba_db = ajr_client.kotoba
manga_db = ajr_client.komga
tests_db = ajr_client.Migii
yomiyasu_db = yomiyasu_client.yomiyasu
