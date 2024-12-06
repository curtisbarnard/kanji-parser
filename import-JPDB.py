import regex as re
import json
import requests
import urllib.parse
from bs4 import BeautifulSoup

ANKI_CONNECT_URL = "http://localhost:8765"
ANKI_DECK = "Import Testing"
VOCAB_NOTE_TYPE = "JPDB Japanese Vocab"
KANJI_NOTE_TYPE = "Japanese Kanji"
RADICAL_NOTE_TYPE = "Japanese Radicals"
KRADFILE = "kanjitoradical/kradfile-combined.json"
REVIEWS = 'reviews.json'

def invoke(action, **params):
    request = {'action': action, 'params': params, 'version': 6}
    response = requests.post(ANKI_CONNECT_URL, json=request).json()
    if len(response) != 2:
        raise Exception('response has an unexpected number of fields')
    if 'error' not in response:
        raise Exception('response is missing required error field')
    if 'result' not in response:
        raise Exception('response is missing required result field')
    if response['error'] is not None:
        raise Exception(response['error'])
    return response['result']

def process_json_data(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    vocab_list = []
    char_list = []

    # Process vocabulary cards
    for card in data.get('cards_vocabulary_jp_en', []):
        vocab = {
            'expression': card['spelling'],
            'tag': 'known' if any(review['grade'] == 'easy' for review in card['reviews']) else 'new'
        }
        vocab_list.append(vocab)

    # Process kanji character cards
    for card in data.get('cards_kanji_keyword_char', []):
        char = {
            'character': card['character'],
            'tag': 'known' if any(review['grade'] == 'easy' for review in card['reviews']) else 'new'
        }
        char_list.append(char)

    return vocab_list, char_list

def note_exists(character):
    query = f"Character:{character}"
    response = invoke("findNotes", query=query)
    return response

def note_expression_exists(expression):
    query = f"Expression:{expression}"
    response = invoke("findNotes", query=query)
    return response

def add_note(note):
    response = invoke("addNote", note=note)
    return response

def get_keyword_and_mnemonic(character):
    encoded_kanji = urllib.parse.quote(character)
    url = f"https://jpdb.io/kanji/{encoded_kanji}"
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

        keyword_div = soup.find('h6', string="Keyword")
        keyword = keyword_div.find_next('div').text if keyword_div else "No keyword found"
        
        mnemonic_div = soup.find('div', class_='mnemonic')
        mnemonic = mnemonic_div.decode_contents().strip() if mnemonic_div else "No mnemonic found"
        
        return keyword, mnemonic
    else:
        print(f"Warning: Failed to fetch data for kanji '{character}', status code: {response.status_code}")
        return "No keyword found", "No mnemonic found"
    
def get_description(word):
    encoded_word = urllib.parse.quote(word)
    url = f"https://jpdb.io/search?q={encoded_word}"
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

        subsection_meanings = soup.find('div', class_='subsection-meanings')
        if subsection_meanings:
            first_description = subsection_meanings.find('div', class_='description')
            description = first_description.text.strip() if first_description else ""
        else:
            description = ""

        return description
    else:
        print(f"Warning: Failed to fetch data for word '{word}', status code: {response.status_code}")
        return ""

def create_vocab_notes(vocab_list):
    
    for word in vocab_list:
        if note_expression_exists(word["expression"]):
            print(f"Skipping {word['expression']} as it already exists.")
            continue
        print(f"Processing {word['expression']}...")

        description = get_description(word["expression"])

        note = {
            "deckName": ANKI_DECK,
            "modelName": VOCAB_NOTE_TYPE,
            "fields": {
                "Expression": word["expression"],
                "Meaning": description,
            },
            "tags": ["import_testing", "vocab", word["tag"]]
        }
        add_note(note)

def create_cards(data, is_radical):
    total = len(data)  # Total number of items to process
    current = 0
    char_type = 'radicals' if is_radical else 'kanji'
    print(f'There are {total} {char_type} to process')

    if is_radical:
        for character, details in data.items():
            current += 1

            if note_exists(character):
                print(f"Skipping {character} as it already exists.")
                continue
            print(f"[{current}/{total}] Processing {character}...")

            keyword, mnemonic = get_keyword_and_mnemonic(character)
            
            note = {
                "deckName": ANKI_DECK,
                "modelName": RADICAL_NOTE_TYPE,
                "fields": {
                    "Character": character,
                    "Keyword": keyword,
                    "Mnemonic": mnemonic,
                },
                "tags": ["import_testing", "radical", details["tag"]]
            }
            add_note(note)
    else:
        for character, details in data.items():
            current += 1
            if note_exists(character):
                print(f"Skipping {character} as it already exists.")
                continue

            print(f"[{current}/{total}] Processing {character}...")
            
            radicals = ", ".join(details["radicals"])
            keyword, mnemonic = get_keyword_and_mnemonic(character)

            note = {
                "deckName": ANKI_DECK,
                "modelName": KANJI_NOTE_TYPE,
                "fields": {
                    "Character": character,
                    "Keyword": keyword,
                    "Mnemonic": mnemonic,
                    "Radicals": radicals
                },
                "tags": ["import_testing", "kanji", details["tag"]]
            }
            add_note(note)

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
    
def map_kanji_and_radicals(char_list, kanji_data):
    mapped_data = {}
    for char in char_list:
        mapped_data[char['character']] = {
            "radicals": kanji_data.get(char['character'], []),
            "tag": char['tag']
        }
    return mapped_data

def create_sets(data):
    kanji_set = {}
    radical_set = {}

    for kanji, details in data.items():
        radicals = details.get("radicals", [])

        if not radicals:
            radical_set[kanji] = {"tag": details.get("tag", "")}
        else:
            kanji_set[kanji] = {
                "radicals": radicals,
                "tag": details.get("tag", "")
            }
            for radical in radicals:
                radical_set.setdefault(radical, {"tag": ""})

    return kanji_set, radical_set
    
def create_kanji_and_radicals(char_list):
    kanji_mapping_data = load_kanji_data(KRADFILE)
    kanji_and_radicals = map_kanji_and_radicals(char_list, kanji_mapping_data)
    kanji_data, radical_data = create_sets(kanji_and_radicals)
    create_cards(kanji_data, is_radical=False)
    create_cards(radical_data, is_radical=True)

vocab_list, char_list = process_json_data(REVIEWS)
# create_vocab_notes(vocab_list)
create_kanji_and_radicals(char_list)