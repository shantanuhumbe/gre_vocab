import os
import json
import requests
import google.generativeai as genai

def generate_mnemonic_and_enrichment(word, definition, api_key=None, engine="Ollama"):
    """
    Queries Ollama (deepseek-r1) or Gemini to generate a mnemonic, 
    context sentence, synonyms, and antonyms for a GRE word.
    """
    prompt = f"""
    You are a GRE Verbal expert and cognitive learning coach. 
    Analyze the following GRE word and generate high-quality learning aids.
    
    Word: "{word}"
    Definition: "{definition}"
    
    You must output your response in EXACTLY the following JSON format:
    {{
        "synonyms": ["synonym1", "synonym2", "synonym3"],
        "antonyms": ["antonym1", "antonym2", "antonym3"],
        "sentence": "A GRE-level context sentence demonstrating the word's usage.",
        "mnemonic": "A memorable and clever mnemonic or mental hook to easily remember this word."
    }}
    Do not include any extra text, comments, markdown blocks, or thinking sections in the final output. Only return the valid JSON string.
    """

    if engine == "Gemini":
        if not api_key:
            return {"error": "Gemini API Key is missing. Set it in the sidebar config."}
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            data = json.loads(response.text)
            return data
        except Exception as e:
            return {"error": f"Gemini API Error: {str(e)}"}
            
    else:  # Ollama (deepseek-r1:14b or similar)
        url = "http://localhost:11434/api/generate"
        payload = {
            "model": "deepseek-r1:14b",
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.4
            }
        }
        try:
            res = requests.post(url, json=payload, timeout=60)
            if res.status_code == 200:
                raw_response = res.json().get("response", "")
                
                # Strip out DeepSeek thinking tags <think>...</think> if present
                if "<think>" in raw_response:
                    raw_response = raw_response.split("</think>")[-1].strip()
                    
                data = json.loads(raw_response)
                return data
            else:
                return {"error": f"Ollama HTTP Error: {res.status_code}"}
        except requests.exceptions.ConnectionError:
            return {"error": "Could not connect to Ollama. Make sure the Ollama app is running locally on port 11434."}
        except Exception as e:
            return {"error": f"Ollama Error: {str(e)}"}

def verify_user_sentence(word, definition, user_sentence, api_key=None, engine="Ollama"):
    """
    Asks Ollama or Gemini to verify if the user's sentence uses the GRE word correctly.
    """
    prompt = f"""
    You are a GRE Verbal coach. Analyze the following sentence written by a student.
    Verify if the GRE word "{word}" is used correctly according to its definition: "{definition}".
    
    Student Sentence: "{user_sentence}"
    
    You must output your response in EXACTLY the following JSON format:
    {{
        "correct": true or false,
        "feedback": "A short (1-2 sentences) explanation of why it is correct, or correcting the grammatical/context error if wrong."
    }}
    Do not output thinking tags (<think>...</think>), markdown, or any text other than the JSON string.
    """
    
    if engine == "Gemini":
        if not api_key:
            return {"error": "Gemini API Key is missing."}
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            return json.loads(response.text)
        except Exception as e:
            return {"error": f"Gemini API Error: {str(e)}"}
            
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
        try:
            res = requests.post(url, json=payload, timeout=60)
            if res.status_code == 200:
                raw_response = res.json().get("response", "")
                if "<think>" in raw_response:
                    raw_response = raw_response.split("</think>")[-1].strip()
                return json.loads(raw_response)
            else:
                return {"error": f"Ollama HTTP Error: {res.status_code}"}
        except requests.exceptions.ConnectionError:
            return {"error": "Could not connect to Ollama. Make sure Ollama is running."}
        except Exception as e:
            return {"error": f"Ollama Error: {str(e)}"}
