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
if "notifications" not in st.session_state: st.session_state.notifications = ["Système prêt."]
if "current_context_doc" not in st.session_state: st.session_state.current_context_doc = None
if "pgi_data" not in st.session_state: st.session_state.pgi_data = None # Pour le simulateur PGI

# GAMIFICATION
if "xp" not in st.session_state: st.session_state.xp = 0
if "grade" not in st.session_state: st.session_state.grade = "👶 Stagiaire"

GRADES = {
    0: "👶 Stagiaire",
    100: "👦 Assistant(e) Junior",
    300: "👨‍💼 Assistant(e) Confirmé(e)",
    600: "👩‍💻 Responsable de Pôle",
    1000: "👑 Directeur(trice)"
}

def update_xp(amount):
    st.session_state.xp += amount
    current_grade = "👶 Stagiaire"
    for palier, titre in GRADES.items():
        if st.session_state.xp >= palier:
            current_grade = titre
    
    if current_grade != st.session_state.grade:
        st.session_state.grade = current_grade
        st.toast(f"PROMOTION ! Tu es maintenant {current_grade} !", icon="🎉")
        st.balloons()
    else:
        st.toast(f"+{amount} XP", icon="⭐")

# --- 3. VARIABLES DE CONTEXTE ---
VILLES_FRANCE = ["Lyon", "Bordeaux", "Lille", "Nantes", "Strasbourg", "Toulouse", "Marseille", "Nice", "Rennes", "Dijon"]
TYPES_ORGANISATIONS = ["Mairie", "Clinique", "Garage", "Association", "PME BTP", "Agence Immo", "Supermarché"]

