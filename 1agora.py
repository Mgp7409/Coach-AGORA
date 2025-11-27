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

# --- 2. GESTION ÉTAT (SESSION STATE) ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "notifications" not in st.session_state:
    st.session_state.notifications = ["Système prêt."]
if "current_context_doc" not in st.session_state:
    st.session_state.current_context_doc = None
if "pgi_data" not in st.session_state:
    st.session_state.pgi_data = None
if "bilan_ready" not in st.session_state:
    st.session_state.bilan_ready = None

# GAMIFICATION
if "xp" not in st.session_state:
    st.session_state.xp = 0
if "grade" not in st.session_state:
    st.session_state.grade = "👶 Stagiaire"

GRADES = {
    0: "👶 Stagiaire",
    100: "👦 Assistant(e) Junior",
    300: "👨‍💼 Assistant(e) Confirmé(e)",
    600: "👩‍💻 Responsable de Pôle",
    1000: "👑 Directeur(trice)"
}

def update_xp(amount: int):
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

VILLES_FRANCE = [
    "Lyon", "Bordeaux", "Lille", "Nantes", "Strasbourg",
    "Toulouse", "Marseille", "Nice", "Rennes", "Dijon",
    "Grenoble", "Clermont-Ferrand", "Tours", "Metz", "Rouen"
]

TYPES_ORGANISATIONS = [
    "Mairie", "Clinique", "Garage", "Association",
    "PME BTP", "Agence immobilière", "Supermarché",
    "Cabinet comptable", "Start-up numérique", "Centre culturel"
]

# Noms / prénoms plus variés, peu de doublons
NOMS = [
    "Martin", "Bernard", "Thomas", "Lopez", "Nguyen",
    "Diallo", "Moreau", "Khan", "Rodriguez", "Schneider",
    "Diop", "Rossi", "Dubois", "Garcia", "Haddad",
    "Kouyaté", "Kim", "Fernandes", "Popov", "Oumar"
]

PRENOMS = [
    "Emma", "Gabriel", "Lina", "Yanis", "Aïcha",
    "Noah", "Sara", "Hugo", "Maya", "Ethan",
    "Inès", "Amir", "Chloé", "Diego", "Léa",
    "Naomi", "Omar", "Sofia", "Jules", "Fatou"
]

# --- 4. OUTILS IMAGE ---
def img_to_base64(img_path: str) -> str:
    if os.path.exists(img_path):
        with open(img_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

# --- 5. STYLE & CSS ---
is_dys = st.session_state.get("mode_dys", False)
font_family = "'Verdana', sans-serif" if is_dys else "'Segoe UI', 'Roboto', Helvetica, Arial, sans-serif"
font_size = "18px" if is_dys else "16px"

st.markdown(
    f"""
<style>
    html, body, [class*="css"] {{
        font-family: {font_family} !important;
        font-size: {font_size};
        color: #202124;
        background-color: #FFFFFF;
    }}
    header {{background-color: transparent !important;}}
    [data-testid="stHeader"] {{
        background-color: rgba(255, 255, 255, 0.95);
    }}
    .reportview-container .main .block-container {{
        padding-top: 1rem;
        max-width: 100%;
    }}

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

    button[kind="primary"] {{
        background: linear-gradient(135deg, #0F9D58 0%, #00C9FF 100%);
        color: white !important;
        border: none;
    }}

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
    [data-testid="stBottom"] {{
        bottom: 30px !important;
        padding-bottom: 10px;
    }}
</style>
""",
    unsafe_allow_html=True,
)

# --- 6. LOGIQUE API GROQ ---

def get_api_keys_list():
    if "groq_keys" in st.secrets:
        return st.secrets["groq_keys"]
    elif "GROQ_API_KEY" in st.secrets:
        return [st.secrets["GROQ_API_KEY"]]
    return []


def query_groq_with_rotation(messages):
    available_keys = get_api_keys_list()
    if not available_keys:
        return None, "ERREUR CONFIG"

    keys = list(available_keys)
    random.shuffle(keys)
    models = ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"]

    for key in keys:
        try:
            client = Groq(api_key=key)
            for model in models:
                try:
                    chat = client.chat.completions.create(
                        messages=messages,
                        model=model,
                        temperature=0.3,
                        max_tokens=1024,
                    )
                    return chat.choices[0].message.content, model
                except Exception:
                    continue
        except Exception:
            continue
    return None, "SATURATION"

# --- 7. OUTILS FICHIERS ---

def extract_text_from_docx(file) -> str:
    try:
        doc = Document(file)
        text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        return text[:8000]
    except Exception as e:
        return f"ERREUR LECTURE DOCX : {e}"


def extract_text_from_table_file(file) -> str:
    """
    Lit un fichier Excel ou CSV rendu par l'élève (tableaux, calculs, etc.)
    et renvoie une version texte exploitable par l'IA.
    """
    try:
        filename = getattr(file, "name", "").lower()
        if filename.endswith(".csv"):
            df = pd.read_csv(file)
        else:
            # xls / xlsx
            df = pd.read_excel(file)

        text = df.to_string(index=False)
        return text[:8000]
    except Exception as e:
        return f"ERREUR LECTURE TABLEUR : {e}"


def clean_text_for_audio(text: str) -> str:
    text = re.sub(r"[\*_]{1,3}", "", text)
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"📎.*", "", text)
    return text


