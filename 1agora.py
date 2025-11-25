import streamlit as st
import pandas as pd
import random
from groq import Groq
from datetime import datetime
from io import StringIO, BytesIO
import re
import os

# --- 0. SÉCURITÉ & DÉPENDANCES ---
try:
    from docx import Document
except ImportError:
    st.error("⚠️ ERREUR CRITIQUE : Le module 'python-docx' manque. Ajoutez-le au fichier requirements.txt")
    st.stop()

try:
    from gtts import gTTS
    HAS_AUDIO = True
except ImportError:
    HAS_AUDIO = False

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Agence Pro'AGOrA", 
    page_icon="🔵", # Icone plus sobre
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. GESTION ÉTAT ---
if "messages" not in st.session_state: st.session_state.messages = []
if "logs" not in st.session_state: st.session_state.logs = []

# --- 3. STYLE "GOOGLE MATERIAL DESIGN" ---
# On récupère l'état DYS
is_dys = st.session_state.get("mode_dys", False)

# Police de base : Roboto/Sans-serif comme Google
font_family = "'Verdana', sans-serif" if is_dys else "'Google Sans', 'Roboto', Helvetica, Arial, sans-serif"
font_size = "18px" if is_dys else "15px"
line_height = "1.8" if is_dys else "1.5"

st.markdown(f"""
<style>
    /* IMPORT POLICE GOOGLE (Simulation) */
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');

    /* GLOBAL */
    html, body, [class*="css"] {{
        font-family: {font_family} !important;
        font-size: {font_size};
        line-height: {line_height};
        color: #202124;
    }}

    /* FOND PRINCIPAL BLANC */
    .stApp {{
        background-color: #FFFFFF;
    }}

    /* SIDEBAR (GRIS CLAIR TYPE GMAIL) */
    [data-testid="stSidebar"] {{
        background-color: #F6F8FC;
        border-right: none;
    }}

    /* BOUTONS (STYLE MATERIAL DESIGN) */
    .stButton > button {{
        background-color: #F1F3F4; /* Gris bouton inactif */
        color: #3c4043;
        border: none;
        border-radius: 24px; /* Très arrondi */
        padding: 10px 24px;
        font-weight: 500;
        transition: all 0.2s;
        box-shadow: none;
    }}
    
    .stButton > button:hover {{
        background-color: #E8EAED;
        box-shadow: 0 1px 2px rgba(60,64,67,0.3);
        color: #202124;
    }}

    /* BOUTON PRIMAIRE (BLEU GOOGLE) - Ciblage du bouton "Lancer" */
    /* Astuce: On cible le bouton spécifique via le type primary en Streamlit */
    button[kind="primary"] {{
        background-color: #1A73E8 !important;
        color: white !important;
        box-shadow: 0 1px 3px rgba(60,64,67,0.3);
    }}
    button[kind="primary"]:hover {{
        background-color: #1765CC !important;
        box-shadow: 0 4px 8px rgba(60,64,67,0.3);
    }}

    /* CHAMPS DE SAISIE (INPUTS) */
    .stTextInput input, .stSelectbox > div > div {{
        background-color: #F1F3F4;
        border: 1px solid transparent;
        border-radius: 8px;
        color: #202124;
    }}
    .stTextInput input:focus, .stSelectbox > div > div:focus-within {{
        background-color: white;
        border: 1px solid #1A73E8;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }}

    /* ZONE DE CHAT ET BULLES */
    [data-testid="stChatMessage"] {{
        background-color: transparent;
        border: none;
        padding: 1rem 0;
    }}
    
    /* Avatar rond */
    [data-testid="stChatMessageAvatar"] {{
        background-color: #1A73E8;
        color: white;
        border-radius: 50%;
    }}

    /* BANDEAU LÉGAL FLOTTANT (Style "Toaster" Google) */
    .fixed-footer {{
        position: fixed;
        left: 50%;
        transform: translateX(-50%);
        bottom: 10px;
        background-color: #323232;
        color: white;
        text-align: center;
        padding: 10px 20px;
        font-size: 12px;
        border-radius: 4px;
        z-index: 99999;
        box-shadow: 0 3px 5px -1px rgba(0,0,0,.2), 0 6px 10px 0 rgba(0,0,0,.14), 0 1px 18px 0 rgba(0,0,0,.12);
        min-width: 300px;
    }}

    /* CACHER LE FOOTER STREAMLIT */
    footer {{visibility: hidden;}}
    
    /* REMONTER LA ZONE DE SAISIE */
    [data-testid="stBottom"] {{
        bottom: 60px !important;
    }}

    /* TITRE PRINCIPAL */
    h1 {{
        color: #202124;
        font-family: 'Google Sans', sans-serif;
        font-weight: 400;
    }}

    /* ALERTE ROUGE SIDEBAR */
    .sidebar-alert {{
        background-color: #FCE8E6;
        color: #C5221F;
        padding: 12px;
        border-radius: 8px;
        font-size: 13px;
        font-weight: 500;
        display: flex;
        align-items: center;
        gap: 8px;
    }}
</style>
""", unsafe_allow_html=True)

