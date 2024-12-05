import regex as re
import json
import os
import requests

ANKI_CONNECT_URL = "http://localhost:8765"
KANJI_OUTPUT = "kanji_to_add.json"

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

def get_card_data(card_id):
    response = invoke("cardsInfo", cards=[card_id])
    return response[0]

def get_card_interval(card_id):
    response = invoke("getIntervals", cards=[card_id])
    return response[0]

def get_note_id_for_cards(cards_ids):
    response = invoke('cardsToNotes', cards=cards_ids)
    return response

def get_cards_with_missing_kanji():
    query = 'note:"yomitan Japanese" Kanji:'
    response = invoke("findCards", query=query)
    return response

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
        data = get_card_data(card_id)
        dependencies = data['fields'][dependency_type]['value']
        dependency_array = [dependency.strip() for dependency in dependencies.split(',')]
        if check_dependencies_known(dependency_array):
            replace_tags([card_id], 'new', 'locked')
            cards_to_unsuspend.append(card_id)
        else:
            print(f"Card {card_id} still has not yet known {dependency_type}")
    invoke('unsuspend', cards=cards_to_unsuspend)


# unlock_cards("yomitan Japanese")
# unlock_cards("Japanese Kanji")

def extract_kanji(word):
    return re.findall(r'\p{Han}', word)

def update_card(card_id, new_kanji):
    note = {"id": card_id, "fields": {"Kanji": new_kanji}}
    response = invoke("updateNoteFields", note=note)
    return response

def add_tags_and_suspend(card_ids, tags):
    # Add tags
    invoke("addTags", notes=card_ids, tags=tags)

    # Suspend cards
    invoke("suspend", cards=card_ids)

def save_kanji_set(kanji_set):
    with open(KANJI_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(sorted(kanji_set), f, ensure_ascii=False, indent=4)

def main():
    # Step 1: Find cards with missing kanji field
    card_ids = get_cards_with_missing_kanji()

    if not card_ids:
        print("No cards found with missing kanji.")
        return

    # Step 2: Get card data
    cards = get_card_data(card_ids)

    # Step 3: Update cards with kanji
    kanji_set = set()
    for card in cards:
        note_id = card['note']
        expression = card['fields']['Expression']['value']
        kanji_list = extract_kanji(expression)
        if not kanji_list:
            print(f"Skipping {expression} as it doesn't contain kanji")
            continue
        kanji_set.update(kanji_list)
        new_kanji = " ".join(kanji_list)
        update_card(note_id, new_kanji)

    save_kanji_set(kanji_set)

    # Step 4: Add tags and suspend cards
    add_tags_and_suspend(card_ids, "locked")
    print(f"Updated {len(card_ids)} cards and suspended them.")
