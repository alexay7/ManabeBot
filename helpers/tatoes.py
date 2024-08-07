""" Helper functions for the Tatoes API. """

import os
import requests
from moviepy.editor import AudioFileClip, ImageClip
import io


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
        print("Failed to download image or audio file.")
        return None

    # Save them locally
    image_path = os.path.join(os.getcwd(), "temp", "image.jpg")
    audio_path = os.path.join(os.getcwd(), "temp", "audio.mp3")

    with open(image_path, "wb") as img_file:
        img_file.write(image_file.content)

    with open(audio_path, "wb") as aud_file:
        aud_file.write(audio_file.content)

    # Load the image and audio into MoviePy
    image_clip = ImageClip(image_path)
    audio_clip = AudioFileClip(audio_path)

    # Set the duration of the image clip to match the duration of the audio
    image_clip = image_clip.set_duration(audio_clip.duration)

    # Set the audio of the image clip
    video_clip = image_clip.set_audio(audio_clip)

    # Write the result to a file
    video_path = os.path.join(os.getcwd(), "temp", "video.mp4")
    video_clip.write_videofile(
        video_path, codec="libx264", audio_codec="aac", fps=24)

    return video_path