# --- 4. OUTILS IMAGE ---
def img_to_base64(img_path):
    if os.path.exists(img_path):
        with open(img_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

# --- 5. STYLE & CSS ---
is_dys = st.session_state.get("mode_dys", False)
font_family = "'Verdana', sans-serif" if is_dys else "'Segoe UI', 'Roboto', Helvetica, Arial, sans-serif"
font_size = "18px" if is_dys else "16px"

st.markdown(f"""
<style>
    html, body, [class*="css"] {{
        font-family: {font_family} !important;
        font-size: {font_size};
        color: #202124;
        background-color: #FFFFFF;
    }}
    header {{background-color: transparent !important;}} 
    [data-testid="stHeader"] {{background-color: rgba(255, 255, 255, 0.95);}}
    .reportview-container .main .block-container {{padding-top: 1rem; max-width: 100%;}}
    
    /* PGI SIMULATEUR */
    .pgi-header {{
        background-color: #E8F0FE;
        border: 1px solid #1A73E8;
        color: #1A73E8;
        padding: 10px;
        border-radius: 8px 8px 0 0;
        font-weight: bold;
        font-size: 14px;
        margin-top: 10px;
    }}
    .pgi-container {{
        border: 1px solid #E0E0E0;
        border-top: none;
        border-radius: 0 0 8px 8px;
        padding: 10px;
        margin-bottom: 20px;
        background: #FAFAFA;
    }}

    /* BOUTONS */
    button[kind="primary"] {{
        background: linear-gradient(135deg, #0F9D58 0%, #00C9FF 100%);
        color: white !important;
        border: none;
    }}
    
    /* CHAT */
    [data-testid="stChatMessage"] {{
        padding: 1rem;
        border-radius: 12px;
        margin-bottom: 0.5rem;
    }}
    [data-testid="stChatMessage"][data-testid="assistant"] {{background-color: #FFFFFF; border: 1px solid #E0E0E0;}}
    [data-testid="stChatMessage"][data-testid="user"] {{background-color: #E3F2FD; border: none;}}
    [data-testid="stChatMessageAvatar"] img {{border-radius: 50%; object-fit: cover;}}

    .fixed-footer {{
        position: fixed;
        left: 0; bottom: 0; width: 100%;
        background: #323232; color: #FFF;
        text-align: center; padding: 6px; font-size: 11px; z-index: 99999;
    }}
    [data-testid="stBottom"] {{ bottom: 30px !important; padding-bottom: 10px; }}
</style>
""", unsafe_allow_html=True)

# --- 6. LOGIQUE API ---
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

# --- 7. OUTILS ---
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

# --- 8. DONNÉES & PGI SIMULATEUR ---
def generate_fake_pgi_data(mission_type):
    """Génère des données fictives pour le PGI selon la mission"""
    if "Recrutement" in mission_type or "RH" in mission_type:
        return pd.DataFrame({
            "Nom Candidat": ["Dubois", "Martin", "Kowalski", "Diallo"],
            "Prénom": ["Marie", "Lucas", "Anna", "Seydou"],
            "Diplôme": ["Bac Pro AGOrA", "BTS GPME", "CAP Vente", "Bac Pro Commerce"],
            "Expérience": ["Débutant", "2 ans", "5 ans", "Débutant"],
            "Statut": ["Reçu", "En attente", "Reçu", "Non retenu"]
        })
    elif "Vente" in mission_type or "Facturation" in mission_type:
        return pd.DataFrame({
            "Client": ["Garage Auto", "Mairie de Lyon", "Assoc. Sport", "Mme Dupont"],
            "Réf. Commande": ["CMD-001", "CMD-002", "CMD-003", "CMD-004"],
            "Montant HT": ["1500 €", "320 €", "45 €", "890 €"],
            "État": ["Facturée", "En cours", "Livrée", "Impayé"]
        })
    else: # Stock / Général
        return pd.DataFrame({
            "Réf. Produit": ["PAP-A4", "STY-BL", "CART-EN", "CLA-USB"],
            "Désignation": ["Papier A4 (500)", "Stylo Bleu", "Cartouche Encre", "Clé USB 32Go"],
            "Stock Réel": [12, 50, 2, 5],
            "Stock Alerte": [5, 20, 3, 2]
        })

DB_PREMIERE = {
    "RESSOURCES HUMAINES": {
        "Recrutement": {
            "competence": "COMPÉTENCE : Définir le Profil, Rédiger l'annonce, Sélectionner (Grille), Convoquer.",
            "procedure": """
            PHASE 1 : Analyse du besoin (Donne le contexte PME, l'élève doit lister 3 compétences clés).
            PHASE 2 : Rédaction de l'annonce (L'élève doit rédiger le corps de l'annonce).
            PHASE 3 : Sélection (Affiche le PGI Candidats, l'élève doit choisir 2 candidats à convoquer).
            PHASE 4 : Convocation (L'élève rédige le mail).
            """,
            "doc": {
                "type": "Fiche Poste", "titre": "Assistant(e) Commercial(e)", 
                "contexte": "Besoin urgent pour renforcer l'équipe.", 
                "missions": ["Accueil", "Devis", "Relance"],
                "lien_url": "https://www.onisep.fr/ressources/univers-metier/metiers/assistant-assistante-de-gestion-pme-pmi"
            }
        },
        "Intégration": {"competence": "COMPÉTENCE : Livret d'accueil, Parcours d'arrivée."},
        "Administratif RH": {"competence": "COMPÉTENCE : Contrat, Registre personnel, Congés."}
    },
    "RELATIONS PARTENAIRES": {
        "Vente": {
            "competence": "COMPÉTENCE : Devis, Facturation.",
            "procedure": "1. Devis -> 2. Commande -> 3. Facture -> 4. Relance."
        },
        "Déplacements": {"competence": "COMPÉTENCE : Réservation Train/Hôtel."}
    }
}

# --- 9. IA (PROMPT "INSPECTEUR") ---
SYSTEM_PROMPT = """
RÔLE : Tu es le Tuteur de stage (Professionnel exigeant).
MISSION : Guider l'élève vers la certification Bac Pro AGOrA.

CRITÈRES D'ÉVALUATION (À GARDER EN TÊTE) :
- Rigueur (Pas de fautes, données exactes).
- Professionnalisme (Ton adapté, vouvoiement).
- Utilisation des outils (L'élève utilise-t-il les données du PGI fourni ?).

CONSIGNES :
1. NE FAIS PAS À LA PLACE DE L'ÉLÈVE.
2. Si l'élève répond, valide ou corrige selon les critères : "Novice" (Trop vague), "Maîtrise" (Correct), "Expertise" (Parfait).
3. Utilise les données du PGI virtuel affiché à l'écran pour tes questions (ex: "Quel candidat as-tu retenu dans la liste ?").
4. Ajoute "📎 Source : [Nom]" pour les règles métier.

SÉCURITÉ : Données réelles -> STOP.
"""

INITIAL_MESSAGE = """
👋 **Bonjour.**

Bienvenue à l'Agence **Pro'AGOrA**.
Veuillez lancer votre mission via le menu.
"""

if not st.session_state.messages:
    st.session_state.messages.append({"role": "assistant", "content": INITIAL_MESSAGE})

def lancer_mission(prenom):
    lieu = random.choice(TYPES_ORGANISATIONS)
    ville = random.choice(VILLES_FRANCE)
    
    data = DB_PREMIERE[st.session_state.theme][st.session_state.dossier]
    
    if isinstance(data, str):
        competence = data
        procedure = "Standard"
        st.session_state.current_context_doc = None
    else:
        competence = data.get("competence", "")
        procedure = data.get("procedure", "Standard")
        st.session_state.current_context_doc = data.get("doc", None)

    # Génération du PGI
    st.session_state.pgi_data = generate_fake_pgi_data(st.session_state.dossier)
    
    st.session_state.messages = []
    
    contexte_ia = ""
    if st.session_state.current_context_doc:
        doc = st.session_state.current_context_doc
        contexte_ia = f"DOCUMENTS : Poste {doc['titre']} - Missions : {', '.join(doc.get('missions', []))}"

    prompt = f"""
    DÉMARRAGE STAGE : Élève {prenom}.
    LIEU : {lieu} à {ville}.
    MISSION : {st.session_state.dossier}.
    PROCÉDURE : {procedure}.
    {contexte_ia}
    
    ACTION :
    1. Accueille l'élève en tant que tuteur dans cette structure précise.
    2. Donne la situation pro.
    3. Donne la 1ère tâche.
    """
    
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}]
    with st.spinner("Préparation du dossier..."):
        resp, _ = query_groq_with_rotation(msgs)
        st.session_state.messages.append({"role": "assistant", "content": resp})
    add_notification(f"Mission lancée : {st.session_state.dossier}")