# --- 4. GESTION API ---
def get_api_keys_list():
    if "groq_keys" in st.secrets:
        return st.secrets["groq_keys"]
    elif "GROQ_API_KEY" in st.secrets:
        return [st.secrets["GROQ_API_KEY"]]
    return []

def query_groq_with_rotation(messages):
    available_keys = get_api_keys_list()
    if not available_keys:
        return None, "ERREUR CONFIG"
    keys_to_try = list(available_keys)
    random.shuffle(keys_to_try)
    models = ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "llama-3.1-8b-instant"]
    for key in keys_to_try:
        try:
            client = Groq(api_key=key)
            for model in models:
                try:
                    chat = client.chat.completions.create(
                        messages=messages, model=model, temperature=0.5, max_tokens=1024
                    )
                    return chat.choices[0].message.content, model
                except: continue 
        except: continue
    return None, "SATURATION SERVICE."

# --- 5. OUTILS FICHIERS ---
def extract_text_from_docx(file):
    try:
        doc = Document(file)
        full_text = []
        for para in doc.paragraphs:
            if para.text.strip(): full_text.append(para.text)
        text = "\n".join(full_text)
        if len(text) > 8000: text = text[:8000] + "\n\n[...TEXTE TRONQUÉ...]"
        return text
    except Exception as e: return f"Erreur : {str(e)}"

