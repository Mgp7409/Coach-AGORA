import streamlit as st
import pandas as pd
import random
from groq import Groq
from datetime import datetime
from io import BytesIO
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

# --- 3. VARIABLES DE CONTEXTE ---

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
        st.error("Aucune clé Groq trouvée dans st.secrets.")
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
                except Exception as e:
                    st.error(f"Erreur modèle {model} : {e}")
                    continue
        except Exception as e:
            st.error(f"Erreur connexion Groq : {e}")
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
    try:
        filename = getattr(file, "name", "").lower()
        if filename.endswith(".csv"):
            df = pd.read_csv(file)
        else:
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

# --- 8. SOMMAIRE OFFICIEL (aligné manuel) ---

DB_OFFICIELLE = {
    "La gestion opérationnelle des espaces de travail": {
        "Dossier 1 – Organiser le fonctionnement des espaces de travail":
            "Écoactif Solidaire : réorganisation des locaux, nouveaux modes de travail et équipements nécessaires.",
        "Dossier 2 – Organiser l’environnement numérique d’un service":
            "Écoactif Solidaire : réseaux, outils numériques et environnement pour les comptables.",
        "Dossier 3 – Gérer les ressources partagées de l’organisation":
            "Écoactif Solidaire : fournitures, salles, matériels partagés, procédures et bases de données.",
        "Dossier 4 – Organiser le partage de l’information":
            "Écoactif Solidaire : communication interne insuffisante, adoption d’un outil collaboratif."
    },
    "Le traitement de formalités administratives liées aux relations avec les partenaires": {
        "Dossier 5 – Participer au lancement d’une nouvelle gamme":
            "Océaform : lancement d’une nouvelle gamme de soins, plan du lancement et communication.",
        "Dossier 6 – Organiser et suivre des réunions":
            "Océaform : réunions de service et visioconférences liées au lancement et au suivi de l’activité.",
        "Dossier 7 – Organiser un déplacement":
            "Océaform : déplacement professionnel (fournisseur / voyage d’affaires), transport, hébergement, formalités."
    },
    "Le suivi administratif des relations avec le personnel": {
        "Dossier 8 – Participer au recrutement du personnel":
            "Léa Nature : recrutement d’un(e) commercial(e) sédentaire, profil de poste, sélection.",
        "Dossier 9 – Participer à l’intégration du personnel":
            "Léa Nature : accueil du nouveau salarié, parcours d’intégration, motivation et cohésion.",
        "Dossier 10 – Actualiser les dossiers du personnel":
            "Léa Nature : contrats, registre du personnel, avenants et complétude des dossiers."
    }
}

# --- 9. FICHES D’AIDE ---

