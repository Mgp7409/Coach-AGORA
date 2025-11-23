import streamlit as st
import pandas as pd
from groq import Groq
from datetime import datetime

# --- 1. CONFIGURATION (Titre de l'onglet = 1AGORA) ---
st.set_page_config(page_title="1AGORA", page_icon="🏢")

# Masquer le menu technique pour faire "Pro"
hide_menu = """<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}</style>"""
st.markdown(hide_menu, unsafe_allow_html=True)

st.title("🏢 Agence PRO'AGORA - Classe de 1ère")

# --- 2. CONNEXION GROQ ---
try:
    api_key = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=api_key)
except:
    st.error("⚠️ Clé API manquante. Vérifiez les 'Secrets' de Streamlit.")
    st.stop()

# ==============================================================================
# LA BIBLIOTHÈQUE DES SCÉNARIOS (Basée sur vos livres Foucher)
# ==============================================================================

# --- RÉVISIONS DE SECONDE (Livre Gestion Admin des Activités) ---
DB_SECONDE = {
    "Pôle 1 : Gestion Relations Externes": {
        "Dossier 1 : L'accueil physique et téléphonique": """
        CONTEXTE : Tu es à l'accueil de l'entreprise 'Azur Buro'.
        DONNÉES : Tu reçois un appel de M. Dupuis (Client) qui est mécontent d'un retard.
        MISSION : 1. Rédiger la fiche de prise de message. 2. Proposer une phrase de réponse diplomate.
        """,
        "Dossier 2 : La gestion du courrier": """
        CONTEXTE : Le courrier du matin est arrivé (5 lettres : 1 pub, 1 chèque client, 1 facture fournisseur, 1 CV, 1 lettre mairie).
        MISSION : 1. Présenter le tableau de tri (Service destinataire / Importance). 2. Enregistrer le chèque à l'arrivée.
        """,
        "Dossier 3 : Le classement et l'archivage": """
        CONTEXTE : Le serveur réseau est en désordre. Le chef ne retrouve pas les devis de 2023.
        MISSION : Proposer une arborescence de classement numérique (Dossiers/Sous-dossiers) pour le service Commercial.
        """
    }
}

# --- PROGRAMME DE PREMIÈRE (Livre Assurer le Suivi Administratif) ---
DB_PREMIERE = {
    "Thème 1 : Suivi des Ventes (Clients)": {
        "Chapitre 1 : Devis et Commandes": """
        CONTEXTE : Client 'SARL BATI-SUD'. Demande prix pour 1000 briques réf B45 et 50 sacs ciment.
        DONNÉES : Brique=0.80€ HT, Ciment=12€ HT. Remise 5% si > 1000€. TVA 20%.
        MISSION : 1. Établir le Devis. 2. Vérifier le Bon de Commande reçu ensuite (n° BC-102).
        """,
        "Chapitre 2 : Livraison et Facturation": """
        CONTEXTE : Suite à la commande BATI-SUD. La livraison a eu lieu le 12/10.
        DONNÉES : Bon de livraison BL-98. Aucun incident.
        MISSION : Établir la facture définitive F-2024-089. Vérifier les montants.
        """,
        "Chapitre 3 : Suivi des Règlements": """
        CONTEXTE : La facture F-2024-089 (BATI-SUD) date d'il y a 40 jours. Délai accordé : 30 jours.
        MISSION : 1. Constater le retard. 2. Rédiger un mail de relance niveau 1 (amiable).
        """
    },
    "Thème 2 : Suivi des Achats (Fournisseurs)": {
        "Chapitre 4 : Recherche Fournisseurs": """
        CONTEXTE : Besoin d'une imprimante laser pro pour le secrétariat. Budget max 400€.
        MISSION : Comparer 3 offres (Canon, HP, Brother) sur les critères : Prix, Vitesse, Coût toner, Garantie.
        """,
        "Chapitre 5 : Commande et Réception": """
        CONTEXTE : Imprimante Brother choisie. Elle arrive mais le carton est abîmé.
        MISSION : 1. Rédiger le Bon de Commande. 2. Rédiger les réserves à porter sur le bon de transport.
        """
    },
    "Thème 3 : Trésorerie et Stocks": {
        "Chapitre 6 : Rapprochement Bancaire": """
        CONTEXTE : Relevé bancaire BNP reçu. Le solde ne correspond pas à notre compte 512.
        MISSION : Identifier les opérations manquantes (chèques non encaissés, frais bancaires).
        """,
        "Chapitre 7 : Suivi des Stocks": """
        CONTEXTE : Inventaire des ramettes de papier. Stock théorique : 50. Stock réel compté : 42.
        MISSION : 1. Calculer l'écart. 2. Mettre à jour la fiche de stock. 3. Proposer une explication.
        """
    }
}

