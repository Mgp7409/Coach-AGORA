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

    /* CHAT (style générique, sans cibler les rôles) */
    [data-testid="stChatMessage"] {{
        padding: 1rem;
        border-radius: 12px;
        margin-bottom: 0.5rem;
    }}

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
    if "groq_keys" in st.secrets:
        return st.secrets["groq_keys"]
    elif "GROQ_API_KEY" in st.secrets:
        return [st.secrets["GROQ_API_KEY"]]
    return []

def query_groq_with_rotation(messages):
    """
    Retourne (texte, modele) ou (None, 'ERREUR CONFIG' / 'SATURATION')
    """
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
                        messages=messages, model=model, temperature=0.3, max_tokens=1024
                    )
                    return chat.choices[0].message.content, model
                except Exception:
                    continue
        except Exception:
            continue
    return None, "SATURATION"

# --- 7. OUTILS ---
def extract_text_from_docx(file):
    try:
        doc = Document(file)
        text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        return text[:8000]
    except Exception as e:
        return str(e)

def clean_text_for_audio(text):
    text = re.sub(r'[\*_]{1,3}', '', text)
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'📎.*', '', text)
    return text

def add_notification(msg):
    ts = datetime.now().strftime("%H:%M")
    st.session_state.notifications.insert(0, f"{ts} - {msg}")

# --- 8. SOMMAIRE (STRUCTURE DES DOSSIERS) ---

DB_OFFICIELLE = {
    "1. La gestion opérationnelle des espaces de travail": {
        "1 Organiser le fonctionnement des espaces de travail":
            "Proposer un environnement de travail adapté et sélectionner les équipements nécessaires.",
        "2 Organiser l'environnement numérique d'un service":
            "Proposer un environnement numérique adapté, recenser les contraintes réglementaires et planifier la mise en œuvre de l'environnement numérique du service.",
        "3 Gérer les ressources partagées de l'organisation":
            "Mettre en place une nouvelle gestion du partage des ressources et proposer l'utilisation de nouveaux outils de partage.",
        "4 Organiser le partage de l'information":
            "Analyser la communication interne et définir une nouvelle stratégie de communication avec un outil collaboratif."
    },
    "2. Le traitement de formalités administratives liées aux relations avec les partenaires": {
        "5 Participer au lancement d'une nouvelle gamme":
            "Préparer le planigramme des tâches du lancement et assurer la communication avec les partenaires.",
        "6 Organiser et suivre des réunions":
            "Organiser une réunion de service et assurer le suivi administratif (compte rendu, relevé de décisions).",
        "7 Organiser un déplacement":
            "Préparer les modalités d'un déplacement professionnel et les formalités administratives associées."
    },
    "3. Le suivi administratif des relations avec le personnel": {
        "8 Participer au recrutement du personnel":
            "Préparer le recrutement et participer à la sélection de la ou du candidat(e).",
        "9 Participer à l'intégration du personnel":
            "Préparer l'accueil du(de la) nouvel(le) salarié(e) et contribuer à sa bonne intégration.",
        "10 Actualiser les dossiers du personnel":
            "Mettre à jour les dossiers du personnel (contrats, avenants, éléments administratifs)."
    }
}

# --- 8 bis. FICHES D'AIDE PAR DOSSIER ---