AIDES_DOSSIERS = {
    "Dossier 1 – Organiser le fonctionnement des espaces de travail": {
        "situation": "Association Écoactif Solidaire qui internalise une partie de sa comptabilité.",
        "contexte": "Réorganisation des services généraux, embauche de deux comptables, nouveaux modes de travail.",
        "missions": [
            "Présenter les modes de travail (télétravail, coworking, open space…) avec avantages et limites.",
            "Proposer une organisation des espaces adaptée au nouveau service comptable.",
            "Lister et justifier les équipements matériels à prévoir pour les postes de travail."
        ],
        "types_production": "Tableau comparatif, note de synthèse, schéma d’aménagement, liste argumentée."
    },
    "Dossier 2 – Organiser l’environnement numérique d’un service": {
        "situation": "Toujours Écoactif Solidaire, suite du projet comptabilité.",
        "contexte": "Les deux comptables travaillent en open space et à distance, l’environnement numérique doit être revu.",
        "missions": [
            "Distinguer les différents réseaux et accès (internet, intranet, extranet, ENT).",
            "Proposer un environnement numérique complet pour les comptables.",
            "Planifier les étapes de mise en place (achat, installation, formation, sauvegardes)."
        ],
        "types_production": "Tableau des outils, plan d’actions, schéma des flux numériques."
    },
    "Dossier 3 – Gérer les ressources partagées de l’organisation": {
        "situation": "Écoactif Solidaire adopte l’open space et partage davantage de ressources.",
        "contexte": "Fournitures, salles de réunion, véhicules, matériels doivent être mieux gérés.",
        "missions": [
            "Analyser la situation actuelle de partage des ressources.",
            "Proposer une nouvelle organisation (stock, réservations, règles d’usage).",
            "Mettre en forme un outil de suivi ou de réservation (tableur ou base)."
        ],
        "types_production": "Tableau d’inventaire, formulaire de réservation, procédure interne."
    },
    "Dossier 4 – Organiser le partage de l’information": {
        "situation": "Communication interne jugée peu collaborative à Écoactif Solidaire.",
        "contexte": "Nouveaux modes de travail ⇒ besoin d’un meilleur partage d’information.",
        "missions": [
            "Diagnostiquer les supports actuels de communication interne.",
            "Proposer une nouvelle stratégie plus collaborative.",
            "Paramétrer ou décrire un espace d’outil collaboratif (équipes, canaux, droits)."
        ],
        "types_production": "Diagnostic, plan de communication, maquette d’espace collaboratif."
    },
    "Dossier 5 – Participer au lancement d’une nouvelle gamme": {
        "situation": "Océaform lance une nouvelle gamme de produits.",
        "contexte": "Croissance de la gamme, besoin de communication et d’organisation du lancement.",
        "missions": [
            "Construire le plan du lancement (actions avant/pendant/après).",
            "Préparer des supports de communication (affiche, mail, réseaux).",
            "Organiser la coordination avec les fournisseurs et l’équipe commerciale."
        ],
        "types_production": "Planigramme, tableaux de suivi, mails ou documents de communication."
    },
    "Dossier 6 – Organiser et suivre des réunions": {
        "situation": "Océaform multiplie les réunions autour du projet et du suivi.",
        "contexte": "Réunions de service en présentiel et visioconférences avec partenaires.",
        "missions": [
            "Préparer une réunion (ordre du jour, convocations, logistique).",
            "Suivre la réunion (présences, décisions, actions à mener).",
            "Organiser une visioconférence (lien, tests, compte rendu)."
        ],
        "types_production": "Convocation, ordre du jour, compte rendu, tableau de suivi des décisions."
    },
    "Dossier 7 – Organiser un déplacement": {
        "situation": "Océaform organise un déplacement chez un fournisseur et un voyage d’affaires.",
        "contexte": "Comparaison des moyens de transport et des hébergements, respect contraintes temps/budget.",
        "missions": [
            "Identifier les contraintes du déplacement (temps, budget, géographie).",
            "Comparer plusieurs options de transport et d’hébergement.",
            "Préparer le dossier de déplacement et les formalités administratives."
        ],
        "types_production": "Tableau comparatif, ordre de mission, check-list des formalités."
    },
    "Dossier 8 – Participer au recrutement du personnel": {
        "situation": "Entreprise Léa Nature, service RH.",
        "contexte": "Recrutement d’un(e) commercial(e) sédentaire pour la gamme beauté/hygiène bio.",
        "missions": [
            "Identifier les étapes du processus de recrutement.",
            "Compléter le profil de poste à partir d’informations données.",
            "Préparer un mail ou document de convocation à un entretien."
        ],
        "types_production": "Profil de poste, tableau de présélection, mail de convocation."
    },
    "Dossier 9 – Participer à l’intégration du personnel": {
        "situation": "Léa Nature accueille le nouveau commercial recruté.",
        "contexte": "Importance de l’onboarding, de la cohésion et des conditions de travail.",
        "missions": [
            "Construire un parcours d’accueil sur plusieurs jours.",
            "Lister les actions pour intégrer le salarié dans l’équipe.",
            "Proposer des actions pour la motivation et la cohésion."
        ],
        "types_production": "Planning d’intégration, fiche d’accueil, note de service ou mail interne."
    },
    "Dossier 10 – Actualiser les dossiers du personnel": {
        "situation": "Toujours Léa Nature, service RH.",
        "contexte": "Contrat de travail, registre du personnel, avenants, pièces justificatives.",
        "missions": [
            "Vérifier la complétude d’un dossier salarié.",
            "Mettre à jour les informations dans un tableau ou registre.",
            "Préparer un document simple (contrat ou avenant prérempli, mail de relance)."
        ],
        "types_production": "Tableau de suivi, extrait de registre, mail administratif."
    }
}