# ==============================================================================

# --- 3. LE CERVEAU (PROMPT SYSTÈME) ---
SYSTEM_PROMPT = """
Tu es le Superviseur de l'Agence PRO'AGORA.
Tu as accès au DOSSIER CORRIGÉ que l'élève a choisi.

TON RÔLE :
1. **Donner les données :** Dès le début, fournis à l'élève le CONTEXTE exact et les DONNÉES (Prix, Noms, Dates) du dossier choisi ci-dessus. Il ne doit pas les inventer.
2. **Guider :** Si le dossier comporte plusieurs étapes, guide-le une étape après l'autre.
3. **Corriger :** Vérifie sa rigueur administrative (Mentions obligatoires, calculs, orthographe).
4. **Bilan :** À la fin, génère le rapport pour le professeur.

RAPPEL : Tu ne fais jamais le travail à sa place. Tu donnes les "billes" (le sujet), il fait le jeu.
"""

# --- 4. GESTION LOGS ---
if "conversation_log" not in st.session_state:
    st.session_state.conversation_log = []

def save_log(student_id, role, content):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.conversation_log.append({
        "Heure": timestamp, "Eleve": student_id, "Role": role, "Message": content
    })

# --- 5. INTERFACE DE NAVIGATION (SIDEBAR) ---
with st.sidebar:
    st.header("🗂️ Navigation 1AGORA")
    
    # Identifiant
    student_id = st.text_input("Votre Prénom :")
    st.markdown("---")
    
    # Sélecteur de Niveau
    niveau = st.radio("Choix du Module :", ["1ère (Suivi Administratif)", "2nde (Révisions GATL)"])
    
    # Chargement de la base de données
    if niveau == "1ère (Suivi Administratif)":
        base_active = DB_PREMIERE
    else:
        base_active = DB_SECONDE
        
    # Sélecteurs Thème/Dossier
    theme_choisi = st.selectbox("Thème :", list(base_active.keys()))
    dossier_choisi = st.selectbox("Activité / Dossier :", list(base_active[theme_choisi].keys()))
    
    # Bouton d'Action
    st.markdown("---")
    if st.button("🚀 LANCER LE DOSSIER", type="primary"):
        contexte_mission = base_active[theme_choisi][dossier_choisi]
        start_msg = f"👋 Bonjour Opérateur. Tu as choisi : **{dossier_choisi}**.\n\nVoici le contexte du dossier :\n{contexte_mission}\n\nQuelle est ta première action ?"
        st.session_state.messages = [{"role": "assistant", "content": start_msg}]
        st.rerun()

    # Sauvegarde / Restauration
    st.markdown("---")
    st.subheader("💾 Sauvegarde")
    if st.session_state.conversation_log:
        df = pd.DataFrame(st.session_state.conversation_log)
        csv = df.to_csv(index=False, sep=';').encode('utf-8-sig')
        st.download_button("📥 Télécharger mon travail", csv, "suivi_1agora.csv", "text/csv")
        
    uploaded_file = st.file_uploader("Reprendre un travail (CSV)", type=['csv'])
    if uploaded_file and st.button("🔄 Restaurer"):
        try:
            df_hist = pd.read_csv(uploaded_file, sep=';')
            st.session_state.messages = []
            st.session_state.conversation_log = []
            for _, row in df_hist.iterrows():
                role_chat = "user" if row['Role'] == "Eleve" else "assistant"
                st.session_state.messages.append({"role": role_chat, "content": row['Message']})
                save_log(row.get('Eleve', student_id), row['Role'], row['Message'])
            st.success("Restauré !")
            st.rerun()
        except: st.error("Erreur fichier")

# --- 6. CHAT ---
if "messages" not in st.session_state:
    st.info("⬅️ Bienvenue sur **1AGORA**. Veuillez choisir un dossier dans le menu de gauche et cliquer sur 'LANCER LE DOSSIER'.")
    st.stop() 

# Affichage
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# Interaction
if prompt := st.chat_input("Votre réponse..."):
    if not student_id:
        st.warning("⚠️ Mettez votre prénom à gauche !")
    else:
        st.chat_message("user").write(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        save_log(student_id, "Eleve", prompt)

        try:
            msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
            msgs.extend([{"role": m["role"], "content": m["content"]} for m in st.session_state.messages])

            chat = client.chat.completions.create(
                messages=msgs,
                model="llama-3.3-70b-versatile",
                temperature=0.7
            )
            bot_reply = chat.choices[0].message.content
            
            st.chat_message("assistant").write(bot_reply)
            st.session_state.messages.append({"role": "assistant", "content": bot_reply})
            save_log(student_id, "Superviseur", bot_reply)
            st.rerun()
        except Exception as e:
            st.error(f"Erreur : {e}")
