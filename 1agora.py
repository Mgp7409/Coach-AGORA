import streamlit as st
import pandas as pd
from groq import Groq
from datetime import datetime

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="1AGORA - Entraînement", page_icon="🏢")

# Masquer le menu
hide_menu = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""
st.markdown(hide_menu, unsafe_allow_html=True)

st.title("♾️ Agence PRO'AGORA - Missions Infinies")
st.caption("Entraînement aux compétences de 1ère - Scénarios Aléatoires")

# --- 2. CONNEXION GROQ ---
try:
    api_key = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=api_key)
except:
    st.error("⚠️ Clé API manquante.")
    st.stop()

# --- 3. STRUCTURE DU LIVRE (TITRES NETTOYÉS) ---
# Plus de "SP1" ni de "Chapitre X". Juste les compétences.

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

# --- 4. LE CERVEAU (IA GÉNÉRATEUR) ---
SYSTEM_PROMPT = """
TU ES : Le Superviseur de l'Agence PRO'AGORA.
TON RÔLE : Entraîner un élève de 1ère sur les compétences de son livre, avec des cas variés.

RÈGLES DU JEU :
1. L'élève choisit une Mission (ex: "Recrutement").
2. TU DOIS INVENTER IMMÉDIATEMENT UN SCÉNARIO ALÉATOIRE COMPLET.
   - INVENTE une PME variée (Garage, Boulangerie, Start-up, Mairie, Asso...).
   - Donne un NOM d'entreprise fictif.
3. FOURNIS LES DONNÉES BRUTES DÈS LE DÉBUT :
   - Donne le Contexte, les Prix, les Dates, les Noms.
   - L'élève ne doit rien inventer, il doit traiter tes données.

EXEMPLE :
Si l'élève lance "Organisation déplacement", tu dis :
"Bonjour ! Mission du jour : Tu es assistant chez 'Bati-Renov'.
Ton directeur M. Thomas doit aller à Lyon le 12 mars. Budget 300€.
Trouve-lui un train et un hôtel. À toi de jouer !"

POSTURE : Pro, bienveillant, exigeant.
"""

# --- 5. GESTION LOGS ---
if "conversation_log" not in st.session_state: st.session_state.conversation_log = []
if "messages" not in st.session_state: st.session_state.messages = []

def save_log(student_id, role, content):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.conversation_log.append({"Heure": ts, "Eleve": student_id, "Role": role, "Message": content})

def lancer_scenario_aleatoire():
    # 1. Récupération choix
    base = DB_PREMIERE if st.session_state.niveau_select == "1ère (Livre Foucher)" else DB_SECONDE
    theme = st.session_state.theme_select
    dossier = st.session_state.dossier_select
    competence = base[theme][dossier]
    
    # 2. Reset historique
    st.session_state.messages = []
    
    # 3. Génération IA
    prompt_demarrage = f"L'élève veut travailler sur : '{dossier}'. Compétence : '{competence}'. INVENTE un scénario d'entreprise aléatoire (Nom, Secteur, Chiffres) et donne-lui les consignes."
    
    try:
        msgs = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt_demarrage}]
        completion = client.chat.completions.create(messages=msgs, model="llama-3.3-70b-versatile", temperature=0.8)
        intro_bot = completion.choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": intro_bot})
    except Exception as e:
        st.error(f"Erreur IA : {e}")

# --- 6. INTERFACE ---
with st.sidebar:
    st.header("🗂️ Menu des Missions")
    student_id = st.text_input("Identifiant Élève :", key="prenom_eleve")
    st.markdown("---")
    
    # Menus
    niveau = st.radio("Livre :", ["1ère (Livre Foucher)", "2nde (Révisions)"], key="niveau_select")
    base_active = DB_PREMIERE if niveau == "1ère (Livre Foucher)" else DB_SECONDE
    theme = st.selectbox("Situation Pro :", list(base_active.keys()), key="theme_select")
    dossier = st.selectbox("Mission à travailler :", list(base_active[theme].keys()), key="dossier_select")
    
    st.markdown("---")
    st.button("🎲 GÉNÉRER MA MISSION", type="primary", on_click=lancer_scenario_aleatoire)

    st.markdown("---")
    # ZONE SAUVEGARDE
    st.subheader("💾 Sauvegarde")
    
    if st.session_state.conversation_log:
        df = pd.DataFrame(st.session_state.conversation_log)
        csv = df.to_csv(index=False, sep=';').encode('utf-8-sig')
        st.download_button("📥 Télécharger CSV", csv, "suivi_1agora.csv", "text/csv")
    else:
        st.info("Le bouton de téléchargement apparaîtra ici une fois la conversation commencée.")
    
    # ZONE REPRISE
    st.markdown("---")
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
    st.info("👋 Bonjour ! Choisis une mission à gauche et clique sur **GÉNÉRER MA MISSION**.")
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
                completion = client.chat.completions.create(messages=msgs, model="llama-3.3-70b-versatile", temperature=0.7)
                rep = completion.choices[0].message.content
                st.chat_message("assistant").write(rep)
                st.session_state.messages.append({"role": "assistant", "content": rep})
                save_log(student_id, "Superviseur", rep)
                # Pas de rerun nécessaire ici
            except Exception as e: st.error(f"Erreur : {e}")
