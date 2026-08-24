import re
import json
import os

def parse_vocab_file(filepath):
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        lines = [line.strip() for line in f.readlines()]
    
    parsed = []
    curr_word = None
    curr_defs = []
    
    def_starters = {
        'to', 'a', 'an', 'the', 'lasting', 'crude', 'capable', 'difficult', 'showing', 
        'excessive', 'occurring', 'unable', 'not', 'lacking', 'of', 'hostile', 'think', 
        'raise', 'regard', 'being', 'having', 'inspiring', 'stubborn', 'stubbornly', 
        'lying', 'growing', 'persuasion', 'a poem', 'in', 'specifically', 'characterized', 
        'tending', 'expressing', 'criticize', 'laugh', 'steal', 'instruct', 'come', 
        'make', 'clear', 'show', 'dwell', 'arrogantly', 'capture', 'based', 'impossibly', 
        'pompous', 'exceptionally', 'at', 'one', 'act', 'tending', 'causing', 'extremely', 
        'using', 'preventing', 'designed', 'relating', 'expressed', 'concerned', 'characterized'
    }
    
    for idx, line in enumerate(lines):
        if not line:
            continue
            
        is_word = False
        if line[0].isupper() and len(line.split()) <= 3:
            first_word = re.sub(r'[^a-zA-Z]', '', line.split()[0]).lower()
            if first_word not in def_starters and not line.startswith('('):
                if not any(x in line for x in [' is ', ' are ', ' was ', ' were ', ' has ', ' have ']):
                    is_word = True
        
        if is_word:
            if curr_word:
                parsed.append((curr_word, ' '.join(curr_defs)))
            curr_word = line
            curr_defs = []
        else:
            if curr_word:
                curr_defs.append(line)
                
    if curr_word:
        parsed.append((curr_word, ' '.join(curr_defs)))
        
    return parsed

def determine_pos(definition):
    # Heuristic to guess Part of Speech from definition
    def_lower = definition.lower()
    if def_lower.startswith('to ') or def_lower.startswith('make ') or def_lower.startswith('express '):
        return 'verb'
    if def_lower.startswith('a ') or def_lower.startswith('an ') or def_lower.startswith('the ') or def_lower.startswith('lack '):
        return 'noun'
    if def_lower.startswith('lasting ') or def_lower.startswith('crude ') or def_lower.startswith('showing ') or def_lower.startswith('difficult ') or def_lower.startswith('unable '):
        return 'adjective'
    return 'noun'  # default fallback

def main():
    txt_path = '/Users/shantanuhumbe/gemini/vocab/VOCAB.LIST.txt'
    json_path = '/Users/shantanuhumbe/gemini/gre_vocab/words.json'
    
    if not os.path.exists(txt_path):
        print(f"Error: Source TXT file not found at {txt_path}")
        return
        
    print(f"Parsing vocab list: {txt_path}...")
    parsed_words = parse_vocab_file(txt_path)
    print(f"Successfully parsed {len(parsed_words)} words.")
    
    words_data = []
    for word, definition in parsed_words:
        pos = determine_pos(definition)
        words_data.append({
            "word": word,
            "part_of_speech": pos,
            "definition": definition,
            "synonyms": [],
            "antonyms": [],
            "sentence": "",
            "mnemonic": "",
            "difficulty": "Medium"
        })
        
    print(f"Writing database to: {json_path}...")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({"words": words_data}, f, indent=2, ensure_ascii=False)
        
    print("Migration complete!")

if __name__ == '__main__':
    main()
