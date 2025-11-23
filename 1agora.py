import streamlit as st
import pandas as pd
from groq import Groq
from datetime import datetime

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="1AGORA - Entraînement", page_icon="♾️")

# Masquer le menu
hide_menu = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""
st.markdown(hide_menu, unsafe_allow_html=True)

st.title("♾️ Agence PRO'AGORA - Générateur de Missions")
st.caption("Structure du livre Foucher 1ère - Scénarios Infinis")

# --- 2. CONNEXION GROQ ---
try:
    api_key = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=api_key)
except:
    st.error("⚠️ Clé API manquante.")
    st.stop()

# --- 3. STRUCTURE DU LIVRE (TITRES EXACTS) ---
# Ici, on garde les titres du livre pour le repérage, 
# mais on donne une consigne GÉNÉRIQUE à l'IA pour qu'elle invente le reste.

DB_PREMIERE = {
    "SP1 : ESPACES DE TRAVAIL (Type Écoactif)": {
        "Chap 1 : Aménagement des espaces": "COMPÉTENCE À TRAVAILLER : Proposer un aménagement de bureau ergonomique et choisir le mobilier.",
        "Chap 2 : Environnement numérique": "COMPÉTENCE À TRAVAILLER : Lister le matériel informatique nécessaire, les logiciels et les règles RGPD.",
        "Chap 3 : Ressources partagées": "COMPÉTENCE À TRAVAILLER : Gérer les stocks de fournitures (partage) et réserver des salles/véhicules.",
        "Chap 4 : Partage de l'info": "COMPÉTENCE À TRAVAILLER : Améliorer la communication interne (Note de service, Outil collaboratif, Agenda partagé)."
    },
    "SP2 : RELATIONS PARTENAIRES (Type Océaform)": {
        "Chap 5 : Lancement produit / Vente": "COMPÉTENCE À TRAVAILLER : Planifier des tâches (Planigramme), Négocier un prix de vente, Créer un flyer/mail commercial.",
        "Chap 6 : Organisation de réunions": "COMPÉTENCE À TRAVAILLER : Convoquer les participants, Réserver la salle, Préparer l'ordre du jour, Faire le Compte-Rendu.",
        "Chap 7 : Organisation déplacement": "COMPÉTENCE À TRAVAILLER : Réserver Train/Avion/Hôtel avec un budget contraint. Faire l'Ordre de Mission."
    },
    "SP3 : RELATIONS PERSONNEL (Type Léa Nature)": {
        "Chap 8 : Recrutement": "COMPÉTENCE À TRAVAILLER : Définir le Profil de poste, Rédiger l'annonce d'embauche, Trier des CV.",
        "Chap 9 : Intégration": "COMPÉTENCE À TRAVAILLER : Préparer l'arrivée (matériel, badges), Créer le livret d'accueil, Organiser un petit-déjeuner.",
        "Chap 10 : Dossiers du personnel": "COMPÉTENCE À TRAVAILLER : Rédiger un Contrat de travail, Mettre à jour le Registre du Personnel, Faire un Avenant."
    },
    "SCÉNARIOS TRANSVERSAUX (Type Wink Digital)": {
        "Scénario 1 : Réorganisation complète": "COMPÉTENCE À TRAVAILLER : Projet global de déménagement ou de réaménagement des services.",
        "Scénario 2 : Campagne Recrutement": "COMPÉTENCE À TRAVAILLER : Projet global de recrutement (de l'annonce à l'intégration)."
    }
}

DB_SECONDE = {
    "Révisions 2nde": {
        "Dossier Accueil": "COMPÉTENCE : Accueil physique et téléphonique (Filtrage, Prise de message).",
        "Dossier Courrier": "COMPÉTENCE : Tri du courrier (Arrivée/Départ) et Enregistrement.",
        "Dossier Classement": "COMPÉTENCE : Organisation de l'arborescence numérique."
    }
}

