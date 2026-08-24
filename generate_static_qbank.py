import json
import os
import sys
import random
import requests
import google.generativeai as genai

# Load data files
words_file = "/Users/shantanuhumbe/gemini/gre_vocab/words.json"
clusters_file = "/Users/shantanuhumbe/gemini/gre_vocab/word_clusters.json"
output_file = "/Users/shantanuhumbe/gemini/gre_vocab/practice_questions.json"

def get_base_words():
    with open(words_file, "r", encoding="utf-8") as f:
        return json.load(f).get("words", [])

def get_clusters():
    with open(clusters_file, "r", encoding="utf-8") as f:
        return json.load(f).get("word_clusters", [])

def generate_verbal_question(word, definition, synonyms, api_key=None, engine="Ollama"):
    """
    Generates a GRE Sentence Equivalence question testing the target word and its synonyms.
    """
    synonyms_str = ", ".join(synonyms)
    prompt = f"""
    You are a GRE Verbal test maker. Write a realistic GRE Sentence Equivalence (SE) question.
    
    Target Word: "{word}"
    Definition: "{definition}"
    Close Synonyms to choose from: {synonyms_str}
    
    An SE question contains a single sentence with one blank and six answer choices (A-F). 
    Exactly two answer choices must be synonyms that logically fit the blank and produce equivalent meaning for the sentence.
    One of the correct answers must be "{word}", and the other correct answer must be one of the close synonyms listed above.
    
    You must output your response in EXACTLY the following JSON format:
    {{
        "sentence": "[Write a unique sentence containing a single blank '________' that tests the target word '{word}' and its synonym]",
        "choices": ["[Choice A including prefix like 'A. ']", "[Choice B]", "[Choice C]", "[Choice D]", "[Choice E]", "[Choice F]"],
        "correct_answers": ["[Letter of first correct answer]", "[Letter of second correct answer]"],
        "explanation": "[Brief explanation of why the correct choices are correct]"
    }}
    Do not output thinking tags (<think>...</think>), comments, or markdown. Output ONLY valid JSON.
    """
    
    if engine == "Gemini":
        if not api_key:
            return {"error": "API Key missing"}
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
            return json.loads(response.text)
        except Exception as e:
            return {"error": str(e)}
    else:  # Ollama
        url = "http://localhost:11434/api/generate"
        payload = {
            "model": "deepseek-r1:14b",
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.4}
        }
        try:
            res = requests.post(url, json=payload, timeout=90)
            if res.status_code == 200:
                raw = res.json().get("response", "")
                if "<think>" in raw:
                    raw = raw.split("</think>")[-1].strip()
                return json.loads(raw)
            return {"error": f"HTTP {res.status_code}"}
        except Exception as e:
            return {"error": str(e)}

def main():
    if not os.path.exists(words_file) or not os.path.exists(clusters_file):
        print("Required files words.json or word_clusters.json not found!")
        return

    base_words = get_base_words()
    clusters = get_clusters()
    
    # Group words by cluster
    groups = {}
    for c in clusters:
        c_name = c["cluster_name"]
        word = c["word"]
        if c_name not in groups:
            groups[c_name] = []
        groups[c_name].append(word)
        
    print(f"Loaded {len(groups)} distinct clusters. Starting Q-bank generation...")
    
    # Load existing practice questions if any to preserve progress
    existing_questions = {}
    if os.path.exists(output_file):
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                existing_questions = json.load(f).get("questions", {})
        except:
            pass
            
    print(f"Found {len(existing_questions)} pre-existing questions in Q-bank.")
    
    # We will generate questions for all clusters that don't have one yet
    count = 0
    for idx, (c_name, words) in enumerate(groups.items()):
        if c_name in existing_questions:
            continue
            
        if len(words) < 2:
            # Not enough words in cluster for a proper SE question
            continue
            
        # Select target word and list of potential synonym options
        target_word = words[0]
        synonyms = words[1:]
        
        # Get target word definition
        definition = ""
        for bw in base_words:
            if bw["word"].lower().strip() == target_word.lower().strip():
                definition = bw["definition"]
                break
        if not definition:
            definition = "related meaning in cluster"
            
        print(f"[{idx+1}/{len(groups)}] Generating question for cluster '{c_name}'...", flush=True)
        
        # Try local Ollama first
        q_data = generate_verbal_question(target_word, definition, synonyms, api_key=None, engine="Ollama")
        
        if "error" in q_data:
            print(f"  Ollama Error: {q_data['error']}. Skipping for now.", flush=True)
            continue
            
        # Save question
        existing_questions[c_name] = q_data
        count += 1
        
        # Save file incrementally after each generation
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({"questions": existing_questions}, f, indent=4)
            
    print(f"\nCompleted! Generated {count} new questions. Total Q-bank size: {len(existing_questions)}")

if __name__ == "__main__":
    main()
