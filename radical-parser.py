import regex as re
import json

KANJI_TO_PARSE = "kanji_to_add.json"
KRADFILE = "kanjitoradical/kradfile-combined.json"

def load_kanji_data(json_file):
    try:
        with open(json_file, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Error: {json_file} not found.")
        return {}
    except json.JSONDecodeError:
        print(f"Error: {json_file} is not a valid JSON file.")
        return {}

def parse_kanji(kanji_list, kanji_data):
    parsed_data = {}
    for kanji in kanji_list:
        parsed_data[kanji] = {
            "radicals": kanji_data.get(kanji, [])
        }
    return parsed_data

kanji_to_parse = load_kanji_data(KANJI_TO_PARSE)
kanji_mapping_data = load_kanji_data(KRADFILE)

# Parse words using loaded kanji data
parsed_kanji = parse_kanji(kanji_to_parse, kanji_mapping_data)

# Save the parsed data to a JSON file for studying
output_file = "kanji_data_output.json"
with open(output_file, "w", encoding="utf-8") as file:
    json.dump(parsed_kanji, file, ensure_ascii=False, indent=4)

print(f"Parsed data saved to {output_file}")
