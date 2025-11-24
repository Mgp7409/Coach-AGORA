import streamlit as st
import pandas as pd
import os
import random
from groq import Groq, RateLimitError, APIConnectionError
from datetime import datetime
from io import StringIO

# --- 1. CONFIGURATION ---
st.set_page_config(
    page_title="Agence Pro'AGOrA", 
    page_icon="🏢",
    initial_sidebar_state="expanded"
)

# --- 2. CSS ---
hide_css = """
<style>
footer {visibility: hidden;}
header {visibility: visible !important;}
</style>
"""
st.markdown(hide_css, unsafe_allow_html=True)

# --- 3. FONCTIONS UTILITAIRES ---

def get_api_key():
    """
    Récupère la clé API.
    Priorité 1 : Clé entrée manuellement dans la sidebar (Secours)
    Priorité 2 : Clé dans les secrets (Production)
    Priorité 3 : Clé dans l'environnement (Local)
    """
    # 1. Vérifier si une clé de secours est entrée dans la session
    if "manual_api_key" in st.session_state and st.session_state.manual_api_key:
        return st.session_state.manual_api_key
    
    # 2. Sinon, chercher dans les secrets ou l'env
    try:
        return os.environ.get("GROQ_API_KEY") or st.secrets["GROQ_API_KEY"]
    except:
        return None

def init_groq_client(api_key):
    try:
        if not api_key: return None
        return Groq(api_key=api_key)
    except:
        return None

# --- 4. GESTION DES LOGS ---
if "conversation_log" not in st.session_state:
    st.session_state.conversation_log = []

if "messages" not in st.session_state:
    st.session_state.messages = []

def save_log(student_id, role, content):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.conversation_log.append({
        "Heure": timestamp,
        "Eleve": student_id,
        "Role": role,
        "Message": content
    })

def load_session_from_df(df):
    st.session_state.conversation_log = df.to_dict('records')
    st.session_state.messages = []
    for row in df.itertuples():
        st.session_state.messages.append({
            "role": "assistant" if row.Role == "Assistant" else "user",
            "content": row.Message
        })
    st.success("Session chargée.")

# --- 5. LOGIQUE INTELLIGENCE ARTIFICIELLE ---

SYSTEM_PROMPT = """
Tu es le Superviseur Virtuel Pro'AGOrA (Bac Pro).
Ton but : faire réfléchir l'élève sans faire le travail à sa place.
Règles : 
1. Une seule question à la fois.
2. Ton professionnel et encourageant.
3. Si l'élève donne une info perso, rappel à l'ordre (Données fictives uniquement).
4. Structure : Accueil -> Activité/Lieu -> Outils/Étapes -> Analyse -> Bilan.
"""

MENU_AGORA = """
**Bonjour Opérateur. Bienvenue à l'Agence Pro'AGOrA.**

Superviseur Virtuel pour Opérateurs Juniors (Bac Pro). **Rappel de sécurité :** Utilise uniquement des données fictives.

**Sur quel BLOC DE COMPÉTENCES souhaites-tu travailler ?**

1. Gérer des relations avec les clients (GRCU).
2. Organiser et suivre l’activité de production (OSP).
3. Administrer le personnel (AP).

**Indique 1, 2 ou 3 pour commencer.**
"""

def get_fallback_response(last_user_msg):
    """Génère une réponse sans IA (Mode Simulation)"""
    msg = last_user_msg.lower()
    if "1" in msg or "client" in msg:
        return "Noté pour le Bloc 1 (GRCU). Quel est le contexte (Lieu, Interlocuteur) ?"
    elif "2" in msg or "prod" in msg:
        return "C'est parti pour le Bloc 2 (OSP). Quelle tâche as-tu réalisée ?"
    elif "3" in msg or "perso" in msg:
        return "D'accord pour le Bloc 3 (Admin Personnel). Recrutement, paie ou gestion ?"
    else:
        responses = [
            "Quels outils numériques as-tu utilisés ?",
            "Pourquoi as-tu choisi cette méthode ?",
            "Quelles difficultés as-tu rencontrées ?",
            "Si tu devais refaire cette tâche, que changerais-tu ?"
        ]
        return random.choice(responses) + " (Mode Simulation 🛠️)"

