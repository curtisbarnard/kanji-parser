import requests
import urllib.request
from bs4 import BeautifulSoup
import urllib.parse
import json

# This script takes a json file (output from radical-parser.py) and creates kanji and radical cards in anki.

# Define the AnkiConnect endpoint
ANKI_CONNECT_URL = "http://localhost:8765"
ANKI_DECK = "Script Testing"
KANJI_NOTE_TYPE = "Japanese Kanji"
RADICAL_NOTE_TYPE = "Japanese Radicals"
file_path = "kanji_data_output.json"

def request(action, **params):
    return {'action': action, 'params': params, 'version': 6}

def invoke(action, **params):
    requestJson = json.dumps(request(action, **params)).encode('utf-8')
    response = json.load(urllib.request.urlopen(urllib.request.Request(ANKI_CONNECT_URL, requestJson)))
    if len(response) != 2:
        raise Exception('response has an unexpected number of fields')
    if 'error' not in response:
        raise Exception('response is missing required error field')
    if 'result' not in response:
        raise Exception('response is missing required result field')
    if response['error'] is not None:
        raise Exception(response['error'])
    return response['result']

def load_json_data(file_path):
    """Load JSON data from a file."""
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def parse_kanji_and_radicals(data):
    kanji_set = {}
    radical_set = set()

    for kanji, details in data.items():
        # Add kanji and its radicals
        kanji_set[kanji] = {
            "radicals": details.get("radicals", []),
        }
        # Update radical_set with the radicals for this kanji
        radical_set.update(details.get("radicals", []))

    return kanji_set, radical_set

def card_exists(character):
    query = f"Character:{character}"
    response = invoke("findNotes", query=query)
    return response

def get_keyword_and_mnemonic(character):
    encoded_kanji = urllib.parse.quote(character)
    url = f"https://jpdb.io/kanji/{encoded_kanji}"
    response = requests.get(url)
    if response.status_code == 200:
        print("Parsing JPDB.io response")
        soup = BeautifulSoup(response.text, 'html.parser')

        keyword_div = soup.find('h6', string="Keyword")
        keyword = keyword_div.find_next('div').text if keyword_div else "No keyword found"
        
        mnemonic_div = soup.find('div', class_='mnemonic')
        mnemonic = mnemonic_div.decode_contents().strip() if mnemonic_div else "No mnemonic found"
        
        return keyword, mnemonic
    else:
        print(f"Warning: Failed to fetch data for kanji '{character}', status code: {response.status_code}")
        return "No keyword found", "No mnemonic found"

def add_note(note):
    response = invoke("addNote", note=note)
    return response

def create_cards(data, is_radical):
    if is_radical:
        for character in data:
            if card_exists(character):
                print(f"Skipping {character} as it already exists.")
                continue
            print(f"Processing {character}...")

            keyword, mnemonic = get_keyword_and_mnemonic(character)
            
            note = {
                "deckName": ANKI_DECK,
                "modelName": RADICAL_NOTE_TYPE,
                "fields": {
                    "Character": character,
                    "Keyword": keyword,
                    "Mnemonic": mnemonic,
                },
                "tags": ["script_testing", "radical"]
            }
            add_note(note)
    else:
        for character, details in data.items():
            if card_exists(character):
                print(f"Skipping {character} as it already exists.")
                continue

            print(f"Processing {character}...")
            
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
                "tags": ["script_testing", "kanji"]
            }
            add_note(note)


data = load_json_data(file_path)

kanji_data, radical_data = parse_kanji_and_radicals(data)
create_cards(kanji_data, is_radical=False)
create_cards(radical_data, is_radical=True)