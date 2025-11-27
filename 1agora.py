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
# Recherche du logo local, sinon icône par défaut
PAGE_ICON = "logo_agora.png" if os.path.exists("logo_agora.png") else "🏢"

st.set_page_config(
    page_title="Agence Pro'AGOrA", 
    page_icon=PAGE_ICON, 
    layout="wide",
    initial_sidebar_state="auto"
)

# --- 2. GESTION ÉTAT (SESSION STATE) ---
if "messages" not in st.session_state: st.session_state.messages = []
if "notifications" not in st.session_state: st.session_state.notifications = ["Système prêt."]
if "current_context_doc" not in st.session_state: st.session_state.current_context_doc = None
if "pgi_data" not in st.session_state: st.session_state.pgi_data = None
if "bilan_ready" not in st.session_state: st.session_state.bilan_ready = None

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

# --- 3. VARIABLES DE CONTEXTE (Aléatoire) ---
VILLES_FRANCE = ["Lyon", "Bordeaux", "Lille", "Nantes", "Strasbourg", "Toulouse", "Marseille", "Nice", "Rennes", "Dijon"]
TYPES_ORGANISATIONS = ["Mairie", "Clinique", "Garage", "Association", "PME BTP", "Agence Immo", "Supermarché", "Cabinet Comptable"]
NOMS = ["Martin", "Bernard", "Thomas", "Petit", "Robert", "Richard", "Durand", "Dubois", "Moreau", "Laurent"]
PRENOMS = ["Emma", "Gabriel", "Léo", "Louise", "Raphaël", "Jade", "Louis", "Ambre", "Lucas", "Arthur"]

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

# --- 8. SOMMAIRE OFFICIEL FOUCHER (NOUVELLE VERSION) ---

