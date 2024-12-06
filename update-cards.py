import regex as re
import json
import requests
import urllib.parse
from bs4 import BeautifulSoup

ANKI_CONNECT_URL = "http://localhost:8765"
ANKI_DECK = "Script Testing"
VOCAB_NOTE_TYPE = "yomitan Japanese"
KANJI_NOTE_TYPE = "Japanese Kanji"
RADICAL_NOTE_TYPE = "Japanese Radicals"
KRADFILE = "kanjitoradical/kradfile-combined.json"

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

def get_cards_by_tag(tag, note_type=None):
    query = f'tag:{tag}'
    if note_type:
        query += f' note:"{note_type}"'
    card_ids = invoke('findCards', query=query)
    return card_ids

def get_card_data(card_ids):
    response = invoke("cardsInfo", cards=card_ids)
    return response

def get_card_interval(card_id):
    response = invoke("getIntervals", cards=[card_id])
    return response[0]

def get_note_data(note_ids):
    response = invoke("notesInfo", notes=note_ids)
    return response

def get_note_id_for_cards(cards_ids):
    response = invoke('cardsToNotes', cards=cards_ids)
    return response

def get_notes_with_missing_kanji():
    query = f'note:"{VOCAB_NOTE_TYPE}" Kanji:'
    response = invoke("findNotes", query=query)
    return response

def note_exists(character):
    query = f"Character:{character}"
    response = invoke("findNotes", query=query)
    return response

def update_note(note_id, new_kanji):
    note = {"id": note_id, "fields": {"Kanji": new_kanji}}
    response = invoke("updateNoteFields", note=note)
    return response

def add_note(note):
    response = invoke("addNote", note=note)
    return response

def suspend_all_locked():
    locked_cards = get_cards_by_tag('locked')
    invoke('suspend', cards=locked_cards)

def move_new_to_known():
    cards_to_update = []
    new_cards = get_cards_by_tag('new')
    for card_id in new_cards:
        interval = get_card_interval(card_id)
        if interval >= 45:
            cards_to_update.append(card_id)
    if not cards_to_update:
        print("No cards to move to known")
        return
    else:
        replace_tags(cards_to_update, 'known', 'new')
        
def replace_tags(card_ids, new_tag, old_tag):
    print(f"Moving {len(card_ids)} cards to {new_tag}")
    note_ids = get_note_id_for_cards(card_ids)
    invoke('replaceTags', notes=note_ids, replace_with_tag=new_tag, tag_to_replace=old_tag)

def check_dependencies_known(characters):
    for character in characters:
        response = invoke('findCards', query=f'Character:{character} tag:known')
        if not response:
            return False
    return True

def unlock_cards(note_type):
    dependency_type = 'Radicals' if note_type == 'Japanese Kanji' else 'Kanji'
    cards_to_unsuspend = []
    card_ids = get_cards_by_tag('locked', note_type)
    for card_id in card_ids:
        data = get_card_data([card_id])[0]
        dependencies = data['fields'][dependency_type]['value']
        dependency_array = [dependency.strip() for dependency in dependencies.split(',')]
        if check_dependencies_known(dependency_array):
            replace_tags([card_id], 'new', 'locked')
            cards_to_unsuspend.append(card_id)
        else:
            print(f"Card {card_id} still has not yet known {dependency_type}")
    invoke('unsuspend', cards=cards_to_unsuspend)

def update_vocab_notes():
    note_ids = get_notes_with_missing_kanji()
    if not note_ids:
        print("No notes found with missing kanji.")
        return
    print(f"Updating {len(note_ids)} notes with missing kanji to update")

    notes = get_note_data(note_ids)
    kanji_set = set()
    for note in notes:
        note_id = note['noteId']
        expression = note['fields']['Expression']['value']
        kanji_list = extract_kanji(expression)
        if not kanji_list:
            print(f"Skipping {expression} as it doesn't contain kanji")
            continue
        kanji_set.update(kanji_list)
        new_kanji = ", ".join(kanji_list)
        update_note(note_id, new_kanji)
        invoke('addTags', notes=[note_id], tags="locked")

    return kanji_set

def get_keyword_and_mnemonic(character):
    encoded_kanji = urllib.parse.quote(character)
    url = f"https://jpdb.io/kanji/{encoded_kanji}"
    response = requests.get(url)
    if response.status_code == 200:
        print("Parsing JPDB.io response")
        soup = BeautifulSoup(response.text, 'html.parser')

        keyword_div = soup.find('h6', string="Keyword")
        keyword = keyword_div.find_next('div').text if keyword_div else ""
        
        mnemonic_div = soup.find('div', class_='mnemonic')
        mnemonic = mnemonic_div.decode_contents().strip() if mnemonic_div else ""
        
        return keyword, mnemonic
    else:
        print(f"Warning: Failed to fetch data for kanji '{character}', status code: {response.status_code}")
        return "", ""
    
def extract_kanji(word):
    return re.findall(r'\p{Han}', word)

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

def map_kanji_and_radicals(kanji_list, kanji_data):
    mapped_data = {}
    for kanji in kanji_list:
        mapped_data[kanji] = {
            "radicals": kanji_data.get(kanji, [])
        }
    return mapped_data

def create_sets(data):
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

def create_cards(data, is_radical):
    if is_radical:
        for character in data:
            if note_exists(character):
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
            if note_exists(character):
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
                "tags": ["script_testing", "kanji", "locked"]
            }
            add_note(note)

def create_kanji_and_radicals(kanji_list):
    kanji_mapping_data = load_kanji_data(KRADFILE)
    kanji_and_radicals = map_kanji_and_radicals(kanji_list, kanji_mapping_data)
    kanji_data, radical_data = create_sets(kanji_and_radicals)
    create_cards(kanji_data, is_radical=False)
    create_cards(radical_data, is_radical=True)

# Step 1 is to add kanji to all vocab cards and then create the kanji and radical cards if need be
kanji_to_create = update_vocab_notes()
if kanji_to_create:
    print(f"Creating cards for {len(kanji_to_create)} kanji")
    create_kanji_and_radicals(kanji_to_create)

# Step 2 is to move all new cards to known if their interval is greater than 45 days
move_new_to_known()

# Step 3 is to unlock any kanji cards that have all their radicals known
unlock_cards(KANJI_NOTE_TYPE)

# Step 4 is to unlock and vocab cards that have all their kanji known
unlock_cards(VOCAB_NOTE_TYPE)