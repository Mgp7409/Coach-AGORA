import streamlit as st
import pandas as pd
import os
from groq import Groq
from datetime import datetime

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Agence Pro’AGoRA", page_icon="🏢")

# Masquer le menu Streamlit
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
Tu es le "Superviseur Pro’AGoRA", responsable opérationnel d’une agence virtuelle.
Tu encadres un élève de 1ère Bac Pro AGOrA.

### 2. RÈGLES DE POSTURE
- **TON :** Professionnel, exigeant, vouvoiement.
- **MÉTHODE :** Une étape à la fois.
- **FOURNISSEUR DE RESSOURCES (VITAL) :** Pour chaque mission, tu dois DONNER les informations techniques brutes (horaires, prix, dates) dès le début. L'élève ne doit pas les inventer.

### 3. SÉCURITÉ
1. Ne rédige jamais à la place de l'élève.
2. Pas de données réelles (RGPD).

### 4. MENU DE DÉMARRAGE
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

# --- 4. GESTION DES LOGS ET MESSAGES ---
if "conversation_log" not in st.session_state:
    st.session_state.conversation_log = []

# Message d'accueil par défaut
welcome_text = """Bonjour Opérateur. Bienvenue à l'Agence Pro’AGoRA.
Rappel de sécurité : Utilise uniquement des données fictives pour cet exercice.
Sur quel dossier souhaites-tu travailler ?

📂 **A. RECRUTEMENT** (Fiche de poste, Annonce, Sélection, Intégration)
✈️ **B. DÉPLACEMENTS** (Comparatif, Réservation, Feuille de route)
🛒 **C. ACHATS** (Devis, Comparatif, Commande)
💶 **D. VENTES & FACTURATION** (Devis client, Facture, Relance)
🗂️ **E. ORGANISATION** (Classement, Archivage, Qualité)

Indique la lettre de la mission."""

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": welcome_text}]

def save_log(student_id, role, content):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.conversation_log.append({
        "Heure": timestamp,
        "Eleve": student_id,
        "Role": role,
        "Message": content
    })

# --- 5. INTERFACE CÔTÉ GAUCHE (SIDEBAR) ---
with st.sidebar:
    st.header("Agence Pro’AGoRA")
    student_id = st.text_input("Identifiant Opérateur :")
    st.info("⚠️ N'utilise jamais ton vrai nom.")
    st.markdown("---")

    # --- ZONE DE SAUVEGARDE (DOWNLOAD) ---
    st.subheader("💾 Sauvegarder")
    if st.session_state.conversation_log:
        df = pd.DataFrame(st.session_state.conversation_log)
        csv = df.to_csv(index=False, sep=';').encode('utf-8-sig')
        st.download_button("📥 Télécharger l'avancement (CSV)", csv, "suivi_agence.csv", "text/csv")
    else:
        st.write("Commencez à discuter pour sauvegarder.")

    st.markdown("---")

    # --- ZONE DE REPRISE (UPLOAD) ---
    st.subheader("📂 Reprendre un travail")
    uploaded_file = st.file_uploader("Charger un ancien CSV pour continuer", type=['csv'])
    
    if uploaded_file is not None:
        try:
            # Lecture du fichier
            df_history = pd.read_csv(uploaded_file, sep=';')
            
            # Vérification que c'est le bon format
            if 'Role' in df_history.columns and 'Message' in df_history.columns:
                if st.button("🔄 Restaurer la conversation"):
                    # 1. On vide la mémoire actuelle
                    st.session_state.messages = []
                    st.session_state.conversation_log = []
                    
                    # 2. On remplit avec l'historique
                    # On remet le message d'accueil si absent
                    st.session_state.messages.append({"role": "assistant", "content": welcome_text})

                    for index, row in df_history.iterrows():
                        role_csv = row['Role'] # "Eleve" ou "Superviseur"
                        content = row['Message']
                        
                        # Conversion pour l'affichage chat
                        role_chat = "user" if role_csv == "Eleve" else "assistant"
                        
                        # On évite de doublonner le message d'accueil s'il est dans le CSV
                        if content != welcome_text:
                            st.session_state.messages.append({"role": role_chat, "content": content})
                            
                            # On remplit aussi le log pour la future sauvegarde
                            st.session_state.conversation_log.append({
                                "Heure": row.get('Heure', datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                                "Eleve": row.get('Eleve', student_id),
                                "Role": role_csv,
                                "Message": content
                            })
                    
                    st.success("Conversation restaurée ! Vous pouvez continuer.")
                    st.rerun() # Recharge la page pour afficher les messages
            else:
                st.error("Format de fichier invalide (colonnes manquantes).")
        except Exception as e:
            st.error(f"Erreur lecture : {e}")

# --- 6. CHAT (AFFICHAGE) ---
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
            st.rerun() # Force le rafraichissement pour le bouton download
            
        except Exception as e:
            st.error(f"Erreur : {e}")
