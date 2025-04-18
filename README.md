# Kanji Parser
This project trys to recreate the study method used on JPDB.io where a vocab word is broken down into it's component kanji and those component kaji are further broken down into component radicals. First the radicals are studied and once they reach the "known" threshold (21 days) and kanji cards that have all radiclas known will be "unlocked" (unsuspended in anki) and ready for study. Once the component kanji for a vocab word are then known that vocab word is unlocked.

## Prereqs
* Anki Desktop
* AnkiConnect
* Create a Python venv and install dependencies with `pip install -r requirements.txt`

## Yomitan Usage
1. Add cards to anki with yomitan to the **yomitan Japanese** note type
1. Run the update script.
1. Run the `update-cards.py` script at whatever cadence to unlock new cards

## JPDB Usage
1. Download reviews.json from JPDB and move file to same dir as `import-JPDB.py`
1. Run the `import-JPDB.py` script
1. Run the `update-cards.py` script

## JLPT Checker
```bash
python jlpt-checker.py
```
- Check all JLPT levels (N5, N4, N3, N2, N1)
- Display the percentage of vocabulary you know for each level
- Create separate files for missing vocabulary at each level
- Show a summary of your overall JLPT vocabulary knowledge

### How It Works

1. The script connects to Anki through the AnkiConnect API
2. It retrieves all notes with the "known" tag
3. It compares these notes with the JLPT vocabulary lists in the `jlpt-vocab` directory
4. It calculates the percentage of vocabulary you know for each level
5. It generates text files listing the missing vocabulary