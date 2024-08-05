""" Helper functions for the Tatoes API. """

import os
import requests
import urllib


async def parse_and_lookup_sentence(sentence):
    """ Parse a sentence and look up the words in the dictionary. """

    url = f"https://manga.manabe.es/api/dictionary/v1/{sentence}"

    response = requests.get(url, timeout=30)

    if response.status_code != 200:
        return None

    parsed_response = response.json()

    if len(parsed_response) == 0:
        return None

    words = []

    for word in parsed_response:
        definitions = ""

        for definition in word["words"][0]["sense"][0]["gloss"]:
            definitions += definition["text"] + "/"

        definitions = definitions[:-1]

        words.append({
            "word": word["words"][0]["kanji"][0]["text"] if len(word["words"][0]["kanji"]) > 0 else word["words"][0]["kana"][0]["text"],
            "reading": word["words"][0]["kana"][0]["text"],
            "definitions": definitions
        })

    return words


async def get_example_sentences(query):
    """ Get example sentences for a word. """

    url = "https://nadedb.manabe.es/api/v1/search/media/sentence"

    body = {"query": query, "exact_match": 0, "limit": 20, "content_sort": "random",
            "random_seed": None, "season": None, "episode": None, "category": None}

    headers = {
        "Content-Type": "application/json",
        "x-api-key": os.getenv("NADEDB_API_KEY")
    }

    response = requests.post(url, json=body, headers=headers, timeout=30)

    if response.status_code != 200:
        return None

    parsed_response = response.json()

    sentences = []

    for sentence in parsed_response["sentences"]:
        series_info = {
            "name": sentence["basic_info"]["name_anime_jp"] if "name_anime_jp" in
            sentence["basic_info"] else None,
            "episode": sentence["basic_info"]["episode"] if "episode" in
            sentence["basic_info"] else None,
            "season": sentence["basic_info"]["season"] if "season" in
            sentence["basic_info"] else None,
            "cover": sentence["basic_info"]["cover"] if "cover" in sentence["basic_info"] else None
        }

        sentence_info = {
            "sentence": sentence["segment_info"]["content_jp"] if "content_jp" in
            sentence["segment_info"] else None,
            "english": sentence["segment_info"]["content_en"] if "content_en" in
            sentence["segment_info"] else None,
            "spanish": sentence["segment_info"]["content_es"] if "content_es" in
            sentence["segment_info"] else None,
            "image": sentence["media_info"]["path_image"] if "path_image" in
            sentence["media_info"] else None,
            "audio": sentence["media_info"]["path_audio"] if "path_audio" in
            sentence["media_info"] else None
        }

        sentences.append({
            "series_info": series_info,
            "sentence_info": sentence_info
        })

    return sentences


async def gen_video_from_img_and_audio(image_url, audio_url):
    """ Generate a video from an image and an audio file. """

    image_file = requests.get(image_url, stream=True, timeout=30)
    audio_file = requests.get(audio_url, stream=True, timeout=30)

    if image_file.status_code != 200 or audio_file.status_code != 200:
        return None

    # Create the video in the temp folder
    video_path = os.path.join(os.getcwd(), "temp", "video.mp4")

    with open(video_path, "wb") as video:
        for chunk in image_file.iter_content(chunk_size=1024):
            video.write(chunk)

    with open(video_path, "ab") as video:
        for chunk in audio_file.iter_content(chunk_size=1024):
            video.write(chunk)

    return video_path