def add_notification(msg: str):
    ts = datetime.now().strftime("%H:%M")
    st.session_state.notifications.insert(0, f"{ts} - {msg}")

# --- 8. SOMMAIRE OFFICIEL (aligné sur Foucher) ---

# Structure en 3 grandes parties comme dans le sommaire du manuel. 
DB_OFFICIELLE = {
    "La gestion opérationnelle des espaces de travail": {
        "Dossier 1 – Organiser le fonctionnement des espaces de travail":
            "Modes de travail (télétravail, coworking…), aménagement open space, matériel et PGI.",
        "Dossier 2 – Organiser l’environnement numérique d’un service":
            "Réseaux (internet/intranet/extranet), ENT, cloud, RGPD, plan de déploiement du service comptable.",
        "Dossier 3 – Gérer les ressources partagées de l’organisation":
            "Gestion des fournitures, salles, véhicules, stocks et outils de réservation.",
        "Dossier 4 – Organiser le partage de l’information":
            "Diagnostic de la communication interne, nouvelle stratégie, paramétrage d’un outil collaboratif."
    },
    "Le traitement de formalités administratives liées aux relations avec les partenaires": {
        "Dossier 5 – Participer au lancement d’une nouvelle gamme":
            "Planigramme du lancement, négociation fournisseur, communication multicanale.",
        "Dossier 6 – Organiser et suivre des réunions":
            "Réunion de service présentielle, visioconférence, convocations et comptes rendus.",
        "Dossier 7 – Organiser un déplacement":
            "Organisation pratique du déplacement et formalités administratives associées."
    },
    "Le suivi administratif des relations avec le personnel": {
        "Dossier 8 – Participer au recrutement du personnel":
            "Préparation du recrutement, tri des candidatures, sélection.",
        "Dossier 9 – Participer à l’intégration du personnel":
            "Accueil du nouveau salarié, parcours d’intégration, motivation et cohésion.",
        "Dossier 10 – Actualiser les dossiers du personnel":
            "Contrats, avenants, registre du personnel, complétude des dossiers."
    }
}

