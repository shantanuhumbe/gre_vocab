import json
import requests
import google.generativeai as genai

def generate_verbal_question(word, definition, api_key=None, engine="Ollama", question_type="SE"):
    """
    Generates a GRE-style practice question (Sentence Equivalence or Text Completion)
    testing the user's understanding of the target word.
    """
    
    if question_type == "SE":
        prompt = f"""
        You are a GRE Verbal test maker. Write a realistic GRE Sentence Equivalence (SE) question.
        
        Target Word: "{word}"
        Definition: "{definition}"
        
        An SE question contains a single sentence with one blank and six answer choices (A-F). 
        Exactly two answer choices must be synonyms that logically fit the blank and produce equivalent meaning for the sentence.
        One of the correct answers must be "{word}", and the other correct answer must be a close synonym of "{word}".
        
        You must output your response in EXACTLY the following JSON format:
        {{
            "type": "SE",
            "sentence": "The candidate's ________ response to the simple question raised suspicions that he was deliberately hiding information.",
            "choices": ["A. laconic", "B. equivocal", "C. explicit", "D. ambiguous", "E. verbose", "F. transparent"],
            "correct_answers": ["B", "D"],
            "explanation": "Both 'equivocal' and 'ambiguous' mean open to multiple interpretations or vague, fitting the clue 'deliberately hiding information'."
        }}
        """
    else:  # Text Completion (TC) - Single blank
        prompt = f"""
        You are a GRE Verbal test maker. Write a realistic GRE Text Completion (TC) question.
        
        Target Word: "{word}"
        Definition: "{definition}"
        
        A single-blank TC question contains a sentence with one blank and five answer choices (A-E). 
        Only one answer choice is correct. The correct answer must be "{word}".
        
        You must output your response in EXACTLY the following JSON format:
        {{
            "type": "TC",
            "sentence": "Despite the team's massive defeat, the coach's comments were surprisingly ________, focusing solely on the players' efforts rather than the score.",
            "choices": ["A. pugnacious", "B. despondent", "C. laudatory", "D. laconic", "E. indifferent"],
            "correct_answers": ["C"],
            "explanation": "The contrast 'Despite... defeat' indicates the coach's comments were praise-filled (laudatory), which focuses on player efforts."
        }}
        """

    prompt += "\nDo not include any thinking tags (<think>...</think>), comments, markdown formatting, or extra text. Output ONLY valid JSON."

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
            
    else:  # Ollama (deepseek-r1)
        url = "http://localhost:11434/api/generate"
        payload = {
            "model": "deepseek-r1:14b",
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.5
            }
        }
        try:
            res = requests.post(url, json=payload, timeout=60)
            if res.status_code == 200:
                raw_response = res.json().get("response", "")
                if "<think>" in raw_response:
                    raw_response = raw_response.split("</think>")[-1].strip()
                data = json.loads(raw_response)
                return data
            else:
                return {"error": f"Ollama HTTP Error: {res.status_code}"}
        except requests.exceptions.ConnectionError:
            return {"error": "Could not connect to Ollama. Make sure Ollama is running locally."}
        except Exception as e:
            return {"error": f"Ollama Error: {str(e)}"}
