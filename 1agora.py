import streamlit as st
import pandas as pd
import random
from groq import Groq
from datetime import datetime
from io import StringIO, BytesIO
import re

# --- 0. SÉCURITÉ & DÉPENDANCES ---
try:
    from docx import Document
except ImportError:
    st.error("⚠️ ERREUR CRITIQUE : Le module 'python-docx' manque. Ajoutez-le au fichier requirements.txt")
    st.stop()

# Import gTTS pour l'audio (si manque, on gère l'erreur sans planter)
try:
    from gtts import gTTS
    HAS_AUDIO = True
except ImportError:
    HAS_AUDIO = False

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Agence Pro'AGOrA", 
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. GESTION ÉTAT (Session State) ---
if "messages" not in st.session_state: st.session_state.messages = []
if "logs" not in st.session_state: st.session_state.logs = []
# Note: mode_dys, mode_audio, mode_simple sont gérés par les widgets

# --- 3. STYLE CSS & CHARTE GRAPHIQUE ---
# Couleurs "Entreprise" (Bleu Pro)
PRIMARY_COLOR = "#0F52BA"
BG_COLOR = "#F0F2F6"

# On récupère l'état DYS
is_dys = st.session_state.get("mode_dys", False)

dys_css = """
    html, body, [class*="css"] {
        font-family: 'Verdana', sans-serif !important;
        font-size: 18px !important;
        line-height: 1.8 !important;
        letter-spacing: 0.5px !important;
    }
""" if is_dys else ""

st.markdown(f"""
<style>
    {dys_css}
    
    /* Masquer le footer Streamlit */
    footer {{visibility: hidden;}}
    .reportview-container .main .block-container {{padding-top: 2rem;}}
    
    /* BANDEAU LÉGAL FIXE EN BAS */
    .fixed-footer {{
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #f8f9fa;
        color: #6c757d;
        text-align: center;
        padding: 8px 10px;
        font-size: 11px;
        border-top: 1px solid #e1e4e8;
        z-index: 99999;
        line-height: 1.4;
        font-family: sans-serif;
    }}

    /* Remonter la zone de saisie pour ne pas être cachée */
    [data-testid="stBottom"] {{
        bottom: 50px !important;
        padding-bottom: 0px !important;
    }}
    
    /* STYLE ALERTE ROUGE (Sidebar) */
    .sidebar-alert {{
        padding: 12px;
        background-color: #fff5f5;
        border-left: 5px solid #c53030;
        color: #c53030;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.85rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }}

    /* BOUTONS STYLISÉS */
    .stButton > button {{
        width: 100%;
        border-radius: 6px;
        font-weight: bold;
    }}
</style>
""", unsafe_allow_html=True)

# --- 4. GESTION DES CLÉS API (ROTATION) ---
def get_api_keys_list():
    if "groq_keys" in st.secrets:
        return st.secrets["groq_keys"]
    elif "GROQ_API_KEY" in st.secrets:
        return [st.secrets["GROQ_API_KEY"]]
    return []

def query_groq_with_rotation(messages):
    available_keys = get_api_keys_list()
    if not available_keys:
        return None, "ERREUR CONFIG : Aucune clé API trouvée."
    
    keys_to_try = list(available_keys)
    random.shuffle(keys_to_try)
    models = ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "llama-3.1-8b-instant"]

    for key in keys_to_try:
        try:
            client = Groq(api_key=key)
            for model in models:
                try:
                    chat = client.chat.completions.create(
                        messages=messages,
                        model=model,
                        temperature=0.5,
                        max_tokens=1024, 
                    )
                    return chat.choices[0].message.content, model
                except: continue 
        except: continue
    return None, "SATURATION SERVICE."

# --- 5. FONCTIONS UTILITAIRES ---
def extract_text_from_docx(file):
    try:
        doc = Document(file)
        full_text = []
        for para in doc.paragraphs:
            if para.text.strip():
                full_text.append(para.text)
        text = "\n".join(full_text)
        if len(text) > 8000:
            text = text[:8000] + "\n\n[...TEXTE TRONQUÉ CAR TROP LONG...]"
        return text
    except Exception as e:
        return f"Erreur de lecture : {str(e)}"

def clean_text_for_audio(text):
    text = re.sub(r'[\*_]{1,3}', '', text) # Enlève gras/italique
    text = re.sub(r'#+', '', text) # Enlève titres
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text) # Enlève liens
    text = re.sub(r'^\s*-\s+', '', text, flags=re.MULTILINE) # Enlève puces
    return text

def log_interaction(student, role, content):
    st.session_state.logs.append({
        "Heure": datetime.now().strftime("%H:%M:%S"),
        "Utilisateur": student,
        "Role": role,
        "Message": content[:50]
    })

