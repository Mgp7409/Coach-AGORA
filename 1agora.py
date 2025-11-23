import streamlit as st
import pandas as pd
from groq import Groq
from datetime import datetime

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
    st.error("⚠️ Clé API manquante. Vérifiez les 'Secrets' de Streamlit.")
    st.stop()

# --- 3. SCÉNARIOS (CONFORMES AU SOMMAIRE FOUCHER 1ère) ---

# NOTE POUR LE PROF : Vous devrez remplir les "CONTEXTE :" avec les détails des corrigés
# J'ai mis des exemples génériques pour que ça marche tout de suite.

DB_SECONDE = {
    "Pôle 1 : Gestion Relations Externes": {
        "Dossier 1 (2nde) : L'accueil": "CONTEXTE : Accueil chez Azur Buro. MISSION : Filtrer les appels.",
        "Dossier 2 (2nde) : Le courrier": "CONTEXTE : Tri du courrier. MISSION : Enregistrer le chèque.",
    }
}

DB_PREMIERE = {
    "Thème 1 : RELATIONS CLIENTS / USAGERS": {
        "Dossier 1 : Actualiser des dossiers clients": "CONTEXTE : Mise à jour de la base de données. Le client 'Durand' a déménagé. MISSION : Mettre à jour sa fiche signalétique dans le PGI.",
        "Dossier 2 : Traiter des devis": "CONTEXTE : Demande de prix de M. Martin pour 10 chaises ref C45. Prix unitaire 50€ HT. Remise 10%. MISSION : Établir le devis.",
        "Dossier 3 : Traiter des commandes": "CONTEXTE : Bon de commande n°502 reçu ce jour. Vérifier la conformité avec le devis D-102. MISSION : Valider la commande.",
        "Dossier 4 : Traiter livraisons et factures": "CONTEXTE : La livraison a été faite (BL n°88). Tout est conforme. MISSION : Établir la facture définitive.",
        "Dossier 5 : Suivi règlements et litiges": "CONTEXTE : La facture F-2024 n'est pas payée. Le délai est dépassé de 15 jours. MISSION : Rédiger la relance amiable."
    },
    "Thème 2 : RELATIONS FOURNISSEURS": {
        "Dossier 6 : Mettre à jour dossiers fournisseurs": "CONTEXTE : Le fournisseur 'PapierPlus' change de RIB. MISSION : Mettre à jour la fiche tiers.",
        "Dossier 7 : Traiter achats et commandes": "CONTEXTE : Besoin de 50 ramettes de papier. Comparer 3 catalogues. MISSION : Rédiger le Bon de Commande.",
        "Dossier 8 : Traiter livraisons et factures": "CONTEXTE : Réception de la marchandise. Le carton est ouvert. MISSION : Émettre des réserves sur le bon de transport.",
        "Dossier 9 : Suivi règlements et litiges": "CONTEXTE : Nous avons reçu une facture erronée (prix trop élevé). MISSION : Rédiger un mail de réclamation."
    },
    "Thème 3 : GESTION INTERNE": {
        "Dossier 10 : Suivre les états des stocks": "CONTEXTE : Inventaire des fournitures. Stock théorique : 100. Stock réel : 98. MISSION : Calculer l'écart et mettre à jour.",
        "Dossier 11 : Mettre à jour le SI": "CONTEXTE : Nouvelle procédure de sauvegarde des données. MISSION : Rédiger la note de service pour le personnel.",
        "Dossier 12 : Gérer les espaces administratifs": "CONTEXTE : Réorganisation de l'open space. MISSION : Proposer un plan d'aménagement ergonomique."
    }
}

# --- 4. CERVEAU (PROMPT) ---
SYSTEM_PROMPT = """
Tu es le Superviseur PRO'AGORA. Tu encadres un élève de 1ère.
TON RÔLE : Fournir les données du dossier choisi et guider l'élève.
1. Donne TOUTES les infos techniques (Prix, Noms, Contexte précis) dès le début.
2. Ne fais jamais le travail à sa place.
3. Sois pro et exigeant.
"""

# --- 5. GESTION ÉTAT & LOGS ---
if "conversation_log" not in st.session_state: st.session_state.conversation_log = []
if "messages" not in st.session_state: st.session_state.messages = []

def save_log(student_id, role, content):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.conversation_log.append({"Heure": ts, "Eleve": student_id, "Role": role, "Message": content})

# FONCTION DE LANCEMENT (Callback)
def lancer_mission():
    base = DB_PREMIERE if st.session_state.niveau_select == "1ère (Programme Année)" else DB_SECONDE
    theme = st.session_state.theme_select
    dossier = st.session_state.dossier_select
    contexte = base[theme][dossier]
    
    msg = f"👋 Bonjour Opérateur. Dossier : **{dossier}**.\n\nCONTEXTE :\n{contexte}\n\nQuelle est ta première action ?"
    st.session_state.messages = [{"role": "assistant", "content": msg}]

# --- 6. INTERFACE ---
with st.sidebar:
    st.header("🗂️ Navigation 1AGORA")
    student_id = st.text_input("Votre Prénom :", key="prenom_eleve")
    st.markdown("---")
    
    niveau = st.radio("Module :", ["1ère (Programme Année)", "2nde (Révisions)"], key="niveau_select")
    base_active = DB_PREMIERE if niveau == "1ère (Programme Année)" else DB_SECONDE
    
    theme = st.selectbox("Thème :", list(base_active.keys()), key="theme_select")
    dossier = st.selectbox("Dossier :", list(base_active[theme].keys()), key="dossier_select")
    
    st.markdown("---")
    st.button("🚀 LANCER LE DOSSIER", type="primary", on_click=lancer_mission)

    st.markdown("---")
    if st.session_state.conversation_log:
        df = pd.DataFrame(st.session_state.conversation_log)
        csv = df.to_csv(index=False, sep=';').encode('utf-8-sig')
        st.download_button("📥 Télécharger (CSV)", csv, "suivi_1agora.csv", "text/csv")

# --- 7. CHAT ---
if not st.session_state.messages:
    st.info("⬅️ Choisissez un dossier à gauche et cliquez sur LANCER.")
else:
    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])

    if prompt := st.chat_input("Votre réponse..."):
        if not student_id:
            st.warning("⚠️ Prénom requis à gauche !")
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
            except Exception as e: st.error(f"Erreur : {e}")
