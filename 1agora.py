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

# --- 8. SOMMAIRE OFFICIEL (simplifié ici, déjà aligné) ---

DB_OFFICIELLE = {
    "La gestion opérationnelle des espaces de travail": {
        "Dossier 1 – Organiser le fonctionnement des espaces de travail":
            "Modes de travail, aménagement open space, matériel, PGI.",
        "Dossier 2 – Organiser l’environnement numérique d’un service":
            "Réseaux, ENT, cloud, RGPD, plan de déploiement numérique.",
        "Dossier 3 – Gérer les ressources partagées de l’organisation":
            "Stocks, fournitures, salles, véhicules, outils de réservation.",
        "Dossier 4 – Organiser le partage de l’information":
            "Diagnostic de la communication interne et déploiement d’un outil collaboratif."
    },
    "Le traitement de formalités administratives liées aux relations avec les partenaires": {
        "Dossier 5 – Participer au lancement d’une nouvelle gamme":
            "Planigramme, négociation fournisseur, communication multicanale.",
        "Dossier 6 – Organiser et suivre des réunions":
            "Réunions de service, visioconférences, comptes rendus.",
        "Dossier 7 – Organiser un déplacement":
            "Organisation pratique du déplacement et formalités."
    },
    "Le suivi administratif des relations avec le personnel": {
        "Dossier 8 – Participer au recrutement du personnel":
            "Préparation du recrutement, tri et sélection des candidatures.",
        "Dossier 9 – Participer à l’intégration du personnel":
            "Accueil, parcours d’intégration, cohésion.",
        "Dossier 10 – Actualiser les dossiers du personnel":
            "Contrats, avenants, complétude des dossiers."
    }
}

# --- 8 bis. AIDES DOSSIERS (raccourcies) ---

AIDES_DOSSIERS = {
    "Dossier 7 – Organiser un déplacement": {
        "situation": "L’entreprise organise le déplacement de plusieurs salariés pour un salon ou une formation.",
        "contexte": "Il faut choisir le transport et l’hébergement, respecter un budget et les règles internes.",
        "missions": [
            "Comparer plusieurs solutions de transport / hébergement.",
            "Préparer les réservations et vérifier les horaires.",
            "Préparer un récapitulatif clair pour le salarié."
        ],
        "types_production": "Tableau comparatif (critères), feuille de route, mail de confirmation."
    },
    # (les autres dossiers peuvent rester comme dans ta version précédente ; je garde l’exemple clé ici)
}

# --- 9. GÉNÉRATEUR PGI (exemple identique à ta version précédente, pas modifié ici sauf noms) ---

def generate_fake_pgi_data(dossier_name: str) -> pd.DataFrame:
    rows = []

    if "Dossier 7" in dossier_name:
        for _ in range(5):
            rows.append({
                "Salarié": f"{random.choice(PRENOMS)} {random.choice(NOMS)}",
                "Ville": random.choice(["Paris", "Lyon", "Marseille", "Bordeaux"]),
                "Transport": random.choice(["Train", "Avion", "Voiture"]),
                "Hébergement": random.choice(["Hôtel", "Airbnb", "Chez partenaire"]),
                "Coût estimé": f"{random.randint(150, 600)} €",
                "Statut": "À comparer"
            })
    else:
        # simple fallback pour les autres dossiers (à reprendre de ta version précédente)
        for _ in range(5):
            rows.append({
                "Info": "Données fictives à définir pour ce dossier."
            })

    return pd.DataFrame(rows)

# --- 10. PROFIL ÉLÈVE & PROMPTS IA ---

def build_differentiation_instruction(profil: str) -> str:
    if profil == "Accompagnement renforcé":
        return """
NIVEAU ÉLÈVE : Besoin d'aide important.
- Utilise des phrases très simples.
- Découpe la tâche en petites étapes numérotées (1, 2, 3...).
- Donne un exemple très court si nécessaire.
- Propose régulièrement de reformuler.
"""
    elif profil == "Autonome":
        return """
NIVEAU ÉLÈVE : Autonome.
- Contextualise rapidement.
- Donne des consignes plus ouvertes.
- Laisse l’élève proposer ses propres choix (tu valideras ensuite).
"""
    else:  # Standard
        return """
NIVEAU ÉLÈVE : Standard.
- Donne une consigne claire et une ou deux étapes clés.
- Tu peux proposer un exemple de structure sans remplir tout le contenu.
"""

