import requests
from bs4 import BeautifulSoup
import urllib.parse
import json

# Define the AnkiConnect endpoint
ANKI_CONNECT_URL = "http://localhost:8765"
file_path = "kanji_data_output.json"

def load_json_data(file_path):
    """Load JSON data from a file."""
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def parse_kanji_and_radicals(data):
    kanji_set = {}
    radical_set = set()  # Use a set to avoid duplicates

    for entry, details in data.items():
        # Process kanji
        for kanji in details.get("kanji", []):
            kanji_set[kanji] = {
                "radicals": details.get("radicals", {}).get(kanji, []),  # Get the list of radicals for the kanji
            }
            # Add the kanji's radicals to the radical set
            radicals = kanji_set[kanji]["radicals"]
            radical_set.update(radicals)

        # Process radicals from radical data
        for radical in details.get("radicals", []):
            radical_set.add(radical)  # Add each radical to the set

    return kanji_set, radical_set

def card_exists(character):
    payload = {
        "action": "findNotes",
        "version": 6,
        "params": {
            "query": f"Character:{character}"
        }
    }
    response = requests.post(ANKI_CONNECT_URL, json=payload)
    if response.status_code == 200:
        result = response.json()
        return len(result['result']) > 0
    else:
        print(f"Error checking card for {character}, status code: {response.status_code}")
        return False

def get_keyword_and_mnemonic(character):
    encoded_kanji = urllib.parse.quote(character)
    url = f"https://jpdb.io/kanji/{encoded_kanji}"
    response = requests.get(url)
    if response.status_code == 200:
        print("Parsing JPDB.io response")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract the keyword
        keyword_div = soup.find('h6', string="Keyword")
        keyword = keyword_div.find_next('div').text if keyword_div else "No keyword found"
        
        # Extract the mnemonic
        mnemonic_div = soup.find('div', class_='mnemonic')
        mnemonic = mnemonic_div.decode_contents().strip() if mnemonic_div else "No mnemonic found"
        
        return keyword, mnemonic
    else:
        print(f"Warning: Failed to fetch data for kanji '{character}', status code: {response.status_code}")
        return "No keyword found", "No mnemonic found"

def add_note(note):
    payload = {
        "action": "addNote",
        "version": 6,
        "params": {
            "note": note
        }
    }
    response = requests.post(ANKI_CONNECT_URL, json=payload)
    if response.status_code == 200:
        result = response.json()
        if "error" in result and result["error"]:
            print(f"Error adding note for {note['fields']['Character']}: {result['error']}")
        else:
            print(f"Note added for {note['fields']['Character']}")
    else:
        print(f"Failed to connect to AnkiConnect: {response.status_code}")

def create_cards(data, is_radical):
    if is_radical:
        for character in data:
            if card_exists(character):
                print(f"Skipping {character} as it already exists.")
                continue
            print(f"Processing {character}...")

            keyword, mnemonic = get_keyword_and_mnemonic(character)
            # Create a radical-specific note
            note = {
                "deckName": "Script Testing",  # Replace with your desired deck name
                "modelName": "Japanese Radicals",  # Model name for radical cards
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
            # Create a kanji-specific note
            radicals = ", ".join(details["radicals"])
            keyword, mnemonic = get_keyword_and_mnemonic(character)

            note = {
                "deckName": "Script Testing",  # Replace with your desired deck name
                "modelName": "Japanese Kanji",  # Model name for kanji cards
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