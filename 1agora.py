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

# --- 3. BASES DE DONNÉES (SCÉNARIOS) ---

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

# --- 4. CERVEAU (PROMPT) ---
SYSTEM_PROMPT = """
Tu es le Superviseur PRO'AGORA. Tu encadres un élève de 1ère.
TON RÔLE : Fournir les données du dossier choisi et guider l'élève.
1. Donne TOUTES les infos techniques (Prix, Noms) dès le début.
2. Ne fais jamais le travail à sa place.
3. Sois pro et exigeant.
"""

# --- 5. GESTION ÉTAT & LOGS ---

# Initialisation sécurisée
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

# --- FONCTION DE LANCEMENT (La partie corrigée) ---
def lancer_mission():
    # Cette fonction est appelée QUAND on clique sur le bouton
    # Elle prépare tout AVANT que la page ne se recharge
    selection_base = DB_PREMIERE if st.session_state.niveau_select == "1ère (Suivi Admin)" else DB_SECONDE
    contexte = selection_base[st.session_state.theme_select][st.session_state.dossier_select]
    
    msg_depart = f"👋 Bonjour Opérateur. Tu as choisi : **{st.session_state.dossier_select}**.\n\nCONTEXTE :\n{contexte}\n\nQuelle est ta première action ?"
    
    st.session_state.messages = [{"role": "assistant", "content": msg_depart}]
    # On ne met pas de st.rerun() ici, Streamlit le fait tout seul après le clic

# --- 6. INTERFACE ---
with st.sidebar:
    st.header("🗂️ Navigation 1AGORA")
    
    # On utilise des clés (key=...) pour que Streamlit s'y retrouve
    student_id = st.text_input("Votre Prénom :", key="prenom_eleve")
    
    st.markdown("---")
    
    # Menus déroulants
    niveau = st.radio("Module :", ["1ère (Suivi Admin)", "2nde (Révisions)"], key="niveau_select")
    
    if niveau == "1ère (Suivi Admin)":
        base_active = DB_PREMIERE
    else:
        base_active = DB_SECONDE
        
    theme = st.selectbox("Thème :", list(base_active.keys()), key="theme_select")
    dossier = st.selectbox("Dossier :", list(base_active[theme].keys()), key="dossier_select")
    
    st.markdown("---")
    
    # LE BOUTON CORRIGÉ : Il appelle la fonction 'lancer_mission'
    st.button("🚀 LANCER LE DOSSIER", type="primary", on_click=lancer_mission)

    # Téléchargement
    st.markdown("---")
    if st.session_state.conversation_log:
        df = pd.DataFrame(st.session_state.conversation_log)
        csv = df.to_csv(index=False, sep=';').encode('utf-8-sig')
        st.download_button("📥 Télécharger (CSV)", csv, "suivi_1agora.csv", "text/csv")

# --- 7. CHAT ---

# Si la liste des messages est vide, on affiche l'écran d'accueil
if not st.session_state.messages:
    st.info("⬅️ Veuillez choisir un dossier dans le menu de gauche et cliquer sur 'LANCER LE DOSSIER'.")
else:
    # Sinon, on affiche le chat
    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])

    # Zone de saisie
    if prompt := st.chat_input("Votre réponse..."):
        if not student_id:
            st.warning("⚠️ Prénom requis à gauche !")
        else:
            # 1. Affiche message élève
            st.chat_message("user").write(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})
            save_log(student_id, "Eleve", prompt)

            # 2. Réponse IA
            try:
                msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
                for m in st.session_state.messages:
                    msgs.append({"role": m["role"], "content": m["content"]})
                
                chat_completion = client.chat.completions.create(
                    messages=msgs,
                    model="llama-3.3-70b-versatile",
                    temperature=0.7
                )
                bot_reply = chat_completion.choices[0].message.content
                
                st.chat_message("assistant").write(bot_reply)
                st.session_state.messages.append({"role": "assistant", "content": bot_reply})
                save_log(student_id, "Superviseur", bot_reply)
                # Pas besoin de rerun ici, Streamlit gère l'affichage du nouveau message
                
            except Exception as e:
                st.error(f"Erreur : {e}")
