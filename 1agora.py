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
if "pgi_data" not in st.session_state: st.session_state.pgi_data = None

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

# --- 3. LISTES DE DONNÉES (POUR PGI) ---
# On garde des listes pour varier les noms, mais les scénarios seront fixes sur la structure.
NOMS = ["Martin", "Bernard", "Thomas", "Petit", "Robert", "Richard", "Durand", "Dubois", "Moreau", "Laurent"]
VILLES = ["Lyon", "Bordeaux", "Lille", "Nantes", "Toulouse"]

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
    
    /* PGI SIMULATEUR STYLE */
    .pgi-container {{
        border: 1px solid #dfe1e5;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 20px;
        background-color: #f8f9fa;
    }}
    .pgi-title {{
        color: #1a73e8;
        font-weight: bold;
        font-size: 14px;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        gap: 10px;
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
                        messages=messages, model=model, temperature=0.3, max_tokens=1024 # Température basse pour rigueur
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

# --- 8. CONFIGURATION DES SCÉNARIOS (TYPE LIVRE/BAC) ---
# Chaque scénario a un "Problème" spécifique caché dans les données PGI

SCENARIOS = {
    "RELATIONS PARTENAIRES": {
        "Traitement de Commande": {
            "contexte": "Vous êtes assistant(e) chez 'BuroPlus'. Un client fidèle, M. Martin, a passé commande mais un article est en rupture.",
            "consigne_1": "Consultez le PGI ci-dessous pour vérifier l'état des stocks de la commande de M. Martin. Identifiez le problème.",
            "pgi_mode": "commande_problematique",
            "procedure": "1. Vérification Stock -> 2. Identification Rupture -> 3. Mail d'information client (Proposition équivalent ou délai)."
        },
        "Relance Facture": {
            "contexte": "Vous travaillez au service comptable de 'Garage Auto'. Plusieurs factures sont en retard.",
            "consigne_1": "Repérez dans le PGI le client qui a la facture impayée la plus ancienne. Quel est le montant et la date ?",
            "pgi_mode": "factures_retard",
            "procedure": "1. Identification Impayé -> 2. Calcul du retard -> 3. Rédaction Mail de relance niveau 1 (Courtois)."
        }
    },
    "RESSOURCES HUMAINES": {
        "Sélection Candidat": {
            "contexte": "La Mairie recrute un agent d'accueil. Profil exigé : Bac Pro + Anglais. 4 candidats ont postulé.",
            "consigne_1": "Analysez le tableau des candidats dans le PGI. Lequel correspond exactement aux critères (Bac Pro + Anglais) ? Justifiez.",
            "pgi_mode": "candidats_tri",
            "procedure": "1. Analyse des critères -> 2. Sélection du bon profil -> 3. Mail de convocation."
        },
        "Organisation Déplacement": {
            "contexte": "M. Le Directeur doit aller à Paris le 15 juin pour une réunion à 14h00. Budget max : 100€.",
            "consigne_1": "Consultez les options de transport dans le PGI. Quel train permet d'arriver à temps tout en respectant le budget ?",
            "pgi_mode": "transport_options",
            "procedure": "1. Analyse contraintes (Heure/Budget) -> 2. Choix solution -> 3. Rédaction Note de synthèse."
        }
    }
}

# --- 9. GÉNÉRATEUR DE DONNÉES PGI (DONNÉES "PREUVES") ---
def get_pgi_data(mode):
    """Génère des données qui contiennent LA réponse au problème posé"""
    
    if mode == "commande_problematique":
        return pd.DataFrame([
            {"Réf": "STY-001", "Article": "Stylo Bille Bleu", "Qté Commandée": 50, "Stock Réel": 200, "Statut": "OK"},
            {"Réf": "PAP-A4", "Article": "Papier A4 80g", "Qté Commandée": 10, "Stock Réel": 100, "Statut": "OK"},
            {"Réf": "IMP-L", "Article": "Imprimante Laser", "Qté Commandée": 1, "Stock Réel": 0, "Statut": "RUPTURE"},
        ])
    
    elif mode == "factures_retard":
        return pd.DataFrame([
            {"Client": "M. Dupont", "Facture": "F-202", "Date": "01/11/2024", "Montant": "150 €", "État": "Réglée"},
            {"Client": "Sarl Durand", "Facture": "F-203", "Date": "15/10/2024", "Montant": "1200 €", "État": "En attente"},
            {"Client": "Assoc. Sport", "Facture": "F-199", "Date": "01/09/2024", "Montant": "450 €", "État": "NON PAYÉE (Retard critique)"},
        ])
        
    elif mode == "candidats_tri":
        return pd.DataFrame([
            {"Nom": "M. ALAMI", "Diplôme": "CAP Vente", "Langue": "Anglais A2", "Expérience": "5 ans"},
            {"Nom": "Mme BERNARD", "Diplôme": "Bac Pro AGOrA", "Langue": "Anglais B2 (Courant)", "Expérience": "Débutant"},
            {"Nom": "M. PETIT", "Diplôme": "Bac Général", "Langue": "Espagnol", "Expérience": "Aucune"},
            {"Nom": "Mme ROUX", "Diplôme": "BTS SAM", "Langue": "Anglais A1", "Expérience": "10 ans (Trop qualifiée)"},
        ])
        
    elif mode == "transport_options":
        return pd.DataFrame([
            {"Train": "TGV 6602", "Départ": "08h00", "Arrivée": "10h00", "Prix": "120 €", "Verdict": "Trop cher"},
            {"Train": "TGV 6614", "Départ": "10h00", "Arrivée": "12h00", "Prix": "90 €", "Verdict": "Idéal"},
            {"Train": "TER 8852", "Départ": "13h00", "Arrivée": "17h00", "Prix": "40 €", "Verdict": "Trop tard (Réunion 14h)"},
        ])
        
    return pd.DataFrame({"Info": ["Aucune donnée spécifique nécessaire"]})

# --- 10. IA (PROMPT TYPE EXAMEN) ---
SYSTEM_PROMPT = """
RÔLE : Tu es Tuteur et Évaluateur pour le Bac Pro AGOrA.
TON : Professionnel, directif.

OBJECTIF : Faire réaliser une TÂCHE ADMINISTRATIVE à l'élève en s'appuyant sur les DOCUMENTS fournis (le PGI).

RÈGLES ABSOLUES :
1. NE DONNE PAS LA RÉPONSE. Si l'élève demande "C'est qui le candidat ?", dis-lui : "Consultez le tableau des candidats ci-dessus et comparez avec les critères."
2. VALIDATION PAR PREUVE : Si l'élève propose une action, vérifie si elle correspond aux données du PGI. (Ex: S'il veut commander l'imprimante alors qu'elle est en rupture, dis non).
3. PRODUCTION ÉCRITE : Une fois l'analyse faite, demande systématiquement une production (Mail, Note, Courrier) en précisant les mentions obligatoires attendues.

SÉCURITÉ : Pas de données réelles.
"""

INITIAL_MESSAGE = """
👋 **Bonjour.**

Bienvenue dans le module d'entraînement **Pro'AGOrA**.
Ici, nous travaillons sur des cas concrets type examen.

Veuillez choisir votre **Mission** dans le menu de gauche.
"""

if not st.session_state.messages:
    st.session_state.messages.append({"role": "assistant", "content": INITIAL_MESSAGE})

def lancer_mission(prenom):
    theme = st.session_state.theme
    dossier = st.session_state.dossier
    
    # Chargement du scénario
    scenario = SCENARIOS.get(theme, {}).get(dossier, None)
    
    if not scenario:
        st.error("Scénario non trouvé.")
        return

    # Chargement PGI
    st.session_state.pgi_data = get_pgi_data(scenario["pgi_mode"])
    
    st.session_state.messages = []
    st.session_state.current_context_doc = scenario # On garde tout le scénario en mémoire

    prompt_init = f"""
    DÉMARRAGE EXERCICE.
    ÉLÈVE : {prenom}
    CONTEXTE ENTREPRISE : {scenario['contexte']}
    PROCÉDURE À SUIVRE : {scenario['procedure']}
    
    CONSIGNE :
    1. Présente le contexte à l'élève.
    2. Affiche la CONSIGNE N°1 : "{scenario['consigne_1']}"
    3. Attends son analyse.
    """
    
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt_init}]
    with st.spinner("Préparation du dossier..."):
        resp, _ = query_groq_with_rotation(msgs)
        st.session_state.messages.append({"role": "assistant", "content": resp})
    add_notification(f"Mission lancée : {dossier}")

