import sqlite3
import os
import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gre_vocab.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Word progress tracking table
    c.execute('''
        CREATE TABLE IF NOT EXISTS word_progress (
            word TEXT PRIMARY KEY,
            box INTEGER DEFAULT 1,
            correct_attempts INTEGER DEFAULT 0,
            incorrect_attempts INTEGER DEFAULT 0,
            last_reviewed TIMESTAMP,
            next_review_date TIMESTAMP,
            starred INTEGER DEFAULT 0,
            mnemonic TEXT DEFAULT "",
            sentence TEXT DEFAULT "",
            synonyms TEXT DEFAULT "",
            antonyms TEXT DEFAULT ""
        )
    ''')
    
    # Quiz history logging table
    c.execute('''
        CREATE TABLE IF NOT EXISTS quiz_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            quiz_type TEXT,
            score INTEGER,
            total_questions INTEGER
        )
    ''')
    
    # Word clusters table for AI grouping
    c.execute('''
        CREATE TABLE IF NOT EXISTS word_clusters (
            cluster_name TEXT,
            word TEXT,
            description TEXT,
            PRIMARY KEY (cluster_name, word)
        )
    ''')
    
    conn.commit()
    conn.close()

def get_word_progress(word):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM word_progress WHERE word = ?', (word,))
    row = c.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def update_word_progress(word, is_correct):
    conn = get_db_connection()
    c = conn.cursor()
    
    # Fetch existing
    c.execute('SELECT box, correct_attempts, incorrect_attempts FROM word_progress WHERE word = ?', (word,))
    row = c.fetchone()
    
    now = datetime.datetime.now()
    
    if row:
        curr_box = row['box']
        correct = row['correct_attempts']
        incorrect = row['incorrect_attempts']
        
        if is_correct:
            new_box = min(5, curr_box + 1)
            correct += 1
        else:
            new_box = 1  # Leitner rule: reset to box 1 on mistake
            incorrect += 1
            
        # Spaced repetition intervals: Box 1 (1 day), Box 2 (2 days), Box 3 (5 days), Box 4 (10 days), Box 5 (30 days)
        intervals = {1: 1, 2: 2, 3: 5, 4: 10, 5: 30}
        next_review = now + datetime.timedelta(days=intervals.get(new_box, 1))
        
        c.execute('''
            UPDATE word_progress 
            SET box = ?, correct_attempts = ?, incorrect_attempts = ?, last_reviewed = ?, next_review_date = ?
            WHERE word = ?
        ''', (new_box, correct, incorrect, now.isoformat(), next_review.isoformat(), word))
    else:
        new_box = 2 if is_correct else 1
        correct = 1 if is_correct else 0
        incorrect = 0 if is_correct else 1
        
        intervals = {1: 1, 2: 2, 3: 5, 4: 10, 5: 30}
        next_review = now + datetime.timedelta(days=intervals.get(new_box, 1))
        
        c.execute('''
            INSERT INTO word_progress (word, box, correct_attempts, incorrect_attempts, last_reviewed, next_review_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (word, new_box, correct, incorrect, now.isoformat(), next_review.isoformat()))
        
    conn.commit()
    conn.close()

def toggle_starred(word):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT starred FROM word_progress WHERE word = ?', (word,))
    row = c.fetchone()
    
    if row:
        new_starred = 0 if row['starred'] else 1
        c.execute('UPDATE word_progress SET starred = ? WHERE word = ?', (new_starred, word))
    else:
        new_starred = 1
        c.execute('INSERT INTO word_progress (word, starred) VALUES (?, 1)', (word,))
        
    conn.commit()
    conn.close()
    return new_starred

def save_ai_enrichment(word, mnemonic, sentence, synonyms, antonyms):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT word FROM word_progress WHERE word = ?', (word,))
    row = c.fetchone()
    
    # Format list inputs to strings if lists are provided
    if isinstance(synonyms, list):
        synonyms = ", ".join(synonyms)
    if isinstance(antonyms, list):
        antonyms = ", ".join(antonyms)
        
    if row:
        c.execute('''
            UPDATE word_progress 
            SET mnemonic = ?, sentence = ?, synonyms = ?, antonyms = ?
            WHERE word = ?
        ''', (mnemonic, sentence, synonyms, antonyms, word))
    else:
        c.execute('''
            INSERT INTO word_progress (word, mnemonic, sentence, synonyms, antonyms)
            VALUES (?, ?, ?, ?, ?)
        ''', (word, mnemonic, sentence, synonyms, antonyms))
        
    conn.commit()
    conn.close()

def get_all_starred():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM word_progress WHERE starred = 1')
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_reviewed():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM word_progress')
    rows = c.fetchall()
    conn.close()
    return {r['word']: dict(r) for r in rows}

def get_leitner_box_counts(total_words):
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('SELECT box, count(*) FROM word_progress GROUP BY box')
    rows = c.fetchall()
    conn.close()
    
    counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for box, cnt in rows:
        if box in counts:
            counts[box] = cnt
            
    # Unstudied words are in Box 1 virtually, but we can display counts of active study
    active_total = sum(counts.values())
    unstudied = max(0, total_words - active_total)
    
    return counts, unstudied

def log_quiz_attempt(quiz_type, score, total_questions):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO quiz_history (quiz_type, score, total_questions)
        VALUES (?, ?, ?)
    ''', (quiz_type, score, total_questions))
    conn.commit()
    conn.close()

def get_quiz_stats():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM quiz_history ORDER BY timestamp DESC')
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def save_word_clusters(clusters_dict):
    """
    Saves AI clusters to SQLite database.
    clusters_dict format: {cluster_name: {"words": [w1, w2], "description": "desc"}}
    """
    conn = get_db_connection()
    c = conn.cursor()
    
    # Clear old entries
    c.execute('DELETE FROM word_clusters')
    
    for cluster_name, data in clusters_dict.items():
        desc = data.get("description", "")
        for word in data.get("words", []):
            c.execute('''
                INSERT OR REPLACE INTO word_clusters (cluster_name, word, description)
                VALUES (?, ?, ?)
            ''', (cluster_name, word, desc))
            
    conn.commit()
    conn.close()

def get_word_clusters():
    """
    Retrieves all saved word clusters from SQLite database.
    """
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM word_clusters')
    rows = c.fetchall()
    conn.close()
    
    clusters = {}
    for row in rows:
        c_name = row['cluster_name']
        w = row['word']
        desc = row['description']
        
        if c_name not in clusters:
            clusters[c_name] = {"words": [], "description": desc}
        clusters[c_name]["words"].append(w)
        
    return clusters

# Initialize on import
init_db()
