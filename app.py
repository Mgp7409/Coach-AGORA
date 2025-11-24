import streamlit as st
import pandas as pd
import os
import random
import time
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

# --- 3. GESTION DES CLÉS (Invisible pour l'élève) ---

def get_api_keys_list():
    """Récupère les clés depuis les secrets uniquement."""
    if "groq_keys" in st.secrets:
        return st.secrets["groq_keys"]
    # Fallback ancienne méthode (une seule clé)
    single_key = os.environ.get("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY")
    if single_key:
        return [single_key]
    return []

def query_groq_with_rotation(messages):
    """Rotation automatique des clés en cas d'erreur."""
    available_keys = get_api_keys_list()
    
    if not available_keys:
        return None, "Aucune clé configurée"
    
    keys_to_try = list(available_keys)
    random.shuffle(keys_to_try)
    
    models = ["llama-3.1-8b-instant", "mixtral-8x7b-32768"]

    for key in keys_to_try:
        client = Groq(api_key=key)
        for model in models:
            try:
                chat = client.chat.completions.create(
                    messages=messages,
                    model=model,
                    temperature=0.7, # Un peu plus créatif pour s'adapter à l'élève
                    max_tokens=600,
                )
                return chat.choices[0].message.content, model
            except:
                continue # On passe à la clé suivante sans rien dire
    
    return None, "Erreur Totale"

# --- 4. DATA ---
if "conversation_log" not in st.session_state:
    st.session_state.conversation_log = []

if "messages" not in st.session_state:
    st.session_state.messages = []