# --- 4. LE CERVEAU (GÉNÉRATEUR ALÉATOIRE) ---
SYSTEM_PROMPT = """
TU ES : Le Superviseur de l'Agence PRO'AGORA.
TON RÔLE : Entraîner un élève de 1ère sur les compétences de son livre, mais avec des cas variés.

RÈGLES DU JEU (IMPORTANT) :
1. L'élève choisit un Chapitre (ex: "Recrutement").
2. TU DOIS INVENTER IMMÉDIATEMENT UN SCÉNARIO ALÉATOIRE COMPLET.
   - Ne reprends PAS les entreprises du livre (Oublie Léa Nature, Océaform...).
   - INVENTE une PME variée : Un Garage, Une Boulangerie, Une Start-up Web, Une Mairie, Une Association Sportive...
3. FOURNIS LES DONNÉES BRUTES DÈS LE DÉBUT :
   - Donne le Nom de l'entreprise, le Contexte, les Prix, les Dates, les Noms des personnes.
   - L'élève ne doit rien inventer, il doit traiter tes données.

EXEMPLE :
Si l'élève clique sur "Chap 7 : Déplacement", tu dis :
"Bienvenue ! Oublions le livre. Aujourd'hui tu es assistant chez 'Bati-Renov'.
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
    # 1. On récupère le choix de l'élève
    base = DB_PREMIERE if st.session_state.niveau_select == "1ère (Livre Foucher)" else DB_SECONDE
    theme = st.session_state.theme_select
    dossier = st.session_state.dossier_select
    competence = base[theme][dossier]
    
    # 2. On vide l'historique pour démarrer à zéro
    st.session_state.messages = []
    
    # 3. On demande à l'IA de générer le scénario
    prompt_demarrage = f"L'élève veut s'entraîner sur : '{dossier}'. La compétence visée est : '{competence}'. INVENTE un scénario d'entreprise aléatoire (Nom, Secteur, Données chiffrées) et donne-lui ses consignes maintenant."
    
    # Appel IA "silencieux" (System + User invisible) pour avoir la première réponse
    try:
        msgs = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt_demarrage}]
        completion = client.chat.completions.create(messages=msgs, model="llama-3.3-70b-versatile", temperature=0.8) # 0.8 pour plus de créativité
        intro_bot = completion.choices[0].message.content
        
        # On affiche uniquement la réponse de l'IA (Le scénario)
        st.session_state.messages.append({"role": "assistant", "content": intro_bot})
    except Exception as e:
        st.error(f"Erreur IA : {e}")

# --- 6. INTERFACE ---
with st.sidebar:
    st.header("🗂️ Menu des Missions")
    student_id = st.text_input("Identifiant Élève :", key="prenom_eleve")
    st.info("🎲 Chaque clic génère une nouvelle entreprise !")
    st.markdown("---")
    
    # Menu Livre
    niveau = st.radio("Livre :", ["1ère (Livre Foucher)", "2nde (Révisions)"], key="niveau_select")
    base_active = DB_PREMIERE if niveau == "1ère (Livre Foucher)" else DB_SECONDE
    theme = st.selectbox("Situation Pro :", list(base_active.keys()), key="theme_select")
    dossier = st.selectbox("Chapitre à travailler :", list(base_active[theme].keys()), key="dossier_select")
    
    st.markdown("---")
    # Bouton qui lance la fonction "lancer_scenario_aleatoire"
    st.button("🎲 GÉNÉRER MA MISSION", type="primary", on_click=lancer_scenario_aleatoire)

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
            for _, row in df_hist.iterrows():
                role_chat = "user" if row['Role'] == "Eleve" else "assistant"
                st.session_state.messages.append({"role": role_chat, "content": row['Message']})
                save_log(row.get('Eleve', student_id), row['Role'], row['Message'])
            st.success("Restauré !")
            st.rerun()
        except: st.error("CSV invalide.")

# --- 7. CHAT ---
if not st.session_state.messages:
    st.info("👋 Bonjour ! Choisis un chapitre du livre à gauche et clique sur **GÉNÉRER MA MISSION**.")
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
                # On envoie tout l'historique pour que l'IA reste cohérente
                msgs = [{"role": "system", "content": SYSTEM_PROMPT}] + [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
                completion = client.chat.completions.create(messages=msgs, model="llama-3.3-70b-versatile", temperature=0.7)
                rep = completion.choices[0].message.content
                st.chat_message("assistant").write(rep)
                st.session_state.messages.append({"role": "assistant", "content": rep})
                save_log(student_id, "Superviseur", rep)
                # Pas de rerun nécessaire
            except Exception as e: st.error(f"Erreur : {e}")
            
