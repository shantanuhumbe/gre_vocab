import streamlit as st
import json
import os
import random
import re
import pandas as pd
import plotly.graph_objects as go
import database as db
from utils.mnemonics import generate_mnemonic_and_enrichment, verify_user_sentence
from utils.verbal_generator import generate_verbal_question
from utils.cluster_generator import run_ai_clustering

# Set page configuration
st.set_page_config(
    page_title="GRE Vocabulary Spaced Repetition Locker",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom injected CSS for premium dark-mode glassmorphism styling
st.markdown("""
<style>
    /* Main container background */
    [data-testid="stAppViewContainer"] {
        background-color: #0B0F19;
        background-image: radial-gradient(circle at 10% 20%, rgba(79, 70, 229, 0.05) 0%, transparent 40%),
                          radial-gradient(circle at 90% 80%, rgba(16, 185, 129, 0.05) 0%, transparent 40%);
        color: #F3F4F6;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #090D16;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    /* Premium card containers */
    .glass-card {
        background: rgba(17, 24, 39, 0.7);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 30px;
        box-shadow: 0 10px 30px 0 rgba(0, 0, 0, 0.5);
        margin: 15px 0;
    }
    
    /* Interactive Card Front/Back */
    .flashcard {
        background: linear-gradient(135deg, rgba(31, 41, 55, 0.9) 0%, rgba(17, 24, 39, 0.9) 100%);
        border: 2px solid rgba(79, 70, 229, 0.3);
        border-radius: 20px;
        padding: 50px 30px;
        text-align: center;
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.6);
        min-height: 280px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        transition: transform 0.3s ease, border-color 0.3s ease;
        margin-bottom: 20px;
    }
    .flashcard:hover {
        border-color: rgba(79, 70, 229, 0.8);
        transform: translateY(-2px);
    }
    
    /* Custom button styling overrides */
    .stButton>button {
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }
    
    /* Title coloring */
    .app-title {
        background: linear-gradient(to right, #6366F1, #10B981);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.2rem;
    }
</style>
""", unsafe_allow_html=True)

# Curated high-frequency GRE Synonym & Semantic Clusters
SYNONYM_CLUSTERS = {
    "Concise / Silent (Lacking Words)": {
        "words": ["laconic", "taciturn", "reticent", "terse", "succinct", "pithy", "brevity"],
        "description": "Words describing people who speak very little, or writing that is extremely brief."
    },
    "Talkative / Wordy": {
        "words": ["loquacious", "garrulous", "voluble", "verbose", "prolix"],
        "description": "Words describing talkative people or excessively wordy speech/writing."
    },
    "Stubborn / Unmanageable": {
        "words": ["obstinate", "obdurate", "refractory", "recalcitrant", "intractable", "dogged", "tenacious", "willful"],
        "description": "Words describing people, animals, or situations that are stubbornly resistant to change, authority, or control."
    },
    "Hostile / Combative": {
        "words": ["pugnacious", "bellicose", "hostile", "malevolent", "belligerent", "truculent", "contentious"],
        "description": "Words describing eager fighting, hostility, or aggressive behaviors."
    },
    "Vague / Ambiguous / Obscure": {
        "words": ["equivocal", "ambiguous", "elusive", "cryptic", "vague", "obscure", "recondite", "abstruse", "arcane", "enigmatic"],
        "description": "Words describing things that are hard to understand, open to double meanings, or require specialized knowledge."
    },
    "Praise / Revere / Glorify": {
        "words": ["adulation", "exalt", "venerate", "laudatory", "extol", "acclaim", "revere", "eulogize"],
        "description": "Words describing high praise, respect, and admiration."
    },
    "Criticize / Scold / Disapprove": {
        "words": ["reprimand", "reproach", "lambast", "recrimination", "tirade", "castigate", "censure", "chastise", "upbraid", "berate", "decry", "scorn"],
        "description": "Words describing harsh criticism, scolding, or expressions of strong disapproval."
    },
    "Arrogant / Proud": {
        "words": ["hubris", "haughty", "disdainful", "contempt", "supercilious", "condescending", "pretentious"],
        "description": "Words describing excessive pride, self-confidence, or treating others as inferior."
    },
    "Fleeting / Temporary": {
        "words": ["ephemeral", "transitory", "transient", "evanescent", "fleeting"],
        "description": "Words describing things that last for a very short time."
    },
    "Timid / Fearful / Shy": {
        "words": ["timorous", "timid", "diffident", "trepidatious", "craven", "pusillanimous"],
        "description": "Words describing nervousness, fear, or a lack of self-confidence."
    },
    "Soothe / Appease / Assuage": {
        "words": ["placate", "mollify", "pacify", "appease", "propitiate", "conciliate", "assuage", "palliative"],
        "description": "Words describing making someone less angry, or relieving pain/hostility."
    },
    "Abundant / Plentiful": {
        "words": ["copious", "profuse", "plethora", "myriad", "abundant", "superfluous", "glut"],
        "description": "Words describing excessive amounts, large quantities, or overflow."
    },
    "Scarcity / Lacking": {
        "words": ["dearth", "paucity", "scarcity", "deficit", "sparse", "meager"],
        "description": "Words describing a lack, shortage, or insufficient amount of something."
    },
    "Truthful / Honest": {
        "words": ["candor", "candid", "veracity", "veritable", "artless", "ingenuous", "probity"],
        "description": "Words describing honesty, sincerity, and moral integrity."
    },
    "Deceptive / Tricky": {
        "words": ["chicanery", "specious", "duplicity", "mendacious", "equivocation", "artful", "guile", "prevaricate"],
        "description": "Words describing trickery, deceit, lying, or making misleading statements."
    }
}

# Load core word database
WORDS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "words.json")

