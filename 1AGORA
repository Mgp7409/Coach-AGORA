import streamlit as st
import pandas as pd
from groq import Groq
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="1AGORA", page_icon="🏢")
hide_menu = """<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}</style>"""
st.markdown(hide_menu, unsafe_allow_html=True)

st.title("🏢 Agence PRO'AGORA - Classe de 1ère")

# --- CONNEXION GROQ ---
try:
    api_key = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=api_key)
except:
    st.error("⚠️ Clé API manquante. Vérifiez les 'Secrets' de Streamlit.")
    st.stop()

# --- SCÉNARIOS (Livres Foucher) ---
DB_SECONDE = {
    "Pôle 1 : Gestion Relations Externes": {
        "Dossier 1 : L'accueil physique et téléphonique": "CONTEXTE : Tu es à l'accueil de l'entreprise 'Azur Buro'. DONNÉES : Appel de M. Dupuis mécontent. MISSION : Fiche de message + Réponse diplomate.",
        "Dossier 2 : La gestion du courrier": "CONTEXTE : Courrier arrivé (Pub, Chèque, Facture). MISSION : Tableau de tri + Enregistrement chèque.",
        "Dossier 3 : Le classement et l'archivage": "CONTEXTE : Serveur en désordre. MISSION : Proposer arborescence numérique."
    }
}

DB_PREMIERE = {
    "Thème 1 : Suivi des Ventes (Clients)": {
        "Chapitre 1 : Devis et Commandes": "CONTEXTE : Client 'SARL BATI-SUD'. Demande prix 1000 briques (0.80€) + 50 ciment (12€). Remise 5% > 1000€. TVA 20%. MISSION : Devis + Vérif Bon de Commande.",
        "Chapitre 2 : Livraison et Facturation": "CONTEXTE : Commande BATI-SUD livrée le 12/10 (BL-98). MISSION : Facture définitive F-2024-089.",
        "Chapitre 3 : Suivi des Règlements": "CONTEXTE : Facture F-2024-089 échue depuis 40 jours. MISSION : Mail de relance amiable."
    },
    "Thème 2 : Suivi des Achats (Fournisseurs)": {
        "Chapitre 4 : Recherche Fournisseurs": "CONTEXTE : Besoin imprimante laser (Budget 400€). MISSION : Comparatif 3 offres (Canon, HP, Brother).",
        "Chapitre 5 : Commande et Réception": "CONTEXTE : Brother choisie. Carton abîmé à la livraison. MISSION : Bon de Commande + Réserves."
    },
    "Thème 3 : Trésorerie et Stocks": {
        "Chapitre 6 : Rapprochement Bancaire": "CONTEXTE : Relevé BNP vs Compte 512. Écarts constatés. MISSION : État de rapprochement.",
        "Chapitre 7 : Suivi des Stocks": "CONTEXTE : Inventaire papier. Théorique 50, Réel 42. MISSION : Calcul écart + Mise à jour fiche."
    }
}

# --- CERVEAU ---
SYSTEM_PROMPT = """
Tu es le Superviseur PRO'AGORA. Tu encadres un élève de 1ère.
TON RÔLE : Fournir les données du dossier choisi et guider l'élève.
1. Donne TOUTES les infos techniques (Prix, Noms) dès le début.
2. Ne fais jamais le travail à sa place.
3. Sois pro et exigeant.
"""

# --- LOGS ---
if "conversation_log" not in st.session_state: st.session_state.conversation_log = []
def save_log(student_id, role, content):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.conversation_log.append({"Heure": ts, "Eleve": student_id, "Role": role, "Message": content})

# --- INTERFACE ---
with st.sidebar:
    st.header("🗂️ Navigation 1AGORA")
    student_id = st.text_input("Votre Prénom :")
    st.markdown("---")
    niveau = st.radio("Module :", ["1ère (Suivi Admin)", "2nde (Révisions)"])
    base = DB_PREMIERE if niveau == "1ère (Suivi Admin)" else DB_SECONDE
    theme = st.selectbox("Thème :", list(base.keys()))
    dossier = st.selectbox("Dossier :", list(base[theme].keys()))
    
    st.markdown("---")
    if st.button("🚀 LANCER LE DOSSIER", type="primary"):
        ctx = base[theme][dossier]
        msg = f"👋 Bonjour Opérateur. Dossier : **{dossier}**.\n\nCONTEXTE :\n{ctx}\n\nQuelle est ta première action ?"
        st.session
