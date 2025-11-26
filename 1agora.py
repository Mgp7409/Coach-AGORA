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

# --- 3. VARIABLES DE CONTEXTE ---
VILLES_FRANCE = ["Lyon", "Bordeaux", "Lille", "Nantes", "Strasbourg", "Toulouse", "Marseille", "Nice", "Rennes", "Dijon"]
TYPES_ORGANISATIONS = ["Mairie", "Clinique", "Garage", "Association", "PME BTP", "Agence Immo", "Supermarché", "Cabinet Comptable"]
NOMS = ["Martin", "Bernard", "Thomas", "Petit", "Robert", "Richard", "Durand", "Dubois", "Moreau", "Laurent"]

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
    
    /* PGI STYLE */
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
                        messages=messages, model=model, temperature=0.3, max_tokens=1024
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

# --- 8. DONNÉES OFFICIELLES DU LIVRE (SOMMAIRE) ---
DB_PREMIERE = {
    "1. RELATIONS CLIENTS & USAGERS": {
        "D1. Traitement des demandes": {
            "competence": "Accueillir, identifier le besoin, orienter, répondre.",
            "procedure": "1. Qualification de la demande -> 2. Recherche d'infos (PGI) -> 3. Réponse (Mail/Tel).",
            "doc": None
        },
        "D2. Suivi des opérations": {
            "competence": "Suivi de dossier, mise à jour PGI.",
            "procedure": "1. Consultation dossier -> 2. Vérification avancement -> 3. Information client.",
            "doc": None
        },
        "D3. Traitement des réclamations": {
            "competence": "Recevoir la plainte, analyser, proposer une solution.",
            "procedure": "1. Analyse du motif -> 2. Vérification validité -> 3. Proposition commerciale/technique.",
            "doc": {"type": "Mail Réclamation", "titre": "Client Mécontent", "contexte": "Livraison incomplète.", "missions": ["Répondre au mail"]}
        },
        "D4. Suivi de la satisfaction": {
            "competence": "Enquêtes, statistiques, fidélisation.",
            "procedure": "1. Collecte avis -> 2. Analyse résultats (Tableau) -> 3. Actions correctives.",
            "doc": None
        }
    },
    "2. ORGANISATION & PRODUCTION": {
        "D5. Suivi des approvisionnements": {
            "competence": "Stocks, commandes fournisseurs, réception.",
            "procedure": "1. Inventaire -> 2. Identification besoins -> 3. Bon de commande fournisseur.",
            "doc": None
        },
        "D6. Suivi des commandes": {
            "competence": "Traitement commande client, bon de livraison.",
            "procedure": "1. Réception BC -> 2. Vérification stock -> 3. Préparation BL.",
            "doc": None
        },
        "D7. Suivi de la facturation": {
            "competence": "Établir facture, TVA, avoir.",
            "procedure": "1. Reprise du BL -> 2. Création Facture (Mentions obligatoires) -> 3. Envoi.",
            "doc": None
        },
        "D8. Suivi des règlements": {
            "competence": "Suivi paiements, relances impayés.",
            "procedure": "1. Pointage banque -> 2. Identification retards -> 3. Relance (Niveau 1, 2, 3).",
            "doc": None
        }
    },
    "3. ADMINISTRATION DU PERSONNEL": {
        "D9. Suivi de la carrière": {
            "competence": "Recrutement, formation, évaluation.",
            "procedure": "1. Fiche de poste -> 2. Annonce -> 3. Tri CV -> 4. Convocation.",
            "doc": {"type": "Besoin RH", "titre": "Recrutement Assistant", "contexte": "Départ retraite.", "missions": ["Créer l'annonce"]}
        },
        "D10. Suivi de l'activité": {
            "competence": "Temps de travail, congés, absences.",
            "procedure": "1. Réception demande -> 2. Vérification solde -> 3. Validation/Refus.",
            "doc": None
        },
        "D11. Participation activité sociale": {
            "competence": "Organiser événements, communication interne.",
            "procedure": "1. Budget -> 2. Choix prestataire -> 3. Note de service.",
            "doc": None
        }
    }
}