# Fiches d’aide par dossier, construites à partir des situations professionnelles du manuel. 
AIDES_DOSSIERS = {
    "Dossier 1 – Organiser le fonctionnement des espaces de travail": {
        "situation": "Association Écoactif Solidaire qui internalise une partie de sa comptabilité.",
        "contexte": "Réorganisation des espaces physiques et numériques, arrivée de deux comptables.",
        "missions": [
            "Comparer les modes de travail (coworking, télétravail, nomadisme) et choisir celui qui convient au service comptable.",
            "Proposer un aménagement en open space (mobilier, cloisons, espaces de travail).",
            "Rédiger un compte rendu de visite d’un espace de coworking.",
            "Lister le matériel à acheter pour les comptables et justifier chaque élément.",
            "Argumenter l’intérêt d’un PGI pour l’association."
        ],
        "types_production": "Compte rendu, mail professionnel, tableau de matériel, justification écrite."
    },
    "Dossier 2 – Organiser l’environnement numérique d’un service": {
        "situation": "Toujours Écoactif Solidaire, mais focalisé sur les outils et réseaux numériques.",
        "contexte": "Les comptables travaillent en open space et en télétravail, il faut adapter l’environnement numérique.",
        "missions": [
            "Distinguer Internet, intranet, extranet et ENT.",
            "Proposer un schéma d’environnement numérique pour l’association.",
            "Identifier les avantages / limites du cloud.",
            "Lister les contraintes réglementaires principales (données personnelles, sauvegardes).",
            "Planifier les étapes de mise en œuvre pour le service comptable."
        ],
        "types_production": "Diapositive de synthèse, tableau comparatif, mini-plan d’actions."
    },
    "Dossier 3 – Gérer les ressources partagées de l’organisation": {
        "situation": "Association Écoactif Solidaire en open space.",
        "contexte": "Nouveaux modes de travail ⇒ besoin d’optimiser la gestion des fournitures, salles, véhicules.",
        "missions": [
            "Ranger et inventorier les fournitures selon une méthode structurée.",
            "Analyser les risques d’une mauvaise gestion des stocks.",
            "Proposer un nouveau fonctionnement (réserve centrale, fiches ou fichier de suivi).",
            "Concevoir un outil de réservation des ressources (salles, véhicules…)."
        ],
        "types_production": "Tableau d’inventaire, fiche procédure, maquette de base de données."
    },
    "Dossier 4 – Organiser le partage de l’information": {
        "situation": "Toujours Écoactif Solidaire.",
        "contexte": "Communication interne jugée insuffisante, besoin de plus de collaboratif.",
        "missions": [
            "Analyser les canaux actuels (mails, affichage, réunions…).",
            "Définir une nouvelle stratégie de communication interne.",
            "Proposer une structure d’espace Teams / plateforme collaborative (équipes, canaux, droits)."
        ],
        "types_production": "Diagnostic, plan d’action, capture ou schéma d’arborescence de l’outil collaboratif."
    },
    "Dossier 5 – Participer au lancement d’une nouvelle gamme": {
        "situation": "Entreprise Océaform (institut de soins).",
        "contexte": "Lancement d’une nouvelle gamme de produits, vous êtes intérimaire en renfort.",
        "missions": [
            "Construire un planigramme des tâches liées au lancement.",
            "Préparer une proposition de conditions commerciales avec le fournisseur.",
            "Préparer des supports de communication (affiche, mail, publication réseaux)."
        ],
        "types_production": "Planning, tableau de négociation, supports de com’ (Word, Canva…)."
    },
    "Dossier 6 – Organiser et suivre des réunions": {
        "situation": "Toujours Océaform.",
        "contexte": "Réunions de préparation du lancement et visioconférence avec partenaires.",
        "missions": [
            "Organiser une réunion de service (ordre du jour, convocation, logistique).",
            "Préparer et suivre une visioconférence (lien, test matériel, compte rendu)."
        ],
        "types_production": "Convocation, ordre du jour, feuille d’émargement, compte rendu."
    },
    "Dossier 7 – Organiser un déplacement": {
        "situation": "Océaform, déplacement du personnel pour un événement.",
        "contexte": "L’équipe se déplace (salon, formation, etc.), vous gérez le suivi administratif.",
        "missions": [
            "Comparer plusieurs solutions de transport / hébergement.",
            "Préparer les réservations et le dossier de déplacement.",
            "Vérifier les formalités (autorisations, assurances, notes de frais)."
        ],
        "types_production": "Tableau comparatif, feuille de route, check-list des formalités."
    },
    "Dossier 8 – Participer au recrutement du personnel": {
        "situation": "Entreprise Léa Nature.",
        "contexte": "Recrutement de nouveaux salariés.",
        "missions": [
            "Préparer le dossier de recrutement (profil de poste, annonce).",
            "Trier les candidatures, proposer une présélection.",
            "Préparer les convocations à l’entretien."
        ],
        "types_production": "Fiche de poste, tableau d’analyse de CV, mails de convocation."
    },
    "Dossier 9 – Participer à l’intégration du personnel": {
        "situation": "Toujours Léa Nature.",
        "contexte": "Accueil d’un nouveau salarié et animation d’un collectif.",
        "missions": [
            "Préparer le parcours d’intégration (planning, personnes ressources).",
            "Concevoir un livret / guide d’accueil.",
            "Proposer des actions pour renforcer la cohésion d’équipe."
        ],
        "types_production": "Planning d’intégration, brochure d’accueil, note de service."
    },
    "Dossier 10 – Actualiser les dossiers du personnel": {
        "situation": "Léa Nature, service RH.",
        "contexte": "Vérification de la complétude des dossiers, rédaction de contrats et avenants.",
        "missions": [
            "Compléter le dossier d’un salarié à partir d’une liste de pièces attendues.",
            "Renseigner le registre du personnel.",
            "Préparer un mail de relance pour pièces manquantes."
        ],
        "types_production": "Tableau d’arborescence du dossier, registre, mail professionnel."
    }
}

