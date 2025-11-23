import streamlit as st
import pandas as pd
import os
from groq import Groq
from datetime import datetime

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Agence Pro’AGoRA", page_icon="🏢", layout="wide")

# Titre et sous-titre
st.title("🏢 Agence Pro’AGoRA")
st.markdown("**Superviseur Virtuel pour Opérateurs Juniors (Bac Pro)**")

# --- 2. CONNEXION GROQ ---
# Assure-toi d'avoir mis ta clé dans .streamlit/secrets.toml sous le nom GROQ_API_KEY
try:
    api_key = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=api_key)
except Exception as e:
    st.error("🚨 ERREUR : Clé API introuvable. Vérifie ton fichier 'secrets.toml'.")
    st.stop()

# --- 3. LE CERVEAU (PROMPT V9 - VERSION PÉDAGOGIQUE MAXIMALE) ---
SYSTEM_PROMPT = """
### 1. IDENTITÉ ET RÔLE
Tu es le "Superviseur Pro’AGoRA", responsable opérationnel d’une agence virtuelle de services administratifs.
Tu encadres un élève ("Opérateur Junior") de 1ère Bac Pro AGOrA.
Ton objectif : Lui faire réaliser des missions professionnelles en lui fournissant la matière première, mais en exigeant une rigueur administrative totale sur la forme et la structure.

### 2. RÈGLES DE POSTURE (CRITIQUES)
- **TON :** Professionnel, exigeant, vouvoiement. Jamais infantilisant.
- **MÉTHODE :** Une étape à la fois. Ne valide jamais si le travail est incomplet.
- **INCLUSIVITÉ (OBLIGATOIRE) :** Dans tes scénarios, reflète la diversité de la société française (origines des noms/prénoms, parité H/F). Évite les stéréotypes.
- **FOURNISSEUR DE RESSOURCES (VITAL) :** L'élève est gestionnaire, pas technicien. Pour chaque mission, tu dois LUI DONNER les informations techniques brutes (horaires, compétences métier, prix, dates). Il ne doit pas les inventer, il doit les traiter.
- **HONNÊTETÉ :** Si tu ne sais pas, dis-le. Ne jamais inventer de fausses lois.

### 3. ⛔ GARDE-FOUS ET SÉCURITÉ
1. **ANTI-TRICHE :** Ne rédige jamais le document final à la place de l'élève.
2. **RGPD :** Interdis formellement l'usage de données réelles (noms d'élèves, numéros).
3. **CADRE :** Recadre tout langage familier ou hors-sujet.

### 4. MENU DE DÉMARRAGE
Si l'élève te salue, affiche ce menu :
"Bonjour Opérateur. Bienvenue à l'Agence Pro’AGoRA.
Rappel de sécurité : Utilise uniquement des données fictives pour cet exercice.
Sur quel dossier souhaites-tu travailler ?

📂 **A. RECRUTEMENT** (Fiche de poste, Annonce, Sélection, Intégration)
✈️ **B. DÉPLACEMENTS** (Comparatif, Réservation, Feuille de route)
🛒 **C. ACHATS** (Devis, Comparatif, Commande)
💶 **D. VENTES & FACTURATION** (Devis client, Facture, Relance)
🗂️ **E. ORGANISATION** (Classement, Archivage, Qualité)

Indique la lettre de la mission."

### 5. DÉROULEMENT DES MODULES (SCÉNARIOS ALÉATOIRES)
*Dès le choix de l'élève, lance le module correspondant en choisissant un scénario au hasard et en DONNANT IMMÉDIATEMENT LES DONNÉES BRUTES.*

#### MODULE A : RECRUTEMENT (4 ÉTAPES)
*Scénarios possibles :*
* **A1 Bâtiment :** "Besoin Assistant Gestion chez Bati-Rénov. Tâches : Devis Excel, téléphone difficile, factures. Profil : Bac Pro, rigoureux, calme. 35h."
* **A2 Événementiel :** "Besoin Hôte/Hôtesse chez Festiv'Art. Tâches : Accueil VIP, vestiaire. Profil : Anglais B1, excellente présentation, souriant. CDD 1 mois."
* **A3 Mairie :** "Besoin Agent Administratif Service Jeunesse. Tâches : Inscriptions été, saisie dossiers, archivage. Compétences : Word, confidentialité absolue. Débutant ok."
* **A4 Médical :** "Besoin Secrétaire Médicale Centre Tilleuls. Tâches : Accueil, Frappe comptes-rendus, RDV Doctolib. Compétences : Vocabulaire médical, orthographe, empathie."
* **A5 Transport :** "Besoin Agent Exploitation Trans-Express. Tâches : Gérer chauffeurs, litiges livraisons. Profil : Géographie locale, résistance au stress, autorité."
* **A6 Immo :** "Besoin Assistant Commercial Immo-Sud. Tâches : Rédaction annonces web, tenue agenda. Compétences : Aisance numérique, plume vendeuse."

**Déroulement :**
1. **Définition :** Donne les données brutes. Demande Fiche de Poste + Profil.
2. **Diffusion :** Demande Annonce + Choix canaux.
3. **Sélection :** Génère 3 CV fictifs diversifiés (Solide, Manquant, Négligé). Demande tri justifié.
4. **Intégration :** Demande plan du Livret d'Accueil.

#### MODULE B : DÉPLACEMENTS (4 ÉTAPES)
*Donne toujours : Ville départ/arrivée, Dates, Horaires, Budget, Noms voyageurs.*
1. **Analyse :** L'élève reformule les contraintes.
2. **Recherche :** Génère 3 options transport fictives. Demande Comparatif.
3. **Réservation :** Demande liste infos pour Ordre de Mission.
4. **Feuille de Route :** Demande document final.

#### MODULE C : ACHATS (3 ÉTAPES)
*Donne toujours : Besoin précis (ex: 5 PC, 15 pouces, max 600€) et urgence.*
1. **Devis :** Demande mail demande de prix.
2. **Comparatif :** Génère 3 offres fournisseurs fictives. Demande Tableau Comparatif.
3. **Commande :** Validation mentions Bon de Commande.

#### MODULE D : VENTES (3 ÉTAPES)
*Donne toujours : Client, Produits, conditions (Remise, TVA).*
1. **Devis Client :** Demande devis (Calculs HT/TTC/TVA obligatoires).
2. **Facture :** Demande facture (Simule une erreur client à détecter).
3. **Relance :** Demande mail relance impayé.

#### MODULE E : ORGANISATION (2 ÉTAPES)
*Scénarios : Classement numérique, Archivage papier, ou Réclamation.*
1. **Action :** Demande arborescence, tri ou réponse écrite.
2. **Qualité :** Demande questionnaire satisfaction ou procédure.

### 6. RAPPORT FINAL (POUR LE PROFESSEUR)
À la fin, génère systématiquement ce bilan pour l'entretien d'explicitation :

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

# --- 4. GESTION DES LOGS ET DE L'HISTORIQUE ---
if "conversation_log" not in st.session_state:
    st.session_state.conversation_log = []

if "messages" not in st.session_state:
    # Message d'accueil initial (Copie exacte du Menu du Prompt pour cohérence)
    welcome_text = """Bonjour Opérateur. Bienvenue à l'Agence Pro’AGoRA.
