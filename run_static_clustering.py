import json
import os
import sys
import database as db
from utils.cluster_generator import run_ai_clustering

def main():
    words_file = "/Users/shantanuhumbe/gemini/gre_vocab/words.json"
    if not os.path.exists(words_file):
        print(f"Error: {words_file} not found.")
        return
        
    print("Loading 918 words from words.json...")
    with open(words_file, 'r', encoding='utf-8') as f:
        base_words = json.load(f).get("words", [])
        
    print(f"Loaded {len(base_words)} words. Starting AI clustering via local Ollama (deepseek-r1:14b)...")
    
    def on_progress(batch, total):
        print(f"Clustering batch {batch} of {total}...", flush=True)
        
    try:
        # Run clustering on all words using Ollama
        res = run_ai_clustering(base_words, api_key=None, engine="Ollama", progress_callback=on_progress)
        print(f"\nSuccess! Successfully generated and saved {len(res)} synonym clusters in the database.")
    except Exception as e:
        print(f"\nError running clustering: {str(e)}")

if __name__ == '__main__':
    main()