AIDES_DOSSIERS = {
    "1 Organiser le fonctionnement des espaces de travail": """
🎯 Objectif de la tâche
- Vérifier si les espaces de travail sont adaptés à l’activité.
- Identifier les manques ou les dysfonctionnements (confort, sécurité, ergonomie).
- Proposer des améliorations concrètes.

🧩 Méthode de travail
1. Observe les données du PGI (type de poste, effectif, remarques éventuelles).
2. Repère ce qui pose problème : surcharge, équipement manquant, matériel obsolète…
3. Classe tes constats : ce qui est à corriger en priorité / à revoir plus tard.
4. Propose des solutions précises : quel matériel ? pour quel poste ? à quel endroit ?
5. Reformule tes propositions dans un document clair et structuré.

📎 Productions possibles
- Tableau “Poste / Constats / Propositions”.
- Mail au responsable des services généraux.
- Note interne de synthèse présentant les améliorations à prévoir.
""",

    "2 Organiser l'environnement numérique d'un service": """
🎯 Objectif de la tâche
- Vérifier que chaque utilisateur dispose des bons outils numériques.
- Assurer la sécurité des accès (identifiants, droits, confidentialité).
- Organiser l’environnement numérique de façon cohérente et efficace.

🧩 Méthode de travail
1. Identifie les utilisateurs dans les données (fonctions, services, missions).
2. Liste les outils numériques nécessaires par profil (logiciels, accès dossiers, messagerie…).
3. Compare avec la situation actuelle : qui a trop d’accès ? qui n’en a pas assez ?
4. Repère les risques (partage de mot de passe, accès trop large, dossiers sensibles).
5. Propose une nouvelle organisation : droits d’accès, règles de nommage, bonnes pratiques.

📎 Productions possibles
- Tableau “Utilisateur / Outils nécessaires / Droits proposés”.
- Procédure interne sur les règles d’utilisation des outils numériques.
- Mail de rappel des bonnes pratiques de sécurité informatique.
""",

    "3 Gérer les ressources partagées de l'organisation": """
🎯 Objectif de la tâche
- Organiser l’accès à des ressources partagées (salles, véhicules, matériels, fournitures…).
- Limiter les conflits d’usage et les ruptures de stock.
- Mettre en place un suivi clair et exploitable.

🧩 Méthode de travail
1. Analyse les données (stocks, plannings, réservations, niveaux d’alerte).
2. Repère les problèmes : ruptures fréquentes, doublons, réservations en conflit…
3. Classe les ressources : très utilisées / peu utilisées / critiques.
4. Propose des règles de gestion (priorités, délais, seuils minimum, validation).
5. Prépare un support de suivi : tableau de réservation, grille de stock, planning.

📎 Productions possibles
- Nouveau tableau de gestion des ressources partagées.
- Note interne expliquant les nouvelles règles d’utilisation.
- Message d’information aux utilisateurs concernant la nouvelle organisation.
""",

    "4 Organiser le partage de l'information": """
🎯 Objectif de la tâche
- Assurer une circulation fluide et fiable de l’information dans le service.
- Choisir les bons canaux (mail, intranet, affichage, outil collaboratif).
- Harmoniser la présentation des informations.

🧩 Méthode de travail
1. Identifie les informations à partager (consignes, procédures, comptes rendus…).
2. Repère pour chaque info : qui doit la recevoir ? à quel moment ? par quel canal ?
3. Analyse les données existantes (doublons, infos manquantes, documents obsolètes).
4. Propose une organisation : dossiers partagés, droits d’accès, modèles de documents.
5. Prépare un exemple concret d’information partagée (message, note, publication).

📎 Productions possibles
- Schéma ou tableau “Type d’information / Destinataires / Canal / Fréquence”.
- Modèle d’email ou de note interne pour diffuser une information.
- Proposition de structure de dossier partagé (arborescence de fichiers).
""",

    "5 Participer au lancement d'une nouvelle gamme": """
🎯 Objectif de la tâche
- Préparer et organiser les actions administratives liées au lancement.
- Coordonner les intervenants (fournisseurs, clients, service com, service commercial).
- Assurer le suivi des éléments opérationnels (planning, stocks, supports).

🧩 Méthode de travail
1. Analyse les informations disponibles : produits, dates, quantités, interlocuteurs.
2. Liste toutes les tâches à réaliser avant, pendant et après le lancement.
3. Organise ces tâches dans un planning (qui fait quoi ? pour quand ?).
4. Vérifie les contraintes : délais fournisseurs, délais de livraison, validation interne.
5. Prépare un document de synthèse pour suivre l’avancement.

📎 Productions possibles
- Plan d’actions ou rétroplanning du lancement.
- Tableau “Tâche / Responsable / Date / Statut”.
- Mail de coordination adressé aux différents intervenants.
""",

    "6 Organiser et suivre des réunions": """
🎯 Objectif de la tâche
- Préparer une réunion efficace (ordre du jour, participants, documents).
- Assurer le suivi administratif avant et après la réunion.
- Tracer les décisions prises et les actions à mener.

🧩 Méthode de travail
1. Identifie l’objectif de la réunion et les thèmes à aborder.
2. Liste les participants indispensables et leurs rôles.
3. Prépare un ordre du jour clair et hiérarchisé.
4. Organise les éléments logistiques : salle, matériel, invitation, visio si besoin.
5. Après la réunion : note les décisions, les actions, les responsables et les échéances.

📎 Productions possibles
- Convocation ou invitation à la réunion (mail ou document).
- Ordre du jour structuré.
- Compte rendu ou relevé de décisions sous forme de tableau.
""",

    "7 Organiser un déplacement": """
🎯 Objectif de la tâche
- Préparer un déplacement professionnel dans le respect du budget et des règles de l’organisation.
- Coordonner transport, hébergement et contraintes horaires.
- Fournir au salarié un dossier de déplacement clair et complet.

🧩 Méthode de travail
1. Analyse les besoins : qui part ? quand ? pour quel motif ? où ? combien de temps ?
2. Recherche les solutions possibles (train, avion, hôtel…) en respectant les consignes internes.
3. Compare les options : coût, durée, horaires, conditions d’annulation.
4. Choisis la solution la plus adaptée et note les références (réservation, horaires, adresses).
5. Prépare un récapitulatif lisible pour le salarié et/ou la hiérarchie.

📎 Productions possibles
- Itinéraire détaillé (trajet, horaires, numéros de réservation).
- Tableau comparatif des solutions envisagées.
- Mail de confirmation du déplacement envoyé au salarié.
""",

    "8 Participer au recrutement du personnel": """
🎯 Objectif de la tâche
- Participer à la préparation d’un recrutement (profil, annonce, tri des candidatures).
- Respecter les règles de non-discrimination et de confidentialité.
- Faciliter le travail du recruteur ou du service RH.

🧩 Méthode de travail
1. Identifie le poste à pourvoir : missions, compétences, type de contrat, durée.
2. Vérifie ou rédige l’offre d’emploi (intitulé, profil recherché, lieu, horaires…).
3. Analyse les candidatures : CV, lettres, adéquation avec le profil.
4. Classe les candidatures (retenu / en attente / refusé) avec des critères objectifs.
5. Prépare les actions suivantes : convocations, demandes de compléments, réponses négatives.

📎 Productions possibles
- Grille de tri des candidatures (critères + appréciations).
- Projet de mail de convocation à un entretien.
- Modèle de réponse à une candidature non retenue.
""",

    "9 Participer à l'intégration du personnel": """
🎯 Objectif de la tâche
- Préparer l’arrivée d’un(e) nouveau(elle) salarié(e).
- Assurer les formalités administratives d’accueil.
- Faciliter son intégration dans l’équipe et l’organisation.

🧩 Méthode de travail
1. Liste les démarches à effectuer avant l’arrivée (compte informatique, badge, matériel, documents…).
2. Prépare le parcours d’intégration : qui va le/la accueillir ? quel programme le 1er jour ?
3. Vérifie les documents obligatoires (contrat, règlement intérieur, consignes de sécurité).
4. Prépare un kit d’accueil (documents utiles, contacts, planning).
5. Organise éventuellement une présentation au reste de l’équipe.

📎 Productions possibles
- Check-list “À faire avant l’arrivée / le jour J / la première semaine”.
- Mail d’accueil envoyé au nouveau salarié.
- Programme d’intégration sur 1 ou 2 jours.
""",

    "10 Actualiser les dossiers du personnel": """
🎯 Objectif de la tâche
- Mettre à jour les informations administratives des salariés.
- Vérifier la conformité des dossiers (contrats, avenants, justificatifs).
- Tracer correctement les changements (fonction, durée du travail, rémunération…).

🧩 Méthode de travail
1. Identifie les dossiers concernés : nouveaux embauchés, changements récents, régularisations.
2. Compare les informations du PGI avec les documents reçus (contrat, avenant, courrier).
3. Repère les éléments manquants ou incohérents (dates, coefficients, horaires…).
4. Mets à jour les champs nécessaires dans le PGI, en respectant la procédure.
5. Si besoin, prépare une demande de document complémentaire au salarié.

📎 Productions possibles
- Tableau de suivi des dossiers mis à jour.
- Mail au salarié pour demander un justificatif ou confirmer une modification.
- Note interne signalant une mise à jour importante (changement de poste, de service…).
"""
}