# --- 9. GÉNÉRATEUR PGI CORRIGÉ ---
def get_pgi_data(theme, dossier):
    """Génère des données spécifiques au dossier choisi"""
    rows = []
    
    # THEME 1 : RELATIONS CLIENTS
    if "RELATIONS CLIENTS" in theme:
        if "réclamations" in dossier:
            # Tableau des tickets SAV
            for i in range(5):
                rows.append({
                    "N° Ticket": f"SAV-{random.randint(100,999)}",
                    "Client": f"{random.choice(NOMS)} {random.choice(['SA', 'SARL'])}",
                    "Motif": random.choice(["Retard", "Casse", "Erreur Réf", "Panne"]),
                    "Statut": random.choice(["Nouveau", "En cours", "Clôturé"])
                })
        elif "satisfaction" in dossier:
            # Résultats enquête
            for i in range(5):
                rows.append({
                    "Critère": random.choice(["Accueil", "Délai", "Qualité Produit", "SAV"]),
                    "Note Moyenne": f"{random.randint(2,5)}/5",
                    "Commentaire": random.choice(["Très bien", "À améliorer", "Parfait", "Déçu"])
                })
        else: # Demandes / Opérations
            for i in range(6):
                rows.append({
                    "Client": f"Client {random.randint(1,50)}",
                    "Dernier Contact": "26/11/2024",
                    "Objet": random.choice(["Devis", "Info Produit", "RDV"]),
                    "État": "À traiter"
                })

    # THEME 2 : ORGANISATION PRODUCTION
    elif "ORGANISATION" in theme:
        if "approvisionnements" in dossier:
            # Stocks et Fournisseurs
            for _ in range(6):
                rows.append({
                    "Réf": f"ART-{random.randint(100,999)}",
                    "Désignation": random.choice(["Papier", "Encre", "Classeurs", "PC"]),
                    "Stock Réel": random.randint(0, 20),
                    "Stock Alerte": 5,
                    "Fournisseur": random.choice(["BureauVallée", "OfficeDepot", "Grossiste"])
                })
        elif "règlements" in dossier:
            # Impayés
            for _ in range(5):
                rows.append({
                    "Facture": f"F-{2024000+random.randint(1,99)}",
                    "Client": random.choice(NOMS),
                    "Montant": f"{random.randint(100, 3000)} €",
                    "Échéance": "15/10/2024 (Dépassée)",
                    "Relance": "À faire"
                })
        else: # Commandes / Facturation
            for i in range(1, 7):
                rows.append({
                    "Commande": f"BC-{100+i}",
                    "Client": random.choice(NOMS),
                    "Montant HT": random.randint(500, 5000),
                    "Statut": random.choice(["À livrer", "Livré non facturé", "Facturé"])
                })

    # THEME 3 : RH
    elif "ADMINISTRATION" in theme:
        if "carrière" in dossier:
            # Candidats
            for _ in range(5):
                rows.append({
                    "Candidat": f"{random.choice(NOMS)} {random.choice(['A.', 'M.', 'L.'])}",
                    "Diplôme": random.choice(["Bac Pro", "BTS", "Autodidacte"]),
                    "Expérience": f"{random.randint(0, 10)} ans",
                    "Avis": "À étudier"
                })
        elif "activité" in dossier:
            # Congés
            for _ in range(6):
                rows.append({
                    "Salarié": random.choice(NOMS),
                    "Type": random.choice(["CP", "RTT", "Maladie"]),
                    "Dates": "Du 10/12 au 15/12",
                    "Solde CP": f"{random.randint(0, 25)} jours"
                })
        else: # Social
            rows.append({"Evénement": "Arbre de Noël", "Budget": "2000 €", "Statut": "Prestataire à trouver"})

    else:
        rows.append({"Info": "Données génériques"})

    return pd.DataFrame(rows)

# --- 10. IA (PROMPT) ---
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
    
    # 1. Tirage contexte aléatoire
    lieu = random.choice(TYPES_ORGANISATIONS)
    ville = random.choice(VILLES_FRANCE)

    # 2. Chargement données dossier
    data = DB_PREMIERE[theme][dossier]
    competence = data["competence"]
    procedure = data.get("procedure", "Standard")
    
    # 3. Génération PGI
    st.session_state.pgi_data = get_pgi_data(theme, dossier)
    st.session_state.messages = []
    st.session_state.current_context_doc = data.get("doc", None)

    prompt_init = f"""
    DÉMARRAGE EXERCICE.
    ÉLÈVE : {prenom}
    CONTEXTE : {lieu} à {ville}.
    MISSION : {dossier}
    PROCÉDURE : {procedure}
    
    CONSIGNE :
    1. Accueille l'élève en présentant l'entreprise.
    2. Donne la 1ère tâche liée au PGI affiché (ex: "Analyse le tableau et dis-moi...").
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
    
    # Sélection Thème
    theme_keys = list(DB_PREMIERE.keys())
    st.session_state.theme = st.selectbox("Thème", theme_keys)
    
    # Sélection Dossier (dynamique)
    dossier_keys = list(DB_PREMIERE[st.session_state.theme].keys())
    st.session_state.dossier = st.selectbox("Mission", dossier_keys)
    
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
        if st.button("Envoyer"):
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
    st.markdown(f"""<div style="display:flex; align-items:center;">{logo_html}<div><div style="font-size:22px; font-weight:bold; color:#202124;">Agence Pro'AGOrA</div><div style="font-size:12px; color:#5F6368;">v4.1 (Conforme Livre)</div></div></div>""", unsafe_allow_html=True)

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
