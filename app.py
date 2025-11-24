import streamlit as st
import pandas as pd
import os
import random
import time
from groq import Groq, RateLimitError, APIConnectionError
from datetime import datetime
from io import StringIO

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Agence Pro'AGOrA", 
    page_icon="🏢",
    initial_sidebar_state="expanded"
)

# --- 2. DIAGNOSTIC SECRET (POUR VOUS AIDER) ---
# Ce bloc vérifie si votre fichier secrets.toml est bien lu
if "groq_keys" in st.secrets:
    nb_keys = len(st.secrets["groq_keys"])
    st.success(f"✅ DIAGNOSTIC SUCCÈS : J'ai trouvé {nb_keys} clés dans la liste 'groq_keys'. Rotation active !")
elif "GROQ_API_KEY" in st.secrets:
    st.info("ℹ️ DIAGNOSTIC : Je ne trouve qu'une seule clé (GROQ_API_KEY). Créez une liste 'groq_keys' pour plus de stabilité.")
else:
    st.error("❌ DIAGNOSTIC ERREUR : Je ne trouve aucune clé ! Vérifiez votre fichier secrets.toml. La variable doit s'appeler 'groq_keys'.")

# --- 3. CSS (STYLE) ---
hide_css = """
<style>
footer {visibility: hidden;}
header {visibility: visible !important;}
</style>
"""
st.markdown(hide_css, unsafe_allow_html=True)

# --- 4. GESTION INTELLIGENTE DES CLÉS (KEY ROTATION) ---

def get_api_keys_list():
    """
    Récupère la liste des clés disponibles.
    Ordre de priorité :
    1. Clé manuelle entrée dans la barre latérale (Urgence)
    2. Liste 'groq_keys' dans les secrets (Recommandé)
    3. Clé unique 'GROQ_API_KEY' (Ancienne méthode)
    """
    # 1. Clé de secours manuelle
    if "manual_api_key" in st.session_state and st.session_state.manual_api_key:
        return [st.session_state.manual_api_key]

    # 2. Liste de clés (Rotation)
    if "groq_keys" in st.secrets:
        return st.secrets["groq_keys"]
    
    # 3. Clé unique (Fallback)
    single_key = os.environ.get("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY")
    if single_key:
        return [single_key]
    
    return []

def query_groq_with_rotation(messages):
    """
    Essaie d'appeler l'API. Si une clé échoue (429), elle en tente une autre
    automatiquement jusqu'à épuisement du stock.
    """
    available_keys = get_api_keys_list()
    
    if not available_keys:
        return None, "Aucune clé trouvée"
    
    # Mélanger les clés pour répartir la charge
    # (On fait une copie pour ne pas modifier l'ordre original à chaque fois)
    keys_to_try = list(available_keys)
    random.shuffle(keys_to_try)
    
    # Modèles à tester par ordre de rapidité/qualité
    models = ["llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it"]

    # On boucle sur CHAQUE clé disponible
    for key in keys_to_try:
        client = Groq(api_key=key)
        
        # On essaie les modèles sur cette clé
        for model in models:
            try:
                chat = client.chat.completions.create(
                    messages=messages,
                    model=model,
                    temperature=0.6,
                    max_tokens=600,
                )
                # SUCCÈS ! On retourne la réponse
                # On cache la clé sauf les 4 derniers caractères pour le debug
                key_suffix = key[-4:] if len(key) > 4 else "???"
                return chat.choices[0].message.content, f"{model} (Clé ...{key_suffix})"
            
            except RateLimitError:
                # Cette clé est saturée, on passe à la suivante
                continue 
            except Exception:
                # Autre erreur, on passe à la suivante
                continue
    
    # Si on arrive ici, c'est que TOUTES les clés ont échoué
    return None, "All_Keys_Failed"

# --- 5. GESTION DES LOGS ---
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
    st.success("Session rechargée avec succès.")

