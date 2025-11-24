import streamlit as st
import pandas as pd
import os
import random
from groq import Groq
from datetime import datetime
from io import StringIO

# --- 0. SÉCURITÉ & DÉPENDANCES ---
# Assurez-vous d'avoir un fichier requirements.txt contenant :
# streamlit
# pandas
# groq
# python-docx

try:
    from docx import Document
except ImportError:
    st.error("⚠️ ERREUR CRITIQUE : Le module 'python-docx' manque. Ajoutez-le au fichier requirements.txt")
    st.stop()

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Superviseur Pro'AGOrA", 
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. STYLE CSS & BANNIÈRE SÉCURITÉ ---
# On cache le footer Streamlit par défaut et on ajoute du style pour les alertes
st.markdown("""
<style>
    footer {visibility: hidden;}
    .reportview-container .main .block-container {padding-top: 2rem;}
    .alert-box {
        padding: 1rem;
        background-color: #fff3cd;
        border: 1px solid #ffeeba;
        color: #856404;
        border-radius: 5px;
        margin-bottom: 1rem;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. GESTION DES CLÉS API (ROTATION SÉCURISÉE) ---
def get_api_keys_list():
    """Récupère les clés de manière sécurisée depuis st.secrets"""
    # Priorité 1 : Liste de clés pour la rotation
    if "groq_keys" in st.secrets:
        return st.secrets["groq_keys"]
    # Priorité 2 : Clé unique
    elif "GROQ_API_KEY" in st.secrets:
        return [st.secrets["GROQ_API_KEY"]]
    return []

def query_groq_with_rotation(messages):
    """Logique de tentative sur plusieurs clés et modèles"""
    available_keys = get_api_keys_list()
    
    if not available_keys:
        return None, "ERREUR CONFIG : Aucune clé API trouvée dans les secrets."
    
    # Mélange aléatoire pour répartir la charge entre les élèves
    keys_to_try = list(available_keys)
    random.shuffle(keys_to_try)
    
    # Modèles par ordre de préférence (Llama 3 est très performant et rapide)
    models = ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "llama-3.1-8b-instant"]

    for key in keys_to_try:
        try:
            client = Groq(api_key=key)
            for model in models:
                try:
                    chat = client.chat.completions.create(
                        messages=messages,
                        model=model,
                        temperature=0.5, # Température basse pour rester professionnel
                        max_tokens=1024, 
                    )
                    return chat.choices[0].message.content, model
                except Exception as e:
                    # Si erreur modèle, on passe au suivant
                    continue 
        except Exception:
            # Si erreur clé, on passe à la suivante
            continue
    
    return None, "SATURATION SERVICE : Tous les modèles sont occupés. Réessaie dans 1 minute."

# --- 4. TRAITEMENT FICHIERS ---
def extract_text_from_docx(file):
    try:
        doc = Document(file)
        return "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
    except Exception as e:
        return f"Erreur de lecture : {str(e)}"

# --- 5. INITIALISATION SESSION ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "logs" not in st.session_state:
    st.session_state.logs = []

def log_interaction(student, role, content):
    """Garde une trace locale (non persistante après fermeture)"""
    st.session_state.logs.append({
        "Heure": datetime.now().strftime("%H:%M:%S"),
        "Utilisateur": student,
        "Role": role,
        "Message": content[:50] + "..." # On tronque pour le log
    })

# --- 6. LE "SUPER PROMPT" PÉDAGOGIQUE ---
# C'est ici que l'intelligence du Gem est injectée
SYSTEM_PROMPT = """
RÔLE : Tu es le Superviseur Virtuel de l'Agence Pro'AGOrA.
TON : Professionnel, encourageant mais exigeant (Vouvoiement).
MISSION : Guider l'élève (Bac Pro) pour qu'il analyse sa propre pratique. Tu ne fais JAMAIS le travail à sa place.

CADRE RÉGLEMENTAIRE (CRITIQUE) :
1. Tu vérifies si l'élève utilise des données FICTIVES. Si un vrai nom apparaît, stoppe tout et demande l'anonymisation.
2. Tu t'appuies sur le Référentiel Bac Pro AGORA (Indicateurs de compétence).

DÉROULEMENT SÉQUENCÉ :
1. CALIBRAGE : Demande le niveau (Seconde/Première/Terminale) et le Bloc (1, 2 ou 3).
2. CONTEXTE : Demande le lieu (PME, Asso...) et le service.
3. ANALYSE : Demande de décrire les étapes et les outils numériques.
4. ÉVALUATION : Vérifie la pertinence des outils. Si l'élève est bloqué, propose un exemple fictif.
5. BILAN : Synthétise les points forts et donne 1 axe de progrès pour le dossier CCF.

RÈGLE D'OR : Une seule question à la fois. Attends toujours la réponse de l'élève.
"""

INITIAL_MESSAGE = """
👋 **Bonjour Opérateur/Opératrice.**

Bienvenue à l'Agence Pro'AGOrA. Je suis ton Superviseur Virtuel.
Je suis là pour t'aider à préparer tes fiches d'activités ou ton dossier CCF.

**⚠️ RÈGLE DE SÉCURITÉ :** Nous travaillons sur des cas **FICTIFS**. 
N'écris jamais ton vrai nom de famille, ni celui d'une vraie entreprise, ni de vrais numéros de téléphone.

**Pour commencer :**
Es-tu en Seconde, Première ou Terminale ? Et sur quel BLOC travailles-tu (1, 2 ou 3) ?
"""

# Initialisation du chat au premier chargement
if not st.session_state.messages:
    st.session_state.messages.append({"role": "assistant", "content": INITIAL_MESSAGE})

# --- 7. INTERFACE GRAPHIQUE ---

# A. EN-TÊTE LÉGAL (DISCLAIMER)
st.markdown("""
<div class="alert-box">
    <b>ℹ️ Outil Pédagogique Expérimental (IA)</b><br>
    Cet assistant est une Intelligence Artificielle. Il peut commettre des erreurs. 
    Vérifiez toujours les informations avec votre professeur. 
    Aucune donnée personnelle ne doit être saisie ici.
</div>
""", unsafe_allow_html=True)

st.title("🎓 Supervision Agence Pro'AGOrA")

# B. BARRE LATÉRALE
with st.sidebar:
    st.image("https://img.icons8.com/color/96/student-center.png", width=80)
    st.header("Profil Élève")
    
    # Alerte Rouge Permanente
    st.error("🚫 **INTERDIT** : Ne jamais saisir de données personnelles réelles (GDPR).")
    
    student_name = st.text_input("Ton Prénom (seulement) :", placeholder="Ex: Thomas")
    
    st.divider()
    
    st.subheader("📂 Analyse de Document")
    st.caption("Si tu as déjà rédigé ton activité sur Word, dépose-la ici pour analyse.")
    uploaded_file = st.file_uploader("Fichier .docx uniquement", type=['docx'])
    
    if uploaded_file and student_name:
        if st.button("🚀 Analyser ce document"):
            with st.spinner("Lecture et analyse en cours..."):
                text_content = extract_text_from_docx(uploaded_file)
                # Injection contextuelle
                prompt_analysis = f"Voici mon compte-rendu écrit (Fichier Word) : \n\n{text_content[:8000]}"
                st.session_state.messages.append({"role": "user", "content": prompt_analysis})
                log_interaction(student_name, "Eleve", "Upload Fichier")
                st.rerun()

    st.divider()
    if st.button("🔄 Nouvelle Session (Effacer tout)"):
        st.session_state.messages = [{"role": "assistant", "content": INITIAL_MESSAGE}]
        st.session_state.logs = []
        st.rerun()

# C. ZONE DE CHAT
chat_container = st.container()

with chat_container:
    for msg in st.session_state.messages:
        # On affiche joliment les messages
        with st.chat_message(msg["role"], avatar="🤖" if msg["role"] == "assistant" else "🧑‍🎓"):
            # Si c'est un long texte (analyse doc), on le replie
            if "Voici mon compte-rendu écrit" in msg["content"]:
                with st.expander("📄 Voir le document envoyé"):
                    st.write(msg["content"])
            else:
                st.markdown(msg["content"])

# D. SAISIE UTILISATEUR
if user_input := st.chat_input("Réponds au superviseur ici..."):
    if not student_name:
        st.toast("⚠️ Indique ton prénom dans le menu de gauche pour commencer !", icon="👉")
    else:
        # 1. Ajout message utilisateur
        st.session_state.messages.append({"role": "user", "content": user_input})
        log_interaction(student_name, "User", user_input)
        
        # 2. Appel IA
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Analyse pédagogique en cours..."):
                
                # Construction de l'historique pour l'API
                # On garde le System Prompt + les 10 derniers échanges pour garder le contexte sans saturer
                messages_payload = [{"role": "system", "content": SYSTEM_PROMPT}]
                messages_payload.extend(st.session_state.messages[-10:])
                
                response_content, debug_model = query_groq_with_rotation(messages_payload)
                
                if not response_content:
                    response_content = "⚠️ Désolé, je suis surchargé. Peux-tu reformuler ta réponse ?"
                
                st.markdown(response_content)
                
        # 3. Sauvegarde réponse IA
        st.session_state.messages.append({"role": "assistant", "content": response_content})
        log_interaction(student_name, "Assistant", response_content)
        st.rerun()
