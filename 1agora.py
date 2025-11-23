import streamlit as st
import pandas as pd
from groq import Groq
from datetime import datetime
import docx
from pypdf import PdfReader

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="1AGORA", page_icon="🏢")

# Masquer le menu
hide_menu = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""
st.markdown(hide_menu, unsafe_allow_html=True)

st.title("🏢 Agence PRO'AGORA - Classe de 1ère")

# --- 2. CONNEXION GROQ ---
try:
    api_key = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=api_key)
except:
    st.error("⚠️ Clé API manquante.")
    st.stop()

# --- 3. LECTURE FICHIERS ---
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

# --- 4. SCÉNARIOS (CONFORMES À VOTRE SOMMAIRE FOUCHER) ---

# NOTE : Vous devrez ouvrir vos PDF corrigés et copier les contextes à la place de "..."
DB_PREMIERE = {
    "SP1 : ÉCOACTIF SOLIDAIRE (Espaces & Info)": {
        "Chap 1 : Organiser le fonctionnement des espaces": "CONTEXTE : Écoactif Solidaire. Problème d'aménagement. MISSION : 1. Proposer un environnement adapté. 2. Sélectionner les équipements.",
        "Chap 2 : Organiser l'environnement numérique": "CONTEXTE : Service comptable. MISSION : 1. Proposer un environnement numérique. 2. Recenser contraintes réglementaires.",
        "Chap 3 : Gérer les ressources partagées": "CONTEXTE : Gestion des fournitures. MISSION : 1. Nouvelle gestion du partage fournitures. 2. Outils de partage ressources physiques.",
        "Chap 4 : Organiser le partage de l'info": "CONTEXTE : Communication interne défaillante. MISSION : 1. Analyser la com. 2. Paramétrer l'outil collaboratif."
    },
    "SP2 : OCÉAFORM (Projets & Déplacements)": {
        "Chap 5 : Lancement nouvelle gamme": "CONTEXTE : Océaform lance un produit. MISSION : 1. Planigramme des tâches. 2. Négocier conditions vente. 3. Communiquer.",
        "Chap 6 : Organiser et suivre des réunions": "CONTEXTE : Réunion de service à planifier. MISSION : 1. Organiser la réunion. 2. Préparer une visioconférence.",
        "Chap 7 : Organiser un déplacement": "CONTEXTE : Déplacement professionnel à prévoir. MISSION : 1. Modalités transport/hébergement. 2. Formalités administratives."
    },
    "SP3 : LÉA NATURE (Ressources Humaines)": {
        "Chap 8 : Participer au recrutement": "CONTEXTE : Léa Nature recrute. MISSION : 1. Préparer le recrutement (Profil/Annonce). 2. Sélectionner le candidat.",
        "Chap 9 : Participer à l'intégration": "CONTEXTE : Arrivée d'un salarié. MISSION : 1. Préparer l'accueil. 2. Livret d'accueil et cohésion.",
        "Chap 10 : Actualiser les dossiers personnel": "CONTEXTE : Gestion administrative RH. MISSION : 1. Contrat de travail. 2. Registre du personnel. 3. Avenant."
    },
    "SCÉNARIOS TRANSVERSAUX (Wink Digital)": {
        "Scénario 1 : Gestion des espaces": "CONTEXTE : Entreprise Wink Digital. MISSION : Réorganisation complète des espaces.",
        "Scénario 2 : Com interne et Recrutement": "CONTEXTE : Wink Digital. MISSION : Campagne de recrutement et communication."
    }
}

DB_SECONDE = {
    "Révisions 2nde": {
        "Dossier Accueil": "CONTEXTE : Révision accueil physique/téléphonique.",
        "Dossier Courrier": "CONTEXTE : Tri et enregistrement du courrier.",
        "Dossier Classement": "CONTEXTE : Organisation numérique."
    }
}

# --- 5. CERVEAU ---
SYSTEM_PROMPT = """
Tu es le Superviseur PRO'AGORA. Tu encadres un élève de 1ère.
TON RÔLE :
1. Donne le CONTEXTE de l'entreprise (Écoactif, Océaform ou Léa Nature) dès le début.
2. Si l'élève dépose un FICHIER, analyse-le.
3. Ne fais jamais le travail à sa place.
"""

# --- 6. LOGS ---
if "conversation_log" not in st.session_state: st.session_state.conversation_log = []
if "messages" not in st.session_state: st.session_state.messages = []

def save_log(student_id, role, content):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.conversation_log.append({"Heure": ts, "Eleve": student_id, "Role": role, "Message": content})

