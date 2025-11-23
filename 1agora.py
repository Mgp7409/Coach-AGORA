import streamlit as st
import pandas as pd
from groq import Groq
from datetime import datetime

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="1AGORA - Entraînement Infini", page_icon="♾️")

# Masquer le menu Streamlit pour faire "App Pro"
hide_menu_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """
st.markdown(hide_menu_style, unsafe_allow_html=True)

st.title("♾️ Agence PRO'AGORA - Générateur de Missions")
st.caption("Entraînement illimité sur les chapitres du livre de 1ère")

# --- 2. CONNEXION GROQ ---
try:
    api_key = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=api_key)
except:
    st.error("ERREUR : Clé API manquante. Vérifiez les Secrets.")
    st.stop()

# --- 3. STRUCTURE DU LIVRE (MENU) ---
# Ici, on ne met que les TITRES. C'est l'IA qui inventera le contenu.
MENU_LIVRE = {
    "Thème 1 : RELATIONS CLIENTS": [
        "Dossier 1 : Actualiser la base clients",
        "Dossier 2 : Établir un Devis",
        "Dossier 3 : Valider une Commande",
        "Dossier 4 : Facturation & Livraison",
        "Dossier 5 : Relance impayés (Amiable)"
    ],
    "Thème 2 : RELATIONS FOURNISSEURS": [
        "Dossier 6 : Actualiser la base fournisseurs",
        "Dossier 7 : Comparatif & Commande d'achat",
        "Dossier 8 : Réception & Réserves (Litige)",
        "Dossier 9 : Contrôle Facture & Paiement"
    ],
    "Thème 3 : GESTION INTERNE": [
        "Dossier 10 : Suivi des Stocks (Inventaire)",
        "Dossier 11 : Mise à jour du SI (Note de service)",
        "Dossier 12 : Aménagement des espaces"
    ]
}

# --- 4. LE CERVEAU (PROMPT "GÉNÉRATEUR ALÉATOIRE") ---
SYSTEM_PROMPT = """
TU ES : Le Superviseur de l'Agence PRO'AGORA.
TON RÔLE : Entraîner un élève de 1ère Bac Pro AGOrA.

RÈGLES DU JEU (IMPORTANT) :
1. L'élève va choisir un Chapitre du livre (ex: "Établir un Devis").
2. À ce moment-là, TU DOIS INVENTER IMMÉDIATEMENT UN SCÉNARIO ALÉATOIRE COMPLET.
3. Ne reprends pas les entreprises du livre. Invente des PME variées (Garage, Boulangerie, Agence Web, BTP, Mode...).
4. FOURNIS LES DONNÉES BRUTES : Tu dois donner les noms, les adresses, les produits, les prix, les quantités, les dates. L'élève ne doit rien inventer.

EXEMPLE D'INTERACTION :
- Élève : "Je veux travailler sur le Dossier 2 : Devis"
- Toi : "Bien reçu. Voici ta mission aléatoire du jour :
  Contexte : Tu es assistant chez 'Vélo-City', magasin de réparation.
  Client : M. Paul (Adresse X).
  Besoin : Il veut réparer 3 vélos VTT (Forfait révision à 45€ HT l'unité) et acheter 2 casques (30€ HT l'unité).
  Consigne : Établis le devis avec une TVA à 20%.
  À toi de jouer !"

POSTURE :
- Professionnel, bienveillant mais exigeant sur la rigueur.
- Une étape à la fois.
- Si l'élève bloque, aide-le sans donner la réponse.
"""

# --- 5. GESTION DES LOGS ---
if "conversation_log" not in st.session_state:
    st.session_state.conversation_log = []
if "messages" not in st.session_state:
    # Message d'accueil neutre (l'IA prendra le relais au lancement)
    st.session_state.messages = []

def save_log(student_id, role, content):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.conversation_log.append({
        "Heure": timestamp,
        "Eleve": student_id,
        "Role": role,
        "Message": content
    })

# Fonction pour déclencher le scénario via l'IA
def lancer_scenario_aleatoire():
    theme = st.session_state.theme_select
    dossier = st.session_state.dossier_select
    
    # On vide l'historique pour commencer propre
    st.session_state.messages = []
    
    # On crée une "instruction invisible" pour forcer l'IA à démarrer
    prompt_demarrage = f"L'élève a choisi le module : '{theme} - {dossier}'. INVENTE un scénario aléatoire (Entreprise, Données chiffrées, Contexte) pour ce dossier et donne-lui les consignes maintenant."
    
    # On ajoute juste le contexte système, pas de message utilisateur visible
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}, 
            {"role": "user", "content": prompt_demarrage}]
    
    try:
        chat_completion = client.chat.completions.create(
            messages=msgs,
            model="llama-3.3-70b-versatile",
            temperature=0.8, # Un peu plus créatif pour varier les scénarios
        )
        bot_reply = chat_completion.choices[0].message.content
        
        # On affiche la réponse de l'IA (le scénario)
        st.session_state.messages.append({"role": "assistant", "content": bot_reply})
        
    except Exception as e:
        st.error(f"Erreur de génération : {e}")

# --- 6. INTERFACE (SIDEBAR) ---
with st.sidebar:
    st.header("🗂️ Menu des Missions")
    student_id = st.text_input("Identifiant Opérateur :")
    st.info("⚠️ Les scénarios sont générés par IA et changent à chaque fois !")
    st.markdown("---")

    # Menu Livre
    theme_choisi = st.selectbox("1. Choisis le Thème :", list(MENU_LIVRE.keys()), key="theme_select")
    dossier_choisi = st.selectbox("2. Choisis le Dossier :", MENU_LIVRE[theme_choisi], key="dossier_select")
    
    st.markdown("---")
    
    # BOUTON MAGIQUE
    # Quand on clique, ça appelle la fonction 'lancer_scenario_aleatoire'
    st.button("🎲 GÉNÉRER UNE MISSION", type="primary", on_click=lancer_scenario_aleatoire)

    st.markdown("---")
    
    # Sauvegarde
    st.subheader("💾 Sauvegarde")
    if st.session_state.conversation_log:
        df = pd.DataFrame(st.session_state.conversation_log)
        csv = df.to_csv(index=False, sep=';').encode('utf-8-sig')
        st.download_button("📥 Télécharger CSV", csv, "mission_agora.csv", "text/csv")

    # Reprise
    st.subheader("📂 Reprendre")
    uploaded_file = st.file_uploader("Charger un CSV", type=['csv'])
    if uploaded_file and st.button("🔄 Restaurer"):
        try:
            df_hist = pd.read_csv(uploaded_file, sep=';')
            st.session_state.messages = []
            st.session_state.conversation_log = []
            for _, row in df_hist.iterrows():
                role_chat = "user" if row['Role'] == "Eleve" else "assistant"
                st.session_state.messages.append({"role": role_chat, "content": row['Message']})
                save_log(row.get('Eleve', student_id), row['Role'], row['Message'])
            st.success("Session restaurée !")
            st.rerun()
        except: st.error("Fichier invalide.")

# --- 7. ZONE DE CHAT ---
if not st.session_state.messages:
    st.info("👋 Bonjour ! Choisis un dossier à gauche et clique sur **GÉNÉRER UNE MISSION** pour commencer l'entraînement.")
else:
    # Affichage des messages
    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])

    # Zone de saisie
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
                # On reconstruit l'historique pour que l'IA suive la conversation
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
                # Pas de rerun nécessaire ici, le chat se met à jour tout seul
                
            except Exception as e:
                st.error(f"Erreur : {e}")
