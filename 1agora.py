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
    initial_sidebar_state="auto"
)

# --- 2. GESTION ÉTAT ---
if "messages" not in st.session_state: st.session_state.messages = []
if "logs" not in st.session_state: st.session_state.logs = []
if "notifications" not in st.session_state: st.session_state.notifications = ["Bienvenue."]
if "current_context_doc" not in st.session_state: st.session_state.current_context_doc = None
# Variables pour le menu
if "selected_theme" not in st.session_state: st.session_state.selected_theme = None
if "selected_dossier" not in st.session_state: st.session_state.selected_dossier = None

# --- 3. OUTILS IMAGE ---
def img_to_base64(img_path):
    if os.path.exists(img_path):
        with open(img_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

# --- 4. STYLE & CSS (MOBILE FIRST) ---
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

    /* --- CORRECTION HEADER MOBILE --- */
    header {{
        background-color: transparent !important;
    }}
    [data-testid="stHeader"] {{
        background-color: rgba(255, 255, 255, 0.95);
    }}
    
    /* La flèche du menu (Sidebar toggle) */
    [data-testid="stSidebarCollapsedControl"] {{
        color: #1A73E8 !important;
        font-weight: bold;
    }}

    /* NAVBAR PERSONNALISÉE */
    .navbar-container {{
        display: flex;
        align-items: center;
        background-color: white;
        padding: 10px 5px;
        border-bottom: 1px solid #E0E0E0;
        margin-bottom: 10px;
        min-height: 60px;
    }}

    /* BOUTONS NAVBAR */
    div[data-testid="stHorizontalBlock"] button {{
        background-color: transparent;
        border: none;
        color: #5F6368;
        font-weight: 500;
        padding: 0 5px;
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

    /* BOUTON PRIMAIRE */
    button[kind="primary"] {{
        background: linear-gradient(135deg, #0F9D58 0%, #00C9FF 100%);
        color: white !important;
        border: none;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        width: 100%;
    }}

    /* CHAT */
    [data-testid="stChatMessage"] {{
        padding: 1rem;
        border-radius: 12px;
        margin-bottom: 0.5rem;
    }}
    /* Assistant */
    [data-testid="stChatMessage"][data-testid="assistant"] {{
        background-color: #FFFFFF;
        border: 1px solid #E0E0E0;
    }}
    /* Élève */
    [data-testid="stChatMessage"][data-testid="user"] {{
        background-color: #E3F2FD;
        border: none;
    }}
    /* Avatars */
    [data-testid="stChatMessageAvatar"] img {{
        border-radius: 50%;
        object-fit: cover;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }}

    /* --- FOOTER FIXE --- */
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
        box-shadow: 0 -2px 5px rgba(0,0,0,0.1);
    }}
    [data-testid="stBottom"] {{ bottom: 40px !important; padding-bottom: 10px; }}
    
    /* CARTE D'ACCUEIL (MOBILE) */
    .welcome-card {{
        background-color: #F8F9FA;
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        border: 1px solid #E0E0E0;
        margin-bottom: 20px;
    }}

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

# --- 7. DONNÉES MÉTIER ---
DB_PREMIERE = {
    "RESSOURCES HUMAINES": {
        "Recrutement": {
            "competence": "COMPÉTENCE : Définir le Profil de poste, Rédiger l'annonce d'embauche, Trier des CV.",
            "doc": {
                "type": "Fiche de Poste",
                "titre": "Assistant(e) Commercial(e) (H/F)",
                "contexte": "La PME 'EcoBat' (Bâtiment écologique, 45 salariés) cherche à renforcer son équipe commerciale.",
                "missions": ["Accueil clients.", "Suivi des devis.", "Relance impayés."],
                "profil": "Bac Pro AGOrA, organisé(e), bon relationnel.",
                "lien_titre": "Fiche métier (ONISEP)",
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
1. SOURCES : Ajoute "📎 Source : [Nom]" quand tu donnes une info.
2. PÉDAGOGIE : Si l'élève bloque, donne un indice.
3. CONTEXTE : Utilise les infos de la mission (Fiche poste, Entreprise).

SÉCURITÉ : Données réelles -> STOP.
"""

INITIAL_MESSAGE = """
👋 **Bonjour.**

Bienvenue à l'Agence **Pro'AGOrA**.
Veuillez lancer votre mission ci-dessous.
"""

# --- 9. FONCTIONS DE LANCEMENT ---
def lancer_mission_centrale(theme, dossier, prenom):
    st.session_state.selected_theme = theme
    st.session_state.selected_dossier = dossier
    
    data = DB_PREMIERE[theme][dossier]
    if isinstance(data, str):
        competence = data
        st.session_state.current_context_doc = None
    else:
        competence = data.get("competence", "")
        st.session_state.current_context_doc = data.get("doc", None)

    st.session_state.messages = []
    
    contexte_ia = ""
    if st.session_state.current_context_doc:
        doc = st.session_state.current_context_doc
        contexte_ia = f"DÉTAILS DU CAS : Poste {doc['titre']} - {doc.get('contexte', '')}"

    prompt = f"""
    CONTEXTE : Démarrage mission '{dossier}' par l'élève {prenom}.
    COMPÉTENCE : {competence}
    {contexte_ia}
    ACTION : Incarne le responsable. Accueille l'élève, donne le contexte et la 1ère consigne.
    """
    
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}]
    with st.spinner("Initialisation..."):
        resp, _ = query_groq_with_rotation(msgs)
        st.session_state.messages.append({"role": "assistant", "content": resp})
    add_notification(f"Mission lancée : {dossier}")

# --- 10. INTERFACE GRAPHIQUE ---

# --- DÉFINITION UTILISATEUR (CORRECTIF) ---
# On récupère le prénom soit de la sidebar, soit du centre, soit vide
current_user_name = st.session_state.get("name_sidebar") or st.session_state.get("name_center")
user_label = f"👤 {current_user_name}" if current_user_name else "👤 Invité"

LOGO_LYCEE = "logo_lycee.png"
LOGO_AGORA = "logo_agora.png"
BOT_AVATAR = LOGO_AGORA if os.path.exists(LOGO_AGORA) else "🤖"

# --- SIDEBAR (Menu Complet) ---
with st.sidebar:
    if os.path.exists(LOGO_LYCEE): st.image(LOGO_LYCEE, width=100)
    else: st.header("Lycée Pro")
    
    st.info("🔒 **Espace Sécurisé** : Données fictives.")
    
    # Champ Prénom Sidebar
    sidebar_name = st.text_input("Votre Prénom (Menu)", key="name_sidebar")
    
    st.subheader("📂 Changer de Mission")
    sb_theme = st.selectbox("Thème", list(DB_PREMIERE.keys()), key="sb_theme")
    sb_dossier = st.selectbox("Dossier", list(DB_PREMIERE[sb_theme].keys()), key="sb_dossier")
    
    if st.button("RELANCER LA MISSION", type="primary", use_container_width=True):
        if sidebar_name:
            lancer_mission_centrale(sb_theme, sb_dossier, sidebar_name)
            st.rerun()
        else:
            st.warning("Prénom requis")

    with st.expander("🛠️ Options"):
        st.checkbox("Mode DYS", key="mode_dys")
        st.checkbox("Audio", key="mode_audio")
        st.checkbox("Simplifié", key="mode_simple")
        
    uploaded_file = st.file_uploader("Rendre un travail", type=['docx'])
    if uploaded_file and sidebar_name:
        if st.button("Envoyer à la correction"):
            txt = extract_text_from_docx(uploaded_file)
            st.session_state.messages.append({"role": "user", "content": f"PROPOSITION : {txt}"})
            st.rerun()
    
    st.markdown("---")
    
    # --- BOUTON SAUVEGARDE (Réintégré) ---
    if len(st.session_state.messages) > 1:
        chat_df = pd.DataFrame(st.session_state.messages)
        csv_data = chat_df.to_csv(index=False).encode('utf-8')
        
        safe_name = sidebar_name if sidebar_name else st.session_state.get("name_center", "anonyme")
        date_str = datetime.now().strftime("%d%m_%H%M")
        file_name = f"suivi_agora_{safe_name}_{date_str}.csv"
        
        st.download_button(
            label="💾 Sauvegarder (CSV)",
            data=csv_data,
            file_name=file_name,
            mime="text/csv",
            use_container_width=True,
            help="Garder une trace de l'échange"
        )
    
    if st.button("🗑️ Reset", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# --- HEADER VISUEL ---
c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 1])
with c1:
    logo_html = ""
    if os.path.exists(LOGO_AGORA):
        b64 = img_to_base64(LOGO_AGORA)
        logo_html = f'<img src="data:image/png;base64,{b64}" style="height:40px; margin-right:10px;">'
    st.markdown(f"""<div style="display:flex; align-items:center; white-space:nowrap; overflow:hidden;">{logo_html}<div><div class="header-title" style="font-weight:bold; color:#202124;">Agence Pro'AGOrA</div><div class="header-subtitle" style="color:#5F6368;">Superviseur IA v2.0</div></div></div>""", unsafe_allow_html=True)

# Boutons Header (Ressources)
with c2:
    if st.session_state.get("current_context_doc"):
        doc = st.session_state.current_context_doc
        with st.popover(f"📄 {doc['type']}", use_container_width=True):
            st.markdown(f"### {doc['titre']}")
            st.info(doc.get('contexte', ''))
            st.markdown("**Missions principales :**")
            for m in doc.get('missions', []):
                st.markdown(f"- {m}")
            st.markdown(f"**Profil recherché :** {doc.get('profil', '')}")
            st.markdown("---")
            if 'lien_url' in doc: st.link_button(doc.get('lien_titre', 'En savoir plus'), doc['lien_url'])

with c3:
    with st.popover("ℹ️ Métiers", use_container_width=True):
        st.markdown("**👩‍💼 Assistant(e) Gestion**\n*Administratif, accueil.*")
        st.markdown("**👥 Assistant(e) RH**\n*Contrats, paie.*")
        st.link_button("🔗 ONISEP", "https://www.onisep.fr/metiers")

with c4:
    with st.popover("❓ Aide", use_container_width=True):
        st.link_button("📂 ENT", "https://cas.ent.auvergnerhonealpes.fr/login?service=https%3A%2F%2Fglieres.ent.auvergnerhonealpes.fr%2Fsg.do%3FPROC%3DPAGE_ACCUEIL")

with c5:
    # Correction NameError : user_label est maintenant défini AVANT
    st.button(f"👤", help=user_label, disabled=True, use_container_width=True)

st.markdown("<hr style='margin: 0 0 10px 0;'>", unsafe_allow_html=True)

# --- PAGE D'ACCUEIL (SI PAS DE MESSAGE) ---
if not st.session_state.messages:
    
    st.markdown("""
    <div class="welcome-card">
        <h3>👋 Bienvenue à l'Agence !</h3>
        <p>Configure ta mission ci-dessous pour commencer.</p>
    </div>
    """, unsafe_allow_html=True)
    
    c_nom, c_btn = st.columns([2,1])
    name_input = c_nom.text_input("Ton Prénom", key="name_center")
    
    col_th, col_dos = st.columns(2)
    theme_center = col_th.selectbox("Choisis ton Thème", list(DB_PREMIERE.keys()), key="center_theme")
    dossier_center = col_dos.selectbox("Choisis ta Mission", list(DB_PREMIERE[theme_center].keys()), key="center_dossier")
    
    if st.button("🚀 COMMENCER LA MISSION", type="primary", use_container_width=True):
        if name_input:
            lancer_mission_centrale(theme_center, dossier_center, name_input)
            st.rerun()
        else:
            st.toast("Entre ton prénom pour valider.", icon="✍️")

# --- CHAT CENTRAL (SI MESSAGE) ---
else:
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

    # INPUT
    if user_input := st.chat_input("Votre réponse..."):
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.rerun()

    # REPONSE IA
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        with st.chat_message("assistant", avatar=BOT_AVATAR):
            with st.spinner("..."):
                sys = SYSTEM_PROMPT
                if st.session_state.get("mode_simple"): sys += " UTILISE DES MOTS SIMPLES."
                if st.session_state.get("current_context_doc"):
                    sys += f"\nCONTEXTE : {st.session_state.current_context_doc['titre']}"

                msgs = [{"role": "system", "content": sys}] + st.session_state.messages[-6:]
                resp, _ = query_groq_with_rotation(msgs)
                if not resp: resp = "Erreur technique."
                st.markdown(resp)
                st.session_state.messages.append({"role": "assistant", "content": resp})
                if st.session_state.get("mode_audio"): st.rerun()

# Footer
st.markdown('<div class="fixed-footer">Agence Pro\'AGOrA - Données Fictives Uniquement</div>', unsafe_allow_html=True)