# --- 9. GÉNÉRATEUR PGI INTELLIGENT (PAR DOSSIER) ---

def generate_fake_pgi_data(dossier_name: str) -> pd.DataFrame:
    rows = []

    # Thème 1 : dossiers 1 à 4
    if "Dossier 1" in dossier_name:
        for _ in range(5):
            rows.append({
                "Contact": f"Client {random.randint(100, 999)}",
                "Canal": random.choice(["Mail", "Téléphone", "Accueil"]),
                "Objet": random.choice(["Info tarif", "Disponibilité", "Horaires"]),
                "Statut": "À traiter"
            })

    elif "Dossier 2" in dossier_name:
        for _ in range(5):
            rows.append({
                "Dossier": f"D-{random.randint(1000, 9999)}",
                "Client": random.choice(NOMS),
                "Type": "Prestation service",
                "Étape": random.choice(["Devis signé", "En cours", "Terminé"]),
                "Action": "Informer le client"
            })

    elif "Dossier 3" in dossier_name:
        for _ in range(4):
            rows.append({
                "N° Litige": f"LIT-{random.randint(10, 99)}",
                "Client": random.choice(NOMS),
                "Motif": random.choice(["Erreur facturation", "Retard", "Produit abîmé"]),
                "Demande": "Remboursement",
                "Priorité": "Haute"
            })

    elif "Dossier 4" in dossier_name:
        for _ in range(5):
            rows.append({
                "Critère": random.choice(["Accueil", "Qualité", "Délai", "Prix"]),
                "Note": f"{random.randint(1, 5)}/5",
                "Verbatim": random.choice(["Très bien", "Déçu", "Correct", "Excellent"])
            })

    # Thème 2 : dossiers 5 à 7
    elif "Dossier 5" in dossier_name:
        produits = ["Gamme Océan Zen", "Gamme Énergie Marine", "Gamme Soins Express"]
        for p in produits:
            rows.append({
                "Produit": p,
                "Tâche": random.choice(["Teasing", "Lancement", "Relance"]),
                "Responsable": random.choice(PRENOMS),
                "Échéance": "Semaine prochaine"
            })

    elif "Dossier 6" in dossier_name:
        for i in range(5):
            rows.append({
                "Réunion": f"R{i+1}",
                "Type": random.choice(["Réunion de service", "Visioconférence"]),
                "Date": "15/11/2025",
                "Statut": random.choice(["À préparer", "En cours", "Clôturée"]),
                "Animateur": random.choice(PRENOMS)
            })

    elif "Dossier 7" in dossier_name:
        for _ in range(5):
            rows.append({
                "Salarié": f"{random.choice(PRENOMS)} {random.choice(NOMS)}",
                "Ville": random.choice(["Paris", "Lyon", "Marseille", "Bordeaux"]),
                "Transport": random.choice(["Train", "Avion", "Voiture"]),
                "Hébergement": random.choice(["Hôtel", "Airbnb", "Chez partenaire"]),
                "Statut": "À confirmer"
            })

    # Thème 3 : dossiers 8 à 10
    elif "Dossier 8" in dossier_name:
        postes = ["Assistant administratif", "Comptable", "Technicien logistique"]
        for _ in range(5):
            rows.append({
                "Candidat": f"{random.choice(PRENOMS)} {random.choice(NOMS)}",
                "Poste visé": random.choice(postes),
                "Diplôme": random.choice(["Bac Pro", "BTS", "Licence"]),
                "Expérience": f"{random.randint(0,5)} ans",
                "Statut": random.choice(["À étudier", "Retenu", "Refusé"])
            })

    elif "Dossier 9" in dossier_name:
        for _ in range(6):
            rows.append({
                "Salarié": f"{random.choice(PRENOMS)} {random.choice(NOMS)}",
                "Jour 1": "Accueil / visite",
                "Jour 2": "Formation poste",
                "Jour 3": "Suivi tuteur",
                "Référent": random.choice(PRENOMS)
            })

    elif "Dossier 10" in dossier_name:
        for _ in range(5):
            rows.append({
                "Salarié": f"{random.choice(PRENOMS)} {random.choice(NOMS)}",
                "Contrat": random.choice(["CDI", "CDD", "Apprentissage"]),
                "Dossier complet": random.choice(["Oui", "Non"]),
                "Pièces manquantes": random.choice(["Diplômes", "Justificatif domicile", "Pièce d'identité", "Aucune"]),
                "Action": "Relance à faire" if random.random() < 0.6 else "OK"
            })

    else:
        rows.append({"Info": "Pas de données spécifiques"})

    return pd.DataFrame(rows)