# --- 6. DONNÉES PÉDAGOGIQUES ---
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

# --- 7. PROMPT SYSTÈME ---
SYSTEM_PROMPT = """
RÔLE : Tu es le Superviseur Virtuel de l'Agence Pro'AGOrA.
TON : Professionnel, encourageant mais exigeant (Vouvoiement).
CIBLE : Élèves de Première Bac Pro AGOrA.
MISSION : Guider l'élève pour qu'il analyse sa propre pratique ou réalise la mission sélectionnée.

⛔ INTERDICTIONS ABSOLUES :
1. NE JAMAIS FAIRE LE TRAVAIL à la place de l'élève (ne rédige pas les mails, ne fais pas les calculs).
2. NE PAS ÉCRIRE DE LONGS PARAGRAPHES. Tes réponses doivent être COURTES (max 3 phrases).
3. Une seule question à la fois.

DÉROULEMENT :
1. Si l'élève lance une MISSION : Incarne le responsable, donne le contexte (Entreprise fictive, chiffres clés) et la consigne de départ.
2. Si l'élève envoie un DOCUMENT (Word) : Analyse-le. Vérifie l'orthographe, la forme et le fond. Dis ce qui va, et pose UNE question sur ce qui manque.
3. Si l'élève DISCUTE : Guide-le par maïeutique (questions ouvertes).

SÉCURITÉ : Si l'élève utilise un VRAI nom de famille ou une vraie entreprise, demande-lui d'anonymiser immédiatement.
"""

INITIAL_MESSAGE = """
👋 **Bonjour Opérateur/Opératrice.**

Bienvenue à l'Agence Pro'AGOrA.

**⚠️ SÉCURITÉ :** Utilise uniquement des données **FICTIVES**.

👉 **Pour commencer :** Sélectionne ta mission dans le menu de gauche et clique sur **LANCER**.
"""

if not st.session_state.messages:
    st.session_state.messages.append({"role": "assistant", "content": INITIAL_MESSAGE})

# Fonction de lancement
def lancer_mission():
    theme = st.session_state.theme_select
    dossier = st.session_state.dossier_select
    competence = DB_PREMIERE[theme][dossier]
    
    st.session_state.messages = []
    
    prompt_demarrage = f"""
    CONTEXTE : L'élève démarre la mission '{dossier}'.
    COMPÉTENCE VISÉE : {competence}
    ACTION : Invente une entreprise fictive (PME ou Asso) et un contexte réaliste.
    CONSIGNE : Accueille l'élève en tant que son responsable, donne-lui les données de départ (budget, dates, contraintes) et la première tâche à réaliser.
    Ne fais PAS la tâche toi-même.
    """
    
    final_system_prompt = SYSTEM_PROMPT
    if st.session_state.get("mode_simple", False):
        final_system_prompt += "\n\n⚠️ MODE SIMPLIFIÉ : Utilise des mots simples. Fais une liste à puces."

    msgs = [{"role": "system", "content": final_system_prompt}]
    msgs.append({"role": "user", "content": prompt_demarrage})
    
    with st.spinner("Chargement du scénario..."):
        intro_bot, _ = query_groq_with_rotation(msgs)
        st.session_state.messages.append({"role": "assistant", "content": intro_bot})

# --- 8. INTERFACE GRAPHIQUE ---

# En-tête principal
st.title("🎓 Agence Pro'AGOrA")
st.caption("Plateforme pédagogique d'entraînement aux situations professionnelles.")

