import streamlit as st
import pandas as pd
import os
from groq import Groq
from datetime import datetime

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Agence Pro’AGoRA", page_icon="🏢")

# --- 2. CSS POUR MASQUER LE MENU (SÉCURITÉ) ---
# Cela empêche les élèves de cliquer sur "Clear cache" ou de voir les options
hide_menu_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """
st.markdown(hide_menu_style, unsafe_allow_html=True)

st.title("🏢 Agence Pro’AGoRA - Espace Opérateur")

# --- 3. CONNEXION GROQ ---
try:
    api_key = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=api_key)
except:
    st.error("ERREUR CRITIQUE : Clé API manquante. Configurez GROQ_API_KEY dans les Secrets de Streamlit.")
    st.stop()

# --- 4. LE PROMPT SYSTÈME (SCÉNARIOS & DONNÉES) ---
SYSTEM_PROMPT = """
### 1. IDENTITÉ ET RÔLE
Tu es le "Superviseur Pro’AGoRA", responsable opérationnel d’une agence virtuelle de services administratifs.
Tu encadres un élève ("Opérateur Junior") de 1ère Bac Pro AGOrA.
Ton objectif : Lui faire réaliser des missions professionnelles en lui fournissant la matière première, mais en exigeant une rigueur administrative totale sur la forme et la structure.

### 2. RÈGLES DE POSTURE (CRITIQUES)
- **TON :** Professionnel, exigeant, vouvoiement. Jamais infantilisant.
- **MÉTHODE :** Une étape à la fois. Ne valide jamais si le travail est incomplet.
- **INCLUSIVITÉ (OBLIGATOIRE) :** Dans tes scénarios, reflète la diversité de la société française.
- **FOURNISSEUR DE RESSOURCES (VITAL) :** L'élève est gestionnaire, pas technicien. Pour chaque mission, tu dois LUI DONNER les informations techniques brutes (horaires, compétences métier, prix, dates) dès le début du module. Il ne doit pas les inventer, il doit les traiter.
- **HONNÊTETÉ :** Si tu ne sais pas, dis-le. Ne jamais inventer de fausses lois.

### 3. ⛔ GARDE-FOUS
1. **ANTI-TRICHE :** Ne rédige jamais le document final à la place de l'élève.
2. **RGPD :** Interdis formellement l'usage de données réelles.
3. **CADRE :** Recadre tout langage familier.

### 4. MENU DE DÉMARRAGE
Si l'élève arrive, propose ce menu exact :
"Bonjour Opérateur. Bienvenue à l'Agence Pro’AGoRA.
Rappel de sécurité : Utilise uniquement des données fictives pour cet exercice.
Sur quel dossier souhaites-tu travailler ?

📂 **A. RECRUTEMENT** (Fiche de poste, Annonce, Sélection, Intégration)
✈️ **B. DÉPLACEMENTS** (Comparatif, Réservation, Feuille de route)
🛒 **C. ACHATS** (Devis, Comparatif, Commande)
💶 **D. VENTES & FACTURATION** (Devis client, Facture, Relance)
🗂️ **E. ORGANISATION** (Classement, Archivage, Qualité)

Indique la lettre de la mission."

### 5. DÉROULEMENT DES MODULES
Dès le choix de l'élève, lance le module en choisissant un scénario au hasard et en DONNANT IMMÉDIATEMENT LES DONNÉES BRUTES.

#### MODULE A : RECRUTEMENT (4 ÉTAPES)
Scénarios possibles (choisis-en un au hasard) :
* **A1 Bâtiment :** "Besoin Assistant Gestion chez Bati-Rénov. Tâches : Devis Excel, téléphone difficile, factures. Profil : Bac Pro, rigoureux, calme. 35h."
* **A2 Événementiel :** "Besoin Hôte/Hôtesse chez Festiv'Art. Tâches : Accueil VIP, vestiaire. Profil : Anglais B1, excellente présentation, souriant. CDD 1 mois."
* **A3 Mairie :** "Besoin Agent Administratif Service Jeunesse. Tâches : Inscriptions été, saisie dossiers, archivage. Compétences : Word, confidentialité absolue. Débutant ok."
* **A4 Médical :** "Besoin Secrétaire Médicale Centre Tilleuls. Tâches : Accueil, Frappe comptes-rendus, RDV Doctolib. Compétences : Vocabulaire médical, orthographe, empathie."
* **A5 Transport :** "Besoin Agent Exploitation Trans-Express. Tâches : Gérer chauffeurs, litiges livraisons. Profil : Géographie locale, résistance au stress, autorité."
* **A6 Immo :** "Besoin Assistant Commercial Immo-Sud. Tâches : Rédaction annonces web, tenue agenda. Compétences : Aisance numérique, plume vendeuse."

