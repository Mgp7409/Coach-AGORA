import streamlit as st
import pandas as pd
from groq import Groq
from datetime import datetime

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="1AGORA", page_icon="🏢")

# Masquer le menu pour un look App Pro
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
    st.error("⚠️ Clé API manquante. Vérifiez les Secrets.")
    st.stop()

# --- 3. STRUCTURE EXACTE DU LIVRE FOUCHER (Votre Copier-Coller) ---
DB_PREMIERE = {
    "SP1 : LA GESTION DES ESPACES (Écoactif Solidaire)": {
        "Chap 1 : Organiser le fonctionnement des espaces": "CONTEXTE : Écoactif Solidaire. MISSION : 1. Proposer un environnement de travail adapté. 2. Sélectionner les équipements.",
        "Chap 2 : Organiser l'environnement numérique": "CONTEXTE : Service Comptable. MISSION : 1. Proposer un environnement numérique. 2. Recenser les contraintes réglementaires. 3. Planifier la mise en œuvre.",
        "Chap 3 : Gérer les ressources partagées": "CONTEXTE : Gestion des fournitures. MISSION : 1. Nouvelle gestion du partage fournitures. 2. Nouveaux outils de partage ressources physiques.",
        "Chap 4 : Organiser le partage de l'info": "CONTEXTE : Communication interne. MISSION : 1. Analyser la com. 2. Définir stratégie. 3. Paramétrer outil collaboratif."
    },
    "SP2 : RELATIONS PARTENAIRES (Océaform)": {
        "Chap 5 : Lancement nouvelle gamme": "CONTEXTE : Océaform (Gamme produits). MISSION : 1. Planigramme des tâches. 2. Négocier conditions vente. 3. Communiquer sur le lancement.",
        "Chap 6 : Organiser et suivre des réunions": "CONTEXTE : Océaform. MISSION : 1. Organiser une réunion de service. 2. Préparer et suivre une visioconférence.",
        "Chap 7 : Organiser un déplacement": "CONTEXTE : Déplacement professionnel. MISSION : 1. Organiser les modalités (Transport/Hôtel). 2. Formalités administratives."
    },
    "SP3 : RELATIONS PERSONNEL (Léa Nature)": {
        "Chap 8 : Participer au recrutement": "CONTEXTE : Léa Nature. MISSION : 1. Préparer le recrutement. 2. Sélectionner le/la candidat(e).",
        "Chap 9 : Participer à l'intégration": "CONTEXTE : Léa Nature. MISSION : 1. Préparer l'accueil. 2. Développer motivation et cohésion.",
        "Chap 10 : Actualiser les dossiers personnel": "CONTEXTE : Léa Nature. MISSION : 1. Établir contrat de travail. 2. Actualiser registre personnel. 3. Établir avenant."
    },
    "SCÉNARIOS TRANSVERSAUX (Wink Digital)": {
        "Scénario 1 : Gestion des espaces": "CONTEXTE : Wink Digital. MISSION : La gestion opérationnelle des espaces de travail.",
        "Scénario 2 : Com interne et recrutement": "CONTEXTE : Wink Digital. MISSION : La communication interne et le suivi du recrutement."
    }
}

DB_SECONDE = {
    "Révisions 2nde": {
        "Dossier Accueil": "CONTEXTE : Révision accueil physique/téléphonique.",
        "Dossier Courrier": "CONTEXTE : Tri et enregistrement du courrier.",
        "Dossier Classement": "CONTEXTE : Organisation numérique."
    }
}

# --- 4. LE CERVEAU (IA) ---
SYSTEM_PROMPT = """
TU ES : Le Superviseur de l'Agence PRO'AGORA.
TON RÔLE : Entraîner un élève de 1ère Bac Pro AGOrA sur son livre Foucher.

CONSIGNES :
1. Tu utilises le CONTEXTE de l'entreprise sélectionnée (Écoactif, Océaform, Léa Nature ou Wink).
2. IMPORTANT : Pour que l'entraînement soit infini, tu gardes le contexte de l'entreprise MAIS tu inventes les détails variables (Dates précises, Noms des interlocuteurs, Chiffres, Lieux).
3. Donne les données brutes à l'élève dès le début.
4. Ne fais jamais le travail à sa place.
5. Sois bienveillant mais exigeant sur la forme professionnelle.
"""