# --- 10. PGI PAR DOSSIER ---

def generate_fake_pgi_data(dossier_name: str) -> pd.DataFrame:
    rows = []

    # --- PARTIE 1 ---

    if "Dossier 1" in dossier_name:
        postes = ["Accueil", "Comptabilité", "Direction", "Open space", "Salle de réunion"]
        for p in postes:
            rows.append({
                "Zone": p,
                "Nombre de postes": random.randint(1, 6),
                "État": random.choice(["Adapté", "Saturé", "Sous-utilisé"]),
                "Problème signalé": random.choice(
                    ["Bruit", "Manque de rangements", "Éclairage insuffisant", "Aucun"]
                ),
                "Priorité": random.choice(["Haute", "Moyenne", "Basse"])
            })

    elif "Dossier 2" in dossier_name:
        outils = ["Suite bureautique", "PGI comptable", "Messagerie", "Drive partagé", "Outil de visio"]
        for o in outils:
            rows.append({
                "Outil": o,
                "Service concerné": random.choice(["Comptabilité", "Accueil", "Direction"]),
                "Nb utilisateurs": random.randint(2, 15),
                "Problème": random.choice(["Aucun", "Droits insuffisants", "Connexion lente", "Formation à prévoir"]),
                "Priorité": random.choice(["Urgent", "À planifier", "Information"])
            })

    elif "Dossier 3" in dossier_name:
        ressources = ["Salle réunion A", "Salle réunion B", "Véhicule 1", "Véhicule 2", "Vidéoprojecteur"]
        for r in ressources:
            rows.append({
                "Ressource": r,
                "Type": random.choice(["Salle", "Véhicule", "Matériel"]),
                "Taux d'utilisation": f"{random.randint(40, 100)} %",
                "Conflits réserv.": random.randint(0, 5),
                "Remarque": random.choice(["Souvent réservé", "Peu utilisé", "Réservation à structurer"])
            })

    elif "Dossier 4" in dossier_name:
        infos = ["Consignes sécurité", "Planning mensuel", "Notes de service", "Procédure d’accueil"]
        for i in infos:
            rows.append({
                "Information": i,
                "Support actuel": random.choice(["Mail", "Affichage", "Intranet", "Oral uniquement"]),
                "Public cible": random.choice(["Tous les salariés", "Service compta", "Direction"]),
                "Fréquence": random.choice(["Ponctuelle", "Hebdomadaire", "Mensuelle"]),
                "Problème": random.choice(["Non à jour", "Non lu", "Trop dispersé", "Aucun"])
            })

    # --- PARTIE 2 ---

    elif "Dossier 5" in dossier_name:
        actions = ["Teasing réseaux sociaux", "Animation point de vente", "Newsletter clients fidèles", "Formation vendeurs"]
        for a in actions:
            rows.append({
                "Action": a,
                "Responsable": random.choice(PRENOMS),
                "Échéance": f"{random.randint(1, 28)}/09/2025",
                "Statut": random.choice(["À faire", "En cours", "Terminé"]),
                "Budget estimé": f"{random.randint(200, 2000)} €"
            })

    elif "Dossier 6" in dossier_name:
        for i in range(4):
            rows.append({
                "Réunion": f"Réunion {i+1}",
                "Objet": random.choice(["Préparation lancement", "Point qualité", "Réunion RH", "Sécurité"]),
                "Date": f"{random.randint(1, 28)}/10/2025",
                "Participants prévus": random.randint(3, 12),
                "Compte rendu": random.choice(["Non rédigé", "En cours", "Diffusé"])
            })

    elif "Dossier 7" in dossier_name:
        villes = ["Pegalajar", "Séville", "Madrid", "Barcelone"]
        for _ in range(5):
            rows.append({
                "Salarié": f"{random.choice(PRENOMS)} {random.choice(NOMS)}",
                "Destination": random.choice(villes),
                "Motif": random.choice(["Visite oliveraie", "Visite usine", "Rencontre fournisseur", "Découverte culturelle"]),
                "Transport": random.choice(["Voiture entreprise", "Train", "Avion"]),
                "Hébergement": random.choice(["Hôtel", "Maison d’hôtes", "Appartement loué"]),
                "Coût estimé": f"{random.randint(180, 650)} €"
            })

    # --- PARTIE 3 ---

    elif "Dossier 8" in dossier_name:
        postes = ["Commercial sédentaire", "Assistant commercial", "Chargé de clientèle"]
        diplomes = ["Bac Pro AGOrA", "Bac STMG", "BTS NDRC", "BTS MCO"]
        for _ in range(8):
            rows.append({
                "Candidat": f"{random.choice(PRENOMS)} {random.choice(NOMS)}",
                "Poste visé": random.choice(postes),
                "Diplôme principal": random.choice(diplomes),
                "Expérience": f"{random.randint(0, 5)} an(s)",
                "Motivation /5": random.randint(1, 5),
                "Statut dossier": random.choice(["À étudier", "Retenu entretien", "Refusé"])
            })

    elif "Dossier 9" in dossier_name:
        etapes = ["Préparation poste", "Création comptes informatiques", "Remise badge", "Présentation équipe", "Formation sécurité"]
        for e in etapes:
            rows.append({
                "Étape d’intégration": e,
                "Responsable": random.choice(["RH", "Manager", "Accueil"]),
                "Moment": random.choice(["Avant arrivée", "Jour J", "Semaine 1"]),
                "Statut": random.choice(["À faire", "En cours", "Terminé"]),
                "Commentaire": random.choice(["Prioritaire", "Peut être délégué", "À vérifier"])
            })

    elif "Dossier 10" in dossier_name:
        for _ in range(6):
            rows.append({
                "Salarié": f"{random.choice(PRENOMS)} {random.choice(NOMS)}",
                "Type modif.": random.choice(["Adresse", "Contrat", "Fonction"]),
                "Document reçu": random.choice(["Oui", "Non"]),
                "Dossier à jour": random.choice(["Oui", "Non"]),
                "Action à mener": random.choice(["Relancer salarié", "Archiver", "Mettre à jour PGI"])
            })

    else:
        for _ in range(5):
            rows.append({"Info": "Données fictives à définir pour ce dossier."})

    return pd.DataFrame(rows)

