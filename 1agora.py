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
    header {{background-color: transparent !important;}} 
    [data-testid="stHeader"] {{background-color: rgba(255, 255, 255, 0.95);}}
    
    .reportview-container .main .block-container {{
        padding-top: 1rem;
        max-width: 100%;
    }}

    /* NAVBAR */
    .navbar-container {{
        display: flex;
        align-items: center;
        background-color: white;
        padding: 10px 20px;
        border-bottom: 1px solid #E0E0E0;
        margin-bottom: 10px;
        height: 80px;
    }}

    /* BOUTON PRIMAIRE */
    button[kind="primary"] {{
        background: linear-gradient(135deg, #0F9D58 0%, #00C9FF 100%);
        color: white !important;
        border: none;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        width: 100%;
    }}

    /* CHAT OPTIMISÉ */
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
        object-fit: cover;
    }}

    /* FOOTER */
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

# --- 7. DONNÉES MÉTIER (CORRIGÉES AVEC PROCÉDURES) ---
# J'ai ajouté un champ "procedure" pour guider l'IA
DB_PREMIERE = {
    "RESSOURCES HUMAINES": {
        "Recrutement": {
            "competence": "COMPÉTENCE : Définir le Profil, Rédiger l'annonce, Sélectionner (Grille), Convoquer.",
            "procedure": "1. Analyse du besoin (Fiche de poste) -> 2. Choix des canaux de diffusion -> 3. Création de la Grille de sélection -> 4. Rédaction du Mail de convocation.",
            "doc": {
                "type": "Fiche de Poste",
                "titre": "Assistant(e) Commercial(e) (H/F)",
                "contexte": "Garage 'AutoPlus' (Lyon), 15 salariés. Besoin urgent suite à un départ.",
                "missions": ["Accueil client", "Facturation", "Gestion planning atelier"],
                "profil": "Bac Pro, bon contact, rigoureux.",
                "lien_titre": "Fiche Métier (ONISEP)",
                "lien_url": "https://www.onisep.fr/ressources/univers-metier/metiers/assistant-assistante-commercial-commerciale"
            }
        },
        "Intégration": {
            "competence": "COMPÉTENCE : Livret d'accueil, Parcours d'arrivée.",
            "procedure": "1. Préparation du poste de travail -> 2. Kit d'accueil -> 3. Planning de la 1ère journée."
        },
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

# --- 8. IA (PROMPT EXPERT BAC PRO) ---
SYSTEM_PROMPT = """
RÔLE : Tu es le Superviseur Virtuel de l'Agence Pro'AGOrA.
TON : Professionnel, directif mais bienveillant.
MISSION : Guider l'élève dans la réalisation de tâches professionnelles CONCRÈTES.

⛔ CE QUE TU NE DOIS PAS FAIRE :
- Ne pose pas de questions de cours théoriques ("C'est quoi le recrutement ?").
- Ne demande pas à l'élève d'inventer des choses qu'il ne sait pas.

✅ CE QUE TU DOIS FAIRE :
1. DONNER LE CADRE : Au début, donne toujours le contexte précis (Entreprise, Ville, Problème à résoudre).
2. SUIVRE LA PROCÉDURE : Guide l'élève étape par étape selon le référentiel Bac Pro AGOrA.
   - Ex pour Recrutement : D'abord on valide le profil, ensuite on fait la grille, enfin on convoque.
3. DEMANDER DES ÉCRITS PROS : Demande à l'élève de rédiger le mail, de lister les critères de la grille, ou de rédiger l'annonce.
4. SOURCES : Ajoute "📎 Source : [Nom]" pour les notions clés.

SÉCURITÉ : Données réelles -> STOP.
"""

INITIAL_MESSAGE = """
👋 **Bonjour.**

Bienvenue à l'Agence **Pro'AGOrA**.
Veuillez sélectionner votre **Mission** à gauche pour commencer.
"""

if not st.session_state.messages:
    st.session_state.messages.append({"role": "assistant", "content": INITIAL_MESSAGE})

def lancer_mission(prenom):
    # Récupération Données
    data = DB_PREMIERE[st.session_state.theme][st.session_state.dossier]
    
    if isinstance(data, str):
        competence = data
        procedure = "Suivre la procédure standard AGOrA."
        st.session_state.current_context_doc = None
    else:
        competence = data.get("competence", "")
        procedure = data.get("procedure", "Procédure standard.")
        st.session_state.current_context_doc = data.get("doc", None)

    st.session_state.messages = []
    
    contexte_ia = ""
    if st.session_state.current_context_doc:
        doc = st.session_state.current_context_doc
        contexte_ia = f"""
        CONTEXTE SCÉNARIO :
        - Entreprise : {doc.get('contexte', 'PME locale')}
        - Poste concerné : {doc['titre']}
        - Missions du poste : {', '.join(doc.get('missions', []))}
        """

    prompt = f"""
    DÉMARRAGE MISSION pour l'élève {prenom}.
    DOSSIER : '{st.session_state.dossier}'.
    PROCÉDURE À SUIVRE : {procedure}
    {contexte_ia}
    
    ACTION ATTENDUE :
    1. Accueille l'élève en tant que Responsable du service.
    2. Donne-lui le contexte précis (Lieu, Entreprise).
    3. Donne la PREMIÈRE consigne concrète (ex: "Prends connaissance de la fiche de poste ci-jointe et liste-moi les 3 critères impératifs pour la grille de sélection").
    """
    
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}]
    with st.spinner("Préparation du dossier..."):
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
    
    # GAMIFICATION & IDENTITÉ
    student_name = st.text_input("Prénom", placeholder="Ex: Camille")
    user_label = f"👤 {student_name}" if student_name else "👤 Invité"
    
    st.subheader("📂 Missions")
    st.session_state.theme = st.selectbox("Thème", list(DB_PREMIERE.keys()))
    st.session_state.dossier = st.selectbox("Dossier", list(DB_PREMIERE[st.session_state.theme].keys()))
    
    if st.button("LANCER LA MISSION", type="primary"):
        if student_name:
            lancer_mission(student_name)
            st.rerun()
        else:
            st.warning("Prénom requis")

    # BOUTON SAUVEGARDE (TOUJOURS VISIBLE MAIS GRISE SI VIDE)
    st.markdown("---")
    csv_data = ""
    disabled_save = True
    if len(st.session_state.messages) > 1:
        chat_df = pd.DataFrame(st.session_state.messages)
        csv_data = chat_df.to_csv(index=False).encode('utf-8')
        disabled_save = False
        
    date_str = datetime.now().strftime("%d%m_%H%M")
    file_name = f"agora_{student_name}_{date_str}.csv"
    
    st.download_button(
        label="💾 Sauvegarder mon travail",
        data=csv_data,
        file_name=file_name,
        mime="text/csv",
        disabled=disabled_save,
        help="Enregistre la conversation pour la montrer au prof."
    )
    
    if st.button("🗑️ Reset"):
        st.session_state.messages = [{"role": "assistant", "content": INITIAL_MESSAGE}]
        st.session_state.current_context_doc = None
        st.rerun()

