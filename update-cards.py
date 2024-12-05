import urllib.request
import regex as re
import json

ANKI_CONNECT_URL = "http://localhost:8765"
KANJI_OUTPUT = "kanji_to_add.json"

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

def extract_kanji(word):
    return re.findall(r'\p{Han}', word)

def get_cards_with_missing_kanji():
    query = 'note:"yomitan Japanese" Kanji:'
    response = invoke("findCards", query=query)
    return response

def get_card_data(card_ids):
    response = invoke("cardsInfo", cards=card_ids)
    return response

def update_card(card_id, new_kanji):
    """Update the kanji field of a card."""
    note = {"id": card_id, "fields": {"Kanji": new_kanji}}
    response = invoke("updateNoteFields", note=note)
    return response

def add_tags_and_suspend(card_ids, tags):
    """Add tags and suspend cards."""
    # Add tags
    invoke("addTags", notes=card_ids, tags=tags)

    # Suspend cards
    invoke("suspend", cards=card_ids)

def save_kanji_set(kanji_set):
    """Save the collected kanji set to a JSON file."""
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

main()