# --- 11. DIFFÉRENCIATION & PROMPTS IA ---

def build_differentiation_instruction(profil: str) -> str:
    if profil == "Accompagnement renforcé":
        return """
NIVEAU ÉLÈVE : Besoin d'aide important.
- Utilise des phrases très simples.
- Découpe la tâche en petites étapes numérotées (1, 2, 3...).
- Donne un exemple très court si nécessaire.
- Propose de reformuler si ce n'est pas clair.
"""
    elif profil == "Autonome":
        return """
NIVEAU ÉLÈVE : Autonome.
- Rappelle rapidement le contexte.
- Donne des consignes plus ouvertes.
- Laisse l’élève proposer ses propres choix, puis valide ou ajuste.
"""
    else:  # Standard
        return """
NIVEAU ÉLÈVE : Standard.
- Donne une consigne claire.
- Ajoute une ou deux étapes clés sous forme de puces.
- Tu peux donner un exemple de structure sans tout remplir.
"""

SYSTEM_PROMPT = """
RÔLE : Tu es le Tuteur de stage et évaluateur CCF (Bac Pro AGOrA).
TON : Professionnel, bienveillant, directif.

OBJECTIF :
- Faire réaliser à l'élève une tâche administrative liée au dossier choisi.
- L’aider à produire un document métier (mail, note, tableau de synthèse, compte rendu, etc.).

PRÉSENTATION :
- Contexte en 3 à 4 puces maximum (phrases courtes).
- Consignes en une phrase courte + éventuellement une micro-liste d’étapes.
- Pas de bloc de texte compact de plus de 7 lignes.
- Utilise des listes à puces chaque fois que cela facilite la lecture.

TABLEAUX :
- Les tableaux PGI sont des données brutes.
- Si tu demandes de « faire un tableau », il doit être :
  - un tableau de synthèse,
  - un tableau comparatif,
  - ou un tableau de plan d’actions / de suivi.
- Ne demande jamais de recopier le tableau du PGI.
"""

