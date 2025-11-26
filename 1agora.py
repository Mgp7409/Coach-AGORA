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

# --- 3. BASES DE DONNÉES ÉTENDUES (ANTI-RÉPÉTITION) ---
VILLES_FRANCE = [
    "Lyon", "Bordeaux", "Lille", "Nantes", "Strasbourg", "Toulouse", "Marseille", "Nice", "Rennes", 
    "Montpellier", "Grenoble", "Dijon", "Angers", "Nîmes", "Saint-Étienne", "Clermont-Ferrand", 
    "Le Havre", "Tours", "Limoges", "Brest", "Metz", "Besançon", "Perpignan", "Orléans", "Mulhouse",
    "Caen", "Nancy", "Argenteuil", "Rouen", "Montreuil"
]

TYPES_ORGANISATIONS = [
    "Mairie (Service Technique)", "Clinique Privée", "Garage Automobile", "Association d'Aide", 
    "PME BTP", "Agence Immobilière", "Cabinet d'Architecte", "Grande Surface", "Entreprise de Transport", 
    "Office de Tourisme", "EHPAD", "Lycée Professionnel", "Cabinet Comptable", "Start-up Tech", 
    "Coopérative Agricole"
]

NOMS = [
    "Martin", "Bernard", "Thomas", "Petit", "Robert", "Richard", "Durand", "Dubois", "Moreau", "Laurent", 
    "Simon", "Michel", "Lefebvre", "Leroy", "Roux", "David", "Bertrand", "Morel", "Fournier", "Girard",
    "Bonnet", "Dupont", "Lambert", "Fontaine", "Rousseau", "Vincent", "Muller", "Lefevre", "Faure", "Andre",
    "Mercier", "Blanc", "Guerin", "Boyer", "Garnier", "Chevalier", "Francois", "Legrand", "Gauthier", "Garcia"
]

PRENOMS = [
    "Emma", "Gabriel", "Léo", "Louise", "Raphaël", "Jade", "Louis", "Ambre", "Lucas", "Arthur", 
    "Jules", "Mila", "Adam", "Alice", "Liam", "Lina", "Sacha", "Chloé", "Hugo", "Léa",
    "Tiago", "Elena", "Mohamed", "Inès", "Noah", "Sarah", "Maël", "Zoé", "Ethan", "Anna",
    "Paul", "Eva", "Nathan", "Manon", "Tom", "Camille", "Aaron", "Lola", "Théo", "Lucie"
]

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

# --- 8. GÉNÉRATEUR PGI (LOGIQUE STRICTE) ---
def generate_fake_pgi_data(theme, mission):
    rows = []
    
    # 1. RESSOURCES HUMAINES (Candidats ou Salariés)
    if theme == "RESSOURCES HUMAINES":
        if "Recrutement" in mission:
            for _ in range(5):
                rows.append({
                    "Nom": random.choice(NOMS).upper(),
                    "Prénom": random.choice(PRENOMS),
                    "Diplôme": random.choice(["Bac Pro AGOrA", "BTS SAM", "CAP Vente"]),
                    "Expérience": f"{random.randint(0, 5)} ans",
                    "Statut": "À étudier"
                })
        else: # Intégration / Admin RH
            postes = ["Comptable", "Commercial", "Technicien", "Assistant RH"]
            for _ in range(6):
                rows.append({
                    "Matricule": f"S-{random.randint(1000,9999)}",
                    "Salarié": f"{random.choice(NOMS)} {random.choice(PRENOMS)}",
                    "Poste": random.choice(postes),
                    "Dossier": random.choice(["Complet", "Manque RIB", "Manque Carte Vitale", "À valider"])
                })

    # 2. RELATIONS PARTENAIRES (Clients, Trains, Salles)
    elif theme == "RELATIONS PARTENAIRES":
        if "Déplacements" in mission:
            for _ in range(5):
                rows.append({
                    "Type": random.choice(["Train", "Avion", "Hôtel"]),
                    "Prestataire": random.choice(["SNCF", "AirFrance", "Ibis", "Kyriad"]),
                    "Horaire": f"{random.randint(6,20)}h{random.randint(10,59)}",
                    "Tarif": f"{random.randint(40, 180)} €",
                    "Option": random.choice(["Annulable", "Non échan.", "Petit-dej inclus"])
                })
        elif "Réunions" in mission:
            salles = ["Salle Conseil", "Salle Bleue", "Auditorium", "Box 1"]
            for s in salles:
                rows.append({
                    "Espace": s,
                    "Capacité": f"{random.randint(4, 50)} pers.",
                    "Équipement": "Vidéoprojecteur, Wifi",
                    "État": random.choice(["Libre", "Occupé", "En travaux"])
                })
        else: # Vente / Achat
            etats = ["Devis envoyé", "Commande reçue", "Facturée", "Relance nécessaire"]
            for i in range(1, 8):
                rows.append({
                    "N°": f"V-{2024000+i}",
                    "Client": f"Sté {random.choice(NOMS)}",
                    "Date": "26/11/2024",
                    "Total TTC": f"{random.randint(200, 5000)} €",
                    "Statut": random.choice(etats)
                })

    # 3. GESTION DES ESPACES (Matériel, Stock)
    elif theme == "GESTION DES ESPACES":
        cats = ["Papeterie", "Informatique", "Entretien"]
        for _ in range(10):
            rows.append({
                "Réf": f"REF-{random.randint(100,999)}",
                "Article": f"Article {random.choice(['Standard', 'Premium', 'Eco'])}",
                "Catégorie": random.choice(cats),
                "Stock": random.randint(0, 100),
                "Alerte": 10
            })
            
    # FALLBACK DE SÉCURITÉ (Si jamais un nouveau thème est créé)
    else:
        rows.append({"Info": "Aucune donnée spécifique pour ce thème."})

    return pd.DataFrame(rows)