def clean_text_for_audio(text):
    text = re.sub(r'[\*_]{1,3}', '', text)
    text = re.sub(r'#+', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    return text

def log_interaction(student, role, content):
    st.session_state.logs.append({
        "Heure": datetime.now().strftime("%H:%M:%S"),
        "Utilisateur": student, "Role": role, "Message": content[:50]
    })

# --- 6. DONNÉES MÉTIER ---
DB_PREMIERE = {
    "GESTION DES ESPACES DE TRAVAIL": {
        "Aménagement des espaces": "COMPÉTENCE : Proposer un aménagement de bureau ergonomique et choisir le mobilier adapté.",
        "Environnement numérique": "COMPÉTENCE : Lister le matériel informatique, les logiciels et vérifier les règles RGPD.",
        "Ressources partagées": "COMPÉTENCE : Gérer le stock de fournitures (commandes/partage) et les réservations (salles/véhicules).",
        "Partage de l'information": "COMPÉTENCE : Améliorer la communication interne (Note de service, Outils collaboratifs, Agenda)."
    },
    "GESTION DES RELATIONS PARTENAIRES": {
        "Lancement produit / Vente": "COMPÉTENCE : Planifier des tâches (Planigramme), Négocier un prix de vente, Communication commerciale.",
        "Organisation de réunions": "COMPÉTENCE : Convoquer les participants, Réserver la salle, Préparer l'ordre du jour, Rédiger le Compte-Rendu.",
        "Organisation déplacement": "COMPÉTENCE : Réserver un déplacement (Train/Avion/Hôtel) avec budget contraint. Établir l'Ordre de Mission."
    },
    "GESTION DES RESSOURCES HUMAINES": {
        "Recrutement": "COMPÉTENCE : Définir le Profil de poste, Rédiger l'annonce d'embauche, Trier des CV.",
        "Intégration du personnel": "COMPÉTENCE : Préparer l'arrivée (matériel, badges), Créer le livret d'accueil, Organiser l'accueil.",
        "Dossiers du personnel": "COMPÉTENCE : Rédiger un Contrat de travail, Mettre à jour le Registre Unique du Personnel, Faire un Avenant."
    },
    "SCÉNARIOS TRANSVERSAUX": {
        "Réorganisation complète": "COMPÉTENCE : Projet global de déménagement ou de réaménagement des services.",
        "Campagne de Recrutement": "COMPÉTENCE : Projet global de recrutement (de l'annonce à l'intégration)."
    }
}

# --- 7. PROMPTS ---
SYSTEM_PROMPT = """
RÔLE : Tu es le Superviseur Virtuel de l'Agence Pro'AGOrA.
TON : Professionnel, encourageant mais exigeant (Vouvoiement).
CIBLE : Élèves de Première Bac Pro AGOrA.
MISSION : Guider l'élève pour qu'il analyse sa propre pratique.

⛔ INTERDICTIONS :
1. NE JAMAIS FAIRE LE TRAVAIL à la place de l'élève.
2. RÉPONSES COURTES (max 3 phrases).
3. UNE SEULE question à la fois.

DÉROULEMENT :
1. MISSION LANCÉE : Incarne le responsable, donne le contexte et la consigne.
2. DOCUMENT REÇU : Analyse la forme et le fond. Dis ce qui va, pose une question sur ce qui manque.
3. DISCUSSION : Guide par maïeutique.

SÉCURITÉ : Si données réelles détectées -> STOP et demande anonymisation.
"""

INITIAL_MESSAGE = """
**Bonjour.** 👋

Bienvenue dans l'espace de supervision **Agence Pro'AGOrA**.

Veuillez sélectionner votre mission dans le menu latéral pour commencer.
"""

if not st.session_state.messages:
    st.session_state.messages.append({"role": "assistant", "content": INITIAL_MESSAGE})

def lancer_mission():
    theme = st.session_state.theme_select
    dossier = st.session_state.dossier_select
    competence = DB_PREMIERE[theme][dossier]
    st.session_state.messages = []
    
    prompt_demarrage = f"""
    CONTEXTE : L'élève démarre la mission '{dossier}'.
    COMPÉTENCE : {competence}
    ACTION : Invente une entreprise fictive (PME/Asso) et un contexte réaliste.
    CONSIGNE : Accueille l'élève (rôle Responsable), donne les données de départ (budget, dates) et la 1ère tâche.
    """
    
    final_system = SYSTEM_PROMPT
    if st.session_state.get("mode_simple", False):
        final_system += "\n\n⚠️ MODE SIMPLIFIÉ : Mots simples, listes à puces."

    msgs = [{"role": "system", "content": final_system}, {"role": "user", "content": prompt_demarrage}]
    
    with st.spinner("Chargement du dossier..."):
        intro_bot, _ = query_groq_with_rotation(msgs)
        st.session_state.messages.append({"role": "assistant", "content": intro_bot})

# --- 8. INTERFACE ---

# Header simple et propre
st.title("Agence Pro'AGOrA")
st.caption("Environnement Numérique de Formation")

# --- SIDEBAR (Menu Latéral) ---
with st.sidebar:
    # Logo
    LOGO_FILE = "logo_lycee.png"
    if os.path.exists(LOGO_FILE):
        st.image(LOGO_FILE, width=80)
    else:
        st.image("https://img.icons8.com/color/96/google-classroom.png", width=60)
    
    st.markdown("### 👤 Identification")
    
    # Alerte stylisée
    st.markdown("""
    <div class="sidebar-alert">
    🛡️ <b>Sécurité RGPD</b><br>
    Aucune donnée réelle ne doit être saisie. Utilisez des pseudonymes.
    </div>
    """, unsafe_allow_html=True)
    
    student_name = st.text_input("Prénom", placeholder="Votre prénom")
    
    st.divider()

    # Options (Switches plus propres)
    st.markdown("### ⚙️ Paramètres")
    col_a, col_b = st.columns(2)
    with col_a:
        st.checkbox("DYS", key="mode_dys")
    with col_b:
        st.checkbox("Audio", key="mode_audio")
    st.checkbox("Simplifié", key="mode_simple")
    
    st.divider()
    
    # Navigation Missions
    st.markdown("### 📂 Missions")
    theme = st.selectbox("Thème", list(DB_PREMIERE.keys()), key="theme_select")
    dossier = st.selectbox("Dossier", list(DB_PREMIERE[theme].keys()), key="dossier_select")
    
    # Bouton d'action principal (Bleu)
    if st.button("Lancer la mission", type="primary"):
        if student_name:
            lancer_mission()
            st.rerun()
        else:
            st.toast("Veuillez vous identifier d'abord.", icon="👤")
            
    st.divider()
    
    # Upload
    st.markdown("### 📤 Rendu")
    uploaded_file = st.file_uploader("Déposer un fichier Word", type=['docx'], label_visibility="collapsed")
    
    if uploaded_file and student_name:
        if st.button("Envoyer à la correction"):
            with st.spinner("Analyse en cours..."):
                text_content = extract_text_from_docx(uploaded_file)
                prompt = f"Voici mon fichier {uploaded_file.name} :\n\n{text_content}"
                st.session_state.messages.append({"role": "user", "content": prompt})
                log_interaction(student_name, "Eleve", f"Upload: {uploaded_file.name}")
                st.rerun()

    # Footer sidebar
    st.markdown("---")
    if st.button("Nouvelle Session"):
        st.session_state.messages = [{"role": "assistant", "content": INITIAL_MESSAGE}]
        st.session_state.logs = []
        st.rerun()

# --- ZONE CENTRALE (CHAT) ---
chat_container = st.container()
with chat_container:
    for i, msg in enumerate(st.session_state.messages):
        # Avatars Google style (lettre ou icone)
        avatar = "🧑‍🎓" if msg["role"] == "user" else "https://img.icons8.com/color/48/google-logo.png"
        
        with st.chat_message(msg["role"], avatar=avatar):
            if "Voici mon fichier" in msg["content"]:
                with st.expander("📄 Fichier joint"):
                    st.write(msg["content"])
            else:
                st.markdown(msg["content"])
                
                # Audio
                if st.session_state.get("mode_audio", False) and msg["role"] == "assistant" and HAS_AUDIO:
                    key = f"audio_{i}"
                    if key not in st.session_state:
                        try:
                            tts = gTTS(text=clean_text_for_audio(msg["content"]), lang='fr')
                            buf = BytesIO()
                            tts.write_to_fp(buf)
                            st.session_state[key] = buf
                        except: pass
                    if key in st.session_state:
                        st.audio(st.session_state[key], format="audio/mp3")

    st.write("<br><br><br>", unsafe_allow_html=True)

# --- BANDEAU LEGAL (Toaster Noir) ---
st.markdown("""
<div class="fixed-footer">
    Outil Pédagogique Expérimental (IA) - Vérifiez toujours les informations.<br>
    Ne saisissez aucune donnée personnelle réelle.
</div>
""", unsafe_allow_html=True)

# --- RÉPONSE AUTO ---
if st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant", avatar="https://img.icons8.com/color/48/google-logo.png"):
        with st.spinner("..."):
            final_system = SYSTEM_PROMPT
            if st.session_state.get("mode_simple", False):
                final_system += "\n\n⚠️ MODE SIMPLIFIÉ : Mots simples, listes à puces."

            msgs = [{"role": "system", "content": final_system}]
            msgs.extend(st.session_state.messages[-10:])
            
            resp, _ = query_groq_with_rotation(msgs)
            if not resp: resp = "Erreur de service. Veuillez réessayer."
            
            st.markdown(resp)
            
    st.session_state.messages.append({"role": "assistant", "content": resp})
    if st.session_state.get("mode_audio", False): st.rerun()

# --- SAISIE ---
if user_input := st.chat_input("Répondre..."):
    if not student_name:
        st.toast("Veuillez indiquer votre prénom dans le menu.", icon="👈")
    else:
        st.session_state.messages.append({"role": "user", "content": user_input})
        log_interaction(student_name, "User", user_input)
        st.rerun()