INITIAL_MESSAGE = """
👋 **Bienvenue dans Agence Pro'AGOrA**

1. Choisis la **Partie** et le **Dossier** dans la barre de gauche.  
2. Sélectionne ton **Profil d’élève**.  
3. Clique sur **LANCER LA MISSION**.  
4. Lis le tableau (PGI) et la fiche d’aide si elle est affichée, puis réponds dans le chat.
"""

if not st.session_state.messages:
    st.session_state.messages.append({"role": "assistant", "content": INITIAL_MESSAGE})

def lancer_mission(prenom: str, profil: str):
    lieu = random.choice(TYPES_ORGANISATIONS)
    ville = random.choice(VILLES_FRANCE)

    theme = st.session_state.theme
    dossier = st.session_state.dossier
    competence = DB_OFFICIELLE[theme][dossier]

    st.session_state.pgi_data = generate_fake_pgi_data(dossier)
    st.session_state.messages = []

    pgi_txt = st.session_state.pgi_data.to_string() if st.session_state.pgi_data is not None else "Aucune donnée."
    diff_instr = build_differentiation_instruction(profil)
    aide = AIDES_DOSSIERS.get(dossier, None)

    aide_txt = ""
    if aide:
        aide_txt = f"""
RÉSUMÉ ENSEIGNANT (contexte dossier) :
- Situation : {aide['situation']}
- Contexte : {aide['contexte']}
- Missions possibles : {", ".join(aide['missions'])}
- Productions habituelles : {aide['types_production']}
"""

    prompt = f"""
{diff_instr}

DOSSIER : {dossier}
PARTIE : {theme}

{aide_txt}

LIEU FICTIF : {lieu} à {ville}.
ÉLÈVE : {prenom} (Première Bac Pro AGOrA).
COMPÉTENCE VISÉE : {competence}

DONNÉES PGI (fictives à utiliser comme base) :
{pgi_txt}

ACTION ATTENDUE :
1. Présente le contexte en 3 à 4 puces maximum.
2. Explique la mission à l'élève en 1 ou 2 phrases courtes.
3. Donne une première consigne claire demandant une PRODUCTION (mail, tableau de synthèse/comparatif, note, compte rendu…).
4. Si tu demandes un tableau, précise qu’il doit être différent du PGI (tableau de synthèse ou comparatif).
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
    history = [m["content"] for m in st.session_state.messages]
    full_text = "\n".join(history)

    prompt_bilan = f"""
Tu es Inspecteur de l'Éducation nationale, jury CCF Bac Pro AGOrA.

Élève : {student_name}
Dossier travaillé : {dossier}

TRANSCRIPTION (dialogue tuteur / élève) :
{full_text}

Produis un bilan structuré pour le professeur :

1. Contexte professionnel (structure + mission).
2. Activités réalisées par l'élève.
3. Niveau atteint sur :
   - Communication écrite,
   - Usage des outils numériques (PGI / Word / Excel),
   - Respect des procédures administratives.
   Niveaux possibles : NOVICE / FONCTIONNEL / MAÎTRISE.
4. Appréciation globale (2 ou 3 phrases à la 3e personne).

