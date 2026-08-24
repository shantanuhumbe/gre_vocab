import sqlite3
import json
import os

def dump():
    db_file = "/Users/shantanuhumbe/gemini/gre_vocab/gre_vocab.db"
    json_file = "/Users/shantanuhumbe/gemini/gre_vocab/word_clusters.json"
    
    if not os.path.exists(db_file):
        print("Database not found!")
        return
        
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM word_clusters")
    rows = c.fetchall()
    conn.close()
    
    data = []
    for r in rows:
        data.append({
            "cluster_name": r["cluster_name"],
            "word": r["word"],
            "description": r["description"]
        })
        
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump({"word_clusters": data}, f, indent=4)
        
    print(f"Successfully dumped {len(data)} word cluster mappings to {json_file}")

if __name__ == "__main__":
    dump()