# --- HEADER ---
c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 1])

with c1:
    logo_html = ""
    if os.path.exists(LOGO_AGORA):
        b64 = img_to_base64(LOGO_AGORA)
        logo_html = f'<img src="data:image/png;base64,{b64}" style="height:45px; vertical-align:middle; margin-right:10px;">'
    st.markdown(f"""<div style="display:flex; align-items:center;">{logo_html}<div><div style="font-size:24px; font-weight:bold; color:#202124; line-height:1.2;">Agence Pro'AGOrA</div><div style="font-size:12px; color:#5F6368;">Superviseur IA v2.2</div></div></div>""", unsafe_allow_html=True)

with c2:
    if st.session_state.get("current_context_doc"):
        doc = st.session_state.current_context_doc
        with st.popover(f"📄 {doc['type']}", use_container_width=True):
            st.markdown(f"### {doc['titre']}")
            st.info(doc.get('contexte', ''))
            st.markdown("**Missions :**")
            for m in doc.get('missions', []): st.markdown(f"- {m}")
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
    st.button(f"👤", help=user_label, disabled=True, use_container_width=True)

st.markdown("<hr style='margin: 0 0 20px 0;'>", unsafe_allow_html=True)

# --- CHAT ---
for i, msg in enumerate(st.session_state.messages):
    avatar = BOT_AVATAR if msg["role"] == "assistant" else "🧑‍🎓"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and HAS_AUDIO:
            # Petit bouton audio discret sous chaque message assistant
            if st.button("🔊", key=f"tts_{i}", help="Lire ce message"):
                try:
                    tts = gTTS(clean_text_for_audio(msg["content"]), lang='fr')
                    buf = BytesIO()
                    tts.write_to_fp(buf)
                    st.audio(buf, format="audio/mp3", start_time=0)
                except: st.warning("Audio indisponible")

st.markdown("<br><br>", unsafe_allow_html=True)

# --- FOOTER & INPUT ---
st.markdown('<div class="fixed-footer">Agence Pro\'AGOrA - Données Fictives Uniquement</div>', unsafe_allow_html=True)

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
            if st.session_state.get("current_context_doc"):
                sys += f"\nCONTEXTE MISSION : {st.session_state.current_context_doc['titre']}."

            msgs = [{"role": "system", "content": sys}] + st.session_state.messages[-6:]
            resp, _ = query_groq_with_rotation(msgs)
            if not resp: resp = "Erreur technique."
            st.markdown(resp)
            st.session_state.messages.append({"role": "assistant", "content": resp})
            # Pas de rerun auto pour l'audio ici, l'élève clique s'il veut écouter