# --- 5. GESTION LOGS ---
if "conversation_log" not in st.session_state:
    st.session_state.conversation_log = []
if "messages" not in st.session_state:
    st.session_state.messages = []

def save_log(student_id, role, content):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.conversation_log.append({
        "Heure": timestamp,
        "Eleve": student_id,
        "Role": role,
        "Message": content
    })

def lancer_mission():
    # Sélection de la base
    base = DB_PREMIERE if st.session_state.niveau_select == "1ère (Livre Foucher)" else DB_SECONDE
    theme = st.session_state.theme_select
    dossier = st.session_state.dossier_select
    contexte_livre = base[theme][dossier]
    
    # Message de démarrage (l'IA générera la suite)
    st.session_state.messages = []
    prompt_demarrage = f"L'élève commence le module '{dossier}'. Contexte du livre : {contexte_livre}. Agis comme le Superviseur, accueille-le et donne-lui les consignes et données précises pour démarrer."
    
    # Appel IA silencieux pour générer l'intro
    try:
        msgs = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt_demarrage}]
        completion = client.chat.completions.create(messages=msgs, model="llama-3.3-70b-versatile", temperature=0.7)
        intro_bot = completion.choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": intro_bot})
    except Exception as e:
        st.error(f"Erreur IA : {e}")

# --- 6. INTERFACE ---
with st.sidebar:
    st.header("🗂️ Navigation")
    student_id = st.text_input("Identifiant Élève :", key="prenom_eleve")
    st.markdown("---")
    
    # Menus
    niveau = st.radio("Livre :", ["1ère (Livre Foucher)", "2nde (Révisions)"], key="niveau_select")
    base_active = DB_PREMIERE if niveau == "1ère (Livre Foucher)" else DB_SECONDE
    theme = st.selectbox("Situation Pro :", list(base_active.keys()), key="theme_select")
    dossier = st.selectbox("Chapitre / Mission :", list(base_active[theme].keys()), key="dossier_select")
    
    st.markdown("---")
    st.button("🚀 LANCER LA MISSION", type="primary", on_click=lancer_mission)

    # Sauvegarde CSV
    st.markdown("---")
    st.subheader("💾 Sauvegarde")
    if st.session_state.conversation_log:
        df = pd.DataFrame(st.session_state.conversation_log)
        csv = df.to_csv(index=False, sep=';').encode('utf-8-sig')
        st.download_button("📥 Télécharger CSV", csv, "suivi_1agora.csv", "text/csv")
    
    # Reprise CSV
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

# --- 7. CHAT ---
if not st.session_state.messages:
    st.info("⬅️ Choisissez une Situation Professionnelle (Écoactif, Océaform, Léa Nature) et cliquez sur LANCER.")
else:
    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])

    if prompt := st.chat_input("Votre réponse..."):
        if not student_id:
            st.warning("⚠️ Prénom requis à gauche !")
        else:
            # 1. Message Élève
            st.chat_message("user").write(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})
            save_log(student_id, "Eleve", prompt)

            # 2. Réponse IA
            try:
                msgs = [{"role": "system", "content": SYSTEM_PROMPT}] + [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
                completion = client.chat.completions.create(messages=msgs, model="llama-3.3-70b-versatile", temperature=0.7)
                rep = completion.choices[0].message.content
                
                st.chat_message("assistant").write(rep)
                st.session_state.messages.append({"role": "assistant", "content": rep})
                save_log(student_id, "Superviseur", rep)
                # Pas de rerun, Streamlit gère l'ajout du message
            except Exception as e: st.error(f"Erreur : {e}")
