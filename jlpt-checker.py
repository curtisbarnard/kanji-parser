import json
import requests
import csv
import os
import regex as re
import sys

# Constants
ANKI_CONNECT_URL = "http://localhost:8765"
JLPT_LEVELS = ["n5", "n4", "n3", "n2", "n1"]  # All JLPT levels
OUTPUT_DIR = "."  # Current directory for output files

def invoke(action, **params):
    """Send a request to AnkiConnect and return the result."""
    request = {'action': action, 'params': params, 'version': 6}
    try:
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
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to Anki. Please make sure Anki is running and AnkiConnect is installed.")
        sys.exit(1)
    except Exception as e:
        print(f"Error communicating with AnkiConnect: {e}")
        sys.exit(1)

def get_known_cards():
    """Get all cards with the 'known' tag."""
    print("Fetching known cards from Anki...")
    query = 'tag:known'
    note_ids = invoke('findNotes', query=query)
    if not note_ids:
        print("No cards with 'known' tag found in Anki.")
        return []
    
    print(f"Found {len(note_ids)} notes with 'known' tag. Fetching details...")
    notes = invoke('notesInfo', notes=note_ids)
    return notes

def extract_kanji(word):
    """Extract kanji characters from a word."""
    return re.findall(r'\p{Han}', word)

def load_jlpt_vocab(level):
    """Load JLPT vocabulary from CSV file."""
    vocab_list = []
    file_path = f"jlpt-vocab/{level}.csv"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                vocab_list.append({
                    'kanji': row['kanji'],
                    'kana': row['kana'],
                    'definition': row['waller_definition']
                })
        return vocab_list
    except Exception as e:
        print(f"Error loading JLPT vocabulary: {e}")
        return []

def normalize_japanese(text):
    """Normalize Japanese text for better matching."""
    # Remove any non-Japanese characters and whitespace
    return re.sub(r'[^\p{Hiragana}\p{Katakana}\p{Han}]', '', text)

def check_jlpt_level(level, known_cards):
    """Check how many words from a JLPT level are known."""
    jlpt_vocab = load_jlpt_vocab(level)
    if not jlpt_vocab:
        print(f"No vocabulary found for JLPT {level.upper()}")
        return
    
    print(f"Analyzing JLPT {level.upper()} vocabulary ({len(jlpt_vocab)} words)...")
    
    # Extract expressions from known cards
    known_expressions = set()
    known_readings = set()
    
    for note in known_cards:
        if 'Expression' in note['fields']:
            expression = note['fields']['Expression']['value']
            normalized_expr = normalize_japanese(expression)
            known_expressions.add(normalized_expr)
            known_expressions.add(expression)
            
            # Also add the reading as some cards might be stored by reading
            if 'Reading' in note['fields']:
                reading = note['fields']['Reading']['value']
                normalized_reading = normalize_japanese(reading)
                known_readings.add(normalized_reading)
                known_readings.add(reading)
    
    # Check which JLPT words are known
    known_jlpt_words = []
    missing_jlpt_words = []
    
    for word in jlpt_vocab:
        # Normalize the vocabulary words
        normalized_kanji = normalize_japanese(word['kanji']) if word['kanji'] else ""
        normalized_kana = normalize_japanese(word['kana'])
        
        # Check if either kanji or kana form is known
        if normalized_kanji and (normalized_kanji in known_expressions or word['kanji'] in known_expressions):
            known_jlpt_words.append(word)
        elif normalized_kana in known_expressions or normalized_kana in known_readings or word['kana'] in known_expressions or word['kana'] in known_readings:
            known_jlpt_words.append(word)
        else:
            missing_jlpt_words.append(word)
    
    # Calculate percentage
    total_words = len(jlpt_vocab)
    known_count = len(known_jlpt_words)
    percentage = (known_count / total_words) * 100 if total_words > 0 else 0
    
    # Print results
    print(f"\nJLPT {level.upper()} Vocabulary Knowledge:")
    print(f"Known: {known_count}/{total_words} words ({percentage:.1f}%)")
    
    # Write missing words to file
    output_file = f"missing_jlpt_{level}_vocab.txt"
    with open(output_file, 'w', encoding='utf-8') as file:
        file.write(f"Missing JLPT {level.upper()} Vocabulary ({len(missing_jlpt_words)} words):\n\n")
        for word in missing_jlpt_words:
            kanji_part = f"{word['kanji']} " if word['kanji'] else ""
            file.write(f"{kanji_part}[{word['kana']}] - {word['definition']}\n")
    
    print(f"Missing words list saved to {output_file}")
    
    return percentage, known_count, total_words

def print_summary(results):
    """Print a summary of all JLPT levels checked."""
    if not results:
        return
    
    print("\n" + "="*50)
    print("SUMMARY OF JLPT VOCABULARY KNOWLEDGE")
    print("="*50)
    
    total_known = sum(result[1] for result in results.values())
    total_words = sum(result[2] for result in results.values())
    overall_percentage = (total_known / total_words) * 100 if total_words > 0 else 0
    
    print(f"Overall: {total_known}/{total_words} words ({overall_percentage:.1f}%)\n")
    
    # Print a table of results for each level
    print(f"{'Level':<10}{'Known':<15}{'Total':<15}{'Percentage':<10}")
    print("-"*50)
    
    # Sort levels from N5 (easiest) to N1 (hardest)
    for level in sorted(results.keys(), reverse=True):
        percentage, known, total = results[level]
        print(f"{level.upper():<10}{known:<15}{total:<15}{percentage:.1f}%")

def main():
    print("Checking JLPT vocabulary knowledge...")
    print("Make sure Anki is running with the AnkiConnect add-on installed.")
    
    try:
        # Check if Anki is running by making a simple request
        invoke('version')
        
        # Get all known cards
        known_cards = get_known_cards()
        if not known_cards:
            return
            
        print(f"Successfully retrieved {len(known_cards)} known cards")
        
        levels_to_check = JLPT_LEVELS
        print("Checking all JLPT levels (N5-N1)...")
        
        # Check each JLPT level and store results
        results = {}
        for level in levels_to_check:
            result = check_jlpt_level(level, known_cards)
            if result:
                results[level] = result
        
        # Print summary if we checked multiple levels
        if len(results) > 1:
            print_summary(results)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
