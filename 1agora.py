				Python PROAGORA
import streamlit as st
import pandas as pd
from groq import Groq
from datetime import datetime
from gtts import gTTS
import io
import re
import docx
from pypdf import PdfReader

# --- 1. CONFIGURATION ---
# J'ai ajouté initial_sidebar_state="expanded" pour forcer le volet à s'ouvrir
st.set_page_config(page_title="1AGORA", page_icon="🏢", initial_sidebar_state="expanded")

# --- 2. GESTION DU STYLE (ACCESSIBILITÉ) ---
if "mode_dys" not in st.session_state:
    st.session_state.mode_dys = False

# Si Mode DYS activé : Police adaptée et gros caractères
if st.session_state.mode_dys:
    st.markdown("""
    <style>
    html, body, [class*="css"] {
        font-family: 'Verdana', sans-serif !important;
        font-size: 18px !important;
        line-height: 1.8 !important;
        letter-spacing: 0.5px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# J'ai SUPPRIMÉ le code qui cachait le menu du haut pour que vous puissiez partager l'appli.

st.title("♾️ Agence PRO'AGORA")
st.caption("Simulation Professionnelle Gamifiée")

# --- 3. CONNEXION ---
try:
    api_key = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=api_key)
except:
    st.error("⚠️ Clé API manquante.")
    st.stop()

# --- 4. FONCTIONS UTILITAIRES ---
def extract_text_from_file(uploaded_file):
    text = ""
    try:
        if uploaded_file.name.endswith(".docx"):
            doc = docx.Document(uploaded_file)
            for para in doc.paragraphs: text += para.text + "\n"
        elif uploaded_file.name.endswith(".pdf"):
            reader = PdfReader(uploaded_file)
            for page in reader.pages: text += page.extract_text() + "\n"
        elif uploaded_file.name.endswith(".txt"):
            text = uploaded_file.read().decode("utf-8")
        return text
    except Exception as e: return f"Erreur lecture : {e}"

def clean_text_for_audio(text):
    text = re.sub(r'[\*_]{1,3}', '', text) # Enlève gras/italique
    text = re.sub(r'#+', '', text) # Enlève titres
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text) # Enlève liens
    text = re.sub(r'^\s*-\s+', '', text, flags=re.MULTILINE) # Enlève puces
    return text

# --- 5. STRUCTURE DU LIVRE (TITRES PROPRES) ---
DB_PREMIERE = {
    "GESTION DES ESPACES DE TRAVAIL": {
        "Aménagement des espaces": "COMPÉTENCE : Proposer un aménagement de bureau ergonomique et choisir le mobilier adapté.",
        "Environnement numérique": "COMPÉTENCE : Lister le matériel informatique, les logiciels et vérifier les règles RGPD.",
        "Ressources partagées": "COMPÉTENCE : Gérer le stock de fournitures (commandes/partage) et les réservations (salles/véhicules).",
        "Partage de l'information": "COMPÉTENCE : Améliorer la communication interne (Note de service, Outils collaboratifs, Agenda)."
    },
    "GESTION DES RELATIONS PARTENAIRES": {
        "Lancement produit / Vente": "COMPÉTENCE : Planifier des tâches (Planigramme), Négocier un prix de vente, Communication commerciale.",
        "Organisation de réunions": "COMPÉTENCE : Convoquer les participants, Réserver la salle, Préparer l'ordre du jour, Rédiger le Compte-Rendu.",
        "Organisation déplacement": "COMPÉTENCE : Réserver un déplacement (Train/Avion/Hôtel) avec budget contraint. Établir l'Ordre de Mission."
    },
    "GESTION DES RESSOURCES HUMAINES": {
        "Recrutement": "COMPÉTENCE : Définir le Profil de poste, Rédiger l'annonce d'embauche, Trier des CV.",
        "Intégration du personnel": "COMPÉTENCE : Préparer l'arrivée (matériel, badges), Créer le livret d'accueil, Organiser l'accueil.",
        "Dossiers du personnel": "COMPÉTENCE : Rédiger un Contrat de travail, Mettre à jour le Registre Unique du Personnel, Faire un Avenant."
    },
    "SCÉNARIOS TRANSVERSAUX": {
        "Réorganisation complète": "COMPÉTENCE : Projet global de déménagement ou de réaménagement des services.",
        "Campagne de Recrutement": "COMPÉTENCE : Projet global de recrutement (de l'annonce à l'intégration)."
    }
}

DB_SECONDE = {
    "Révisions 2nde": {
        "Accueil physique et téléphonique": "COMPÉTENCE : Accueil physique et téléphonique (Filtrage, Prise de message).",
        "Gestion du courrier": "COMPÉTENCE : Tri du courrier (Arrivée/Départ) et Enregistrement.",
        "Classement et Archivage": "COMPÉTENCE : Organisation de l'arborescence numérique."
    }
}

# --- 6. GAMIFICATION ---
GRADES = {
    0: "👶 Stagiaire",
    100: "👦 Assistant(e) Junior",
    300: "👨‍💼 Assistant(e) Confirmé(e)",
    600: "👩‍💻 Responsable de Pôle",
    1000: "👑 Assistant(e) de Direction"
}

if "xp" not in st.session_state: st.session_state.xp = 0

def get_grade(xp):
    current_grade = "Stagiaire"
    for palier, titre in GRADES.items():
        if xp >= palier:
            current_grade = titre
    return current_grade

def ajouter_xp():
    st.session_state.xp += 50
    st.balloons()
    st.toast("Bravo ! +50 XP 🚀", icon="⭐")

# --- 7. CERVEAU (PROMPT) ---
def get_system_prompt(simplified_mode):
    base_prompt = """
    TU ES : Le Superviseur de l'Agence PRO'AGORA.
    RÈGLES DU JEU :
    1. L'élève choisit une mission. TU DOIS INVENTER un scénario d'entreprise aléatoire (Nom, Chiffres, Contexte) immédiatement.
    2. Fournis les données brutes dès le début.
    3. Ne fais jamais le travail à la place de l'élève.
    4. À la fin, génère un BILAN D'ÉVALUATION (Points forts / Points à améliorer).
    """
    if simplified_mode:
        base_prompt += """
        ⚠️ MODE ACCESSIBILITÉ : Fais des phrases courtes. Utilise des listes à puces. Mets les mots clés en GRAS.
        """
    return base_prompt

# --- 8. LOGS ---
if "conversation_log" not in st.session_state: st.session_state.conversation_log = []
if "messages" not in st.session_state: st.session_state.messages = []

def save_log(student_id, role, content):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.conversation_log.append({
        "Heure": ts,
        "Eleve": student_id,
        "Role": role,
        "Message": content,
        "XP_Sauvegarde": st.session_state.xp
    })

def lancer_mission():
    base = DB_PREMIERE if st.session_state.niveau_select == "1ère (Livre Foucher)" else DB_SECONDE
    theme = st.session_state.theme_select
    dossier = st.session_state.dossier_select
    competence = base[theme][dossier]
    
    st.session_state.messages = []
    prompt_demarrage = f"Mission : '{dossier}' ({competence}). Invente le scénario et donne les consignes."
    
    try:
        msgs = [{"role": "system", "content": get_system_prompt(st.session_state.mode_simple)}]
        msgs.append({"role": "user", "content": prompt_demarrage})
        
        completion = client.chat.completions.create(messages=msgs, model="llama-3.3-70b-versatile", temperature=0.8)
        intro_bot = completion.choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": intro_bot})
    except Exception as e:
        st.error(f"Erreur IA : {e}")

# --- 9. INTERFACE SIDEBAR ---
with st.sidebar:
    st.header("👤 Profil")
    student_id = st.text_input("Prénom :", key="prenom_eleve")
    
    # Gamification
    grade_actuel = get_grade(st.session_state.xp)
    st.metric("Niveau & XP", value=f"{st.session_state.xp} XP", delta=grade_actuel)
    progress_val = min(st.session_state.xp / 1000, 1.0)
    st.progress(progress_val)
    
    st.markdown("---")
    st.header("♿ Accessibilité")
    st.session_state.mode_dys = st.checkbox("👁️ DYS (Gros caractères)")
    st.session_state.mode_simple = st.checkbox("🧠 Consignes Simplifiées")
    st.session_state.mode_audio = st.checkbox("🔊 Lecture Audio")

    st.markdown("---")
    st.header("🗂️ Missions")
    niveau = st.radio("Livre :", ["1ère (Livre Foucher)", "2nde (Révisions)"], key="niveau_select")
    base_active = DB_PREMIERE if niveau == "1ère (Livre Foucher)" else DB_SECONDE
    theme = st.selectbox("Thème :", list(base_active.keys()), key="theme_select")
    dossier = st.selectbox("Mission :", list(base_active[theme].keys()), key="dossier_select")
    
    col1, col2 = st.columns(2)
    with col1:
        st.button("🚀 LANCER", type="primary", on_click=lancer_mission)
    with col2:
        st.button("✅ FINIR", on_click=ajouter_xp)

    st.markdown("---")
    # Sauvegarde
    if st.session_state.conversation_log:
        df = pd.DataFrame(st.session_state.conversation_log)
        csv = df.to_csv(index=False, sep=';').encode('utf-8-sig')
        st.download_button("📥 Télécharger (CSV)", csv, "suivi_1agora.csv", "text/csv")
    
    # Reprise
    uploaded_csv = st.file_uploader("Reprendre (CSV)", type=['csv'])
    if uploaded_csv and st.button("🔄 Restaurer"):
        try:
            df_hist = pd.read_csv(uploaded_csv, sep=';')
            st.session_state.messages = []
            st.session_state.conversation_log = []
            if 'XP_Sauvegarde' in df_hist.columns:
                st.session_state.xp = int(df_hist['XP_Sauvegarde'].iloc[-1])
            for _, row in df_hist.iterrows():
                role_chat = "user" if row['Role'] == "Eleve" else "assistant"
                st.session_state.messages.append({"role": role_chat, "content": row['Message']})
                save_log(row.get('Eleve', student_id), row['Role'], row['Message'])
            st.success(f"Restauré ! Niveau : {st.session_state.xp} XP")
            st.rerun()
        except: st.error("Fichier invalide.")

# --- 10. CHAT & AUDIO ---
if not st.session_state.messages:
    st.info("👋 Bonjour ! Configure tes options à gauche et lance une mission.")
else:
    for i, msg in enumerate(st.session_state.messages):
        st.chat_message(msg["role"]).write(msg["content"])
        
        # LECTEUR AUDIO
        if st.session_state.mode_audio and msg["role"] == "assistant":
            if f"audio_{i}" not in st.session_state:
                try:
                    clean_text = clean_text_for_audio(msg["content"])
                    tts = gTTS(text=clean_text, lang='fr')
                    audio_buffer = io.BytesIO()
                    tts.write_to_fp(audio_buffer)
                    st.session_state[f"audio_{i}"] = audio_buffer
                except: pass
            if f"audio_{i}" in st.session_state:
                st.audio(st.session_state[f"audio_{i}"], format="audio/mp3")

    # DÉPÔT FICHIER
    with st.expander("📎 Joindre un fichier (Word/PDF)"):
        uploaded_doc = st.file_uploader("Fichier à corriger", type=['docx', 'pdf', 'txt'], key="doc_upload")
        if uploaded_doc and st.button("Envoyer fichier"):
            content = extract_text_from_file(uploaded_doc)
            user_msg = f"📄 Fichier **{uploaded_doc.name}** : {content}"
            st.chat_message("user").write(f"📄 *Fichier envoyé : {uploaded_doc.name}*")
            st.session_state.messages.append({"role": "user", "content": user_msg})
            save_log(student_id, "Eleve", f"[FICHIER] {uploaded_doc.name}")
            try:
                msgs = [{"role": "system", "content": get_system_prompt(st.session_state.mode_simple)}] + [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
                completion = client.chat.completions.create(messages=msgs, model="llama-3.3-70b-versatile", temperature=0.7)
                rep = completion.choices[0].message.content
                st.chat_message("assistant").write(rep)
                st.session_state.messages.append({"role": "assistant", "content": rep})
                save_log(student_id, "Superviseur", rep)
                st.rerun()
            except Exception as e: st.error(f"Erreur : {e}")

    # SAISIE
    if prompt := st.chat_input("Votre réponse..."):
        if not student_id: st.warning("⚠️ Prénom requis !")
        else:
            st.chat_message("user").write(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})
            save_log(student_id, "Eleve", prompt)
            try:
                msgs = [{"role": "system", "content": get_system_prompt(st.session_state.mode_simple)}] + [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
                completion = client.chat.completions.create(messages=msgs, model="llama-3.3-70b-versatile", temperature=0.7)
                rep = completion.choices[0].message.content
                st.chat_message("assistant").write(rep)
                st.session_state.messages.append({"role": "assistant", "content": rep})
                save_log(student_id, "Superviseur", rep)
                st.rerun()
            except Exception as e: st.error(f"Erreur : {e}")
