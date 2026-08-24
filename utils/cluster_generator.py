import json
import re
import requests
import google.generativeai as genai
import database as db

def run_ai_clustering(base_words, api_key=None, engine="Ollama", progress_callback=None):
    """
    Groups all base_words into semantic categories in batches of 50 using Ollama or Gemini.
    """
    batch_size = 50
    all_clusters = {}
    
    total_batches = (len(base_words) + batch_size - 1) // batch_size
    
    for i in range(0, len(base_words), batch_size):
        batch_idx = (i // batch_size) + 1
        if progress_callback:
            progress_callback(batch_idx, total_batches)
            
        batch = base_words[i:i+batch_size]
        words_input = [{"word": w["word"], "definition": w["definition"]} for w in batch]
        
        prompt = f"""
        You are a GRE Verbal curriculum designer. 
        Analyze the following {len(batch)} GRE words and group them into logical synonym/semantic clusters.
        Create groups for similar-meaning words, matching concepts (e.g. 'Stubbornness', 'Talkative', 'Vague/Ambiguous').
        Each word should be placed in at least one group.
        
        Input:
        {json.dumps(words_input, indent=2)}
        
        You must output your response in EXACTLY the following JSON format:
        {{
            "Group Name 1": {{
                "description": "Short description of this group's theme",
                "words": ["word_from_input_1", "word_from_input_2"]
            }},
            "Group Name 2": {{
                "description": "...",
                "words": ["word_from_input_3"]
            }}
        }}
        Do not output thinking tags (<think>...</think>), comments, markdown, or any text other than the JSON string.
        """
        
        try:
            if engine == "Gemini":
                if not api_key:
                    print("Error: API Key missing for Gemini clustering.")
                    break
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-2.5-flash")
                response = model.generate_content(
                    prompt,
                    generation_config={"response_mime_type": "application/json"}
                )
                batch_clusters = json.loads(response.text)
            else:  # Ollama
                url = "http://localhost:11434/api/generate"
                payload = {
                    "model": "deepseek-r1:14b",
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": 0.3
                    }
                }
                res = requests.post(url, json=payload, timeout=90)
                if res.status_code == 200:
                    raw_response = res.json().get("response", "")
                    if "<think>" in raw_response:
                        raw_response = raw_response.split("</think>")[-1].strip()
                    batch_clusters = json.loads(raw_response)
                else:
                    print(f"Ollama Error in batch {batch_idx}: HTTP {res.status_code}")
                    continue
                    
            # Merge batch clusters into all_clusters
            for group_name, data in batch_clusters.items():
                # Normalize group name to group similar groups
                g_key = group_name.strip().title()
                
                # Deduplicate group names if similar
                matched_key = g_key
                for existing_key in all_clusters.keys():
                    if existing_key.lower() == g_key.lower() or existing_key.lower() in g_key.lower() or g_key.lower() in existing_key.lower():
                        matched_key = existing_key
                        break
                        
                if matched_key not in all_clusters:
                    all_clusters[matched_key] = {"description": data.get("description", ""), "words": []}
                
                # Append words case-sensitively matching user database
                for w in data.get("words", []):
                    # Find exact word format from batch
                    orig_word = w.strip()
                    for item in batch:
                        if item["word"].lower().strip() == w.lower().strip():
                            orig_word = item["word"]
                            break
                    if orig_word not in all_clusters[matched_key]["words"]:
                        all_clusters[matched_key]["words"].append(orig_word)
                        
            # Save progress incrementally after each batch
            if all_clusters:
                db.save_word_clusters(all_clusters)
                
        except Exception as e:
            print(f"Exception during clustering batch {batch_idx}: {str(e)}")
            continue
            
    return all_clusters