# --- CONFIGURATION DES MISSIONS ---
DB_PREMIERE = {
    "RESSOURCES HUMAINES": {
        "Recrutement": {
            "competence": "COMPÉTENCE : Définir le Profil, Rédiger l'annonce, Sélectionner (Grille), Convoquer.",
            "procedure": "1. Analyse besoin -> 2. Annonce -> 3. Sélection (Grille) -> 4. Convocation.",
            "doc": {"type": "Fiche Poste", "titre": "Assistant Commercial", "contexte": "Remplacement.", "missions": ["Accueil", "Devis"], "lien_url": "https://www.onisep.fr"}
        },
        "Intégration": {
            "competence": "COMPÉTENCE : Livret d'accueil, Parcours d'arrivée.",
            "procedure": "1. Checklist matériel -> 2. Livret d'accueil -> 3. Planning."
        },
        "Administratif RH": {
            "competence": "COMPÉTENCE : Contrat, DPAE, Registre personnel.",
            "procedure": "1. Vérification pièces -> 2. DPAE -> 3. Registre unique."
        }
    },
    "RELATIONS PARTENAIRES": {
        "Vente": {
            "competence": "COMPÉTENCE : Devis, Facturation, Relance.",
            "procedure": "1. Devis -> 2. Bon de commande -> 3. Facture -> 4. Relance."
        },
        "Réunions": {
            "competence": "COMPÉTENCE : Ordre du jour, Invitation, Réservation.",
            "procedure": "1. Ordre du jour -> 2. Choix salle -> 3. Invitation."
        },
        "Déplacements": {
            "competence": "COMPÉTENCE : Comparatif, Réservation, Ordre de Mission.",
            "procedure": "1. Recueil besoins -> 2. Comparatif (Tableau) -> 3. Réservation -> 4. Feuille de route."
        }
    },
    "GESTION DES ESPACES": {
        "Aménagement": {
            "competence": "COMPÉTENCE : Ergonomie, Plan d'aménagement.",
            "procedure": "1. Analyse besoins -> 2. Choix mobilier -> 3. Plan."
        },
        "Numérique": {
            "competence": "COMPÉTENCE : Inventaire, Charte, RGPD.",
            "procedure": "1. Inventaire -> 2. Charte -> 3. Conformité."
        },
        "Ressources": {
            "competence": "COMPÉTENCE : Gestion stocks, Commandes.",
            "procedure": "1. Inventaire -> 2. Identification besoins -> 3. Bon de commande."
        }
    }
}