def save_log(student_id, role, content):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.conversation_log.append({
        "Heure": timestamp, "Eleve": student_id, "Role": role, "Message": content
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

# --- 5. CERVEAU DU SUPERVISEUR ---

SYSTEM_PROMPT = """
Tu es le Superviseur Virtuel de l'Agence Pro'AGOrA.
Ton rôle est d'aider l'élève à ANALYSER l'activité qu'il vient de réaliser.

RÈGLES STRICTES :
1. NE JAMAIS PROPOSER DE SCÉNARIO FICTIF. C'est l'élève qui doit raconter SON travail.
2. Demande toujours : "Quelle tâche as-tu réalisée ?" ou "Explique-moi ce que tu as fait".
3. Une seule question à la fois.
4. Si l'élève est vague, demande des précisions sur les outils, les logiciels ou les étapes.
5. Rappelle toujours la "Règle d'Or" (Données fictives) si l'élève semble donner un vrai nom.

Déroulement type :
1. Demander le Bloc (1, 2 ou 3).
2. Demander de DÉCRIRE l'activité réalisée.
3. Questionner sur les OUTILS / LOGICIELS utilisés.
4. Questionner sur les DIFFICULTÉS ou la MÉTHODE.
5. Faire une courte synthèse positive.
"""

MENU_AGORA = """
**Bonjour Opérateur.** Je suis ton Superviseur.

Nous allons analyser le travail que tu as réalisé aujourd'hui.
**Rappel :** Utilise des données fictives (ne donne pas les vrais noms des clients).

**Dans quel BLOC s'inscrit ton activité ?**

1. Relation Clients / Usagers (GRCU)
2. Organisation / Production (OSP)
3. Administration du Personnel (AP)

**Tape 1, 2 ou 3 pour commencer.**
"""

def get_fallback_response(last_user_msg):
    """
    Mode Secours (Si l'IA est HS).
    Ne propose plus de choix, mais pose des questions ouvertes.
    """
    msg = last_user_msg.lower()
    
    # Si l'élève vient de choisir un bloc (1, 2 ou 3)
    if msg in ["1", "bloc 1", "grcu"]:
        return "C'est noté pour le Bloc 1 (Relation Client). **Quelle activité précise as-tu réalisée ?** Décris-moi la situation (Accueil, Téléphone, Courrier...)."
    elif msg in ["2", "bloc 2", "osp"]:
        return "C'est noté pour le Bloc 2 (Organisation). **Sur quelle tâche as-tu travaillé ?** (Classement, Planification, Gestion de stock...)."
    elif msg in ["3", "bloc 3", "ap"]:
        return "C'est noté pour le Bloc 3 (Personnel). **Quelle opération as-tu effectuée ?** (Congés, Recrutement, Paie...)."
    
    # Si la réponse est courte, on demande de développer
    elif len(msg) < 10:
        return "Peux-tu être plus précis ? Explique-moi les étapes de ton travail."
    
    # Questions génériques de relance
    else:
        return random.choice([
            "Très bien. Quels logiciels ou outils numériques as-tu utilisés pour faire cela ?",
            "As-tu rencontré des difficultés particulières durant cette tâche ?",
            "Pourquoi as-tu choisi de procéder ainsi ? Justifie ta méthode.",
            "Si tu devais refaire cette activité, que changerais-tu pour être plus efficace ?"
        ]) + " (Mode Relance 🛠️)"

# --- 6. INTERFACE ---
st.title("🏢 Agence Pro'AGOrA")

# Diagnostic silencieux (Bandeau vert uniquement si succès)
if "groq_keys" in st.secrets:
    if len(st.secrets["groq_keys"]) > 0:
        st.success(f"✅ Système connecté ({len(st.secrets['groq_keys'])} clés actives)", icon="🟢")
    else:
        st.error("⚠️ Liste de clés vide dans les secrets.", icon="🔴")
elif "GROQ_API_KEY" not in st.secrets:
    st.error("⚠️ Aucune clé API configurée.", icon="🔴")

if not st.session_state.messages:
    st.session_state.messages.append({"role": "assistant", "content": MENU_AGORA})

with st.sidebar:
    st.header("👤 Élève")
    student_id = st.text_input("Ton Prénom :", placeholder="Ex: Alex")
    
    st.markdown("---")
    
    uploaded_file = st.file_uploader("📂 Reprendre une session (CSV)", type=['csv'])
    if uploaded_file:
        try:
            string_data = StringIO(uploaded_file.getvalue().decode('utf-8-sig')).read()
            load_session_from_df(pd.read_csv(StringIO(string_data), sep=';'))
        except: st.error("Fichier invalide")

    if st.session_state.conversation_log:
        df = pd.DataFrame(st.session_state.conversation_log)
        st.download_button("💾 Sauvegarder mon travail", df.to_csv(index=False, sep=';').encode('utf-8-sig'), f"agora_{student_id}.csv", "text/csv")
    
    st.markdown("---")
    if st.button("🗑️ Nouvelle Session"):
        st.session_state.messages = [{"role": "assistant", "content": MENU_AGORA}]
        st.session_state.conversation_log = []
        st.rerun()

# --- 7. CHAT ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if prompt := st.chat_input("Décris ton activité ici..."):
    if not student_id:
        st.toast("⚠️ Entre ton prénom à gauche pour commencer !")
    else:
        # Message Elève
        st.chat_message("user").write(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        save_log(student_id, "Eleve", prompt)

        # Context (8 derniers messages)
        messages_api = [{"role": "system", "content": SYSTEM_PROMPT}]
        recent_history = st.session_state.messages[-8:] 
        for m in recent_history:
            messages_api.append({"role": m["role"], "content": m["content"]})

        # Réponse Assistant
        with st.chat_message("assistant"):
            with st.spinner("Analyse de l'activité..."):
                reply, debug_info = query_groq_with_rotation(messages_api)
                
                if not reply:
                    # Si l'IA échoue, on utilise le fallback "ouvert" (sans menu)
                    reply = get_fallback_response(prompt)
                
                st.write(reply)
            
            st.session_state.messages.append({"role": "assistant", "content": reply})
            save_log(student_id, "Assistant", reply)
