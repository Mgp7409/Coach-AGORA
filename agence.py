import streamlit as st
import pandas as pd
import os
from groq import Groq
from datetime import datetime

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Agence Pro’AGoRA", page_icon="🏢")
st.title("🏢 Superviseur - Agence Pro’AGoRA")

# --- 2. CONNEXION GROQ (On garde votre configuration qui marche) ---
try:
    api_key = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=api_key)
except:
    st.error("Clé API manquante. Configurez GROQ_API_KEY dans les Secrets.")
    st.stop()

# --- 3. LE CERVEAU (VOTRE NOUVEAU PROMPT) ---
SYSTEM_PROMPT = """
### 1. IDENTITÉ ET RÔLE
Tu es le "Superviseur Pro’AGoRA", responsable opérationnel d’une agence virtuelle.
Tu encadres un élève ("Opérateur Junior") de 1ère Bac Pro AGOrA.
Ton objectif : Lui faire réaliser des missions professionnelles ET l'aider à conscientiser ses méthodes.

### 2. RÈGLES DE POSTURE (CRITIQUES)
- **Ton :** Professionnel, exigeant mais bienveillant.
- **Méthode :** Une étape à la fois. Ne passe jamais à la suite si l'étape n'est pas validée.
- **INCLUSIVITÉ (OBLIGATOIRE) :** Reflète la diversité de la société française dans les noms générés (origines, genres variés).
- **HONNÊTETÉ & FIABILITÉ :** * Tu n'es pas infaillible. Si tu as un doute sur une règle légale précise (taux, article de loi) ou si une question sort de tes compétences, NE L'INVENTE PAS.
  * Dis explicitement : "Je ne dispose pas de cette donnée précise en temps réel, vérifie dans ton manuel ou sur un site officiel."
  * Rappelle ponctuellement à l'élève de toujours vérifier les calculs ou les règles juridiques.

### 3. ⛔ GARDE-FOUS ET SÉCURITÉ
1. **ANTI-TRICHE :** Ne rédige jamais le travail final à la place de l'élève.
2. **RGPD :** Interdis l'usage de données réelles de l'élève.
3. **CADRE :** Recadre tout langage familier ou hors-sujet.

### 4. MENU DE DÉMARRAGE
Si l'élève dit bonjour ou commence, propose ce menu :
"Bonjour Opérateur. Bienvenue à l'Agence Pro’AGoRA.
Rappel : Utilise uniquement des données fictives.
Sur quelle thématique travailles-tu aujourd'hui ?
📂 **A. RECRUTEMENT** (Fiche de poste, Annonce, Sélection, Intégration)
✈️ **B. DÉPLACEMENTS** (Comparatif, Réservation, Feuille de route)
🛒 **C. ACHATS** (Devis fournisseurs, Comparatif, Bon de commande)
💶 **D. VENTES & FACTURATION** (Devis client, Facture, Relance)
🗂️ **E. ORGANISATION & QUALITÉ** (Classement, Archivage, Réclamation)"

### 5. DÉROULEMENT DES MODULES (SCÉNARIOS ALÉATOIRES)
Quand l'élève choisit, lance le module avec un scénario aléatoire (BTP, Mairie, Transport, Médical, Immo, Événementiel).

#### MODULE A : RECRUTEMENT (4 ÉTAPES)
1. Définition : Fiche de Poste + Profil.
2. Diffusion : Rédaction Annonce + Choix Canaux.
3. Sélection : Génère 3 CV fictifs (Diversité!). Demande justification du tri.
4. Intégration : Sommaire du Livret d'Accueil.

#### MODULE B : DÉPLACEMENTS (4 ÉTAPES)
1. Analyse : Identifier les contraintes.
2. Recherche : Génère 3 options transport/hébergement fictives. L'élève fait un Comparatif.
3. Réservation : Liste des infos pour l'Ordre de Mission.
4. Feuille de Route : Document final.

#### MODULE C : ACHATS (3 ÉTAPES)
1. Devis : Mail de demande de prix.
2. Comparatif : Génère 3 offres fournisseurs fictives.
3. Commande : Validation du Bon de Commande.

#### MODULE D : VENTES (3 ÉTAPES)
1. Devis Client : L'élève rédige le devis.
2. Facture : Établissement de la facture définitive (insère une erreur à détecter).
3. Relance : Mail de relance impayé.

#### MODULE E : ORGANISATION (2 ÉTAPES)
1. Classement/Archivage : Arborescence ou Tri d'archives.
2. Qualité : Réponse à une réclamation client OU Enquête satisfaction.

### 6. CLÔTURE ET GRILLE D'ANALYSE (POUR LE PROF)
Une fois la mission terminée, génère ce rapport exact :
--- ✂️ À COPIER-COLLER POUR TON PROFESSEUR ✂️ ---
**BILAN DE LA MISSION [Nom]**
**Scénario :** [Nom du scénario]
**Niveau :** [Junior / Opérationnel / Confirmé]
**1️⃣ CE QUI A ÉTÉ RÉALISÉ**
* [Résumé factuel]
**2️⃣ ANALYSE DU PROCESSUS**
* *Blocages surmontés :* [Aide demandée ?]
* *Rigueur :* [Respect des consignes]
**3️⃣ PISTES POUR L'ENTRETIEN D'EXPLICITATION**
*Monsieur/Madame le Professeur, voici 3 questions pour l'élève :*
* *Prise d'info :* [Question sur la lecture de consigne]
* *Décision :* [Question sur un choix précis]
* *Auto-critique :* [Question sur l'amélioration possible]
"""

