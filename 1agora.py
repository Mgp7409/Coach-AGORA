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
    page_icon="🏢", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. GESTION ÉTAT ---
if "messages" not in st.session_state: st.session_state.messages = []
if "logs" not in st.session_state: st.session_state.logs = []

# --- 3. STYLE PRO (BLEU/VERT AGORA) ---
is_dys = st.session_state.get("mode_dys", False)
font_family = "'Verdana', sans-serif" if is_dys else "'Segoe UI', 'Roboto', Helvetica, Arial, sans-serif"
font_size = "18px" if is_dys else "15px"

st.markdown(f"""
<style>
    /* POLICE & COULEURS */
    html, body, [class*="css"] {{
        font-family: {font_family} !important;
        font-size: {font_size};
        color: #202124;
    }}

    /* SIDEBAR BLANCHE */
    [data-testid="stSidebar"] {{
        background-color: #FFFFFF;
        border-right: 1px solid #E0E0E0;
    }}

    /* BOUTONS ARRONDIS & VERTS (Charte AGORA) */
    .stButton > button {{
        background-color: #F0F4F8;
        color: #2E3B4E;
        border: none;
        border-radius: 12px;
        padding: 10px 20px;
        font-weight: 600;
        transition: 0.2s;
    }}
    .stButton > button:hover {{
        background-color: #E2E8F0;
    }}

    /* BOUTON PRIMAIRE (VERT/CYAN AGORA) */
    button[kind="primary"] {{
        background: linear-gradient(90deg, #00C9FF 0%, #92FE9D 100%);
        color: #004e64 !important;
        border: none;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }}
    button[kind="primary"]:hover {{
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        transform: translateY(-1px);
    }}

    /* CHAMPS SAISIE */
    .stTextInput input {{
        border-radius: 10px;
        border: 1px solid #E0E0E0;
    }}
    .stTextInput input:focus {{
        border-color: #00C9FF;
        box-shadow: 0 0 0 2px rgba(0,201,255,0.2);
    }}

    /* AVATAR ROND */
    [data-testid="stChatMessageAvatar"] img {{
        border-radius: 50%;
        object-fit: cover;
    }}

    /* BANDEAU LÉGAL */
    .fixed-footer {{
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background: white;
        color: #666;
        text-align: center;
        padding: 8px;
        font-size: 11px;
        border-top: 1px solid #eee;
        z-index: 99999;
    }}
    [data-testid="stBottom"] {{ bottom: 50px !important; }}

    /* ALERTE SIDEBAR */
    .sidebar-alert {{
        background-color: #FFF4F4;
        color: #D32F2F;
        padding: 12px;
        border-radius: 8px;
        font-size: 13px;
        font-weight: 600;
        border-left: 4px solid #D32F2F;
    }}
</style>
""", unsafe_allow_html=True)

# --- 4. LOGIQUE API ---
def get_api_keys_list():
    if "groq_keys" in st.secrets: return st.secrets["groq_keys"]
    elif "GROQ_API_KEY" in st.secrets: return [st.secrets["GROQ_API_KEY"]]
    return []

def query_groq_with_rotation(messages):
    available_keys = get_api_keys_list()
    if not available_keys: return None, "ERREUR CONFIG"
    keys = list(available_keys)
    random.shuffle(keys)
    models = ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"]
    
    for key in keys:
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
    return None, "SATURATION"

# --- 5. OUTILS ---
def extract_text_from_docx(file):
    try:
        doc = Document(file)
        text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        return text[:8000] + ("..." if len(text)>8000 else "")
    except Exception as e: return str(e)

def clean_text_for_audio(text):
    text = re.sub(r'[\*_]{1,3}', '', text)
    text = re.sub(r'\[.*?\]', '', text)
    return text

def log_interaction(student, role, content):
    st.session_state.logs.append({
        "Heure": datetime.now().strftime("%H:%M"),
        "User": student, "Role": role, "Msg": content[:50]
    })