DB_OFFICIELLE = {
    "1. La gestion opérationnelle des espaces de travail": {
        "1 Organiser le fonctionnement des espaces de travail":
            "Proposer un environnement de travail adapté et sélectionner les équipements nécessaires.",
        "2 Organiser l'environnement numérique d'un service":
            "Proposer un environnement numérique adapté, recenser les contraintes réglementaires et planifier la mise en œuvre de l'environnement du service comptable.",
        "3 Gérer les ressources partagées de l'organisation":
            "Mettre en place une nouvelle gestion du partage des fournitures de bureau et proposer de nouveaux outils de partage des ressources physiques.",
        "4 Organiser le partage de l'information":
            "Analyser la communication interne, définir une nouvelle stratégie de communication et paramétrer l’outil numérique collaboratif."
    },

    "2. Le traitement de formalités administratives liées aux relations avec les partenaires": {
        "5 Participer au lancement d'une nouvelle gamme":
            "Préparer le planigramme des tâches liées au lancement, négocier les conditions de vente auprès du fournisseur et communiquer sur le lancement.",
        "6 Organiser et suivre des réunions":
            "Organiser une réunion de service et préparer / suivre une visioconférence.",
        "7 Organiser un déplacement":
            "Organiser les modalités du déplacement et préparer les formalités administratives."
    },

    "3. Le suivi administratif des relations avec le personnel": {
        "8 Participer au recrutement du personnel":
            "Préparer le recrutement et sélectionner le ou la candidat(e).",
        "9 Participer à l'intégration du personnel":
            "Préparer l’accueil du(de la) nouvel(le) salarié(e) et développer la motivation et la cohésion.",
        "10 Actualiser les dossiers du personnel":
            "Établir un contrat de travail, actualiser le registre du personnel et établir un avenant au contrat de travail."
    }
}
# --- 9. GÉNÉRATEUR PGI INTELLIGENT (Par Dossier) ---
def generate_fake_pgi_data(dossier_name):
    rows = []
    
    # --- THEME 1 : RELATIONS CLIENTS ---
    if "Dossier 1" in dossier_name: # Demandes
        for i in range(5):
            rows.append({
                "Contact": f"Client {random.randint(100,999)}",
                "Canal": random.choice(["Mail", "Téléphone", "Accueil"]),
                "Objet": random.choice(["Info Tarif", "Disponibilité", "Horaires"]),
                "Statut": "À traiter"
            })
    elif "Dossier 2" in dossier_name: # Opérations
        for i in range(5):
            rows.append({
                "Dossier": f"D-{random.randint(1000,9999)}",
                "Client": random.choice(NOMS),
                "Type": "Prestation Service",
                "Étape": random.choice(["Devis signé", "En cours", "Terminé"]),
                "Action": "Informer client"
            })
    elif "Dossier 3" in dossier_name: # Réclamations
        for i in range(4):
            rows.append({
                "N° Litige": f"LIT-{random.randint(10,99)}",
                "Client": random.choice(NOMS),
                "Motif": random.choice(["Erreur facturation", "Retard", "Produit abîmé"]),
                "Demande": "Remboursement",
                "Priorité": "Haute"
            })
    elif "Dossier 4" in dossier_name: # Satisfaction
        for i in range(5):
            rows.append({
                "Critère": random.choice(["Accueil", "Qualité", "Délai", "Prix"]),
                "Note": f"{random.randint(1,5)}/5",
                "Verbatim": random.choice(["Très bien", "Déçu", "Correct", "Excellent"])
            })

    # --- THEME 2 : ORGANISATION ---
    elif "Dossier 5" in dossier_name: # Appro
        produits = ["Papier A4", "Cartouches", "Stylos", "Classeurs"]
        for p in produits:
            rows.append({
                "Réf": f"REF-{random.randint(100,999)}",
                "Article": p,
                "Stock Physique": random.randint(0, 20),
                "Stock Minimum": 10,
                "Fournisseur": "OfficePro"
            })
    elif "Dossier 6" in dossier_name: # Commandes
        for i in range(5):
            rows.append({
                "BC N°": f"C-{2024000+i}",
                "Client": random.choice(NOMS),
                "Date": "26/11/2024",
                "Montant": f"{random.randint(100, 1000)} €",
                "Statut": "À valider"
            })
    elif "Dossier 7" in dossier_name: # Facturation
        for i in range(5):
            rows.append({
                "BL N°": f"BL-{100+i}",
                "Client": random.choice(NOMS),
                "Marchandise": "Livrée conforme",
                "Facture": "À émettre",
                "TVA": "20%"
            })
    elif "Dossier 8" in dossier_name: # Règlements
        for i in range(5):
            rows.append({
                "Facture": f"F-{500+i}",
                "Client": random.choice(NOMS),
                "Échéance": "15/10/2024 (Dépassée)",
                "Reste dû": f"{random.randint(50, 500)} €",
                "Relance": "Niveau 1 à faire"
            })

    # --- THEME 3 : RH ---
    elif "Dossier 9" in dossier_name: # Carrière
        postes = ["Assistant", "Comptable", "Technicien"]
        for _ in range(5):
            rows.append({
                "Candidat": f"{random.choice(NOMS)}",
                "Poste Visé": random.choice(postes),
                "Diplôme": "Bac Pro",
                "Expérience": f"{random.randint(0,5)} ans",
                "Statut": "À trier"
            })
    elif "Dossier 10" in dossier_name: # Activité
        for _ in range(6):
            rows.append({
                "Salarié": random.choice(NOMS),
                "Demande": random.choice(["CP", "RTT", "Récup"]),
                "Dates": "Décembre",
                "Solde Dispo": f"{random.randint(0, 30)} jours",
                "Validation": "En attente"
            })
    elif "Dossier 11" in dossier_name: # Social
        rows.append({"Projet": "Arbre de Noël", "Budget": "1500 €", "État": "Prestataire à chercher"})
        rows.append({"Projet": "Journal Interne", "Budget": "200 €", "État": "Articles à rédiger"})

    else:
        rows.append({"Info": "Pas de données spécifiques"})

    return pd.DataFrame(rows)