# --- 10. IA (PROMPT ÉVALUATEUR CCF) ---

SYSTEM_PROMPT = """
RÔLE : Tu es le Tuteur de stage et Evaluateur CCF (Bac Pro AGOrA).
TON : Professionnel, directif.

OBJECTIF : Faire réaliser une TÂCHE ADMINISTRATIVE liée au DOSSIER choisi.

CONSigne :
1. IDENTIFIER la tâche du dossier (ex: Dossier 7 = déplacement -> faire les réservations, les documents).
2. UTILISER LE PGI : Les données sont fournies ci-dessous. Interroge l'élève dessus.
3. NE PAS DONNER la réponse finale.
4. DEMANDER une PRODUCTION concrète (mail, tableau, courrier, document Word ou Excel).
5. Rester dans le contexte Bac Pro AGOrA et dans le dossier sélectionné.
"""

INITIAL_MESSAGE = """
👋 **Bonjour.**

Bienvenue dans le module **Pro'AGOrA** (aligné sur le manuel *Assurer le suivi administratif des activités* – 1re Bac Pro AGOrA).
Choisis une **Partie** et un **Dossier** dans le menu de gauche, puis lance la mission.
"""

if not st.session_state.messages:
    st.session_state.messages.append({"role": "assistant", "content": INITIAL_MESSAGE})