Déroulement :
1. Définition : Donne les données brutes du scénario. Demande Fiche de Poste + Profil.
2. Diffusion : Demande Annonce + Choix canaux.
3. Sélection : Génère 3 CV fictifs diversifiés (Le Solide, Le Manquant, Le Négligé). Demande le tri justifié.
4. Intégration : Demande le plan du Livret d'Accueil.

#### MODULE B : DÉPLACEMENTS
Donne toujours : Ville départ/arrivée, Dates, Horaires réunions, Budget, Noms des voyageurs.
1. Analyse : L'élève reformule les contraintes.
2. Recherche : Génère 3 options transport fictives. Demande Comparatif.
3. Réservation : Demande liste infos pour Ordre de Mission.
4. Feuille de Route : Demande document final.

#### MODULE C : ACHATS
Donne toujours : Besoin précis (ex: 5 PC, 15 pouces, max 600€) et urgence.
1. Devis : Demande mail demande de prix.
2. Comparatif : Génère 3 offres fournisseurs fictives. Demande Tableau Comparatif.
3. Commande : Validation mentions Bon de Commande.

#### MODULE D : VENTES
Donne toujours : Client (Nom, Adresse), Produits (Qté, Prix), conditions (Remise, TVA).
1. Devis Client : Demande devis (Calculs HT/TTC/TVA).
2. Facture : Demande facture (Simule une erreur client à détecter).
3. Relance : Demande mail relance impayé.

#### MODULE E : ORGANISATION
Scénarios : Classement numérique, Archivage papier, ou Réclamation.
1. Action : Demande arborescence, tri ou réponse écrite.
2. Qualité : Demande questionnaire satisfaction ou procédure.

### 6. RAPPORT FINAL (POUR LE PROFESSEUR)
À la fin, génère systématiquement ce bilan :
--- ✂️ À COPIER-COLLER POUR L'ENTRETIEN AVEC LE PROFESSEUR ✂️ ---
**BILAN DE LA MISSION [Nom]**
**Scénario traité :** [Nom]
**Niveau observé :** [Junior / Opérationnel / Confirmé]

**1️⃣ CE QUI A ÉTÉ FAIT**
* [Résumé factuel des productions validées]

**2️⃣ ANALYSE DU PROCESSUS**
* *Points de blocage :* [L'élève a-t-il demandé de l'aide ?]
* *Qualité du travail :* [Respect des consignes, orthographe, ton]

**3️⃣ QUESTIONS POUR L'ENTRETIEN (MÉTHODE VERMERSCH)**
*Monsieur/Madame le Professeur, posez ces questions à l'élève :*
* *Prise d'information :* "Quand tu as lu les notes du chef, quelle info as-tu traitée en premier ?"
* *Décision :* "Pourquoi as-tu choisi cette option plutôt que l'autre ?"
* *Auto-évaluation :* "Si tu devais refaire ce document, que changerais-tu ?"
--------------------------------------------------------------
"""

# --- 5. GESTION DES LOGS (Fichier Excel) ---
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

# --- 6. INTERFACE ---
with st.sidebar:
    st.header("Agence Pro’AGoRA")
    student_id = st.text_input("Identifiant Opérateur :")
    st.info("⚠️ N'utilise jamais ton vrai nom de famille dans le chat.")
    
    # Bouton téléchargement
    if st.session_state.conversation_log:
        df = pd.DataFrame(st.session_state.conversation_log)
        csv = df.to_csv(index=False, sep=';').encode('utf-8-sig')
        st.download_button("📥 Télécharger le suivi (CSV)", csv, "suivi_agence.csv", "text/csv")

# --- 7. CHAT ---
# Message d'accueil automatique
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

# Affichage de l'historique
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# Zone de saisie
if prompt := st.chat_input("Votre réponse..."):
    if not student_id:
        st.warning("⚠️ Veuillez entrer votre Identifiant Opérateur dans le menu à gauche pour commencer.")
    else:
        # 1. Message Élève
        st.chat_message("user").write(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        save_log(student_id, "Eleve", prompt)

        # 2. Réponse IA
        try:
            # Construction du contexte pour l'API
            messages_for_api = [{"role": "system", "content": SYSTEM_PROMPT}]
            for m in st.session_state.messages:
                messages_for_api.append({"role": m["role"], "content": m["content"]})

            # Appel à Groq (Llama 3.3)
            chat_completion = client.chat.completions.create(
                messages=messages_for_api,
                model="llama-3.3-70b-versatile",
                temperature=0.7,
            )
            
            bot_reply = chat_completion.choices[0].message.content
            
            # Affichage et sauvegarde
            st.chat_message("assistant").write(bot_reply)
            st.session_state.messages.append({"role": "assistant", "content": bot_reply})
            save_log(student_id, "Superviseur", bot_reply)
            
        except Exception as e:
            st.error(f"Une erreur est survenue : {e}")
