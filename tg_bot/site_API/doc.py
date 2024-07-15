import json

# Конвертнём документацию кинопоиска в читаемую форму
# https://api.kinopoisk.dev/v1/documentation-json

with open("documentation-json.json", "r", encoding="utf-8") as file:
    text: str = file.read()
    with open("documentation.json", "w", encoding="utf-8") as json_text:
        json.dump(json.loads(text), json_text, indent=4, ensure_ascii=False)