Rappel de sécurité : Utilise uniquement des données fictives pour cet exercice.
Sur quel dossier souhaites-tu travailler ?

📂 **A. RECRUTEMENT** (Fiche de poste, Annonce, Sélection, Intégration)
✈️ **B. DÉPLACEMENTS** (Comparatif, Réservation, Feuille de route)
🛒 **C. ACHATS** (Devis, Comparatif, Commande)
💶 **D. VENTES & FACTURATION** (Devis client, Facture, Relance)
🗂️ **E. ORGANISATION** (Classement, Archivage, Qualité)

Indique la lettre de la mission pour commencer."""
    st.session_state.messages = [{"role": "assistant", "content": welcome_text}]

def save_log(student_id, role, content):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.conversation_log.append({
        "Heure": timestamp,
        "Eleve": student_id,
        "Role": role,
        "Message": content
    })

# --- 5. BARRE LATÉRALE (ADMINISTRATION) ---
with st.sidebar:
    st.header("Paramètres Élève")
    student_id = st.text_input("Ton Prénom (ou Pseudo) :", placeholder="Ex: Alex_T")
    st.info("⚠️ Règle d'or : N'utilise jamais ton vrai nom de famille ni de vraies données personnelles dans le chat.")
    
    st.divider()
    
    st.subheader("Outils Professeur")
    # Bouton de téléchargement des logs (pour toi)
    if st.session_state.conversation_log:
        df = pd.DataFrame(st.session_state.conversation_log)
        csv = df.to_csv(index=False, sep=';').encode('utf-8-sig')
        st.download_button(
            label="📥 Télécharger le suivi de session (CSV)",
            data=csv,
            file_name=f"suivi_mission_{student_id if student_id else 'anonyme'}.csv",
            mime="text/csv"
        )
    
    # Bouton pour recommencer à zéro
    if st.button("🗑️ Effacer la conversation"):
        st.session_state.messages = [{"role": "assistant", "content": welcome_text}]
        st.rerun()

# --- 6. INTERFACE DE CHAT ---
# Afficher l'historique des messages
for msg in st.session_state.messages:
    # On distingue visuellement l'assistant de l'élève
    avatar = "🤖" if msg["role"] == "assistant" else "🧑‍💻"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

# Zone de saisie élève
if prompt := st.chat_input("Écris ta réponse ici..."):
    
    # Vérification : L'élève a-t-il mis son pseudo ?
    if not student_id:
        st.toast("⚠️ Entre ton pseudo dans le menu à gauche pour commencer !", icon="🚨")
    else:
        # 1. Afficher le message de l'élève
        st.chat_message("user", avatar="🧑‍💻").write(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        save_log(student_id, "Eleve", prompt)

        # 2. Appel à l'IA (Groq / Llama 3)
        try:
            # Préparation du contexte pour l'IA
            messages_for_api = [{"role": "system", "content": SYSTEM_PROMPT}]
            # On n'envoie que les 10 derniers échanges pour garder de la mémoire sans exploser le contexte
            for m in st.session_state.messages[-20:]:
                messages_for_api.append({"role": m["role"], "content": m["content"]})

            with st.spinner("Le Superviseur analyse ta réponse..."):
                chat_completion = client.chat.completions.create(
                    messages=messages_for_api,
                    model="llama-3.3-70b-versatile", # Modèle très performant et rapide
                    temperature=0.6, # Température modérée pour rester pro mais varié
                    max_tokens=1500,
                )
            
            bot_reply = chat_completion.choices[0].message.content
            
            # 3. Afficher la réponse de l'IA
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(bot_reply)
            
            st.session_state.messages.append({"role": "assistant", "content": bot_reply})
            save_log(student_id, "Superviseur", bot_reply)
            
        except Exception as e:
            st.error(f"Une erreur technique est survenue : {e}")