def generer_bilan_ccf():
    """Génère un bilan type fiche E31/E32"""
    history = [m["content"] for m in st.session_state.messages if m["role"] == "user"]
    full_text = "\n".join(history) 
    
    prompt_bilan = f"""
    Agis comme un Professeur correcteur. Analyse le travail de l'élève :
    {full_text}
    
    Remplis la fiche d'appréciation (à la 3ème personne : "L'élève...") :
    1. **Compréhension du problème** : (A-t-il bien identifié l'info dans le PGI ?)
    2. **Qualité de la production écrite** : (Respect des formes, orthographe).
    3. **Compétence globale** : (Acquise / En cours / Non acquise).
    """
    msgs = [{"role": "system", "content": "Evaluateur strict."}, {"role": "user", "content": prompt_bilan}]
    return query_groq_with_rotation(msgs)[0]

# --- 11. INTERFACE GRAPHIQUE ---

LOGO_LYCEE = "logo_lycee.png"
LOGO_AGORA = "logo_agora.png"
BOT_AVATAR = LOGO_AGORA if os.path.exists(LOGO_AGORA) else "🤖"

# --- SIDEBAR ---
with st.sidebar:
    if os.path.exists(LOGO_LYCEE): st.image(LOGO_LYCEE, width=100)
    else: st.header("Lycée Pro")
    
    st.markdown("---")
    
    # GAMIFICATION
    st.markdown(f"### 🏆 {st.session_state.grade}")
    st.progress(min(st.session_state.xp / 1000, 1.0))
    st.caption(f"XP : {st.session_state.xp}")
    
    student_name = st.text_input("Prénom", placeholder="Ex: Camille")
    
    st.subheader("📂 Dossiers Professionnels")
    
    # Sélection dynamique basée sur les nouveaux scénarios SCENARIOS
    themes_dispo = list(SCENARIOS.keys())
    st.session_state.theme = st.selectbox("Thème", themes_dispo)
    
    dossiers_dispo = list(SCENARIOS[st.session_state.theme].keys())
    st.session_state.dossier = st.selectbox("Mission", dossiers_dispo)
    
    if st.button("LANCER", type="primary"):
        if student_name:
            lancer_mission(student_name)
            st.rerun()
        else:
            st.warning("Prénom requis")
    
    if st.button("✅ ÉTAPE VALIDÉE"):
        update_xp(10)
        st.rerun()

    # OUTILS
    st.markdown("---")
    uploaded_file = st.file_uploader("Rendre un travail (Word)", type=['docx'])
    if uploaded_file and student_name:
        if st.button("Envoyer à la correction"):
            txt = extract_text_from_docx(uploaded_file)
            st.session_state.messages.append({"role": "user", "content": f"PROPOSITION ÉLÈVE : {txt}"})
            update_xp(20)
            st.rerun()
            
    # BILAN
    st.markdown("---")
    if st.button("📝 Générer Bilan CCF"):
        if len(st.session_state.messages) > 2:
            bilan = generer_bilan_ccf()
            st.session_state.messages.append({"role": "assistant", "content": f"**FICHE D'ÉVALUATION :**\n\n{bilan}"})
            st.rerun()

    # SAUVEGARDE (Toujours visible)
    csv_data = ""
    if len(st.session_state.messages) > 0:
        chat_df = pd.DataFrame(st.session_state.messages)
        csv_data = chat_df.to_csv(index=False).encode('utf-8')
    
    st.download_button("💾 Sauvegarder", csv_data, "agora_save.csv", "text/csv", disabled=(len(csv_data)==0))
    
    if st.button("🗑️ Reset"):
        st.session_state.messages = [{"role": "assistant", "content": INITIAL_MESSAGE}]
        st.session_state.pgi_data = None
        st.session_state.current_context_doc = None
        st.rerun()

