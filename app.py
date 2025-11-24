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

# --- 2. CSS POUR L'INTERFACE ---
hide_css = """
<style>
footer {visibility: hidden;}
header {visibility: visible !important;}
</style>
"""
st.markdown(hide_css, unsafe_allow_html=True)

# --- 3. GROQ CLIENT INITIALISATION ---
try:
    api_key = os.environ.get("GROQ_API_KEY") or st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=api_key)
except Exception as e:
    st.error("Clé API Groq manquante. Vérifiez vos secrets.")
    st.stop()

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

# --- 5. INTELLIGENCE ARTIFICIELLE & MODE SECOURS ---

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
    """Génère une réponse sans IA (Mode Dégradé)"""
    msg = last_user_msg.lower()
    if "1" in msg or "client" in msg:
        return "Noté pour le Bloc 1 (GRCU). Quel est le contexte de l'accueil ou de l'échange client (Lieu, Type d'interlocuteur) ?"
    elif "2" in msg or "prod" in msg:
        return "C'est parti pour le Bloc 2 (OSP). Quelle tâche de production ou d'organisation as-tu réalisée ?"
    elif "3" in msg or "perso" in msg:
        return "D'accord pour le Bloc 3 (Admin Personnel). S'agit-il d'un recrutement, d'une paie ou d'une gestion de dossier ?"
    elif len(msg) < 5:
        return "Peux-tu être plus précis ? Décris ta démarche avec des phrases complètes."
    else:
        responses = [
            "Très bien. Quels outils numériques as-tu utilisés pour réaliser cette tâche ?",
            "Peux-tu m'expliquer pourquoi tu as choisi cette méthode plutôt qu'une autre ?",
            "Quelles difficultés as-tu rencontrées et comment les as-tu surmontées ?",
            "C'est clair. Si tu devais refaire cette tâche, que changerais-tu pour être plus efficace ?",
            "Parfait. Vérifie bien l'orthographe et la syntaxe pour ton rapport final."
        ]
        return random.choice(responses) + " (Réponse générée en mode secours 🛠️)"

def query_groq_with_fallback(messages):
    """Tente plusieurs modèles, sinon passe en mode secours."""
    # Liste des modèles par ordre de préférence (du plus léger au plus performant)
    models_to_try = [
        "llama-3.1-8b-instant",  # Rapide & Pas cher
        "mixtral-8x7b-32768",    # Alternative fiable
        "gemma2-9b-it"           # Google via Groq
    ]
    
    for model in models_to_try:
        try:
            chat_completion = client.chat.completions.create(
                messages=messages,
                model=model,
                temperature=0.6,
                max_tokens=600,
            )
            return chat_completion.choices[0].message.content, model
        except RateLimitError:
            continue # Passe au modèle suivant
        except Exception as e:
            continue # Passe au modèle suivant
            
    # Si tout échoue, on retourne None pour déclencher le mode secours
    return None, "None"

# --- 6. INTERFACE ---
st.title("🏢 Agence Pro'AGOrA - Superviseur")

if not st.session_state.messages:
    st.session_state.messages.append({"role": "assistant", "content": MENU_AGORA})

with st.sidebar:
    st.header("Paramètres")
    student_id = st.text_input("Ton Prénom :", placeholder="Ex: Alex")
    st.warning("⚠️ Règle d'Or : Données fictives uniquement.")
    
    st.divider()
    
    # Upload
    uploaded_file = st.file_uploader("📂 Charger session (CSV)", type=['csv'])
    if uploaded_file:
        try:
            string_data = StringIO(uploaded_file.getvalue().decode('utf-8-sig')).read()
            load_session_from_df(pd.read_csv(StringIO(string_data), sep=';'))
        except: st.error("Erreur lecture CSV")

    # Download
    if st.session_state.conversation_log:
        df = pd.DataFrame(st.session_state.conversation_log)
        st.download_button(
            "💾 Sauvegarder", 
            df.to_csv(index=False, sep=';').encode('utf-8-sig'), 
            f"session_{student_id}.csv", "text/csv"
        )
    
    if st.button("🗑️ Reset"):
        st.session_state.messages = [{"role": "assistant", "content": MENU_AGORA}]
        st.session_state.conversation_log = []
        st.rerun()

# --- 7. CHAT LOGIC ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if prompt := st.chat_input("Ta réponse..."):
    if not student_id:
        st.toast("⚠️ Entre ton prénom à gauche !")
    else:
        # User message
        st.chat_message("user").write(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        save_log(student_id, "Eleve", prompt)

        # Prepare context (Last 8 messages only)
        messages_api = [{"role": "system", "content": SYSTEM_PROMPT}]
        recent_history = st.session_state.messages[-8:] 
        for m in recent_history:
            messages_api.append({"role": m["role"], "content": m["content"]})

        # AI Response logic
        with st.chat_message("assistant"):
            with st.spinner("Analyse en cours..."):
                reply, model_used = query_groq_with_fallback(messages_api)
                
                if reply:
                    st.write(reply)
                    # Petit indicateur discret du modèle utilisé (utile pour debug)
                    st.caption(f"🤖 Superviseur connecté via {model_used}")
                else:
                    # Mode Secours
                    reply = get_fallback_response(prompt)
                    st.write(reply)
                    st.warning("⚠️ Réseau IA saturé (Erreur 429). Passage en mode 'Secours' automatique.")
            
            st.session_state.messages.append({"role": "assistant", "content": reply})
            save_log(student_id, "Assistant", reply)