Phrases courtes, style directement exploitable dans un dossier CCF.
"""

    msgs = [
        {"role": "system", "content": "Tu es un Inspecteur IEN neutre et bienveillant."},
        {"role": "user", "content": prompt_bilan},
    ]
    bilan, _ = query_groq_with_rotation(msgs)
    return bilan or "Impossible de générer le bilan (problème d'IA)."

# --- 12. INTERFACE GRAPHIQUE ---

LOGO_LYCEE = "logo_lycee.png"
LOGO_AGORA = "logo_agora.png"
BOT_AVATAR = LOGO_AGORA if os.path.exists(LOGO_AGORA) else "🤖"

# --- SIDEBAR ---
with st.sidebar:
    # DEBUG GROQ
    try:
        ks = get_api_keys_list()
        st.caption(f"🔍 Debug IA : {len(ks)} clé(s) Groq détectée(s).")
    except Exception as e:
        st.error(f"Erreur lecture des clés Groq : {e}")

    if os.path.exists(LOGO_LYCEE):
        st.image(LOGO_LYCEE, width=100)
    else:
        st.header("Lycée Pro")

    st.markdown("---")

    st.markdown(f"### 🏆 {st.session_state.grade}")
    st.progress(min(st.session_state.xp / 1000, 1.0))
    st.caption(f"XP : {st.session_state.xp}")

    student_name = st.text_input("Prénom de l'élève", placeholder="Ex : Camille")

    profil_eleve = st.selectbox(
        "Profil de l'élève (différenciation)",
        ["Accompagnement renforcé", "Standard", "Autonome"]
    )
    st.session_state.profil_eleve = profil_eleve

    st.subheader("📂 Sommaire (manuel Foucher)")
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
            lancer_mission(student_name, profil_eleve)
            st.rerun()
        else:
            st.warning("Merci de saisir le prénom de l'élève.")

    if st.button("✅ Étape validée", use_container_width=True):
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
                <div style="font-size:12px; color:#5F6368;">Exercices inspirés du manuel de 1re Bac Pro AGOrA</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c2:
    with st.popover("ℹ️ Aide Métier"):
        st.info("Appuie-toi sur ton manuel, tes cours et les sites officiels (service-public.fr, ameli.fr...).")

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

# --- FICHE D'AIDE ---

dossier_courant = st.session_state.dossier
fiche_aide = AIDES_DOSSIERS.get(dossier_courant)

if fiche_aide:
    with st.expander("📎 Fiche d'aide (résumé enseignant)", expanded=False):
        st.markdown(f"**Situation :** {fiche_aide['situation']}")
        st.markdown(f"**Contexte :** {fiche_aide['contexte']}")
        st.markdown("**Missions typiques :**")
        for m in fiche_aide["missions"]:
            st.markdown(f"- {m}")
        st.markdown(f"**Productions attendues :** {fiche_aide['types_production']}")

st.markdown("<br>", unsafe_allow_html=True)

# --- AFFICHAGE PGI ---

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
            if st.button("🔊 Lire", key=f"tts_{i}"):
                try:
                    tts = gTTS(clean_text_for_audio(msg["content"]), lang="fr")
                    buf = BytesIO()
                    tts.write_to_fp(buf)
                    st.audio(buf, format="audio/mp3", start_time=0)
                except Exception:
                    st.warning("Lecture audio impossible pour ce message.")

st.markdown("<br><br>", unsafe_allow_html=True)

st.markdown(
    '<div class="fixed-footer">Agence Pro\'AGOrA - Données 100 % fictives (structures inspirées du manuel, sans reproduction intégrale)</div>',
    unsafe_allow_html=True,
)

# --- INPUT & TOUR D'IA ---

if user_input := st.chat_input("Ta réponse (ou le résumé de ton Word / Excel)…"):
    if not student_name:
        st.toast("Identifie-toi avant de répondre (prénom).", icon="👤")
    else:
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.rerun()

if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant", avatar=BOT_AVATAR):
        with st.spinner("Analyse de ta réponse…"):
            pgi_str = ""
            if st.session_state.pgi_data is not None:
                pgi_str = st.session_state.pgi_data.to_string()

            dernier_texte_eleve = st.session_state.messages[-1]["content"]
            diff_instr = build_differentiation_instruction(st.session_state.profil_eleve)

            prompt_tour = f"""
{diff_instr}

DOSSIER : {st.session_state.dossier}
PARTIE : {st.session_state.theme}

DONNÉES PGI :
{pgi_str}

RÉPONSE DE L'ÉLÈVE :
\"\"\"{dernier_texte_eleve}\"\"\"

CONSigne :
1. Vérifie si l'élève exploite vraiment les données PGI ou le contexte du dossier.
2. Si c'est pertinent, valide un point précis, explique pourquoi c'est bien, puis propose la prochaine étape.
3. Si c'est incomplet ou hors sujet, explique ce qui manque en phrases courtes et donne une consigne guidée.
4. Si tu proposes un tableau, rappelle clairement qu'il s'agit d'un tableau de synthèse/comparatif différent du PGI.
5. Réponds avec des blocs courts et/ou listes à puces (pas de gros pavé).
"""

            msgs = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt_tour},
            ]
            resp, _ = query_groq_with_rotation(msgs)
            if resp is None:
                resp = "Je n'arrive pas à analyser ta réponse pour le moment. Préviens ton professeur."
            st.markdown(resp)
            st.session_state.messages.append({"role": "assistant", "content": resp})