# A. BARRE LATÉRALE
with st.sidebar:
    # LOGO DU LYCÉE (Placeholder)
    # Remplacez l'URL ci-dessous par celle de votre lycée
    LOGO_URL = "https://img.icons8.com/clouds/200/school.png" 
    st.image(LOGO_URL, width=120)
    
    st.header("👤 Espace Élève")
    
    # ALERTE ROUGE
    st.markdown("""
    <div class="sidebar-alert">
    🚫 <b>INTERDIT</b><br>
    Ne jamais saisir de données personnelles réelles (RGPD).
    </div>
    """, unsafe_allow_html=True)
    
    student_name = st.text_input("Ton Prénom :", placeholder="Ex: Thomas")
    
    st.divider()

    # ACCESSIBILITÉ
    st.subheader("♿ Accessibilité")
    col_a, col_b = st.columns(2)
    with col_a:
        st.checkbox("👁️ DYS", key="mode_dys", help="Police adaptée pour la dyslexie")
    with col_b:
        st.checkbox("🔊 Audio", key="mode_audio", help="Lecture à voix haute des réponses")
    
    st.checkbox("🧠 Consignes Simplifiées", key="mode_simple", help="Langage plus simple et structuré")
    
    st.divider()
    
    # CHOIX MISSION
    st.subheader("📚 Choix de la Mission")
    theme = st.selectbox("Thème :", list(DB_PREMIERE.keys()), key="theme_select")
    dossier = st.selectbox("Dossier :", list(DB_PREMIERE[theme].keys()), key="dossier_select")
    
    if st.button("🚀 LANCER LE SCÉNARIO", type="primary"):
        if student_name:
            lancer_mission()
            st.rerun()
        else:
            st.toast("⚠️ Indique ton prénom avant de lancer !", icon="🛑")
            
    st.divider()
    
    # DÉPÔT FICHIER
    st.subheader("📂 Rendre un travail")
    uploaded_file = st.file_uploader("Fichier Word (.docx)", type=['docx'], label_visibility="collapsed")
    
    if uploaded_file and student_name:
        if st.button("📤 Envoyer à la correction"):
            with st.spinner("Analyse du document..."):
                text_content = extract_text_from_docx(uploaded_file)
                prompt_analysis = f"Voici ma production (Fichier Word : {uploaded_file.name}) :\n\n{text_content}"
                st.session_state.messages.append({"role": "user", "content": prompt_analysis})
                log_interaction(student_name, "Eleve", f"Upload: {uploaded_file.name}")
                st.rerun()

    st.divider()

    # SAUVEGARDE
    if len(st.session_state.messages) > 1:
        chat_df = pd.DataFrame(st.session_state.messages)
        csv_data = chat_df.to_csv(index=False).encode('utf-8')
        filename = f"agora_{student_name if student_name else 'anonyme'}.csv"
        st.download_button("💾 Sauvegarder ma session", csv_data, filename, "text/csv")
    
    # BOUTON RESET
    if st.button("🗑️ Nouvelle Session"):
        st.session_state.messages = [{"role": "assistant", "content": INITIAL_MESSAGE}]
        st.session_state.logs = []
        st.rerun()

# B. ZONE DE CHAT
chat_container = st.container()
with chat_container:
    for i, msg in enumerate(st.session_state.messages):
        # Avatar personnalisé
        avatar = "🧑‍🎓" if msg["role"] == "user" else "🤖"
        
        with st.chat_message(msg["role"], avatar=avatar):
            if "Voici ma production (Fichier Word" in msg["content"]:
                with st.expander("📄 Voir le contenu du fichier analysé"):
                    st.write(msg["content"])
            else:
                st.markdown(msg["content"])
                
                # LECTEUR AUDIO
                if st.session_state.get("mode_audio", False) and msg["role"] == "assistant" and HAS_AUDIO:
                    audio_key = f"audio_{i}"
                    if audio_key not in st.session_state:
                        try:
                            clean_txt = clean_text_for_audio(msg["content"])
                            tts = gTTS(text=clean_txt, lang='fr')
                            audio_buffer = BytesIO()
                            tts.write_to_fp(audio_buffer)
                            st.session_state[audio_key] = audio_buffer
                        except: pass
                    
                    if audio_key in st.session_state:
                        st.audio(st.session_state[audio_key], format="audio/mp3")

    st.write("<br><br><br>", unsafe_allow_html=True)

# C. BANDEAU LÉGAL
st.markdown("""
<div class="fixed-footer">
    ℹ️ <b>Outil Pédagogique Expérimental (IA)</b><br>
    Cet assistant peut commettre des erreurs. Vérifiez toujours avec votre professeur. 
    Aucune donnée personnelle ne doit être saisie ici.
</div>
""", unsafe_allow_html=True)

# D. RÉPONSE IA
if st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Analyse du superviseur..."):
            
            final_system_prompt = SYSTEM_PROMPT
            if st.session_state.get("mode_simple", False):
                final_system_prompt += "\n\n⚠️ MODE SIMPLIFIÉ : Utilise des mots simples. Fais une liste à puces."

            messages_payload = [{"role": "system", "content": final_system_prompt}]
            messages_payload.extend(st.session_state.messages[-10:])
            
            response_content, _ = query_groq_with_rotation(messages_payload)
            
            if not response_content:
                response_content = "⚠️ Mes systèmes sont saturés. Peux-tu répéter ?"
            
            st.markdown(response_content)
            
    st.session_state.messages.append({"role": "assistant", "content": response_content})
    
    if st.session_state.get("mode_audio", False):
        st.rerun()

# E. SAISIE
if user_input := st.chat_input("Réponds au superviseur ici..."):
    if not student_name:
        st.toast("⚠️ Indique ton prénom à gauche !", icon="👉")
    else:
        st.session_state.messages.append({"role": "user", "content": user_input})
        log_interaction(student_name, "User", user_input)
        st.rerun()
