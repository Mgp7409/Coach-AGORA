import streamlit as st
import pandas as pd
import os
from groq import Groq
from datetime import datetime

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Agence Pro’AGoRA", page_icon="🏢")

# Masquer le menu pour éviter les effacements accidentels
hide_menu_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """
st.markdown(hide_menu_style, unsafe_allow_html=True)

st.title("🏢 Agence Pro’AGoRA - Espace Opérateur")

# --- 2. CONNEXION GROQ ---
try:
    api_key = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=api_key)
except:
    st.error("ERREUR : Clé API manquante. Configurez GROQ_API_KEY dans les Secrets.")
    st.stop()

# --- 3. LE CERVEAU (PROMPT) ---
SYSTEM_PROMPT = """
### 1. IDENTITÉ ET RÔLE
Tu es le "Superviseur Pro’AGoRA", responsable opérationnel d’une agence virtuelle de services administratifs.
Tu encadres un élève ("Opérateur Junior") de 1ère Bac Pro AGOrA.
Ton objectif : Lui faire réaliser des missions professionnelles en lui fournissant la matière première.

### 2. RÈGLES DE POSTURE
- **TON :** Professionnel, exigeant, vouvoiement.
- **MÉTHODE :** Une étape à la fois.
- **FOURNISSEUR DE RESSOURCES (VITAL) :** Pour chaque mission, tu dois DONNER les informations techniques brutes (horaires, prix, dates) dès le début. L'élève ne doit pas les inventer.

### 3. SÉCURITÉ
1. Ne rédige jamais à la place de l'élève.
2. Pas de données réelles (RGPD).

### 4. MENU DE DÉMARRAGE
Propose ce menu :
"Bonjour Opérateur. Bienvenue à l'Agence Pro’AGoRA.
Rappel : Utilise uniquement des données fictives.
Sur quel dossier souhaites-tu travailler ?

📂 **A. RECRUTEMENT** (Fiche de poste, Annonce, Sélection, Intégration)
✈️ **B. DÉPLACEMENTS** (Comparatif, Réservation, Feuille de route)
🛒 **C. ACHATS** (Devis, Comparatif, Commande)
💶 **D. VENTES & FACTURATION** (Devis client, Facture, Relance)
🗂️ **E. ORGANISATION** (Classement, Archivage, Qualité)

Indique la lettre de la mission."

### 5. DÉROULEMENT
Choisis un scénario au hasard et DONNE LES DONNÉES BRUTES.

#### MODULE A : RECRUTEMENT
Scénarios : Bâtiment, Événementiel, Mairie, Médical, Transport, Immo.
1. Définition : Donne données brutes. Demande Fiche de Poste + Profil.
2. Diffusion : Demande Annonce + Canaux.
3. Sélection : Génère 3 CV fictifs. Demande tri.
4. Intégration : Demande Livret d'Accueil.

#### MODULE B : DÉPLACEMENTS
Donne : Ville, Dates, Horaires, Budget.
1. Analyse : Reformulation contraintes.
2. Recherche : Génère 3 options transport. Demande Comparatif.
3. Réservation : Demande infos Ordre de Mission.
4. Feuille de Route : Demande doc final.

#### MODULE C : ACHATS
Donne : Besoin et urgence.
1. Devis : Demande mail.
2. Comparatif : Génère 3 offres. Demande Tableau.
3. Commande : Validation Bon de Commande.

#### MODULE D : VENTES
Donne : Client, Produits, Conditions.
1. Devis Client : Demande devis.
2. Facture : Demande facture (avec erreur à trouver).
3. Relance : Demande mail relance.

#### MODULE E : ORGANISATION
1. Action : Demande arborescence ou tri.
2. Qualité : Demande questionnaire ou procédure.

### 6. RAPPORT FINAL
Génère ce bilan :
--- ✂️ À COPIER-COLLER POUR L'ENTRETIEN ✂️ ---
**BILAN DE LA MISSION [Nom]**
**1️⃣ CE QUI A ÉTÉ FAIT**
* [Résumé]
**2️⃣ ANALYSE DU PROCESSUS**
* [Blocages ? Qualité ?]
**3️⃣ QUESTIONS POUR L'ENTRETIEN**
* [3 questions réflexives pour le prof]
--------------------------------------------------------------
"""

# --- 4. GESTION DES LOGS (POUR LE CSV) ---
if "conversation_log" not in st.session_state:
    st.session_state.conversation_log = []

def save_log(student_id, role, content):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.conversation_log.append({
        "Heure": timestamp,
        "Eleve": student_id,
        "Role": role,
        "Message": content
    })

# --- 5. INTERFACE (AVEC LE BOUTON CSV) ---
with st.sidebar:
    st.header("Agence Pro’AGoRA")
    student_id = st.text_input("Identifiant Opérateur :")
    st.info("⚠️ N'utilise jamais ton vrai nom.")
    
    # <--- C'EST ICI QUE SE TROUVE LE BOUTON DE TÉLÉCHARGEMENT
    if st.session_state.conversation_log:
        df = pd.DataFrame(st.session_state.conversation_log)
        # On force l'encodage utf-8-sig pour que Excel lise bien les accents
        csv = df.to_csv(index=False, sep=';').encode('utf-8-sig')
        st.download_button(
            label="📥 Télécharger le suivi (CSV)",
            data=csv,
            file_name="suivi_agence.csv",
            mime="text/csv"
        )

# --- 6. CHAT ---
if "messages" not in st.session_state:
    welcome_text = """Bonjour Opérateur. Bienvenue à l'Agence Pro’AGoRA.
Rappel de sécurité : Utilise uniquement des données fictives pour cet exercice.
Sur quel dossier souhaites-tu travailler ?

📂 **A. RECRUTEMENT** (Fiche de poste, Annonce, Sélection, Intégration)
✈️ **B. DÉPLACEMENTS** (Comparatif, Réservation, Feuille de route)
🛒 **C. ACHATS** (Devis, Comparatif, Commande)
💶 **D. VENTES & FACTURATION** (Devis client, Facture, Relance)
🗂️ **E. ORGANISATION** (Classement, Archivage, Qualité)

Indique la lettre de la mission."""
    st.session_state.messages = [{"role": "assistant", "content": welcome_text}]

# Affichage historique
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# Interaction
if prompt := st.chat_input("Votre réponse..."):
    if not student_id:
        st.warning("⚠️ Identifiant requis à gauche !")
    else:
        # 1. Message Élève
        st.chat_message("user").write(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        save_log(student_id, "Eleve", prompt)

        # 2. Réponse IA
        try:
            messages_for_api = [{"role": "system", "content": SYSTEM_PROMPT}]
            for m in st.session_state.messages:
                messages_for_api.append({"role": m["role"], "content": m["content"]})

            chat_completion = client.chat.completions.create(
                messages=messages_for_api,
                model="llama-3.3-70b-versatile",
                temperature=0.7,
            )
            
            bot_reply = chat_completion.choices[0].message.content
            
            st.chat_message("assistant").write(bot_reply)
            st.session_state.messages.append({"role": "assistant", "content": bot_reply})
            save_log(student_id, "Superviseur", bot_reply)
            
        except Exception as e:
            st.error(f"Erreur : {e}")