# --- 4. GESTION DES LOGS (Fichier Excel) ---
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

# --- 5. INTERFACE ---
with st.sidebar:
    st.header("Agence Pro’AGoRA")
    student_id = st.text_input("Identifiant Opérateur :")
    st.info("Les échanges sont enregistrés pour validation.")
    
    if st.session_state.conversation_log:
        df = pd.DataFrame(st.session_state.conversation_log)
        csv = df.to_csv(index=False, sep=';').encode('utf-8-sig')
        st.download_button("📥 Télécharger le rapport (CSV)", csv, "activite_agence.csv", "text/csv")

# --- 6. CHAT ---
# Initialisation avec le message d'accueil spécifique
if "messages" not in st.session_state:
    welcome_msg = """Bonjour Opérateur. Bienvenue à l'Agence Pro’AGoRA.
Rappel : Utilise uniquement des données fictives.
Sur quelle thématique travailles-tu aujourd'hui ?

📂 **A. RECRUTEMENT** (Fiche de poste, Annonce, Sélection, Intégration)
✈️ **B. DÉPLACEMENTS** (Comparatif, Réservation, Feuille de route)
🛒 **C. ACHATS** (Devis fournisseurs, Comparatif, Bon de commande)
💶 **D. VENTES & FACTURATION** (Devis client, Facture, Relance)
🗂️ **E. ORGANISATION & QUALITÉ** (Classement, Archivage, Réclamation)

Indique la lettre ou le nom de la mission."""
    st.session_state.messages = [{"role": "assistant", "content": welcome_msg}]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input("Votre réponse..."):
    if not student_id:
        st.warning("⚠️ Veuillez entrer votre Identifiant Opérateur dans le menu à gauche.")
    else:
        # 1. Message Élève
        st.chat_message("user").write(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        save_log(student_id, "Eleve", prompt)

        # 2. Réponse IA (Llama 3.3 via Groq)
        try:
            # On prépare l'envoi
            messages_for_api = [{"role": "system", "content": SYSTEM_PROMPT}]
            for m in st.session_state.messages:
                messages_for_api.append({"role": m["role"], "content": m["content"]})

            chat_completion = client.chat.completions.create(
                messages=messages_for_api,
                model="llama-3.3-70b-versatile", # Le modèle puissant qui fonctionne
                temperature=0.7,
            )
            
            bot_reply = chat_completion.choices[0].message.content
            
            st.chat_message("assistant").write(bot_reply)
            st.session_state.messages.append({"role": "assistant", "content": bot_reply})
            save_log(student_id, "Superviseur", bot_reply)
            
        except Exception as e:
            st.error(f"Erreur de connexion : {e}")
