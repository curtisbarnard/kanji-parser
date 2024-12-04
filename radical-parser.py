import regex as re
import json

def load_kanji_data(json_file):
    """Load kanji and radicals from a JSON file."""
    try:
        with open(json_file, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Error: {json_file} not found.")
        return {}
    except json.JSONDecodeError:
        print(f"Error: {json_file} is not a valid JSON file.")
        return {}

def extract_kanji(word):
    """Extract kanji from a Japanese word."""
    return re.findall(r'\p{Han}', word)

def parse_words(word_list, kanji_data):
    """Parse words into kanji and radicals."""
    parsed_data = {}
    for word in word_list:
        kanji_list = extract_kanji(word)
        parsed_data[word] = {
            "kanji": kanji_list,
            "radicals": {kanji: kanji_data.get(kanji, []) for kanji in kanji_list}
        }
    return parsed_data

# Load kanji and radicals data from JSON file
kanji_data_file = "kanjitoradical/kradfile-combined.json"
kanji_data = load_kanji_data(kanji_data_file)

# Example list of Japanese words
words = ["日本", "語学", "学校"]

# Parse words using loaded kanji data
parsed_words = parse_words(words, kanji_data)

# Save the parsed data to a JSON file for studying
output_file = "test-output.json"
with open(output_file, "w", encoding="utf-8") as file:
    json.dump(parsed_words, file, ensure_ascii=False, indent=4)

print(f"Parsed data saved to {output_file}")