# --- 10. IA (PROMPT "EVALUATEUR CCF") ---
SYSTEM_PROMPT = """
RÔLE : Tu es le Tuteur de stage et Evaluateur CCF (Bac Pro AGOrA).
TON : Professionnel, directif.

OBJECTIF : Faire réaliser une TÂCHE ADMINISTRATIVE liée au DOSSIER choisi.

CONSIGNE À L'IA :
1. IDENTIFIE la tâche du dossier (ex: Dossier 7 = Facturation -> Demande de faire la facture).
2. UTILISE LE PGI : Les données sont ci-dessous. Interroge l'élève dessus.
3. NE DONNE PAS LA RÉPONSE.
4. DEMANDE UNE PRODUCTION (Mail, Tableau, Courrier).

SÉCURITÉ : Données réelles -> STOP.
"""

INITIAL_MESSAGE = """
👋 **Bonjour.**

Bienvenue dans le module **Pro'AGOrA** (Conforme Référentiel Foucher).
Veuillez choisir votre **Dossier** dans le menu de gauche.
"""

if not st.session_state.messages:
    st.session_state.messages.append({"role": "assistant", "content": INITIAL_MESSAGE})

def lancer_mission(prenom):
    lieu = random.choice(TYPES_ORGANISATIONS)
    ville = random.choice(VILLES_FRANCE)
    
    theme = st.session_state.theme
    dossier = st.session_state.dossier
    competence = DB_OFFICIELLE[theme][dossier]
    
    st.session_state.pgi_data = generate_fake_pgi_data(dossier)
    st.session_state.messages = []
    
    pgi_txt = st.session_state.pgi_data.to_string() if st.session_state.pgi_data is not None else "Aucune donnée."

    prompt = f"""
    DÉMARRAGE.
    STAGIAIRE : {prenom}.
    CONTEXTE : {lieu} à {ville}.
    DOSSIER : {dossier}.
    COMPÉTENCE : {competence}.
    
    DONNÉES PGI :
    {pgi_txt}
    
    ACTION :
    1. Accueille l'élève.
    2. Présente le contexte.
    3. Donne la 1ère consigne liée à ce dossier précis.
    """
    
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}]
    with st.spinner("Chargement du dossier..."):
        resp, _ = query_groq_with_rotation(msgs)
        st.session_state.messages.append({"role": "assistant", "content": resp})
    add_notification(f"Dossier lancé : {dossier}")