# --- HEADER ---
c1, c2, c3 = st.columns([3, 1, 1])
with c1:
    logo_html = ""
    if os.path.exists(LOGO_AGORA):
        b64 = img_to_base64(LOGO_AGORA)
        logo_html = f'<img src="data:image/png;base64,{b64}" style="height:40px; margin-right:10px;">'
    st.markdown(f"""<div style="display:flex; align-items:center;">{logo_html}<div><div style="font-size:22px; font-weight:bold; color:#202124;">Agence Pro'AGOrA</div><div style="font-size:12px; color:#5F6368;">v4.0 (Conforme Référentiel)</div></div></div>""", unsafe_allow_html=True)

with c2:
    with st.popover("ℹ️ Aide Métier"):
        st.info("Consultez les fiches ONISEP ou vos cours pour répondre.")
        st.link_button("Fiches Métiers", "https://www.onisep.fr")

with c3:
    st.button(f"👤 {student_name if student_name else 'Invité'}", disabled=True)

st.markdown("<hr style='margin: 0 0 20px 0;'>", unsafe_allow_html=True)

# --- AFFICHAGE PGI (PREUVES) ---
if st.session_state.pgi_data is not None:
    st.markdown(f'<div class="pgi-title">📁 DOCUMENTS DE L\'ENTREPRISE ({st.session_state.dossier})</div>', unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="pgi-container">', unsafe_allow_html=True)
        st.dataframe(st.session_state.pgi_data, use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)

# --- CHAT ---
for i, msg in enumerate(st.session_state.messages):
    avatar = BOT_AVATAR if msg["role"] == "assistant" else "🧑‍🎓"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and HAS_AUDIO:
            if st.button("🔊", key=f"tts_{i}"):
                try:
                    tts = gTTS(clean_text_for_audio(msg["content"]), lang='fr')
                    buf = BytesIO()
                    tts.write_to_fp(buf)
                    st.audio(buf, format="audio/mp3", start_time=0)
                except: pass

st.markdown("<br><br>", unsafe_allow_html=True)

# --- INPUT ---
st.markdown('<div class="fixed-footer">Agence Pro\'AGOrA - Données Fictives Uniquement</div>', unsafe_allow_html=True)

if user_input := st.chat_input("Votre réponse..."):
    if not student_name:
        st.toast("Identifiez-vous !", icon="👤")
    else:
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.rerun()

if st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant", avatar=BOT_AVATAR):
        with st.spinner("Analyse..."):
            # Construction du prompt avec les données PGI injectées
            sys = SYSTEM_PROMPT
            pgi_str = ""
            if st.session_state.pgi_data is not None:
                pgi_str = st.session_state.pgi_data.to_string()
            
            # On donne l'historique récent + le PGI à l'IA
            prompt_tour = f"""
            DONNÉES DU PGI ACTUEL (PREUVE) :
            {pgi_str}
            
            DERNIÈRE RÉPONSE ÉLÈVE : "{user_input}"
            
            TA MISSION :
            1. Vérifie si l'élève a utilisé les bonnes infos du PGI ci-dessus.
            2. Si oui, valide et demande la production suivante (Mail, Document).
            3. Si non, dis-lui "Regarde bien le tableau...".
            """
            
            msgs = [{"role": "system", "content": sys}, {"role": "user", "content": prompt_tour}]
            resp, _ = query_groq_with_rotation(msgs)
            
            st.markdown(resp)
            st.session_state.messages.append({"role": "assistant", "content": resp})