def lancer_mission(prenom: str):
    lieu = random.choice(TYPES_ORGANISATIONS)
    ville = random.choice(VILLES_FRANCE)

    theme = st.session_state.theme
    dossier = st.session_state.dossier
    competence = DB_OFFICIELLE[theme][dossier]

    st.session_state.pgi_data = generate_fake_pgi_data(dossier)
    st.session_state.messages = []

    pgi_txt = st.session_state.pgi_data.to_string() if st.session_state.pgi_data is not None else "Aucune donnée."

    prompt = f"""
    DÉMARRAGE MISSION.
    STAGIAIRE : {prenom}.
    CONTEXTE : Organisation de type "{lieu}" située à {ville}.
    PARTIE DU MANUEL : {theme}.
    DOSSIER : {dossier}.
    RÉSUMÉ COMPÉTENCES : {competence}

    DONNÉES PGI (FICTIVES) :
    {pgi_txt}

    ACTION :
    1. Accueille l'élève.
    2. Rappelle le contexte professionnel.
    3. Explique la mission liée au dossier.
    4. Formule une première consigne précise (production attendue en Word ou Excel si pertinent).
    """

    msgs = [{"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}]
    with st.spinner("Chargement du dossier..."):
        resp, _ = query_groq_with_rotation(msgs)
        if resp is None:
            resp = "Désolé, le service d'IA n'est pas disponible pour le moment."
        st.session_state.messages.append({"role": "assistant", "content": resp})
    add_notification(f"Dossier lancé : {dossier}")


def generer_bilan_ccf(student_name: str, dossier: str) -> str:
    """Génère un bilan type CCF à partir de l'historique de la session."""
    history = [m["content"] for m in st.session_state.messages]
    full_text = "\n".join(history)

    prompt_bilan = f"""
    Tu es Inspecteur de l'Éducation nationale, jury CCF Bac Pro AGOrA.

    Élève : {student_name}
    Dossier travaillé : {dossier}

    TRANSCRIPTION DE LA SÉANCE (dialogue tuteur / élève) :
    {full_text}

    PRODUIS UN BILAN STRUCTURÉ pour le professeur :

    1. 🏢 CONTEXTE PROFESSIONNEL
       - Structure d'accueil
       - Missions confiées à l'élève

    2. ✅ ACTIVITÉS RÉALISÉES PAR LE CANDIDAT
       - Liste factuelle des tâches réalisées ou simulées.

    3. 📊 ÉVALUATION DES COMPÉTENCES (NIVEAUX : NOVICE / FONCTIONNEL / MAÎTRISE)
       - Communication écrite
       - Usage des outils numériques (PGI, Word/Excel)
       - Respect des procédures administratives

    4. 📝 APPRÉCIATION GLOBALE
       - 2 à 3 phrases à la 3e personne : 'L'élève a...', 'Le candidat démontre...'

    Style attendu : clair, professionnel, directement exploitable dans un dossier CCF.
    """

    msgs = [
        {"role": "system", "content": "Tu es un Inspecteur IEN neutre et bienveillant."},
        {"role": "user", "content": prompt_bilan},
    ]
    bilan, _ = query_groq_with_rotation(msgs)
    return bilan or "Impossible de générer le bilan (problème d'IA)."

# --- 11. INTERFACE GRAPHIQUE ---

LOGO_LYCEE = "logo_lycee.png"
LOGO_AGORA = "logo_agora.png"
BOT_AVATAR = LOGO_AGORA if os.path.exists(LOGO_AGORA) else "🤖"

# --- SIDEBAR ---
with st.sidebar:
    if os.path.exists(LOGO_LYCEE):
        st.image(LOGO_LYCEE, width=100)
    else:
        st.header("Lycée Pro")

    st.markdown("---")

    # XP
    st.markdown(f"### 🏆 {st.session_state.grade}")
    st.progress(min(st.session_state.xp / 1000, 1.0))
    st.caption(f"XP : {st.session_state.xp}")

    student_name = st.text_input("Prénom de l'élève", placeholder="Ex : Camille")

    st.subheader("📂 Sommaire Foucher (1re Bac Pro AGOrA)")
    st.session_state.theme = st.selectbox(
        "Partie du manuel",
        list(DB_OFFICIELLE.keys())
    )
    st.session_state.dossier = st.selectbox(
        "Dossier",
        list(DB_OFFICIELLE[st.session_state.theme].keys())
    )

    if st.button("LANCER LA MISSION", type="primary", use_container_width=True):
        if student_name:
            lancer_mission(student_name)
            st.rerun()
        else:
            st.warning("Merci de saisir le prénom de l'élève.")

    if st.button("✅ ÉTAPE VALIDÉE", use_container_width=True):
        update_xp(10)
        st.rerun()

    st.markdown("---")
    st.markdown("### 📤 Rendre un travail")

    uploaded_work = st.file_uploader(
        "Fichier élève (Word / Excel / CSV)",
        type=['docx', 'xlsx', 'xls', 'csv']
    )

    if uploaded_work and student_name:
        if st.button("Envoyer le travail", use_container_width=True):
            ext = os.path.splitext(uploaded_work.name)[1].lower()
            if ext == ".docx":
                txt = extract_text_from_docx(uploaded_work)
            else:
                txt = extract_text_from_table_file(uploaded_work)

            st.session_state.messages.append({
                "role": "user",
                "content": f"PROPOSITION DE L'ÉLÈVE (extrait du fichier {uploaded_work.name}) :\n\n{txt}"
            })
            update_xp(20)
            st.rerun()
    elif uploaded_work and not student_name:
        st.info("Renseigner le prénom avant d'envoyer un travail.")

    # BILAN CCF
    st.markdown("---")
    if st.button("📝 Générer Bilan CCF", use_container_width=True):
        if student_name and len(st.session_state.messages) > 2:
            with st.spinner("Rédaction du bilan officiel..."):
                bilan = generer_bilan_ccf(student_name, st.session_state.dossier)
                st.session_state.bilan_ready = bilan
            st.rerun()
        else:
            st.warning("Il faut d'abord avoir travaillé avec l'élève (échanges dans le chat).")

    if st.session_state.bilan_ready:
        st.download_button(
            label="📥 Télécharger Fiche Bilan (txt)",
            data=st.session_state.bilan_ready,
            file_name=f"Bilan_CCF_{student_name}.txt",
            mime="text/plain",
            use_container_width=True
        )

    # SAUVEGARDE / RESTAURATION
    st.markdown("---")
    st.markdown("### 💾 Sauvegarde de la session")

    csv_data = b""
    btn_state = True
    if len(st.session_state.messages) > 0:
        chat_df = pd.DataFrame(st.session_state.messages)
        csv_data = chat_df.to_csv(index=False).encode("utf-8")
        btn_state = False

    st.download_button(
        "💾 Télécharger la sauvegarde (CSV)",
        csv_data,
        "agora_session.csv",
        "text/csv",
        disabled=btn_state,
        use_container_width=True,
    )

    restore_file = st.file_uploader(
        "♻️ Recharger une sauvegarde (CSV)",
        type=["csv"],
        help="Permet à un élève de renvoyer son fichier de sauvegarde pour reprendre la séance."
    )
    if restore_file is not None:
        try:
            df_restore = pd.read_csv(restore_file)
            if {"role", "content"}.issubset(df_restore.columns):
                st.session_state.messages = df_restore[["role", "content"]].to_dict(orient="records")
                st.success("Conversation rechargée depuis le CSV.")
                st.rerun()
            else:
                st.warning("Le CSV doit contenir les colonnes 'role' et 'content'.")
        except Exception as e:
            st.error(f"Impossible d'importer le fichier : {e}")

    if st.button("🗑️ Reset complet", use_container_width=True):
        st.session_state.messages = [{"role": "assistant", "content": INITIAL_MESSAGE}]
        st.session_state.pgi_data = None
        st.session_state.bilan_ready = None
        st.rerun()

# --- HEADER PRINCIPAL ---
c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 1])