# --- 9. IA (PROMPT "EVALUATEUR CCF") ---
SYSTEM_PROMPT = """
RÔLE : Tu es le Tuteur de stage et Evaluateur CCF (Bac Pro AGOrA).
TON : Professionnel, exigeant.

OBJECTIF : Guider l'élève pour qu'il réalise la tâche AVEC LES DONNÉES DU PGI CI-DESSOUS.

CRITÈRES :
1. Forme : Orthographe, ton pro.
2. Fond : Exactitude des données (L'élève doit utiliser les chiffres/noms du PGI).
3. Procédure : Respect des étapes.

CONSIGNE :
- Utilise les données du tableau pour poser des questions (ex: "Quel candidat a le diplôme requis ?").
- Si l'élève invente, dis-lui : "Regarde le PGI".

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
    # 1. Contexte aléatoire
    lieu = random.choice(TYPES_ORGANISATIONS)
    ville = random.choice(VILLES_FRANCE)
    
    # 2. Données
    theme = st.session_state.theme
    dossier = st.session_state.dossier
    data = DB_PREMIERE[theme][dossier]
    
    if isinstance(data, str):
        competence = data
        procedure = "Standard"
        st.session_state.current_context_doc = None
    else:
        competence = data.get("competence", "")
        procedure = data.get("procedure", "Standard")
        st.session_state.current_context_doc = data.get("doc", None)

    # 3. Génération PGI strict
    st.session_state.pgi_data = generate_fake_pgi_data(theme, dossier)
    
    st.session_state.messages = []
    
    contexte_ia = ""
    if st.session_state.current_context_doc:
        doc = st.session_state.current_context_doc
        contexte_ia = f"DOCUMENTS : Poste {doc['titre']} - Missions : {', '.join(doc.get('missions', []))}"

    # Injection des données PGI dans le prompt de démarrage
    pgi_txt = st.session_state.pgi_data.to_string() if st.session_state.pgi_data is not None else "Aucune donnée PGI."

    prompt = f"""
    DÉMARRAGE MISSION.
    STAGIAIRE : {prenom}.
    CONTEXTE : {lieu} à {ville}.
    MISSION : {dossier} (Thème: {theme}).
    PROCÉDURE : {procedure}.
    {contexte_ia}
    
    DONNÉES PGI DU JOUR :
    {pgi_txt}
    
    ACTION :
    1. Accueille l'élève.
    2. Présente le contexte ({lieu} à {ville}).
    3. Donne la 1ère consigne en lien avec ces données PGI.
    """
    
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}]
    with st.spinner("Préparation du dossier..."):
        resp, _ = query_groq_with_rotation(msgs)
        st.session_state.messages.append({"role": "assistant", "content": resp})
    add_notification(f"Mission lancée : {dossier}")

def generer_bilan_ccf():
    history = [m["content"] for m in st.session_state.messages if m["role"] == "user"]
    full_text = "\n".join(history[-15:]) 
    
    prompt_bilan = f"""
    Agis comme un Inspecteur IEN. Analyse ce travail d'élève (Bac Pro AGORA) :
    {full_text}
    
    Rédige le contenu pour sa "Fiche Descriptive d'Activité" (E31 ou E32) :
    1. Contexte : (Résume le lieu et la mission).
    2. Activités réalisées : (Liste les tâches faites).
    3. Outils mobilisés : (Cite le PGI, le traitement de texte...).
    4. Bilan des compétences : (Utilise les termes : Novice, Fonctionnel, Maîtrise).
    """
    msgs = [{"role": "system", "content": "Tu es un expert évaluation."}, {"role": "user", "content": prompt_bilan}]
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
            
    # BILAN CCF
    st.markdown("---")
    if st.button("📝 Générer Bilan CCF"):
        if len(st.session_state.messages) > 2:
            bilan = generer_bilan_ccf()
            st.session_state.messages.append({"role": "assistant", "content": f"**BILAN POUR DOSSIER CCF :**\n\n{bilan}"})
            st.rerun()
        else:
            st.warning("Travaillez d'abord !")

    # SAUVEGARDE
    csv_data = ""
    btn_state = True
    if len(st.session_state.messages) > 0:
        chat_df = pd.DataFrame(st.session_state.messages)
        csv_data = chat_df.to_csv(index=False).encode('utf-8')
        btn_state = False
        
    st.download_button("💾 Sauvegarder", csv_data, "agora_save.csv", "text/csv", disabled=btn_state)
    
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
    st.markdown(f"""<div style="display:flex; align-items:center;">{logo_html}<div><div style="font-size:24px; font-weight:bold; color:#202124; line-height:1.2;">Agence Pro'AGOrA</div><div style="font-size:12px; color:#5F6368;">Superviseur IA v3.1</div></div></div>""", unsafe_allow_html=True)

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
    st.button(f"👤", help=f"Connecté : {student_name}", disabled=True, use_container_width=True)

st.markdown("<hr style='margin: 0 0 20px 0;'>", unsafe_allow_html=True)

# --- SIMULATEUR PGI (AFFICHAGE) ---
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
            
            # Injection PGI
            if st.session_state.pgi_data is not None:
                sys += f"\nDONNÉES PGI DISPONIBLES : {st.session_state.pgi_data.to_string()}"

            msgs = [{"role": "system", "content": sys}] + st.session_state.messages[-6:]
            resp, _ = query_groq_with_rotation(msgs)
            if not resp: resp = "Erreur technique."
            st.markdown(resp)
            st.session_state.messages.append({"role": "assistant", "content": resp})