def generer_bilan_competences():
    """Génère un résumé pour la fiche CCF"""
    history = [m["content"] for m in st.session_state.messages if m["role"] == "user"]
    full_text = "\n".join(history[-10:]) # Analyse les 10 derniers échanges
    
    prompt_bilan = f"""
    Analyse ce travail d'élève :
    {full_text}
    
    Génère un 'Bilan pour Fiche CCF' court :
    1. Contexte (1 phrase).
    2. Activités réalisées.
    3. Outils mobilisés.
    4. Niveau estimé (Novice/Fonctionnel/Maîtrise).
    """
    msgs = [{"role": "system", "content": "Tu es un évaluateur."}, {"role": "user", "content": prompt_bilan}]
    return query_groq_with_rotation(msgs)[0]

# --- 10. INTERFACE ---

LOGO_LYCEE = "logo_lycee.png"
LOGO_AGORA = "logo_agora.png"
BOT_AVATAR = LOGO_AGORA if os.path.exists(LOGO_AGORA) else "🤖"

# --- SIDEBAR ---
with st.sidebar:
    if os.path.exists(LOGO_LYCEE): st.image(LOGO_LYCEE, width=100)
    else: st.header("Lycée Pro")
    
    st.markdown("---")
    
    # XP & GAMIFICATION
    st.markdown(f"### 🏆 {st.session_state.grade}")
    st.progress(min(st.session_state.xp / 1000, 1.0))
    st.caption(f"XP : {st.session_state.xp}")
    
    student_name = st.text_input("Prénom", placeholder="Ex: Camille")
    user_label = f"👤 {student_name}" if student_name else "👤 Invité"
    
    st.subheader("📂 Missions")
    st.session_state.theme = st.selectbox("Thème", list(DB_PREMIERE.keys()))
    st.session_state.dossier = st.selectbox("Dossier", list(DB_PREMIERE[st.session_state.theme].keys()))
    
    if st.button("LANCER", type="primary"):
        if student_name:
            lancer_mission(student_name)
            st.rerun()
        else:
            st.warning("Prénom requis")
    
    if st.button("✅ ÉTAPE VALIDÉE"):
        update_xp(10)
        st.rerun()

    # OUTILS FICHIER
    st.markdown("---")
    uploaded_file = st.file_uploader("Rendre un travail", type=['docx'])
    if uploaded_file and student_name:
        if st.button("Envoyer"):
            txt = extract_text_from_docx(uploaded_file)
            st.session_state.messages.append({"role": "user", "content": f"PROPOSITION : {txt}"})
            update_xp(20)
            st.rerun()
            
    # BILAN CCF (NOUVEAU)
    if st.button("📝 Générer Bilan CCF"):
        if len(st.session_state.messages) > 2:
            bilan = generer_bilan_competences()
            st.session_state.messages.append({"role": "assistant", "content": f"**BILAN AUTOMATIQUE :**\n\n{bilan}"})
            st.rerun()
        else:
            st.warning("Travaillez d'abord !")

    # SAUVEGARDE
    st.markdown("---")
    if len(st.session_state.messages) > 0:
        chat_df = pd.DataFrame(st.session_state.messages)
        csv_data = chat_df.to_csv(index=False).encode('utf-8')
        st.download_button("💾 Sauvegarder", csv_data, "agora_save.csv", "text/csv")
    
    if st.button("🗑️ Reset"):
        st.session_state.messages = [{"role": "assistant", "content": INITIAL_MESSAGE}]
        st.session_state.pgi_data = None
        st.session_state.current_context_doc = None
        st.rerun()