# --- 6. DONNÉES ---
DB_PREMIERE = {
    "GESTION DES ESPACES": {
        "Aménagement": "COMPÉTENCE : Proposer un aménagement ergonomique.",
        "Numérique": "COMPÉTENCE : Lister matériel et logiciels (RGPD).",
        "Ressources": "COMPÉTENCE : Gérer stocks et réservations.",
        "Info Interne": "COMPÉTENCE : Note de service, Outils collaboratifs."
    },
    "RELATIONS PARTENAIRES": {
        "Vente": "COMPÉTENCE : Devis, Négociation, Facturation.",
        "Réunions": "COMPÉTENCE : Ordre du jour, Réservation, Compte-Rendu.",
        "Déplacements": "COMPÉTENCE : Réservation Train/Hôtel, Ordre de Mission."
    },
    "RESSOURCES HUMAINES": {
        "Recrutement": "COMPÉTENCE : Profil de poste, Annonce, Tri CV.",
        "Intégration": "COMPÉTENCE : Livret d'accueil, Parcours d'arrivée.",
        "Administratif RH": "COMPÉTENCE : Contrat, Registre personnel, Congés."
    }
}

# --- 7. IA ---
SYSTEM_PROMPT = """
RÔLE : Tu es le Superviseur Virtuel de l'Agence Pro'AGOrA.
TON : Professionnel, bienveillant mais exigeant.
MISSION : Guider l'élève (Bac Pro) sans jamais faire le travail à sa place.

RÈGLES :
1. Si l'élève envoie un TEXTE : Corrige le ton et la forme. Pose UNE question pour améliorer.
2. Si l'élève pose une QUESTION : Réponds par un indice ou une méthode, pas la solution.
3. SÉCURITÉ : Si données réelles (noms, tel) -> STOP et demande anonymisation.

FORMAT : Réponses courtes (max 3 phrases).
"""

INITIAL_MESSAGE = """
👋 **Bonjour.**

Bienvenue à l'Agence **Pro'AGOrA**.
Je suis votre superviseur virtuel.

Veuillez sélectionner votre **Mission** dans le menu de gauche pour commencer.
"""

if not st.session_state.messages:
    st.session_state.messages.append({"role": "assistant", "content": INITIAL_MESSAGE})

def lancer_mission():
    competence = DB_PREMIERE[st.session_state.theme][st.session_state.dossier]
    st.session_state.messages = []
    prompt = f"""
    CONTEXTE : Démarrage mission '{st.session_state.dossier}'.
    COMPÉTENCE : {competence}
    ACTION : Incarne le responsable. Donne le contexte (PME fictive) et la 1ère consigne à l'élève.
    """
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}]
    with st.spinner("Initialisation..."):
        resp, _ = query_groq_with_rotation(msgs)
        st.session_state.messages.append({"role": "assistant", "content": resp})

# --- 8. INTERFACE ---

# --- CONFIG IMAGES ---
# 1. Logo Lycée (Sidebar)
LOGO_LYCEE = "logo_lycee.png" 
# 2. Logo Agence (Avatar Bot)
LOGO_AGORA = "logo_agora.png"

# Avatar du Bot : Utilise le logo AGORA si présent, sinon Robot
BOT_AVATAR = LOGO_AGORA if os.path.exists(LOGO_AGORA) else "🤖"