def lancer_mission():
    base = DB_PREMIERE if st.session_state.niveau_select == "1ère (Programme Foucher)" else DB_SECONDE
    theme = st.session_state.theme_select
    dossier = st.session_state.dossier_select
    contexte = base[theme][dossier]
    msg = f"👋 Bonjour Opérateur. Dossier : **{dossier}**.\n\nCONTEXTE :\n{contexte}\n\nQuelle est ta première action ?"
    st.session_state.messages = [{"role": "assistant", "content": msg}]

# --- 7. INTERFACE ---
with st.sidebar:
    st.header("🗂️ Navigation 1AGORA")
    student_id = st.text_input("Votre Prénom :", key="prenom_eleve")
    st.markdown("---")
    
    niveau = st.radio("Livre / Module :", ["1ère (Programme Foucher)", "2nde (Révisions)"], key="niveau_select")
    base_active = DB_PREMIERE if niveau == "1ère (Programme Foucher)" else DB_SECONDE
    theme = st.selectbox("Situation Pro :", list(base_active.keys()), key="theme_select")
    dossier = st.selectbox("Chapitre :", list(base_active[theme].keys()), key="dossier_select")
    
    st.markdown("---")
    st.button("🚀 LANCER LA MISSION", type="primary", on_click=lancer_mission)

    st.markdown("---")
    # SAUVEGARDE
    if st.session_state.conversation_log:
        df = pd.DataFrame(st.session_state.conversation_log)
        csv = df.to_csv(index=False, sep=';').encode('utf-8-sig')
        st.download_button("📥 Télécharger CSV", csv, "suivi_1agora.csv", "text/csv")
    
    # RESTAURATION
    uploaded_csv = st.file_uploader("Reprendre (CSV)", type=['csv'])
    if uploaded_csv and st.button("🔄 Restaurer"):
        try:
            df_hist = pd.read_csv(uploaded_csv, sep=';')
            st.session_state.messages = []
            st.session_state.conversation_log = []
            for _, row in df_hist.iterrows():
                role_chat = "user" if row['Role'] == "Eleve" else "assistant"
                st.session_state.messages.append({"role": role_chat, "content": row['Message']})
                save_log(row.get('Eleve', student_id), row['Role'], row['Message'])
            st.success("Restauré !")
            st.rerun()
        except: st.error("CSV invalide.")

# --- 8. CHAT ---
if not st.session_state.messages:
    st.info("⬅️ Choisissez une Situation Professionnelle (Écoactif, Océaform, Léa Nature) et lancez.")
else:
    for msg in st.session_state.messages: st.chat_message(msg["role"]).write(msg["content"])

    with st.expander("📎 Joindre un fichier (Word/PDF)"):
        uploaded_doc = st.file_uploader("Fichier à corriger", type=['docx', 'pdf', 'txt'], key="doc_upload")
        if uploaded_doc and st.button("Envoyer fichier"):
            content = extract_text_from_file(uploaded_doc)
            user_msg = f"📄 Fichier **{uploaded_doc.name}** : {content}"
            st.chat_message("user").write(f"📄 *Fichier envoyé : {uploaded_doc.name}*")
            st.session_state.messages.append({"role": "user", "content": user_msg})
            save_log(student_id, "Eleve", f"[FICHIER] {uploaded_doc.name}")
            # Réponse IA
            try:
                msgs = [{"role": "system", "content": SYSTEM_PROMPT}] + [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
                chat = client.chat.completions.create(messages=msgs, model="llama-3.3-70b-versatile", temperature=0.7)
                rep = chat.choices[0].message.content
                st.chat_message("assistant").write(rep)
                st.session_state.messages.append({"role": "assistant", "content": rep})
                save_log(student_id, "Superviseur", rep)
                st.rerun()
            except Exception as e: st.error(f"Erreur : {e}")

    if prompt := st.chat_input("Votre réponse..."):
        if not student_id: st.warning("⚠️ Prénom requis !")
        else:
            st.chat_message("user").write(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})
            save_log(student_id, "Eleve", prompt)
            try:
                msgs = [{"role": "system", "content": SYSTEM_PROMPT}] + [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
                chat = client.chat.completions.create(messages=msgs, model="llama-3.3-70b-versatile", temperature=0.7)
                rep = chat.choices[0].message.content
                st.chat_message("assistant").write(rep)
                st.session_state.messages.append({"role": "assistant", "content": rep})
                save_log(student_id, "Superviseur", rep)
                st.rerun()
            except Exception as e: st.error(f"Erreur : {e}")