def query_groq_optimized(messages, api_key):
    """Essaie d'interroger l'API avec rotation de modèles."""
    if not api_key:
        return None, "Pas de clé"

    client = Groq(api_key=api_key)
    
    # Ordre : Modèle rapide -> Modèle performant -> Modèle Google
    models = ["llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it"]
    
    for model in models:
        try:
            chat = client.chat.completions.create(
                messages=messages,
                model=model,
                temperature=0.6,
                max_tokens=600,
            )
            return chat.choices[0].message.content, model
        except RateLimitError:
            continue # Essayer le suivant
        except APIConnectionError:
            continue
        except Exception:
            continue
            
    return None, "Erreur 429"

# --- 6. INTERFACE ---
st.title("🏢 Agence Pro'AGOrA - Superviseur")

if not st.session_state.messages:
    st.session_state.messages.append({"role": "assistant", "content": MENU_AGORA})

with st.sidebar:
    st.header("👤 Élève")
    student_id = st.text_input("Ton Prénom :", placeholder="Ex: Alex")
    
    st.divider()
    
    st.header("🔧 Professeur / Dépannage")
    with st.expander("🆘 Clé API de Secours (Si erreur 429)"):
        st.caption("Si l'IA est saturée, collez une nouvelle clé Groq ici pour reprendre immédiatement.")
        manual_key = st.text_input("Clé Groq temporaire :", type="password")
        if manual_key:
            st.session_state.manual_api_key = manual_key
            st.success("Clé temporaire active !")
            
    st.divider()
    
    # Upload/Download (Code identique avant)
    uploaded_file = st.file_uploader("📂 Charger CSV", type=['csv'])
    if uploaded_file:
        try:
            string_data = StringIO(uploaded_file.getvalue().decode('utf-8-sig')).read()
            load_session_from_df(pd.read_csv(StringIO(string_data), sep=';'))
        except: st.error("Erreur lecture CSV")

    if st.session_state.conversation_log:
        df = pd.DataFrame(st.session_state.conversation_log)
        st.download_button("💾 Sauvegarder", df.to_csv(index=False, sep=';').encode('utf-8-sig'), f"session_{student_id}.csv", "text/csv")
    
    if st.button("🗑️ Reset"):
        st.session_state.messages = [{"role": "assistant", "content": MENU_AGORA}]
        st.session_state.conversation_log = []
        st.rerun()

# --- 7. CHAT LOGIC ---
current_api_key = get_api_key()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if prompt := st.chat_input("Ta réponse..."):
    if not student_id:
        st.toast("⚠️ Identifie-toi à gauche !")
    else:
        st.chat_message("user").write(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        save_log(student_id, "Eleve", prompt)

        # Contexte limité (8 derniers messages)
        messages_api = [{"role": "system", "content": SYSTEM_PROMPT}]
        recent_history = st.session_state.messages[-8:] 
        for m in recent_history:
            messages_api.append({"role": m["role"], "content": m["content"]})

        with st.chat_message("assistant"):
            with st.spinner("Analyse..."):
                reply, model_used = query_groq_optimized(messages_api, current_api_key)
                
                if reply:
                    st.write(reply)
                    if model_used != "None":
                        st.caption(f"⚡ Connecté ({model_used})")
                else:
                    # Mode Simulation
                    reply = get_fallback_response(prompt)
                    st.write(reply)
                    st.warning("⚠️ Mode Simulation (Réseau saturé). Pour réparer : Professeur > Clé de Secours.")
            
            st.session_state.messages.append({"role": "assistant", "content": reply})
            save_log(student_id, "Assistant", reply)