@st.cache_data
def load_base_words():
    if os.path.exists(WORDS_FILE):
        with open(WORDS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f).get("words", [])
    return []

base_words = load_base_words()
total_words = len(base_words)

# Initialize Session States
if "current_word_idx" not in st.session_state:
    st.session_state.current_word_idx = 0
if "card_flipped" not in st.session_state:
    st.session_state.card_flipped = False
if "active_box" not in st.session_state:
    st.session_state.active_box = "All"
if "quiz_question" not in st.session_state:
    st.session_state.quiz_question = None
if "selected_choices" not in st.session_state:
    st.session_state.selected_choices = []
if "quiz_answered" not in st.session_state:
    st.session_state.quiz_answered = False

# Sidebar Configuration
st.sidebar.markdown("<h2 style='text-align: center;'>🎓 Study Config</h2>", unsafe_allow_html=True)

# AI Engine Settings
engine = st.sidebar.selectbox("Mnemonic Engine", ["Ollama (Local)", "Gemini (Cloud)"])
gemini_api_key = ""
if engine == "Gemini (Cloud)":
    gemini_api_key = st.sidebar.text_input("Gemini API Key", type="password", value=os.environ.get("GEMINI_API_KEY", ""))

# Spaced Repetition stats
counts, unstudied = db.get_leitner_box_counts(total_words)
st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Leitner Mastery Box")
col1, col2 = st.sidebar.columns(2)
col1.metric("Box 1 (Hard)", counts[1])
col2.metric("Box 2 (Medium)", counts[2])
col3, col4 = st.sidebar.columns(2)
col3.metric("Box 3 (Easy)", counts[3])
col4.metric("Box 4/5 (Master)", counts[4] + counts[5])
st.sidebar.metric("Unstudied", unstudied)

# Reset option
st.sidebar.markdown("---")
if st.sidebar.button("⚠️ Reset Study History"):
    # Delete DB file
    if os.path.exists(db.DB_PATH):
        os.remove(db.DB_PATH)
    db.init_db()
    st.sidebar.success("Database reset successfully! Reloading...")
    st.rerun()

# Header
st.markdown("<div><span class='app-title'>GRE Vocabulary Spaced Repetition Locker</span></div>", unsafe_allow_html=True)
st.markdown("Master high-frequency GRE words with active recall, spaced repetition, and dynamic verbal practice.", unsafe_allow_html=True)

# Tabs navigation
tab_cards, tab_groups, tab_roots, tab_confusables, tab_practice, tab_analytics = st.tabs([
    "🗂️ Spaced Repetition Locker", 
    "📚 Synonym Groupings",
    "🔑 Root Decoders",
    "🔀 Confusables Locker",
    "⚔️ Practice Arena", 
    "📊 Progress Analytics"
])

# Load reviews progress from SQLite DB
reviewed_data = db.get_all_reviewed()

# Import datetime for due calculations
import datetime