with c1:
    logo_html = ""
    if os.path.exists(LOGO_AGORA):
        b64 = img_to_base64(LOGO_AGORA)
        logo_html = f'<img src="data:image/png;base64,{b64}" style="height:40px; margin-right:10px;">'
    st.markdown(
        f"""
        <div style="display:flex; align-items:center;">
            {logo_html}
            <div>
                <div style="font-size:22px; font-weight:bold; color:#202124;">Agence Pro'AGOrA</div>
                <div style="font-size:12px; color:#5F6368;">Aligné sur "Assurer le suivi administratif des activités" – 1re Bac Pro AGOrA</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c2:
    with st.popover("ℹ️ Aide Métier"):
        st.info("Appuie-toi sur le manuel, les fiches de cours et les sites institutionnels (service-public.fr, ameli.fr...).")
        st.link_button("Fiches ONISEP", "https://www.onisep.fr")

with c3:
    with st.popover("❓ Aide Outil"):
        st.link_button(
            "Accès ENT",
            "https://cas.ent.auvergnerhonealpes.fr/login?service=https%3A%2F%2Fglieres.ent.auvergnerhonealpes.fr%2Fsg.do%3FPROC%3DPAGE_ACCUEIL",
        )

with c4:
    user_label = f"👤 {student_name}" if student_name else "👤 Invité"
    st.button(user_label, disabled=True, use_container_width=True)

st.markdown("<hr style='margin: 0 0 10px 0;'>", unsafe_allow_html=True)

# --- FICHE D'AIDE DU DOSSIER SÉLECTIONNÉ ---

dossier_courant = st.session_state.dossier
fiche_aide = AIDES_DOSSIERS.get(dossier_courant)

if fiche_aide:
    with st.expander("📎 Fiche d'aide (résumé du manuel pour ce dossier)", expanded=False):
        st.markdown(f"**Situation professionnelle :** {fiche_aide['situation']}")
        st.markdown(f"**Contexte :** {fiche_aide['contexte']}")
        st.markdown("**Missions typiques à confier à l'élève :**")
        for m in fiche_aide["missions"]:
            st.markdown(f"- {m}")
        st.markdown(f"**Types de productions attendues :** {fiche_aide['types_production']}")

st.markdown("<br>", unsafe_allow_html=True)

# --- AFFICHAGE PGI (PREUVES) ---
if st.session_state.pgi_data is not None:
    st.markdown(
        f'<div class="pgi-title">📁 Données métier fictives (PGI) – {st.session_state.dossier}</div>',
        unsafe_allow_html=True,
    )
    with st.container():
        st.markdown('<div class="pgi-container">', unsafe_allow_html=True)
        st.dataframe(st.session_state.pgi_data, use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

# --- CHAT ---
for i, msg in enumerate(st.session_state.messages):
    avatar = BOT_AVATAR if msg["role"] == "assistant" else "🧑‍🎓"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and HAS_AUDIO:
            # petit bouton audio facultatif par message
            if st.button("🔊 Lire le message", key=f"tts_{i}"):
                try:
                    tts = gTTS(clean_text_for_audio(msg["content"]), lang="fr")
                    buf = BytesIO()
                    tts.write_to_fp(buf)
                    st.audio(buf, format="audio/mp3", start_time=0)
                except Exception:
                    st.warning("Lecture audio impossible pour ce message.")

st.markdown("<br><br>", unsafe_allow_html=True)

# --- INPUT CHAT ---
st.markdown(
    '<div class="fixed-footer">Agence Pro\'AGOrA - Données 100 % fictives (inspirées du manuel Foucher, corrigé enseignant)</div>',
    unsafe_allow_html=True,
)

if user_input := st.chat_input("Votre réponse, votre question ou votre production (résumé de votre Word/Excel)…"):
    if not student_name:
        st.toast("Identifiez-vous (prénom) avant de répondre.", icon="👤")
    else:
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.rerun()

# --- RÉPONSE AUTOMATIQUE SI DERNIER MESSAGE = ÉLÈVE ---
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant", avatar=BOT_AVATAR):
        with st.spinner("Analyse de ta réponse…"):
            sys = SYSTEM_PROMPT
            pgi_str = ""
            if st.session_state.pgi_data is not None:
                pgi_str = st.session_state.pgi_data.to_string()

            dernier_texte_eleve = st.session_state.messages[-1]["content"]

            prompt_tour = f"""
            CONTEXTE DOSSIER : {st.session_state.dossier}
            PARTIE : {st.session_state.theme}

            DONNÉES PGI (fictives, à exploiter) :
            {pgi_str}

            DERNIÈRE RÉPONSE DE L'ÉLÈVE :
            \"\"\"{dernier_texte_eleve}\"\"\"

            CONSIGNE POUR LE TUTEUR IA :
            1. Vérifie si l'élève utilise correctement les informations du PGI et du contexte (manuel Foucher).
            2. Si la réponse est pertinente, VALIDE un point, précise ce qui est bien, puis propose la prochaine étape
               (ex : rédiger le mail complet dans Word, construire le tableau Excel…).
            3. Si la réponse est incomplète ou hors sujet, explique clairement ce qui manque et donne une consigne guidée.
            4. Reste toujours dans le même dossier et le même contexte.
            """

            msgs = [
                {"role": "system", "content": sys},
                {"role": "user", "content": prompt_tour},
            ]
            resp, _ = query_groq_with_rotation(msgs)
            if resp is None:
                resp = "Je n'arrive pas à analyser ta réponse pour le moment. Réessaie dans quelques instants."
            st.markdown(resp)
            st.session_state.messages.append({"role": "assistant", "content": resp})
