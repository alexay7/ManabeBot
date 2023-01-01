import json


NOKEN_LEVELS = ["N1", "N2", "N3", "N4", "N5"]

ALL_CATEGORIES = ["VOCABULARIO", "GRAMATICA", "KANJI", "CONTEXTO",
                  "PARAFRASES", "USO", "GRAMATICAFRASES", "ORDENAR", "ORTOGRAFIA", "FORMACION"]

CATEGORIES = ["VOCABULARIO", "GRAMATICA"]

TYPES = ["KANJI", "CONTEXTO", "PARAFRASES", "USO",
         "GRAMATICAFRASES", "ORDENAR", "ORTOGRAFIA", "FORMACION"]

LEVELS = {
    "N5": {"TYPES": ["KANJI", "CONTEXTO", "PARAFRASES", "USO", "GRAMATICAFRASES", "ORDENAR"]},
    "N4": {"TYPES": ["KANJI", "CONTEXTO", "PARAFRASES", "USO", "GRAMATICAFRASES", "ORDENAR", "ORTOGRAFIA"]},
    "N3": {"TYPES": ["KANJI", "CONTEXTO", "PARAFRASES", "USO", "GRAMATICAFRASES", "ORDENAR", "ORTOGRAFIA"]},
    "N2": {"TYPES": ["KANJI", "CONTEXTO", "PARAFRASES", "USO", "GRAMATICAFRASES", "ORDENAR", "ORTOGRAFIA", "FORMACION"]},
    "N1": {"TYPES": ["KANJI", "CONTEXTO", "PARAFRASES", "USO", "GRAMATICAFRASES", "ORDENAR"]}}


def getQuestion(userid, index):
    with open(f"temp/test-{userid}.json", encoding="utf8") as json_file:
        questions = json.load(json_file)
    return questions[index]


def question_params(question):
    if question == "kanji":
        name = "Lectura de Kanjis (漢字読み)"
        description = "_____の言葉の読み方として最もよいものを、１・２・３・４から一つ選びなさい。"
        time = 10
    elif question == "contexto":
        name = "Contexto (文脈規定)"
        description = "_____に入れるのに最もよいものを、１・２・３・４から一つ選びなさい。"
        time = 20
    elif question == "parafrases":
        name = "Parafraseo (言い換え類義)"
        description = "_____の言葉に意味が最も近ものを、１・２・３・４から一つ選びなさい。"
        time = 20
    elif question == "uso":
        name = "Uso de palabras (用法)"
        description = "次の言葉の使い方として最もよいものを、１・２・３・４から一つ選びなさい。"
        time = 30
    elif question == "gramaticafrases":
        name = "Gramática (文法形式の判断)"
        description = "次の文の_____に入れるのに最もよいものを、１・２・３・４から一つ選びなさい。"
        time = 15
    elif question == "ordenar":
        name = "Ordenar frases (文の組み立て)"
        description = "次の文の＿★＿に入れる最も良いものを、１・２・３・４から一つ選びなさい。"
        time = 40
    elif question == "ortografia":
        name = "Ortografía ()",
        description = "問題＿＿＿の言葉を漢字で書くとき、最もよいものを１・２・３・４から一つ選びなさい。"
        time = 30
    elif question == "formacion":
        name = "Formación de palabras ()"
        description = "問題（　　　）に入れるのに最もよいものを、１・２・３・４から一つ選びなさい。"
        time = 20
    else:
        name = "No implementado",
        description = "no implementado"
        time = 60
    return name, description, time