# ----------------- TABS: Leitner Flashcards Locker -----------------
with tab_cards:
    # Filter selection
    box_filter = st.selectbox("Select Study Box Filter", [
        "All", 
        "⏰ Due for Review (Spaced Repetition)", 
        "⭐ Starred Words",
        "Unstudied", 
        "Box 1 (Hard)", 
        "Box 2 (Medium)", 
        "Box 3 (Easy)", 
        "Box 4/5 (Mastered)"
    ])
    
    # Compile candidate list of words based on box filters
    candidate_words = []
    now_dt = datetime.datetime.now()
    
    for w in base_words:
        progress = reviewed_data.get(w['word'])
        if box_filter == "All":
            candidate_words.append(w)
        elif box_filter == "⏰ Due for Review (Spaced Repetition)":
            if progress:
                next_review_str = progress.get('next_review_date')
                if next_review_str:
                    next_review_dt = datetime.datetime.fromisoformat(next_review_str)
                    if next_review_dt <= now_dt:
                        candidate_words.append(w)
            else:
                # Unstudied words are always due
                candidate_words.append(w)
        elif box_filter == "⭐ Starred Words" and progress and progress.get('starred', 0) == 1:
            candidate_words.append(w)
        elif box_filter == "Unstudied" and not progress:
            candidate_words.append(w)
        elif box_filter == "Box 1 (Hard)" and progress and progress['box'] == 1:
            candidate_words.append(w)
        elif box_filter == "Box 2 (Medium)" and progress and progress['box'] == 2:
            candidate_words.append(w)
        elif box_filter == "Box 3 (Easy)" and progress and progress['box'] == 3:
            candidate_words.append(w)
        elif box_filter == "Box 4/5 (Mastered)" and progress and progress['box'] in [4, 5]:
            candidate_words.append(w)

    if not candidate_words:
        st.info(f"No words in selected filter: **{box_filter}**.")
    else:
        # Prevent index out of bounds
        if st.session_state.current_word_idx >= len(candidate_words):
            st.session_state.current_word_idx = 0
            
        current_w = candidate_words[st.session_state.current_word_idx]
        word_text = current_w['word']
        base_definition = current_w['definition']
        pos = current_w.get('part_of_speech', 'noun')
        
        # Enrich from DB if saved previously
        db_details = reviewed_data.get(word_text, {})
        starred = db_details.get('starred', 0)
        mnemonic = db_details.get('mnemonic', '')
        sentence = db_details.get('sentence', '')
        synonyms = db_details.get('synonyms', '')
        antonyms = db_details.get('antonyms', '')
        
        # Flashcard Workspace
        st.markdown(f"**Word {st.session_state.current_word_idx + 1} of {len(candidate_words)}**")
        
        # Card container
        if not st.session_state.card_flipped:
            # Front of the card
            st.markdown(f"""
            <div class='flashcard'>
                <h1 style='font-size: 3.5rem; margin: 0; color: #FFF;'>{word_text}</h1>
                <p style='color: #6366F1; font-style: italic; font-weight: 500; font-size: 1.1rem; margin-top: 10px;'>({pos})</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Browser native Text-To-Speech component (hidden, triggers on click)
            st.components.v1.html(
                f"""
                <button onclick="window.speechSynthesis.speak(new SpeechSynthesisUtterance('{word_text}'))"
                        style="background-color: #4F46E5; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 600; display: inline-flex; align-items: center; gap: 8px; margin-bottom: 20px;">
                    🔊 Pronounce
                </button>
                """,
                height=45
            )
            
            if st.button("Flip to Reveal Meaning", use_container_width=True, type="primary"):
                st.session_state.card_flipped = True
                st.rerun()
        else:
            # Back of the card
            st.markdown(f"""
            <div class='flashcard' style='border-color: rgba(16, 185, 129, 0.4);'>
                <h2 style='font-size: 2.8rem; margin: 0; color: #10B981;'>{word_text}</h2>
                <p style='color: #6B7280; font-style: italic; margin-bottom: 20px;'>({pos})</p>
                <h4 style='color: #FFF; font-weight: 500; padding: 0 10px;'>{base_definition}</h4>
            </div>
            """, unsafe_allow_html=True)
            
            # Show AI Enrichment if exists
            if mnemonic or sentence or synonyms or antonyms:
                st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
                st.subheader("💡 Memory Aids & Context")
                if synonyms:
                    st.write(f"**Synonyms:** {synonyms}")
                if antonyms:
                    st.write(f"**Antonyms:** {antonyms}")
                if sentence:
                    st.info(f"**Example Sentence:** {sentence}")
                if mnemonic:
                    st.success(f"**Mnemonic Hook:** {mnemonic}")
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.info("No memory aids generated yet for this word.")
                
            # Socratic Sentence Checker UI
            st.markdown("<div class='glass-card' style='border-color: rgba(99, 102, 241, 0.4); margin-top: 15px;'>", unsafe_allow_html=True)
            st.subheader("✍️ Socratic Sentence Writer")
            st.write("Write your own sentence using this word to test your active recall and get AI feedback!")
            user_sentence = st.text_input("Enter your sentence:", key=f"user_sent_{word_text}")
            if st.button("🔍 Check Sentence with AI", key=f"btn_chk_{word_text}", use_container_width=True):
                if not user_sentence.strip():
                    st.warning("Please type a sentence first!")
                else:
                    with st.spinner("AI coach is evaluating your sentence context..."):
                        engine_val = "Gemini" if engine == "Gemini (Cloud)" else "Ollama"
                        eval_res = verify_user_sentence(word_text, base_definition, user_sentence, gemini_api_key, engine_val)
                        if "error" in eval_res:
                            st.error(eval_res["error"])
                        else:
                            st.session_state[f"feedback_{word_text}"] = eval_res
                            
            # Display feedback
            fb_key = f"feedback_{word_text}"
            if fb_key in st.session_state:
                res = st.session_state[fb_key]
                if res.get("correct"):
                    st.success(f"🎉 **Correct Context!**\n\n{res.get('feedback')}")
                    # Auto promote word progress in Leitner system on correct sentence creation!
                    if not st.session_state.get(f"promoted_{word_text}"):
                        db.update_word_progress(word_text, is_correct=True)
                        st.session_state[f"promoted_{word_text}"] = True
                        st.balloons()
                else:
                    st.error(f"❌ **Incorrect Context or Grammar:**\n\n{res.get('feedback')}")
            st.markdown("</div>", unsafe_allow_html=True)
                
            # Starred button & AI generation button
            col_act1, col_act2 = st.columns(2)
            star_label = "⭐ Starred (Remove)" if starred else "☆ Star Word"
            if col_act1.button(star_label, use_container_width=True):
                db.toggle_starred(word_text)
                st.rerun()
                
            btn_text = "✨ Generate AI Mnemonics & Details"
            if col_act2.button(btn_text, use_container_width=True, type="secondary"):
                with st.spinner("AI is generating custom mnemonics, synonyms, and sentences..."):
                    engine_val = "Gemini" if engine == "Gemini (Cloud)" else "Ollama"
                    enrich = generate_mnemonic_and_enrichment(word_text, base_definition, gemini_api_key, engine_val)
                    if "error" in enrich:
                        st.error(enrich["error"])
                    else:
                        db.save_ai_enrichment(
                            word_text, 
                            enrich.get("mnemonic", ""),
                            enrich.get("sentence", ""),
                            enrich.get("synonyms", []),
                            enrich.get("antonyms", [])
                        )
                        st.success("Successfully enriched!")
                        st.rerun()

            st.markdown("---")
            st.markdown("### Do you know this word?")
            col_l1, col_l2 = st.columns(2)
            
            # Leitner Grading
            if col_l1.button("❌ No / Incorrect (Reset to Box 1)", use_container_width=True):
                db.update_word_progress(word_text, is_correct=False)
                st.session_state.card_flipped = False
                st.session_state.current_word_idx = (st.session_state.current_word_idx + 1) % len(candidate_words)
                st.rerun()
                
            if col_l2.button("✅ Yes / Correct (Promote Box)", use_container_width=True):
                db.update_word_progress(word_text, is_correct=True)
                st.session_state.card_flipped = False
                st.session_state.current_word_idx = (st.session_state.current_word_idx + 1) % len(candidate_words)
                st.rerun()
                
        # Navigation bar
        col_nav1, col_nav2 = st.columns(2)
        if col_nav1.button("⬅️ Previous Word", use_container_width=True):
            st.session_state.card_flipped = False
            st.session_state.current_word_idx = (st.session_state.current_word_idx - 1) % len(candidate_words)
            st.rerun()
        if col_nav2.button("➡️ Skip / Next Word", use_container_width=True):
            st.session_state.card_flipped = False
            st.session_state.current_word_idx = (st.session_state.current_word_idx + 1) % len(candidate_words)
            st.rerun()

# ----------------- TABS: Synonym Groupings -----------------
with tab_groups:
    st.markdown("### 📚 GRE Synonym & Semantic Clusters")
    
    # Check if database has AI-generated clusters
    ai_clusters = db.get_word_clusters()
    
    if not ai_clusters:
        st.warning("⚠️ No vocabulary groupings found in the database. Please run the static clustering generator to populate groupings.")
    else:
        # Load user reviewed progress to compute mastery per cluster
        reviewed_data = db.get_all_reviewed()
        
        # Sort and pre-compute mastery states for all clusters
        cluster_mastery = {}
        for c_name, data in ai_clusters.items():
            words = data.get("words", [])
            mastered_cnt = 0
            for w in words:
                p = reviewed_data.get(w)
                if p and p.get("box", 1) in [4, 5]:
                    mastered_cnt += 1
            mastery_pct = int(mastered_cnt / len(words) * 100) if words else 0
            cluster_mastery[c_name] = {
                "mastery_pct": mastery_pct,
                "mastered_cnt": mastered_cnt,
                "total_cnt": len(words)
            }
            
        # Add column layouts: Left side = Grid of categories, Right side = Detailed category viewer
        col_grid, col_detail = st.columns([3, 2])
        
        with col_grid:
            st.markdown("##### 📁 Select a Cluster to Study")
            
            # Alphabetical tabs/selectors to keep it extremely compact
            alphabet_tabs = ["A-C", "D-F", "G-I", "J-L", "M-O", "P-R", "S-U", "V-Z"]
            selected_alpha = st.radio("Alphabetical Filter", alphabet_tabs, horizontal=True)
            
            # Filter cluster list by selected alphabetical range
            alpha_ranges = {
                "A-C": re.compile(r"^[A-C]", re.I),
                "D-F": re.compile(r"^[D-F]", re.I),
                "G-I": re.compile(r"^[G-I]", re.I),
                "J-L": re.compile(r"^[J-L]", re.I),
                "M-O": re.compile(r"^[M-O]", re.I),
                "P-R": re.compile(r"^[P-R]", re.I),
                "S-U": re.compile(r"^[S-U]", re.I),
                "V-Z": re.compile(r"^[V-Z]", re.I),
            }
            
            active_regex = alpha_ranges[selected_alpha]
            filtered_clusters = [c for c in sorted(ai_clusters.keys()) if active_regex.match(c)]
            
            if not filtered_clusters:
                st.info("No categories match this alphabetical range.")
            else:
                # Render categories as a clickable grid (using multiple columns per row)
                cols = st.columns(2)
                for idx, c_name in enumerate(filtered_clusters):
                    col = cols[idx % 2]
                    mastery_info = cluster_mastery[c_name]
                    m_pct = mastery_info["mastery_pct"]
                    m_cnt = mastery_info["mastered_cnt"]
                    t_cnt = mastery_info["total_cnt"]
                    
                    # Highlight active card
                    is_active = st.session_state.get("selected_ai_cluster") == c_name
                    border_style = "border-color: rgba(99, 102, 241, 0.9); box-shadow: 0 0 10px rgba(99, 102, 241, 0.4);" if is_active else "border-color: rgba(255, 255, 255, 0.08);"
                    
                    # Renders a premium card card with inline details
                    card_html = f"""
                    <div style="background: rgba(17, 24, 39, 0.7); border: 1px solid; {border_style} border-radius: 12px; padding: 16px; margin-bottom: 12px;">
                        <h4 style="margin: 0; font-size: 1rem; color: #FFF; line-height: 1.2;">{c_name}</h4>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 8px; font-size: 0.8rem; color: #9CA3AF;">
                            <span>{t_cnt} words</span>
                            <span>{m_cnt}/{t_cnt} mastered ({m_pct}%)</span>
                        </div>
                        <div style="background: rgba(255, 255, 255, 0.05); border-radius: 4px; height: 6px; width: 100%; margin-top: 8px; overflow: hidden;">
                            <div style="background: linear-gradient(90deg, #6366F1, #10B981); width: {m_pct}%; height: 100%;"></div>
                        </div>
                    </div>
                    """
                    col.markdown(card_html, unsafe_allow_html=True)
                    
                    # Click button to select
                    if col.button("Study this Cluster", key=f"sel_{c_name}", use_container_width=True):
                        st.session_state.selected_ai_cluster = c_name
                        st.rerun()
                        
        # Detailed Viewer Column
        with col_detail:
            # Set default selection if none exists
            if "selected_ai_cluster" not in st.session_state or st.session_state.selected_ai_cluster not in ai_clusters:
                # Default to first available cluster in current alphabet range
                if filtered_clusters:
                    st.session_state.selected_ai_cluster = filtered_clusters[0]
                else:
                    st.session_state.selected_ai_cluster = sorted(ai_clusters.keys())[0]
                    
            active_c = st.session_state.selected_ai_cluster
            c_data = ai_clusters[active_c]
            words_in_cluster = c_data.get("words", [])
            desc = c_data.get("description", "Semantic grouping of related vocab.")
            
            st.markdown(f"##### 📖 Active Cluster Details")
            
            st.markdown(f"""
            <div class='glass-card' style='border-color: rgba(16, 185, 129, 0.4); padding: 20px; margin-top: 0;'>
                <h3 style='margin: 0; color: #10B981;'>📁 {active_c}</h3>
                <p style='color: #9CA3AF; font-style: italic; margin-top: 6px; font-size: 0.9rem;'>{desc}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Map word list to definitions
            matched_list = []
            for w in words_in_cluster:
                for base_item in base_words:
                    if base_item["word"].lower().strip() == w.lower().strip():
                        matched_list.append(base_item)
                        break
            
            if matched_list:
                st.write(f"**Words in Cluster ({len(matched_list)}):**")
                for item in sorted(matched_list, key=lambda x: x["word"]):
                    # Highlight if mastered
                    p = reviewed_data.get(item["word"])
                    mastery_badge = "✅" if p and p.get("box", 1) in [4, 5] else "🔹"
                    st.markdown(f"{mastery_badge} **{item['word']}** *({item.get('part_of_speech', 'noun')})* — {item['definition']}")
                    
                st.markdown("---")
                
                # Quiz option
                if st.button(f"🎯 Practice Quiz: {active_c}", use_container_width=True, type="primary"):
                    rand_word_item = random.choice(matched_list)
                    with st.spinner(f"Generating GRE question testing meaning of {rand_word_item['word']}..."):
                        engine_val = "Gemini" if engine == "Gemini (Cloud)" else "Ollama"
                        q_data = generate_verbal_question(
                            rand_word_item['word'], 
                            rand_word_item['definition'], 
                            gemini_api_key, 
                            engine_val, 
                            "SE"
                        )
                        if "error" in q_data:
                            st.error(q_data["error"])
                        else:
                            st.session_state.quiz_question = q_data
                            st.session_state.selected_choices = []
                            st.session_state.quiz_answered = False
                            st.session_state.quiz_target_word = rand_word_item['word']
                            st.success(f"Generated Sentence Equivalence question for **{rand_word_item['word']}**! Go to the **Practice Arena** tab below to solve it.")
# ----------------- TABS: Root Decoders -----------------
with tab_roots:
    st.markdown("### 🔑 Greek & Latin Root Decoders")
    st.write("Reinforce vocabulary structure by studying word families connected by historical roots. Master the roots to unlock unfamiliar words!")
    
    ROOTS_DICTIONARY = {
        "loqu / locut": {"meaning": "speak, talk", "examples": ["loquacious", "eloquent", "circumlocution", "colloquial"]},
        "pugn": {"meaning": "fight, fist", "examples": ["pugnacious", "repugnant"]},
        "anim": {"meaning": "mind, soul, spirit, life", "examples": ["magnanimous", "animosity", "pusillanimous", "equanimity", "animated"]},
        "mal": {"meaning": "bad, evil", "examples": ["malevolent", "malign", "malfeasance", "malady"]},
        "bene": {"meaning": "good, well", "examples": ["benevolent", "beneficent", "benediction", "beneficial"]},
        "ver": {"meaning": "truth", "examples": ["verity", "veracious", "aver", "veracity"]},
        "plac": {"meaning": "please, calm", "examples": ["placate", "implacable", "complacent", "complaisant"]},
        "luc / lum": {"meaning": "light, clear", "examples": ["elucidate", "lucid", "luminous", "luminary"]},
        "bell": {"meaning": "war", "examples": ["bellicose", "belligerent"]},
        "chron": {"meaning": "time", "examples": ["anachronism", "chronic", "chronology"]},
        "path": {"meaning": "feeling, suffering, disease", "examples": ["apathy", "antipathy", "sympathy", "empathy"]},
        "tort": {"meaning": "twist", "examples": ["contort", "distort", "tortuous", "extort"]},
        "greg": {"meaning": "flock, gather, herd", "examples": ["gregarious", "aggregate", "egregious"]},
        "cap / cip / cept": {"meaning": "take, hold, seize", "examples": ["captious", "cipient", "intercept", "recipient"]},
        "aud": {"meaning": "hear, listen", "examples": ["audacious", "audible", "auditory"]},
    }
    
    # 2-column layout: selector on left, list of matched words on right
    col_roots_l, col_roots_r = st.columns([1, 2])
    
    with col_roots_l:
        selected_root = st.selectbox("Select a Root to Decode:", list(ROOTS_DICTIONARY.keys()))
        root_data = ROOTS_DICTIONARY[selected_root]
        st.markdown(f"""
        <div class='glass-card' style='border-color: rgba(99, 102, 241, 0.5);'>
            <h3 style='margin: 0; color: #6366F1;'>Root: {selected_root}</h3>
            <p style='color: #E5E7EB; font-weight: bold;'>Meaning: "{root_data['meaning']}"</p>
            <p style='color: #9CA3AF; font-size: 0.9rem;'>Common Examples: {", ".join(root_data['examples'])}</p>
        </div>
        """, unsafe_allow_html=True)
        
    with col_roots_r:
        # Search base_words for occurrences containing the root
        sub_roots = [r.strip() for r in selected_root.split("/")]
        matched_root_words = []
        for w_item in base_words:
            word_lower = w_item["word"].lower()
            if any(sr in word_lower for sr in sub_roots):
                matched_root_words.append(w_item)
                
        st.markdown(f"##### Words in Your Database Matching '{selected_root}' ({len(matched_root_words)} found):")
        if not matched_root_words:
            st.info("No matching words in the current high-frequency list.")
        else:
            for item in sorted(matched_root_words, key=lambda x: x["word"]):
                # Highlight if mastered
                p = reviewed_data.get(item["word"])
                mastery_badge = "✅" if p and p.get("box", 1) in [4, 5] else "🔹"
                st.markdown(f"{mastery_badge} **{item['word']}** *({item.get('part_of_speech', 'noun')})* — {item['definition']}")

# ----------------- TABS: Confusables Locker -----------------
with tab_confusables:
    st.markdown("### 🔀 Confusables Locker")
    st.write("The GRE loves to trap students with words that look or sound almost identical but mean completely different things. Study these pairs and test your precision!")
    
    CONFUSABLE_PAIRS = [
        ("complacent", "complaisant", "Complacent means smug, self-satisfied, or unconcerned. Complaisant means eager to please, obliging, or polite."),
        ("venal", "venerable", "Venal means corruptible or open to bribery. Venerable means worthy of deep respect due to age, wisdom, or character."),
        ("chary", "wary", "Chary means cautious or hesitant to do something (often out of shyness or frugality). Wary means watchful and alert to danger."),
        ("prevaricate", "procrastinate", "Prevaricate means to speak evasively or avoid telling the truth. Procrastinate means to delay or postpone action."),
        ("disinterested", "uninterested", "Disinterested means impartial, unbiased, or neutral. Uninterested means bored, indifferent, or lacking interest."),
        ("officious", "official", "Officious means meddlesome, intrusive, or offering unwanted help. Official means authorized or formal."),
        ("capricious", "contentious", "Capricious means unpredictable, impulsive, or prone to sudden changes. Contentious means controversial or argumentative."),
        ("aesthetic", "ascetic", "Aesthetic concerns beauty or art appreciation. Ascetic refers to severe self-discipline and abstention from all forms of indulgence."),
        ("perfunctory", "peremptory", "Perfunctory means carried out with minimal effort or reflection. Peremptory means insisting on immediate attention or obedience, dictatorial.")
    ]
    
    conf_mode = st.radio("Locker Workspace", ["Study Pairs", "Accuracy Quiz"], horizontal=True, key="conf_mode_select")
    
    if conf_mode == "Study Pairs":
        st.markdown("##### 📁 Confusing Word Pairs Definition Deck")
        
        # Grid of confusing pairs
        cols = st.columns(3)
        for idx, (w1, w2, explanation) in enumerate(CONFUSABLE_PAIRS):
            col = cols[idx % 3]
            
            # Find definitions
            def1, def2 = "Not in database", "Not in database"
            for b in base_words:
                if b["word"].lower().strip() == w1:
                    def1 = b["definition"]
                if b["word"].lower().strip() == w2:
                    def2 = b["definition"]
                    
            col.markdown(f"""
            <div class='glass-card' style='border-color: rgba(239, 68, 68, 0.3); padding: 15px; margin-bottom: 15px; min-height: 250px;'>
                <h4 style='color: #EF4444; margin-top: 0;'>🥊 {w1.title()} vs {w2.title()}</h4>
                <p style='font-size: 0.85rem;'><b>{w1.title()}:</b> {def1}</p>
                <p style='font-size: 0.85rem;'><b>{w2.title()}:</b> {def2}</p>
                <hr style='border:0; border-top:1px solid rgba(255,255,255,0.05); margin: 10px 0;'/>
                <p style='color: #9CA3AF; font-size: 0.8rem; font-style: italic;'>{explanation}</p>
            </div>
            """, unsafe_allow_html=True)
            
    else:  # Accuracy Quiz
        st.markdown("##### 🎯 Accuracy Test: Distinguish the Confusables")
        st.write("Match the correct word to its definition to build bulletproof precision!")
        
        # Initialize quiz state
        if "conf_quiz_item" not in st.session_state:
            # Pick a random pair
            pair = random.choice(CONFUSABLE_PAIRS)
            # Pick a random word from the pair
            target_word = random.choice([pair[0], pair[1]])
            # Get true definition
            true_def = ""
            for b in base_words:
                if b["word"].lower().strip() == target_word:
                    true_def = b["definition"]
                    break
            if not true_def:
                true_def = "Definition not found in base list."
                
            st.session_state.conf_quiz_item = {
                "pair": pair,
                "target_word": target_word,
                "definition": true_def,
                "options": [pair[0], pair[1]],
                "answered": False,
                "correct": False
            }
            
        q = st.session_state.conf_quiz_item
        
        st.markdown(f"""
        <div class='glass-card' style='border-color: rgba(99, 102, 241, 0.4); padding: 20px;'>
            <h4>Identify the correct word matching this definition:</h4>
            <p style='font-size: 1.1rem; color: #FFF; font-style: italic;'>"{q['definition']}"</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Choice input
        choice = st.radio("Which word matches?", [w.title() for w in q["options"]], key="conf_choice_input")
        
        if st.button("Submit Answer", type="primary", key="conf_quiz_submit"):
            q["answered"] = True
            if choice.lower().strip() == q["target_word"].lower().strip():
                q["correct"] = True
            else:
                q["correct"] = False
                
        if q["answered"]:
            if q["correct"]:
                st.success(f"🎉 **Correct!** **{q['target_word'].title()}** matches the definition.")
                st.balloons()
            else:
                st.error(f"❌ **Incorrect.** The correct word is **{q['target_word'].title()}**.")
                st.info(f"💡 **Memory Aid:** {q['pair'][2]}")
                
            if st.button("Next Question", key="conf_quiz_next"):
                del st.session_state.conf_quiz_item
                st.rerun()
# ----------------- TABS: GRE Practice Arena -----------------
with tab_practice:
    st.markdown("### ⚔️ GRE Practice Arena")
    quiz_mode = st.radio("Select Practice Format", ["Synonym Matcher", "AI Verbal Question Generator"], horizontal=True)
    
    if quiz_mode == "Synonym Matcher":
        st.write("Match 5 random GRE words to their correct meanings!")
        
        # Pull 5 random words
        if "matcher_words" not in st.session_state:
            sample_w = random.sample(base_words, min(5, total_words))
            st.session_state.matcher_words = sample_w
            # Scramble definitions
            defs = [w['definition'] for w in sample_w]
            random.shuffle(defs)
            st.session_state.matcher_defs = defs
            st.session_state.matcher_selections = {}
            st.session_state.matcher_checked = False
            
        # Select matching
        for i, w in enumerate(st.session_state.matcher_words):
            word_str = w['word']
            st.session_state.matcher_selections[word_str] = st.selectbox(
                f"Word: {word_str}", 
                ["-- Choose Definition --"] + st.session_state.matcher_defs,
                key=f"match_{word_str}"
            )
            
        if st.button("Check Matching Answers", type="primary"):
            st.session_state.matcher_checked = True
            
        if st.session_state.matcher_checked:
            correct_count = 0
            for w in st.session_state.matcher_words:
                word_str = w['word']
                true_def = w['definition']
                user_def = st.session_state.matcher_selections[word_str]
                if user_def == true_def:
                    correct_count += 1
                    st.success(f"✅ **{word_str}**: Correctly matched!")
                else:
                    st.error(f"❌ **{word_str}**: Mismatched. Correct definition is: *{true_def}*")
            
            st.markdown(f"**Overall Score:** {correct_count}/5")
            db.log_quiz_attempt("Synonym Matcher", correct_count, 5)
            
            if st.button("Load New Matcher Game"):
                del st.session_state.matcher_words
                st.session_state.matcher_checked = False
                st.rerun()
                
    else:  # AI Verbal Question Generator
        st.write("Generate a dynamic Sentence Equivalence (SE) or Text Completion (TC) question for a random word!")
        q_type_choice = st.selectbox("Question Type", ["Sentence Equivalence (SE) - Select 2 choices", "Text Completion (TC) - Select 1 choice"])
        
        col_gen1, col_gen2 = st.columns([1, 4])
        if col_gen1.button("Generate New AI Question", type="primary"):
            # Pick a random word
            rand_w = random.choice(base_words)
            with st.spinner(f"Generating GRE question testing meaning of {rand_w['word']}..."):
                engine_val = "Gemini" if engine == "Gemini (Cloud)" else "Ollama"
                q_type = "SE" if "Sentence Equivalence" in q_type_choice else "TC"
                q_data = generate_verbal_question(rand_w['word'], rand_w['definition'], gemini_api_key, engine_val, q_type)
                
                if "error" in q_data:
                    st.error(q_data["error"])
                    st.session_state.quiz_question = None
                else:
                    st.session_state.quiz_question = q_data
                    st.session_state.selected_choices = []
                    st.session_state.quiz_answered = False
                    st.session_state.quiz_target_word = rand_w['word']
                    
        # Render active quiz question
        if st.session_state.quiz_question:
            q = st.session_state.quiz_question
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.markdown(f"**GRE {q.get('type', 'SE')} Question:**")
            st.markdown(f"### {q.get('sentence', '')}")
            
            # Select boxes
            if q.get('type') == 'SE':
                st.write("Choose exactly **two** choices:")
                user_ans = []
                for choice in q.get('choices', []):
                    letter = choice[0]
                    if st.checkbox(choice, key=f"choice_{letter}"):
                        user_ans.append(letter)
                st.session_state.selected_choices = user_ans
            else:  # TC
                user_ans = st.radio("Choose the correct choice:", q.get('choices', []))
                if user_ans:
                    st.session_state.selected_choices = [user_ans[0]]
                    
            if not st.session_state.quiz_answered:
                if st.button("Submit Answer"):
                    st.session_state.quiz_answered = True
                    st.rerun()
            else:
                correct_ans = q.get('correct_answers', [])
                user_ans = st.session_state.selected_choices
                
                is_correct = sorted(user_ans) == sorted(correct_ans)
                
                if is_correct:
                    st.success("🎉 **Correct!** Excellent verbal reasoning logic.")
                    db.log_quiz_attempt(f"AI GRE {q.get('type')}", 1, 1)
                    # Update word progress as correct
                    db.update_word_progress(st.session_state.quiz_target_word, is_correct=True)
                else:
                    st.error(f"❌ **Incorrect.** The correct answer was **{', '.join(correct_ans)}**.")
                    db.log_quiz_attempt(f"AI GRE {q.get('type')}", 0, 1)
                    # Update word progress as incorrect
                    db.update_word_progress(st.session_state.quiz_target_word, is_correct=False)
                    
                st.write(f"**Explanation:** {q.get('explanation', '')}")
            st.markdown("</div>", unsafe_allow_html=True)

# ----------------- TABS: Progress Analytics -----------------
with tab_analytics:
    st.markdown("### 📊 Progress Analytics")
    
    # 1. Plotly gauge chart
    active_total = sum(counts.values())
    mastered = counts[4] + counts[5]
    
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = mastered,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Words Mastered (Box 4/5)"},
        gauge = {
            'axis': {'range': [None, max(10, total_words)]},
            'bar': {'color': "#10B981"},
            'steps': [
                {'range': [0, total_words * 0.3], 'color': "#374151"},
                {'range': [total_words * 0.3, total_words * 0.7], 'color': "#1E293B"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': total_words * 0.8
            }
        }
    ))
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': "#FFF"}
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # 2. History of quiz attempts
    st.subheader("📝 Quiz History Logs")
    history = db.get_quiz_stats()
    if history:
        df = pd.DataFrame(history)
        df['percentage'] = (df['score'] / df['total_questions'] * 100).round(1)
        st.dataframe(
            df[['timestamp', 'quiz_type', 'score', 'total_questions', 'percentage']],
            use_container_width=True
        )
    else:
        st.info("No quizzes attempted yet. Head over to the **Practice Arena** to begin testing yourself!")
        
    # 3. Starred Words list
    st.subheader("⭐ Starred Vocabulary Locker")
    starred_list = db.get_all_starred()
    if starred_list:
        star_df = pd.DataFrame(starred_list)
        st.dataframe(
            star_df[['word', 'box', 'mnemonic', 'sentence', 'synonyms']],
            use_container_width=True
        )
    else:
        st.info("No starred words yet. Click the **☆ Star Word** button inside cards to save difficult words here.")