def generer_bilan_ccf(student_name, dossier):
    """Génère le bilan officiel pour le professeur"""
    history = [m["content"] for m in st.session_state.messages]
    full_text = "\n".join(history)
    
    prompt_bilan = f"""
    AGIS COMME UN INSPECTEUR DE L'ÉDUCATION NATIONALE.
    
    Élève : {student_name}
    Mission : {dossier}
    
    ANALYSE CETTE SESSION D'EXAMEN CCF (Bac Pro AGORA) :
    {full_text}
    
    RÉDIGE LE BILAN FINAL (FICHE D'ÉVALUATION) À L'ATTENTION DU JURY :
    
    1. 🏢 CONTEXTE PROFESSIONNEL
       - Structure : [Citer le lieu/ville]
       - Mission : [Citer la mission]
       
    2. ✅ ACTIVITÉS RÉALISÉES PAR LE CANDIDAT
       - [Lister les tâches effectuées factuellement]
       
    3. 📊 ÉVALUATION DES COMPÉTENCES (Utiliser : NOVICE / FONCTIONNEL / MAÎTRISE)
       - Communication écrite : [Niveau] + [Justification]
       - Usage des outils numériques (PGI) : [Niveau] + [Justification]
       - Respect des procédures : [Niveau] + [Justification]
       
    4. 📝 APPRÉCIATION GLOBALE
       - [Rédiger 2 phrases de synthèse sur la prestation du candidat à la 3ème personne ("L'élève a...", "Le candidat démontre...")]
    """
    
    msgs = [{"role": "system", "content": "Tu es un Inspecteur IEN neutre et bienveillant."}, {"role": "user", "content": prompt_bilan}]
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
    
    # XP
    st.markdown(f"### 🏆 {st.session_state.grade}")
    st.progress(min(st.session_state.xp / 1000, 1.0))
    st.caption(f"XP : {st.session_state.xp}")
    
    student_name = st.text_input("Prénom", placeholder="Ex: Camille")
    
    st.subheader("📂 Dossiers (Manuel Foucher)")
    st.session_state.theme = st.selectbox("Thème", list(DB_OFFICIELLE.keys()))
    st.session_state.dossier = st.selectbox("Dossier", list(DB_OFFICIELLE[st.session_state.theme].keys()))
    
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
            st.session_state.messages.append({"role": "user", "content": f"PROPOSITION : {txt}"})
            update_xp(20)
            st.rerun()
            
    # BILAN
    st.markdown("---")
    if st.button("📝 Générer Bilan CCF"):
        if len(st.session_state.messages) > 2:
            with st.spinner("Rédaction du Bilan Officiel..."):
                bilan = generer_bilan_ccf(student_name, st.session_state.dossier)
                st.session_state.bilan_ready = bilan
            st.rerun()
        else:
            st.warning("Travaillez d'abord !")
            
    if st.session_state.bilan_ready:
        st.download_button(
            label="📥 Télécharger Fiche Bilan",
            data=st.session_state.bilan_ready,
            file_name=f"Bilan_CCF_{student_name}.txt",
            mime="text/plain"
        )

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
        st.session_state.bilan_ready = None
        st.rerun()

# --- HEADER ---
c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 1])
with c1:
    logo_html = ""
    if os.path.exists(LOGO_AGORA):
        b64 = img_to_base64(LOGO_AGORA)
        logo_html = f'<img src="data:image/png;base64,{b64}" style="height:40px; margin-right:10px;">'
    st.markdown(f"""<div style="display:flex; align-items:center;">{logo_html}<div><div style="font-size:22px; font-weight:bold; color:#202124;">Agence Pro'AGOrA</div><div style="font-size:12px; color:#5F6368;">Conforme Foucher</div></div></div>""", unsafe_allow_html=True)

with c2:
    with st.popover("ℹ️ Aide Métier"):
        st.info("Consultez les fiches ONISEP ou vos cours pour répondre.")
        st.link_button("Fiches Métiers", "https://www.onisep.fr")

with c3:
    with st.popover("❓ Aide Outil"):
        st.link_button("Accès ENT", "https://cas.ent.auvergnerhonealpes.fr/login?service=https%3A%2F%2Fglieres.ent.auvergnerhonealpes.fr%2Fsg.do%3FPROC%3DPAGE_ACCUEIL")

with c4:
    user_label = f"👤 {student_name}" if student_name else "👤 Invité"
    st.button(user_label, disabled=True, use_container_width=True)

st.markdown("<hr style='margin: 0 0 20px 0;'>", unsafe_allow_html=True)

# --- AFFICHAGE PGI (PREUVES) ---
if st.session_state.pgi_data is not None:
    st.markdown(f'<div class="pgi-title">📁 DOCUMENTS ({st.session_state.dossier})</div>', unsafe_allow_html=True)
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
            DONNÉES PGI (PREUVE) : {pgi_str}
            RÉPONSE ÉLÈVE : "{user_input}"
            MISSION : {st.session_state.dossier}
            
            CONSIGNE :
            1. Vérifie si l'élève utilise bien le PGI.
            2. Si oui, valide et demande la production suivante.
            3. Si non, corrige-le.
            """
            
            msgs = [{"role": "system", "content": sys}, {"role": "user", "content": prompt_tour}]
            resp, _ = query_groq_with_rotation(msgs)
            
            st.markdown(resp)
            st.session_state.messages.append({"role": "assistant", "content": resp})