# --- 9. GÉNÉRATEUR PGI INTELLIGENT (Par Dossier) ---
def generate_fake_pgi_data(dossier_name):
    rows = []

    # 1 Organiser le fonctionnement des espaces de travail
    if dossier_name.startswith("1 "):
        postes = ["Accueil", "Comptabilité", "Direction", "Open space", "Archivage"]
        for p in postes:
            rows.append({
                "Poste": p,
                "Effectif": random.randint(1, 6),
                "Équipement principal": random.choice(["Bureau + PC", "PC portable", "Poste partagé"]),
                "État": random.choice(["Conforme", "À améliorer", "Saturé"]),
                "Remarque": random.choice(["Manque de rangements", "Problème de bruit", "Rien à signaler"])
            })

    # 2 Organiser l'environnement numérique d'un service
    elif dossier_name.startswith("2 "):
        for i in range(6):
            rows.append({
                "Salarié": random.choice(PRENOMS) + " " + random.choice(NOMS),
                "Fonction": random.choice(["Assistant", "Comptable", "Technicien", "Commercial"]),
                "Logiciels nécessaires": random.choice(["Suite bureautique", "PGI complet", "Outil CRM", "Outil comptable"]),
                "Accès dossiers": random.choice(["Partagé", "Limité", "Trop large"]),
                "Problème signalé": random.choice(["Mot de passe partagé", "Droit manquant", "Aucun"])
            })

    # 3 Gérer les ressources partagées de l'organisation
    elif dossier_name.startswith("3 "):
        ressources = ["Salle réunion A", "Salle réunion B", "Véhicule 1", "Véhicule 2", "Vidéo-projecteur"]
        for r in ressources:
            rows.append({
                "Ressource": r,
                "Type": random.choice(["Salle", "Véhicule", "Matériel"]),
                "Taux d'utilisation": f"{random.randint(30, 100)}%",
                "Conflits recensés": random.randint(0, 5),
                "Commentaire": random.choice(["Souvent réservée", "Peu utilisée", "Utilisation à organiser"])
            })

    # 4 Organiser le partage de l'information
    elif dossier_name.startswith("4 "):
        infos = ["Consignes de sécurité", "Planning mensuel", "Procédure accueil", "Notes de service", "Compte rendu réunion"]
        for info in infos:
            rows.append({
                "Information": info,
                "Support actuel": random.choice(["Mail", "Affichage", "Intranet", "Oral uniquement"]),
                "Destinataires": random.choice(["Tous", "Service compta", "Direction", "Atelier"]),
                "Fréquence": random.choice(["Ponctuelle", "Hebdomadaire", "Mensuelle"]),
                "Problème": random.choice(["Information perdue", "Non à jour", "Trop de doublons", "Aucun"])
            })

    # 5 Participer au lancement d'une nouvelle gamme
    elif dossier_name.startswith("5 "):
        taches = ["Création supports", "Commande échantillons", "Formation vendeurs", "Mise à jour tarifs", "Communication réseaux"]
        for t in taches:
            rows.append({
                "Tâche": t,
                "Responsable": random.choice(PRENOMS),
                "Échéance": f"{random.randint(1, 30)}/09/2025",
                "Statut": random.choice(["À faire", "En cours", "Terminé"]),
                "Priorité": random.choice(["Haute", "Moyenne", "Basse"])
            })

    # 6 Organiser et suivre des réunions
    elif dossier_name.startswith("6 "):
        for i in range(5):
            rows.append({
                "Réunion": f"Réunion {i+1}",
                "Objet": random.choice(["Point commercial", "Point RH", "Sécurité", "Projet X"]),
                "Date": f"{random.randint(1, 28)}/10/2025",
                "Participants prévus": random.randint(3, 12),
                "Compte rendu": random.choice(["Non rédigé", "En cours", "Archivé"])
            })

    # 7 Organiser un déplacement
    elif dossier_name.startswith("7 "):
        villes = ["Paris", "Lyon", "Marseille", "Toulouse", "Bordeaux"]
        for i in range(4):
            rows.append({
                "Salarié": random.choice(PRENOMS) + " " + random.choice(NOMS),
                "Destination": random.choice(villes),
                "Motif": random.choice(["Salon pro", "Formation", "Rendez-vous client"]),
                "Dates": f"{random.randint(5,10)}/11 au {random.randint(11,15)}/11/2025",
                "Statut réservation": random.choice(["À faire", "Confirmée", "En attente validation"])
            })

    # 8 Participer au recrutement du personnel
    elif dossier_name.startswith("8 "):
        postes = ["Assistant administratif", "Technicien support", "Comptable"]
        for _ in range(6):
            rows.append({
                "Candidat": f"{random.choice(PRENOMS)} {random.choice(NOMS)}",
                "Poste visé": random.choice(postes),
                "Diplôme": random.choice(["Bac Pro", "BTS", "Licence"]),
                "Expérience": f"{random.randint(0, 5)} ans",
                "Statut dossier": random.choice(["À étudier", "Retenu", "Refusé"])
            })

    # 9 Participer à l'intégration du personnel
    elif dossier_name.startswith("9 "):
        étapes = ["Préparation poste", "Création compte informatique", "Remise badge", "Présentation équipe", "Formation sécurité"]
        for e in étapes:
            rows.append({
                "Étape": e,
                "Responsable": random.choice(["RH", "Manager", "Accueil"]),
                "Délai": random.choice(["Avant arrivée", "Jour J", "Semaine 1"]),
                "Statut": random.choice(["À faire", "En cours", "Terminé"]),
                "Commentaire": random.choice(["Prioritaire", "Peut être délégué", "À vérifier"])
            })

    # 10 Actualiser les dossiers du personnel
    elif dossier_name.startswith("10 "):
        for _ in range(6):
            rows.append({
                "Salarié": f"{random.choice(PRENOMS)} {random.choice(NOMS)}",
                "Type de modification": random.choice(["Avenant temps de travail", "Changement de poste", "Mise à jour adresse"]),
                "Document reçu": random.choice(["Oui", "Non"]),
                "PGI à jour": random.choice(["Oui", "Non"]),
                "Remarque": random.choice(["Relancer salarié", "Faire signer", "Archiver"])
            })

    else:
        rows.append({"Info": "Pas de données spécifiques pour ce dossier."})

    return pd.DataFrame(rows)