# --- SIDEBAR ---
with st.sidebar:
    # AFFICHE LE LOGO DU LYCEE EN HAUT A GAUCHE
    if os.path.exists(LOGO_LYCEE):
        st.image(LOGO_LYCEE, width=100)
    else:
        st.header("Lycée Pro") # Fallback si pas d'image
    
    st.markdown("---")
    
    st.markdown("""
    <div class="sidebar-alert">
    🔒 <b>Espace Sécurisé</b><br>
    Utilisez uniquement des données fictives.
    </div>
    """, unsafe_allow_html=True)
    
    student_name = st.text_input("Votre Prénom", placeholder="Ex: Alex")
    
    # Menu Mission
    st.subheader("📂 Missions")
    st.session_state.theme = st.selectbox("Thème", list(DB_PREMIERE.keys()))
    st.session_state.dossier = st.selectbox("Dossier", list(DB_PREMIERE[st.session_state.theme].keys()))
    
    if st.button("LANCER LA MISSION", type="primary"):
        if student_name:
            lancer_mission()
            st.rerun()
        else:
            st.toast("Prénom requis !", icon="⚠️")
            
    # Options
    with st.expander("🛠️ Options & Accessibilité"):
        st.checkbox("Mode DYS", key="mode_dys")
        st.checkbox("Lecture Audio", key="mode_audio")
        st.checkbox("Consignes Simplifiées", key="mode_simple")
        
    # Upload
    uploaded_file = st.file_uploader("Déposer un travail (.docx)", type=['docx'])
    if uploaded_file and st.button("Envoyer à la correction"):
        txt = extract_text_from_docx(uploaded_file)
        st.session_state.messages.append({"role": "user", "content": f"PROPOSITION : {txt}"})
        st.rerun()
    
    st.markdown("---")
    
    # --- BOUTON SAUVEGARDE (Ajouté) ---
    if len(st.session_state.messages) > 1:
        # Conversion de l'historique en CSV
        chat_df = pd.DataFrame(st.session_state.messages)
        csv_data = chat_df.to_csv(index=False).encode('utf-8')
        
        date_str = datetime.now().strftime("%d%m_%H%M")
        file_name = f"suivi_agora_{student_name}_{date_str}.csv"
        
        st.download_button(
            label="💾 Sauvegarder la conversation",
            data=csv_data,
            file_name=file_name,
            mime="text/csv",
            help="Télécharge un fichier pour garder une trace de ton travail."
        )

    if st.button("🗑️ Reset"):
        st.session_state.messages = [{"role": "assistant", "content": INITIAL_MESSAGE}]
        st.rerun()

# --- CHAT CENTRAL ---
st.title("Agence Pro'AGOrA")

for i, msg in enumerate(st.session_state.messages):
    # Choix de l'avatar : Logo AGORA pour l'assistant, Étudiant pour l'user
    avatar = BOT_AVATAR if msg["role"] == "assistant" else "🧑‍🎓"
    
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])
        
        # Audio Player
        if st.session_state.get("mode_audio") and msg["role"] == "assistant" and HAS_AUDIO:
            key = f"aud_{i}"
            if key not in st.session_state:
                try:
                    tts = gTTS(clean_text_for_audio(msg["content"]), lang='fr')
                    buf = BytesIO()
                    tts.write_to_fp(buf)
                    st.session_state[key] = buf
                except: pass
            if key in st.session_state:
                st.audio(st.session_state[key], format="audio/mp3")

st.markdown("<br><br>", unsafe_allow_html=True)

# --- INPUT & FOOTER ---
if user_input := st.chat_input("Votre réponse..."):
    if not student_name:
        st.toast("Identifiez-vous dans le menu.", icon="👤")
    else:
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.rerun()

# Réponse IA
if st.session_state.messages[-1]["role"] == "user":
    # Avatar AGORA ici aussi pour le spinner de chargement
    with st.chat_message("assistant", avatar=BOT_AVATAR):
        with st.spinner("Analyse..."):
            sys = SYSTEM_PROMPT
            if st.session_state.get("mode_simple"): sys += " UTILISE DES MOTS SIMPLES."
            msgs = [{"role": "system", "content": sys}] + st.session_state.messages[-6:]
            
            resp, _ = query_groq_with_rotation(msgs)
            if not resp: resp = "Erreur technique. Réessayez."
            st.markdown(resp)
            st.session_state.messages.append({"role": "assistant", "content": resp})
            if st.session_state.get("mode_audio"): st.rerun()

st.markdown('<div class="fixed-footer">Agence Pro\'AGOrA v1.0 - Outil Pédagogique IA - Données Fictives Uniquement</div>', unsafe_allow_html=True)