SYSTEM_PROMPT = """
RÔLE : Tu es le Tuteur de stage et Evaluateur CCF (Bac Pro AGOrA).
TON : Professionnel, bienveillant, directif.

OBJECTIF :
- Faire réaliser à l'élève une TÂCHE ADMINISTRATIVE liée au DOSSIER choisi.
- L'aider à produire un document métier (mail, note, tableau de synthèse, compte rendu...).

RÈGLES DE PRÉSENTATION :
- Quand tu présentes le contexte : 3 à 4 puces maximum, pas de long paragraphe.
- Quand tu donnes une consigne : une phrase courte + éventuellement une micro-liste d’étapes.
- Pas de texte compact de plus de 7 lignes d’affilée.
- Tu peux utiliser des listes à puces pour faciliter la lecture.

IMPORTANT SUR LES TABLEAUX :
- Les tableaux fournis dans le PGI sont des DONNÉES BRUTES.
- Si tu demandes de « faire un tableau », il doit être DIFFÉRENT :
  - tableau de synthèse,
  - tableau comparatif,
  - tableau de plan d’actions ou de suivi.
- Ne demande jamais de recopier exactement le tableau du PGI.
"""

INITIAL_MESSAGE = """
👋 **Bienvenue dans Agence Pro'AGOrA**

1. Choisis ta **Partie** et ton **Dossier** dans la barre de gauche.  
2. Sélectionne ton **Profil d’élève**.  
3. Clique sur **LANCER LA MISSION**.  
4. Lis le tableau (PGI) et la fiche d’aide si elle est proposée, puis réponds dans le chat.
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
RAPPEL DU CONTEXTE D'EXERCICE (extrait enseignant) :
- Situation : {aide['situation']}
- Contexte : {aide['contexte']}
- Missions possibles : {", ".join(aide['missions'])}
- Types de productions : {aide['types_production']}
"""

    prompt = f"""
{diff_instr}

DOSSIER : {dossier}
PARTIE : {theme}

{aide_txt}

LIEU FICTIF : {lieu} situé à {ville}.
ÉLÈVE : {prenom} (Bac Pro AGOrA).
COMPÉTENCE VISÉE : {competence}

DONNÉES PGI (fictives à utiliser comme base) :
{pgi_txt}

ACTION ATTENDUE DE TA PART :
1. Présente le contexte en 3 à 4 puces maximum.
2. Explique la mission à l'élève en 1 ou 2 phrases courtes.
3. Donne une première consigne claire qui demande une PRODUCTION (mail, tableau de synthèse, note, compte rendu...).
4. Si tu demandes un tableau, impose qu'il s'agisse d'un tableau de synthèse ou comparatif, différent du PGI.
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

TRANSCRIPTION DE LA SÉANCE (dialogue tuteur / élève) :
{full_text}

Produis un bilan clair et structuré pour le professeur :

1. Contexte professionnel (structure + mission).
2. Activités réalisées par l'élève.
3. Niveau atteint sur :
   - Communication écrite,
   - Usage des outils numériques (PGI / Word / Excel),
   - Respect des procédures administratives.
   (Niveaux : NOVICE / FONCTIONNEL / MAÎTRISE)
4. Appréciation globale en 2 à 3 phrases.

Style : phrases courtes, directement exploitables dans un dossier CCF.
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

    st.markdown(f"### 🏆 {st.session_state.grade}")
    st.progress(min(st.session_state.xp / 1000, 1.0))
    st.caption(f"XP : {st.session_state.xp}")

    student_name = st.text_input("Prénom de l'élève", placeholder="Ex : Camille")

    profil_eleve = st.selectbox(
        "Profil de l'élève (différenciation)",
        ["Accompagnement renforcé", "Standard", "Autonome"]
    )
    st.session_state.profil_eleve = profil_eleve

    st.subheader("📂 Sommaire (Foucher)")
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
        st.info("Appuie-toi sur le manuel, les cours et les sites officiels (service-public.fr, ameli.fr...).")

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

# --- FICHE D'AIDE (si dispo) ---

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
    '<div class="fixed-footer">Agence Pro\'AGOrA - Données 100 % fictives</div>',
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
5. Réponds sous forme de blocs courts et/ou listes à puces (pas de gros pavé).
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