# --- HEADER ---
c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 1])
with c1:
    logo_html = ""
    if os.path.exists(LOGO_AGORA):
        b64 = img_to_base64(LOGO_AGORA)
        logo_html = f'<img src="data:image/png;base64,{b64}" style="height:45px; vertical-align:middle; margin-right:10px;">'
    st.markdown(f"""<div style="display:flex; align-items:center;">{logo_html}<div><div style="font-size:24px; font-weight:bold; color:#202124; line-height:1.2;">Agence Pro'AGOrA</div><div style="font-size:12px; color:#5F6368;">Superviseur IA v3.0 (Expert)</div></div></div>""", unsafe_allow_html=True)

# BOUTONS RESSOURCES
with c2:
    if st.session_state.get("current_context_doc"):
        doc = st.session_state.current_context_doc
        with st.popover(f"📄 {doc['type']}", use_container_width=True):
            st.markdown(f"### {doc['titre']}")
            st.info(doc.get('contexte', ''))
            st.markdown("**Missions :**")
            for m in doc.get('missions', []): st.markdown(f"- {m}")
            if 'lien_url' in doc: st.link_button("Fiche Métier", doc['lien_url'])

with c3:
    with st.popover("ℹ️ Métiers", use_container_width=True):
        st.link_button("🔗 ONISEP", "https://www.onisep.fr/metiers")

with c4:
    with st.popover("❓ Aide", use_container_width=True):
        st.link_button("📂 ENT", "https://cas.ent.auvergnerhonealpes.fr/login?service=https%3A%2F%2Fglieres.ent.auvergnerhonealpes.fr%2Fsg.do%3FPROC%3DPAGE_ACCUEIL")

with c5:
    st.button(f"👤", help=user_label, disabled=True, use_container_width=True)

st.markdown("<hr style='margin: 0 0 20px 0;'>", unsafe_allow_html=True)

# --- SIMULATEUR PGI (NOUVEAU) ---
if st.session_state.pgi_data is not None:
    st.markdown('<div class="pgi-header">🖥️ PGI - Espace de Gestion (Données Entreprise)</div>', unsafe_allow_html=True)
    with st.expander("Voir les données (Clients / Stocks / RH)", expanded=True):
        st.dataframe(st.session_state.pgi_data, use_container_width=True)

# --- CHAT ---
for i, msg in enumerate(st.session_state.messages):
    avatar = BOT_AVATAR if msg["role"] == "assistant" else "🧑‍🎓"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and HAS_AUDIO:
            if st.button("🔊", key=f"tts_{i}", help="Lire"):
                try:
                    tts = gTTS(clean_text_for_audio(msg["content"]), lang='fr')
                    buf = BytesIO()
                    tts.write_to_fp(buf)
                    st.audio(buf, format="audio/mp3", start_time=0)
                except: st.warning("Audio indisponible")

st.markdown("<br><br>", unsafe_allow_html=True)

# --- INPUT ---
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
                sys += f"\nCONTEXTE : {st.session_state.current_context_doc['titre']}."
            
            # Injection des données PGI dans le prompt pour que l'IA sache de quoi on parle
            if st.session_state.pgi_data is not None:
                sys += f"\nDONNÉES PGI DISPONIBLES : {st.session_state.pgi_data.to_string()}"

            msgs = [{"role": "system", "content": sys}] + st.session_state.messages[-6:]
            resp, _ = query_groq_with_rotation(msgs)
            if not resp: resp = "Erreur technique."
            st.markdown(resp)
            st.session_state.messages.append({"role": "assistant", "content": resp})
