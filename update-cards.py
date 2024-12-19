import regex as re
import json
import requests
import urllib.parse
from bs4 import BeautifulSoup

ANKI_CONNECT_URL = "http://localhost:8765"
ANKI_DECK = "Kanji and Radicals"
VOCAB_NOTE_TYPE = "yomitan Japanese" #"JPDB Japanese Vocab"
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

def get_intervals(card_ids):
    response = invoke("getIntervals", cards=card_ids)
    return response

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
    print("🔐 Suspended all locked cards")

def move_new_to_known():
    cards_to_update = []
    new_cards = get_cards_by_tag('new')
    intervals = get_intervals(new_cards)
    total = len(new_cards)
    current = 0
    print(f"Checking {total} cards to see if any can be moved to known...")

    for card_id, interval in zip(new_cards, intervals):
        current += 1
        print(f"\rChecking {current}/{total}...", end="", flush=True)

        if interval >= 21:
            cards_to_update.append(card_id)
    if cards_to_update:
        replace_tags(cards_to_update, 'known', 'new')
        print(f"\n✅ {len(cards_to_update)} cards moved to known")
    else:
        print(f"\n📝 No new cards known. Keep studying!")
        
def replace_tags(card_ids, new_tag, old_tag):
    note_ids = get_note_id_for_cards(card_ids)
    invoke('replaceTags', notes=note_ids, replace_with_tag=new_tag, tag_to_replace=old_tag)

def check_dependencies_known(characters, known_cards):
    for character in characters:
        if any(card.get("fields",{}).get("Character",{}).get("value") == character for card in known_cards):
            continue
        else:
            return False
    return True

def unlock_cards(note_type):
    dependency_type = 'Radicals' if note_type == 'Japanese Kanji' else 'Kanji'
    cards_to_unlock = []
    locked_card_ids = get_cards_by_tag('locked', note_type)
    known_card_ids = get_cards_by_tag('known')
    known_card_data = get_card_data(known_card_ids)
    total = len(locked_card_ids)
    current = 0
    print(f"Checking {total} {note_type} cards to see if any can be unlocked...")

    for card_id in locked_card_ids:
        current += 1
        print(f"\rChecking {current}/{total}...", end="", flush=True)

        data = get_card_data([card_id])[0]
        dependencies = data['fields'][dependency_type]['value']
        dependency_array = [dependency.strip() for dependency in dependencies.split(',')]
        if check_dependencies_known(dependency_array, known_card_data):
            cards_to_unlock.append(card_id)
    if len(cards_to_unlock) > 0:
        replace_tags(cards_to_unlock, 'new', 'locked')
        invoke('unsuspend', cards=cards_to_unlock)
        print(f"\n🔓 {len(cards_to_unlock)} cards unlocked!")
    else:
        print(f"\n📝 No cards to unlock. Keep studying!")

def update_vocab_notes():
    note_ids = get_notes_with_missing_kanji()
    if not note_ids:
        print("No notes found with missing kanji.")
        return
    print(f"🈳 Checking {len(note_ids)} notes with missing kanji...")

    notes = get_note_data(note_ids)
    kanji_set = set()
    updated = 0
    for note in notes:
        note_id = note['noteId']
        expression = note['fields']['Expression']['value']
        kanji_list = extract_kanji(expression)
        if not kanji_list:
            continue
        updated += 1
        kanji_set.update(kanji_list)
        new_kanji = ", ".join(kanji_list)
        update_note(note_id, new_kanji)
        current_tags = invoke('getNoteTags', note=note_id)
        if "known" not in current_tags and "new" not in current_tags:
            invoke('addTags', notes=[note_id], tags="locked")
    if updated > 0:
        print(f"🟢 Updated {len(updated)} vocab cards with kanji!")
    else:
        print(f"No notes need kanji added")

    return kanji_set

def get_keyword_and_mnemonic(character):
    encoded_kanji = urllib.parse.quote(character)
    url = f"https://jpdb.io/kanji/{encoded_kanji}"
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

        keyword_div = soup.find('h6', string="Keyword")
        keyword = keyword_div.find_next('div').text if keyword_div else ""
        
        mnemonic_div = soup.find('div', class_='mnemonic')
        mnemonic = mnemonic_div.decode_contents().strip() if mnemonic_div else ""
        
        return keyword, mnemonic
    else:
        print(f"🟡 Warning: Failed to fetch data for '{character}', status code: {response.status_code}")
        return "", ""
    
def extract_kanji(word):
    return re.findall(r'\p{Han}', word)

def load_kanji_data(json_file):
    try:
        with open(json_file, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"🔴 Error: {json_file} not found.")
        return {}
    except json.JSONDecodeError:
        print(f"🔴 Error: {json_file} is not a valid JSON file.")
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
        radicals = details.get("radicals", [])

        if not radicals:
            radical_set.add(kanji)
        else:
            kanji_set[kanji] = {
                "radicals": radicals,
            }
            radical_set.update(radicals)

    return kanji_set, radical_set

def create_cards(data, is_radical):
    total = len(data)  # Total number of items to process
    current = 0
    created = 0
    char_type = 'radicals' if is_radical else 'kanji'
    print(f'There are {total} {char_type} to process')

    if is_radical:
        for character in data:
            current += 1

            if note_exists(character):
                continue
            print(f"\r{current}/{total} Processing...", end="", flush=True)

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
            created += 1
        print(f"🟢 Created {len(created)} new radical cards!")

    else:
        for character, details in data.items():
            current += 1

            if note_exists(character):
                continue
            print(f"\r{current}/{total} Processing...", end="", flush=True)
            
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
            created += 1
        print(f"🟢 Created {len(created)} new radical cards!")

def create_kanji_and_radicals(kanji_list):
    kanji_mapping_data = load_kanji_data(KRADFILE)
    kanji_and_radicals = map_kanji_and_radicals(kanji_list, kanji_mapping_data)
    kanji_data, radical_data = create_sets(kanji_and_radicals)
    create_cards(kanji_data, is_radical=False)
    create_cards(radical_data, is_radical=True)

# Step 1 is to add kanji to all vocab cards and then create the kanji and radical cards if need be
print("This script will evaluate your ANKI collection and make sure that it has\nall the correct kanji and radicals needed to learn new vocab words. Make\nsure you let it run to completion so it doesn't leave any cards partially\ncomplete.\n")
print("🚀 Off we go!")
kanji_to_create = update_vocab_notes()
if kanji_to_create:
    create_kanji_and_radicals(kanji_to_create)

# Step 2 is to move all new cards to known if their interval is greater than 45 days
move_new_to_known()

# Step 3 is to unlock any kanji cards that have all their radicals known
unlock_cards(KANJI_NOTE_TYPE)

# Step 4 is to unlock and vocab cards that have all their kanji known
unlock_cards(VOCAB_NOTE_TYPE)

# Make sure any cards tagged locked are suspended
suspend_all_locked()
print("🎉 Updates are completed. Don't forget to run this script on a regular cadence to unlock new cards!")