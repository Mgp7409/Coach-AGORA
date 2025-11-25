import streamlit as st
import pandas as pd
import random
from groq import Groq
from datetime import datetime
from io import StringIO, BytesIO
import re
import os
import base64

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
# On utilise le logo Agence comme icône de page si disponible
PAGE_ICON = "logo_agora.png" if os.path.exists("logo_agora.png") else "🏢"

st.set_page_config(
    page_title="Agence Pro'AGOrA", 
    page_icon=PAGE_ICON, 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. GESTION ÉTAT ---
if "messages" not in st.session_state: st.session_state.messages = []
if "logs" not in st.session_state: st.session_state.logs = []
if "notifications" not in st.session_state: st.session_state.notifications = ["Bienvenue sur la plateforme."]

# --- 3. OUTILS IMAGE ---
def img_to_base64(img_path):
    if os.path.exists(img_path):
        with open(img_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

# --- 4. STYLE & CSS AVANCÉ ---
is_dys = st.session_state.get("mode_dys", False)
font_family = "'Verdana', sans-serif" if is_dys else "'Segoe UI', 'Roboto', Helvetica, Arial, sans-serif"
font_size = "18px" if is_dys else "15px"

st.markdown(f"""
<style>
    /* GLOBAL */
    html, body, [class*="css"] {{
        font-family: {font_family} !important;
        font-size: {font_size};
        color: #202124;
        background-color: #FFFFFF;
    }}

    /* SUPPRESSION MARGES HEADER */
    .reportview-container .main .block-container {{
        padding-top: 1rem;
        padding-right: 1rem;
        padding-left: 1rem;
        max-width: 100%;
    }}
    header {{visibility: hidden;}} 

    /* STYLE NAVBAR (CONTAINER) */
    .navbar-container {{
        display: flex;
        align-items: center;
        background-color: white;
        padding: 10px 20px;
        border-bottom: 1px solid #E0E0E0;
        margin-bottom: 10px;
        height: 80px;
    }}

    /* BOUTONS NAVBAR */
    div[data-testid="stHorizontalBlock"] button {{
        background-color: transparent;
        border: none;
        color: #5F6368;
        box-shadow: none;
        font-weight: 500;
    }}
    div[data-testid="stHorizontalBlock"] button:hover {{
        color: #1A73E8;
        background-color: #F1F3F4;
    }}

    /* SIDEBAR */
    [data-testid="stSidebar"] {{
        background-color: #F8F9FA;
        border-right: 1px solid #E0E0E0;
    }}

    /* BOUTONS ACTION (Verts/Bleus) */
    div[data-testid="stSidebar"] button {{
        background-color: #FFFFFF;
        border: 1px solid #DADCE0;
        color: #3C4043;
        border-radius: 8px;
    }}
    
    /* Bouton Primaire (Lancer) */
    button[kind="primary"] {{
        background: linear-gradient(135deg, #0F9D58 0%, #00C9FF 100%);
        color: white !important;
        border: none;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }}

    /* CHAT */
    [data-testid="stChatMessage"] {{
        background-color: transparent;
        padding: 1rem;
        border-radius: 8px;
    }}
    [data-testid="stChatMessage"][data-testid="user"] {{
        background-color: #F1F3F4;
    }}

    /* AVATAR */
    [data-testid="stChatMessageAvatar"] img {{
        border-radius: 50%;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        object-fit: cover;
    }}

    /* FOOTER & INPUT */
    .fixed-footer {{
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background: #323232;
        color: #FFF;
        text-align: center;
        padding: 6px;
        font-size: 11px;
        z-index: 99999;
    }}
    [data-testid="stBottom"] {{ bottom: 40px !important; }}
</style>
""", unsafe_allow_html=True)

# --- 5. LOGIQUE API ---
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

# --- 6. OUTILS ---
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

def add_notification(msg):
    ts = datetime.now().strftime("%H:%M")
    st.session_state.notifications.insert(0, f"{ts} - {msg}")

def log_interaction(student, role, content):
    st.session_state.logs.append({
        "Heure": datetime.now().strftime("%H:%M"),
        "User": student, "Role": role, "Msg": content[:50]
    })

# --- 7. DONNÉES ---
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

# --- 8. IA ---
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
    add_notification(f"Mission lancée : {st.session_state.dossier}")

# --- 9. INTERFACE ---

# --- IMAGES ---
LOGO_LYCEE = "logo_lycee.png"
LOGO_AGORA = "logo_agora.png"
BOT_AVATAR = LOGO_AGORA if os.path.exists(LOGO_AGORA) else "🤖"

# --- SIDEBAR (Menu) ---
with st.sidebar:
    if os.path.exists(LOGO_LYCEE):
        st.image(LOGO_LYCEE, width=100)
    else:
        st.header("Lycée Pro")
    
    st.markdown("---")
    st.info("🔒 **Espace Sécurisé** : Données fictives uniquement.")
    
    student_name = st.text_input("Prénom", placeholder="Ex: Camille")
    user_label = f"👤 {student_name}" if student_name else "👤 Invité"
    
    st.subheader("📂 Missions")
    st.session_state.theme = st.selectbox("Thème", list(DB_PREMIERE.keys()))
    st.session_state.dossier = st.selectbox("Dossier", list(DB_PREMIERE[st.session_state.theme].keys()))
    
    if st.button("LANCER LA MISSION", type="primary"):
        if student_name:
            lancer_mission()
            st.rerun()
        else:
            st.warning("Prénom requis !")
            
    with st.expander("🛠️ Options"):
        st.checkbox("Mode DYS", key="mode_dys")
        st.checkbox("Audio", key="mode_audio")
        st.checkbox("Simplifié", key="mode_simple")
        
    uploaded_file = st.file_uploader("Rendre un travail (.docx)", type=['docx'])
    if uploaded_file and student_name:
        if st.button("Envoyer à la correction"):
            txt = extract_text_from_docx(uploaded_file)
            st.session_state.messages.append({"role": "user", "content": f"PROPOSITION : {txt}"})
            add_notification(f"Fichier envoyé : {uploaded_file.name}")
            st.rerun()
    
    st.markdown("---")
    
    if len(st.session_state.messages) > 1:
        chat_df = pd.DataFrame(st.session_state.messages)
        csv_data = chat_df.to_csv(index=False).encode('utf-8')
        date_str = datetime.now().strftime("%d%m_%H%M")
        st.download_button("💾 Sauvegarder (CSV)", csv_data, f"agora_{student_name}_{date_str}.csv", "text/csv")

    if st.button("🗑️ Reset"):
        st.session_state.messages = [{"role": "assistant", "content": INITIAL_MESSAGE}]
        st.session_state.notifications = ["Session réinitialisée."]
        st.rerun()

# --- HEADER FONCTIONNEL (Navbar) ---
c1, c2, c3, c4 = st.columns([4, 1, 1, 1])

with c1:
    logo_html = ""
    if os.path.exists(LOGO_AGORA):
        b64 = img_to_base64(LOGO_AGORA)
        logo_html = f'<img src="data:image/png;base64,{b64}" style="height:45px; vertical-align:middle; margin-right:10px;">'
    
    st.markdown(f"""
    <div style="display:flex; align-items:center;">
        {logo_html}
        <div>
            <div style="font-size:24px; font-weight:bold; color:#202124; line-height:1.2;">Agence Pro'AGOrA</div>
            <div style="font-size:12px; color:#5F6368;">Superviseur IA v1.3</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# BOUTON AIDE (LIEN WEB vers ENT)
with c2:
    with st.popover("❓ Aide", use_container_width=True):
        st.markdown("### 📚 Centre de Ressources")
        st.info("Besoin d'un mémo ou d'un cours ?")
        # LIEN MIS À JOUR AVEC L'ADRESSE ENT AUVERGNE-RHÔNE-ALPES
        st.link_button("📂 Accéder aux Cours (ENT)", "https://cas.ent.auvergnerhonealpes.fr/login?service=https%3A%2F%2Fglieres.ent.auvergnerhonealpes.fr%2Fsg.do%3FPROC%3DPAGE_ACCUEIL")
        st.markdown("---")
        st.caption("En cas de problème technique, contactez votre professeur.")

# BOUTON NOTIFICATIONS
with c3:
    with st.popover("🔔 Notif.", use_container_width=True):
        st.markdown("### 📜 Historique")
        if not st.session_state.notifications:
            st.caption("Aucune notification.")
        else:
            for note in st.session_state.notifications[:10]:
                st.text(f"• {note}")

# BOUTON PROFIL
with c4:
    st.button(user_label, disabled=True, use_container_width=True)

st.markdown("<hr style='margin: 0 0 20px 0;'>", unsafe_allow_html=True)

# --- CHAT CENTRAL ---
for i, msg in enumerate(st.session_state.messages):
    avatar = BOT_AVATAR if msg["role"] == "assistant" else "🧑‍🎓"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])
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

# --- FOOTER ---
st.markdown('<div class="fixed-footer">Agence Pro\'AGOrA - Environnement Pédagogique Sécurisé - Données Fictives Uniquement</div>', unsafe_allow_html=True)

# --- INPUT & LOGIC ---
if user_input := st.chat_input("Votre réponse..."):
    if not student_name:
        st.toast("Identifiez-vous dans le menu.", icon="👤")
    else:
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.rerun()

if st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant", avatar=BOT_AVATAR):
        with st.spinner("Analyse..."):
            sys = SYSTEM_PROMPT
            if st.session_state.get("mode_simple"): sys += " UTILISE DES MOTS SIMPLES."
            msgs = [{"role": "system", "content": sys}] + st.session_state.messages[-6:]
            resp, _ = query_groq_with_rotation(msgs)
            if not resp: resp = "Erreur technique."
            st.markdown(resp)
            st.session_state.messages.append({"role": "assistant", "content": resp})
            if st.session_state.get("mode_audio"): st.rerun()