# --- 6. PROMPTS ET CONTENU ---
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
    """Mode Simulation (Dernier recours si tout est cassé)"""
    msg = last_user_msg.lower()
    if "1" in msg or "client" in msg:
        return "Noté Bloc 1. Quel est le contexte (Lieu, Interlocuteur) ?"
    elif "2" in msg or "prod" in msg:
        return "Noté Bloc 2. Quelle tâche as-tu réalisée ?"
    elif "3" in msg or "perso" in msg:
        return "Noté Bloc 3. Recrutement, paie ou gestion ?"
    else:
        return random.choice([
            "Quels outils numériques as-tu utilisés ?",
            "Pourquoi as-tu choisi cette méthode ?",
            "Quelles difficultés as-tu rencontrées ?",
            "Si tu devais refaire cette tâche, que changerais-tu ?"
        ]) + " (Mode Simulation 🤖 - IA Saturée)"

# --- 7. INTERFACE ---
st.title("🏢 Agence Pro'AGOrA - Superviseur")

if not st.session_state.messages:
    st.session_state.messages.append({"role": "assistant", "content": MENU_AGORA})

with st.sidebar:
    st.header("👤 Élève")
    student_id = st.text_input("Ton Prénom :", placeholder="Ex: Alex")
    
    # Indicateur du nombre de clés trouvées (Discret)
    keys_count = len(get_api_keys_list())
    if keys_count > 0:
        st.caption(f"🔑 Système actif : {keys_count} clés disponibles.")
    else:
        st.error("🔑 Aucune clé API détectée !")
    
    st.divider()
    
    st.header("🔧 Professeur / Dépannage")
    with st.expander("🆘 Clé API de Secours (Si erreur 429)"):
        st.caption("Si le bandeau rouge s'affiche ou que l'IA est saturée, collez une clé temporaire ici :")
        manual_key = st.text_input("Clé Groq temporaire :", type="password")
        if manual_key:
            st.session_state.manual_api_key = manual_key
            st.success("Clé de secours activée ! Elle sera utilisée en priorité.")
    
    st.divider()
    
    # Upload
    uploaded_file = st.file_uploader("📂 Charger une session (CSV)", type=['csv'])
    if uploaded_file:
        try:
            string_data = StringIO(uploaded_file.getvalue().decode('utf-8-sig')).read()
            load_session_from_df(pd.read_csv(StringIO(string_data), sep=';'))
        except: st.error("Erreur lecture CSV")

    # Download
    if st.session_state.conversation_log:
        df = pd.DataFrame(st.session_state.conversation_log)
        st.download_button("💾 Sauvegarder la session", df.to_csv(index=False, sep=';').encode('utf-8-sig'), f"session_{student_id}.csv", "text/csv")
    
    if st.button("🗑️ Reset / Nouvelle Session"):
        st.session_state.messages = [{"role": "assistant", "content": MENU_AGORA}]
        st.session_state.conversation_log = []
        if "manual_api_key" in st.session_state:
            del st.session_state.manual_api_key
        st.rerun()

# --- 8. LOGIQUE CHAT ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if prompt := st.chat_input("Ta réponse..."):
    if not student_id:
        st.toast("⚠️ N'oublie pas de mettre ton prénom à gauche !")
    else:
        # Message Utilisateur
        st.chat_message("user").write(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        save_log(student_id, "Eleve", prompt)

        # Préparation du contexte (8 derniers messages seulement)
        messages_api = [{"role": "system", "content": SYSTEM_PROMPT}]
        recent_history = st.session_state.messages[-8:] 
        for m in recent_history:
            messages_api.append({"role": m["role"], "content": m["content"]})

        # Réponse Assistant
        with st.chat_message("assistant"):
            with st.spinner("Le superviseur analyse ta réponse..."):
                
                # Appel API avec rotation automatique
                reply, info_debug = query_groq_with_rotation(messages_api)
                
                if reply:
                    st.write(reply)
                    # Debug discret pour savoir quelle clé a travaillé
                    # st.caption(f"⚡ {info_debug}") 
                else:
                    # Mode Secours si tout a échoué
                    reply = get_fallback_response(prompt)
                    st.write(reply)
                    st.warning("⚠️ Toutes les clés API sont saturées. Passage en mode simulation.")
            
            st.session_state.messages.append({"role": "assistant", "content": reply})
            save_log(student_id, "Assistant", reply)