# --- 10. IA (PROMPT "EVALUATEUR CCF") ---
SYSTEM_PROMPT = """
RÔLE : Tu es le Tuteur de stage et Evaluateur CCF (Bac Pro AGOrA).
TON : Professionnel, directif.

OBJECTIF : Faire réaliser une TÂCHE ADMINISTRATIVE liée au DOSSIER choisi.

CONSIGNE À L'IA :
1. IDENTIFIE la tâche du dossier.
2. UTILISE LE PGI : Les données sont ci-dessous. Interroge l'élève dessus.
3. NE DONNE PAS LA RÉPONSE.
4. DEMANDE UNE PRODUCTION (Mail, Tableau, Courrier).

SÉCURITÉ : Données réelles -> STOP.
"""

INITIAL_MESSAGE = """
👋 **Bonjour.**

Bienvenue dans le module **Pro'AGOrA**.
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
        resp, status = query_groq_with_rotation(msgs)
        if resp is None:
            resp = "⚠️ L'agent n'est pas disponible pour le moment (problème de configuration ou saturation). Préviens ton professeur."
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

    msgs = [{"role": "system", "content": "Tu es un Inspecteur IEN neutre et bienveillant."},
            {"role": "user", "content": prompt_bilan}]
    resp, status = query_groq_with_rotation(msgs)
    if resp is None:
        resp = "⚠️ Impossible de générer le bilan pour le moment (problème de configuration ou saturation de l'IA)."
    return resp

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

    # Journal de bord / notifications
    with st.expander("📝 Journal de bord"):
        for note in st.session_state.notifications[:10]:
            st.caption(note)

    student_name = st.text_input("Prénom", placeholder="Ex: Camille")

    st.subheader("📂 Dossiers")
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

    # OUTILS - Rendu Word
    st.markdown("---")
    uploaded_file = st.file_uploader("Rendre un travail (Word)", type=['docx'], key="word_uploader")
    if uploaded_file and student_name:
        if st.button("Envoyer", key="btn_envoyer_word"):
            txt = extract_text_from_docx(uploaded_file)
            st.session_state.messages.append({"role": "user", "content": f"PROPOSITION : {txt}"})
            update_xp(20)
            add_notification(f"Document Word remis par {student_name}")
            st.rerun()

    # OUTILS - Charger une sauvegarde CSV
    st.markdown("---")
    csv_upload = st.file_uploader("Charger une sauvegarde (CSV)", type=['csv'], key="csv_loader")
    if csv_upload is not None:
        if st.button("Importer la sauvegarde", key="btn_import_csv"):
            try:
                df_chat = pd.read_csv(csv_upload)
                if {"role", "content"}.issubset(df_chat.columns):
                    st.session_state.messages = df_chat[["role", "content"]].to_dict(orient="records")
                    add_notification("Sauvegarde CSV importée.")
                    st.success("Conversation rechargée depuis le fichier CSV.")
                    st.rerun()
                else:
                    st.error("Le fichier CSV ne contient pas les colonnes 'role' et 'content'.")
            except Exception as e:
                st.error(f"Erreur lors de la lecture du CSV : {e}")

    # BILAN
    st.markdown("---")
    if st.button("📝 Générer Bilan CCF"):
        if not student_name:
            st.warning("Prénom requis pour générer le bilan.")
        elif len(st.session_state.messages) <= 2:
            st.warning("Travaillez d'abord avec l'agent avant de générer un bilan.")
        else:
            with st.spinner("Rédaction du Bilan Officiel..."):
                bilan = generer_bilan_ccf(student_name, st.session_state.dossier)
                st.session_state.bilan_ready = bilan
                add_notification(f"Bilan CCF généré pour {student_name}")
            st.rerun()

    if st.session_state.bilan_ready:
        st.download_button(
            label="📥 Télécharger Fiche Bilan",
            data=st.session_state.bilan_ready,
            file_name=f"Bilan_CCF_{student_name if student_name else 'Eleve'}.txt",
            mime="text/plain"
        )

    # SAUVEGARDE
    csv_data = ""
    btn_state = True
    if len(st.session_state.messages) > 0:
        chat_df = pd.DataFrame(st.session_state.messages)
        csv_data = chat_df.to_csv(index=False).encode('utf-8')
        btn_state = False

    st.download_button("💾 Sauvegarder la conversation", csv_data, "agora_save.csv", "text/csv", disabled=btn_state)

    if st.button("🗑️ Reset"):
        st.session_state.messages = [{"role": "assistant", "content": INITIAL_MESSAGE}]
        st.session_state.pgi_data = None
        st.session_state.bilan_ready = None
        add_notification("Réinitialisation de la session.")
        st.rerun()

# --- HEADER ---
c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 1])
with c1:
    logo_html = ""
    if os.path.exists(LOGO_AGORA):
        b64 = img_to_base64(LOGO_AGORA)
        logo_html = f'<img src="data:image/png;base64,{b64}" style="height:40px; margin-right:10px;">'
    st.markdown(
        f"""<div style="display:flex; align-items:center;">
        {logo_html}
        <div>
            <div style="font-size:22px; font-weight:bold; color:#202124;">Agence Pro'AGOrA</div>
            <div style="font-size:12px; color:#5F6368;">Données fictives uniquement</div>
        </div>
        </div>""",
        unsafe_allow_html=True
    )

with c2:
    with st.popover("ℹ️ Aide Métier"):
        st.info("Consultez vos cours ou des ressources métier pour répondre.")
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

    # AIDE LIÉE AU DOSSIER
    aide = AIDES_DOSSIERS.get(st.session_state.dossier)
    with st.expander("📘 Aide pour réussir cet exercice"):
        if aide:
            st.markdown(aide)
        else:
            st.info("Aucune fiche d'aide n'est encore définie pour ce dossier.")

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
                except Exception:
                    pass

st.markdown("<br><br>", unsafe_allow_html=True)

# --- INPUT ---
st.markdown('<div class="fixed-footer">Agence Pro\'AGOrA - Données Fictives Uniquement</div>', unsafe_allow_html=True)

if user_input := st.chat_input("Votre réponse..."):
    if not student_name:
        st.toast("Identifiez-vous !", icon="👤")
    else:
        st.session_state.messages.append({"role": "user", "content": user_input})
        add_notification(f"Réponse élève : {student_name}")
        st.rerun()

if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant", avatar=BOT_AVATAR):
        with st.spinner("Analyse..."):
            sys = SYSTEM_PROMPT
            pgi_str = ""
            if st.session_state.pgi_data is not None:
                pgi_str = st.session_state.pgi_data.to_string()

            aide_dossier = AIDES_DOSSIERS.get(st.session_state.dossier, "")

            prompt_tour = f"""
            DONNÉES PGI (PREUVE) : {pgi_str}
            RÉPONSE ÉLÈVE : "{user_input}"
            MISSION : {st.session_state.dossier}

            RÉFÉRENCE PÉDAGOGIQUE (à utiliser comme ligne directrice, sans la restituer telle quelle) :
            {aide_dossier}

            CONSIGNE :
            1. Vérifie si l'élève utilise bien le PGI.
            2. Si oui, valide et demande la production suivante (mail, tableau, note...).
            3. Si non, corrige-le et redirige-le vers les données utiles.
            """

            msgs = [{"role": "system", "content": sys}, {"role": "user", "content": prompt_tour}]
            resp, status = query_groq_with_rotation(msgs)
            if resp is None:
                resp = "⚠️ L'agent ne peut pas analyser ta réponse pour le moment. Préviens ton professeur."
            st.markdown(resp)
            st.session_state.messages.append({"role": "assistant", "content": resp})
            add_notification("Réponse de l'agent générée.")
