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
if "notifications" not in st.session_state: st.session_state.notifications = ["Bienvenue."]
# Stockage du contexte métier actuel (Fiche de poste, Infos mission...)
if "current_context_doc" not in st.session_state: st.session_state.current_context_doc = None

# --- 3. OUTILS IMAGE ---
def img_to_base64(img_path):
    if os.path.exists(img_path):
        with open(img_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

# --- 4. STYLE & CSS ---
is_dys = st.session_state.get("mode_dys", False)
font_family = "'Verdana', sans-serif" if is_dys else "'Segoe UI', 'Roboto', Helvetica, Arial, sans-serif"
font_size = "18px" if is_dys else "16px"

st.markdown(f"""
<style>
    /* GLOBAL */
    html, body, [class*="css"] {{
        font-family: {font_family} !important;
        font-size: {font_size};
        color: #202124;
        background-color: #FFFFFF;
    }}

    /* HEADER CLEAN */
    header {{visibility: hidden;}} 
    .reportview-container .main .block-container {{
        padding-top: 1rem;
        max-width: 100%;
    }}

    /* NAVBAR */
    div[data-testid="stHorizontalBlock"] button {{
        background-color: transparent;
        border: none;
        color: #5F6368;
        font-weight: 500;
    }}
    div[data-testid="stHorizontalBlock"] button:hover {{
        color: #1A73E8;
        background-color: #F1F3F4;
    }}

    /* BOUTON CONTEXTE (Rouge/Actif) */
    .context-btn button {{
        color: #D93025 !important;
        font-weight: bold !important;
        border: 1px solid #FCE8E6 !important;
        background-color: #FEF7F6 !important;
    }}

    /* SIDEBAR */
    [data-testid="stSidebar"] {{
        background-color: #F8F9FA;
        border-right: 1px solid #E0E0E0;
    }}

    /* CHAT */
    [data-testid="stChatMessage"] {{
        padding: 1rem;
        border-radius: 12px;
        margin-bottom: 0.5rem;
    }}
    [data-testid="stChatMessage"][data-testid="assistant"] {{
        background-color: #FFFFFF;
        border: 1px solid #E0E0E0;
    }}
    [data-testid="stChatMessage"][data-testid="user"] {{
        background-color: #E3F2FD;
        border: none;
    }}
    [data-testid="stChatMessageAvatar"] img {{
        border-radius: 50%;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
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
    [data-testid="stBottom"] {{ bottom: 30px !important; padding-bottom: 10px; }}
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
        return text[:8000]
    except Exception as e: return str(e)

def clean_text_for_audio(text):
    text = re.sub(r'[\*_]{1,3}', '', text)
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'📎.*', '', text)
    return text

def add_notification(msg):
    ts = datetime.now().strftime("%H:%M")
    st.session_state.notifications.insert(0, f"{ts} - {msg}")

def log_interaction(student, role, content):
    st.session_state.logs.append({
        "Heure": datetime.now().strftime("%H:%M"),
        "User": student, "Role": role, "Msg": content[:50]
    })

# --- 7. DONNÉES MÉTIER RICHES ---
# Structure : "Nom": {"competence": "...", "doc": { ... }}
# Si "doc" est présent, un bouton "Fiche de Poste" apparaîtra.

DB_PREMIERE = {
    "RESSOURCES HUMAINES": {
        "Recrutement": {
            "competence": "COMPÉTENCE : Définir le Profil de poste, Rédiger l'annonce d'embauche, Trier des CV.",
            "doc": {
                "type": "Fiche de Poste",
                "titre": "Assistant(e) Commercial(e) (H/F)",
                "contexte": "La PME 'EcoBat' (Bâtiment écologique, 45 salariés) cherche à renforcer son équipe commerciale.",
                "missions": [
                    "Accueil téléphonique et physique des clients.",
                    "Rédaction et suivi des devis.",
                    "Mise à jour de la base de données clients.",
                    "Relance des impayés."
                ],
                "profil": "Bac Pro AGOrA, organisé(e), bon relationnel, maîtrise d'Excel.",
                "lien_titre": "Voir la fiche métier complète (ONISEP)",
                "lien_url": "https://www.onisep.fr/ressources/univers-metier/metiers/assistant-assistante-commercial-commerciale"
            }
        },
        "Intégration": {"competence": "COMPÉTENCE : Livret d'accueil, Parcours d'arrivée."},
        "Administratif RH": {"competence": "COMPÉTENCE : Contrat, Registre personnel, Congés."}
    },
    "GESTION DES ESPACES": {
        "Aménagement": {"competence": "COMPÉTENCE : Proposer un aménagement ergonomique."},
        "Numérique": {"competence": "COMPÉTENCE : Lister matériel et logiciels (RGPD)."},
        "Ressources": {"competence": "COMPÉTENCE : Gérer stocks et réservations."}
    },
    "RELATIONS PARTENAIRES": {
        "Vente": {"competence": "COMPÉTENCE : Devis, Négociation, Facturation."},
        "Réunions": {"competence": "COMPÉTENCE : Ordre du jour, Réservation, Compte-Rendu."},
        "Déplacements": {"competence": "COMPÉTENCE : Réservation Train/Hôtel, Ordre de Mission."}
    }
}

# --- 8. IA ---
SYSTEM_PROMPT = """
RÔLE : Tu es le Superviseur Virtuel de l'Agence Pro'AGOrA.
TON : Professionnel, bienveillant mais exigeant.
MISSION : Guider l'élève (Bac Pro) sans jamais faire le travail à sa place.

RÈGLES CLÉS :
1. SOURCES (TROMBONE) : Quand tu donnes une info, AJOUTE SYSTÉMATIQUEMENT une source à la fin.
   - "📎 Source : [Nom de la source]"
2. PÉDAGOGIE : Si l'élève est bloqué, donne-lui un indice.
3. CONTEXTE : Tu connais les détails de la mission (Fiche de poste, Entreprise) si elles sont fournies. Utilise-les.

SÉCURITÉ : Si données réelles (noms, tel) -> STOP et demande anonymisation.
FORMAT : Réponses aérées. Max 4 phrases.
"""

INITIAL_MESSAGE = """
👋 **Bonjour.**

Bienvenue à l'Agence **Pro'AGOrA**.
Veuillez sélectionner votre **Mission** à gauche.
"""

if not st.session_state.messages:
    st.session_state.messages.append({"role": "assistant", "content": INITIAL_MESSAGE})

def lancer_mission():
    # Récupération des données
    data = DB_PREMIERE[st.session_state.theme][st.session_state.dossier]
    
    # Gestion de la compatibilité (si ancienne structure sans dict)
    if isinstance(data, str):
        competence = data
        st.session_state.current_context_doc = None
    else:
        competence = data.get("competence", "")
        st.session_state.current_context_doc = data.get("doc", None)

    st.session_state.messages = []
    
    # Construction du Prompt de démarrage pour l'IA
    contexte_ia = ""
    if st.session_state.current_context_doc:
        doc = st.session_state.current_context_doc
        contexte_ia = f"""
        DÉTAILS DU CAS PRATIQUE (A UTILISER) :
        - Poste : {doc['titre']}
        - Contexte : {doc.get('contexte', '')}
        - Missions : {', '.join(doc.get('missions', []))}
        """

    prompt = f"""
    CONTEXTE : Démarrage mission '{st.session_state.dossier}'.
    COMPÉTENCE : {competence}
    {contexte_ia}
    ACTION : Incarne le responsable. Accueille l'élève, donne le contexte et la 1ère consigne.
    """
    
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}]
    with st.spinner("Initialisation..."):
        resp, _ = query_groq_with_rotation(msgs)
        st.session_state.messages.append({"role": "assistant", "content": resp})
    add_notification(f"Mission lancée : {st.session_state.dossier}")

# --- 9. INTERFACE ---

LOGO_LYCEE = "logo_lycee.png"
LOGO_AGORA = "logo_agora.png"
BOT_AVATAR = LOGO_AGORA if os.path.exists(LOGO_AGORA) else "🤖"

# --- SIDEBAR ---
with st.sidebar:
    if os.path.exists(LOGO_LYCEE): st.image(LOGO_LYCEE, width=100)
    else: st.header("Lycée Pro")
    
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
    if st.button("🗑️ Reset"):
        st.session_state.messages = [{"role": "assistant", "content": INITIAL_MESSAGE}]
        st.session_state.current_context_doc = None
        st.rerun()

# --- HEADER FONCTIONNEL ---
c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 1]) # Ajout d'une colonne pour le bouton Fiche

with c1:
    logo_html = ""
    if os.path.exists(LOGO_AGORA):
        b64 = img_to_base64(LOGO_AGORA)
        logo_html = f'<img src="data:image/png;base64,{b64}" style="height:45px; vertical-align:middle; margin-right:10px;">'
    st.markdown(f"""<div style="display:flex; align-items:center;">{logo_html}<div><div style="font-size:24px; font-weight:bold; color:#202124; line-height:1.2;">Agence Pro'AGOrA</div><div style="font-size:12px; color:#5F6368;">Superviseur IA v1.7</div></div></div>""", unsafe_allow_html=True)

# BOUTON CONTEXTE MÉTIER (S'affiche seulement si une fiche existe)
with c2:
    if st.session_state.get("current_context_doc"):
        doc = st.session_state.current_context_doc
        # On utilise un container pour le style "Bouton Rouge/Important"
        with st.popover(f"📄 {doc['type']}", use_container_width=True):
            st.markdown(f"### {doc['titre']}")
            st.info(doc.get('contexte', ''))
            st.markdown("**Missions principales :**")
            for m in doc.get('missions', []):
                st.markdown(f"- {m}")
            st.markdown(f"**Profil recherché :** {doc.get('profil', '')}")
            st.markdown("---")
            if 'lien_url' in doc:
                st.link_button(doc.get('lien_titre', 'En savoir plus'), doc['lien_url'])

# BOUTON AIDE
with c3:
    with st.popover("❓ Aide", use_container_width=True):
        st.markdown("### 📚 Ressources")
        st.link_button("📂 Accéder aux Cours (ENT)", "https://cas.ent.auvergnerhonealpes.fr/login?service=https%3A%2F%2Fglieres.ent.auvergnerhonealpes.fr%2Fsg.do%3FPROC%3DPAGE_ACCUEIL")
        st.link_button("🔗 Fiches Métiers (ONISEP)", "https://www.onisep.fr/metiers")

# BOUTON NOTIF
with c4:
    with st.popover("🔔 Notif.", use_container_width=True):
        st.caption("Historique :")
        for note in st.session_state.notifications[:5]:
            st.text(f"• {note}")

# BOUTON PROFIL
with c5:
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

# --- FOOTER & INPUT ---
st.markdown('<div class="fixed-footer">Agence Pro\'AGOrA - Environnement Pédagogique Sécurisé - Données Fictives Uniquement</div>', unsafe_allow_html=True)

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
            # Injection du contexte métier si existant
            if st.session_state.get("current_context_doc"):
                sys += f"\nCONTEXTE MISSION : Tu recrutes pour le poste de {st.session_state.current_context_doc['titre']}."

            msgs = [{"role": "system", "content": sys}] + st.session_state.messages[-6:]
            resp, _ = query_groq_with_rotation(msgs)
            if not resp: resp = "Erreur technique."
            st.markdown(resp)
            st.session_state.messages.append({"role": "assistant", "content": resp})
            if st.session_state.get("mode_audio"): st.rerun()
