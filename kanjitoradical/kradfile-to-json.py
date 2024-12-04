import json

def convert_text_to_json(input_file, output_file):
    """Convert kanji-radicals text file to JSON format."""
    kanji_to_radicals = {}
    try:
        with open(input_file, 'r', encoding='utf-8') as file:
            for line in file:
                # Skip empty lines
                if line.strip():
                    # Split the line by ':' to separate kanji from radicals
                    if ':' in line:
                        kanji, radicals = line.split(':')
                        # Remove whitespace and split radicals into a list
                        kanji_to_radicals[kanji.strip()] = radicals.strip().split()
        # Write the dictionary to a JSON file
        with open(output_file, 'w', encoding='utf-8') as json_file:
            json.dump(kanji_to_radicals, json_file, ensure_ascii=False, indent=4)
        print(f"Converted {input_file} to {output_file} successfully.")
    except FileNotFoundError:
        print(f"Error: {input_file} not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

# File paths
input_file = "kradfile-combined"  # Replace with your text file name
output_file = "kradfile-combined.json"  # Output JSON file name

# Convert the file
convert_text_to_json(input_file, output_file)
