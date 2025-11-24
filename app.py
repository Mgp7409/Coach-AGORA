import streamlit as st
import pandas as pd
import os
import random
from groq import Groq
from datetime import datetime
from io import StringIO

# --- 0. IMPORTATION MODULE WORD ---
# Si cette ligne échoue, c'est que requirements.txt n'est pas lu
try:
    from docx import Document
except ImportError:
    st.error("⚠️ ERREUR : Le module 'python-docx' manque. Vérifiez votre fichier requirements.txt")

# --- 1. CONFIGURATION ---
st.set_page_config(
    page_title="Agence Pro'AGOrA", 
    page_icon="🏢",
    initial_sidebar_state="expanded"
)

# --- 2. STYLE CSS ---
hide_css = """
<style>
footer {visibility: hidden;}
header {visibility: visible !important;}
</style>
"""
st.markdown(hide_css, unsafe_allow_html=True)

# --- 3. GESTION DES CLÉS API (ROTATION) ---
def get_api_keys_list():
    """Récupère la liste des clés dans secrets.toml"""
    if "groq_keys" in st.secrets:
        return st.secrets["groq_keys"]
    # Fallback ancienne méthode
    single_key = os.environ.get("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY")
    if single_key:
        return [single_key]
    return []

def query_groq_with_rotation(messages):
    """Essaie plusieurs clés et plusieurs modèles si saturation"""
    available_keys = get_api_keys_list()
    
    if not available_keys:
        return None, "Aucune clé configurée"
    
    # Mélange pour répartir la charge
    keys_to_try = list(available_keys)
    random.shuffle(keys_to_try)
    
    # Liste des modèles (Le 70b est meilleur pour les longs textes Word)
    models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"]

    for key in keys_to_try:
        client = Groq(api_key=key)
        for model in models:
            try:
                # On augmente max_tokens pour permettre des réponses détaillées sur les rapports
                chat = client.chat.completions.create(
                    messages=messages,
                    model=model,
                    temperature=0.6,
                    max_tokens=1000, 
                )
                return chat.choices[0].message.content, model
            except:
                continue # Clé suivante
    
    return None, "Saturation Totale"

# --- 4. FONCTIONS FICHIERS (WORD & CSV) ---
def extract_text_from_docx(file):
    """Extrait le texte brut d'un fichier .docx"""
    try:
        doc = Document(file)
        full_text = []
        for para in doc.paragraphs:
            if para.text.strip():
                full_text.append(para.text)
        return "\n".join(full_text)
    except Exception as e:
        return f"Erreur lecture fichier : {str(e)}"

# Gestion de l'état
if "conversation_log" not in st.session_state:
    st.session_state.conversation_log = []
if "messages" not in st.session_state:
    st.session_state.messages = []
if "file_processed" not in st.session_state:
    st.session_state.file_processed = False

def save_log(student_id, role, content):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.conversation_log.append({
        "Heure": timestamp, "Eleve": student_id, "Role": role, "Message": content
    })

def load_session_from_df(df):
    st.session_state.conversation_log = df.to_dict('records')
    st.session_state.messages = []
    for row in df.itertuples():
        st.session_state.messages.append({
            "role": "assistant" if row.Role == "Assistant" else "user",
            "content": row.Message
        })
    st.success("Session chargée.")

# --- 5. INTELLIGENCE ARTIFICIELLE ---
SYSTEM_PROMPT = """
Tu es le Superviseur Virtuel de l'Agence Pro'AGOrA (Bac Pro).
Ton rôle : Aider l'élève à ANALYSER son activité professionnelle.

CONTEXTE :
L'élève peut te parler via le chat OU t'envoyer un compte-rendu écrit (fichier Word).

RÈGLES D'INTERACTION :
1. Si l'élève envoie un DOCUMENT (Compte-rendu) :
   - Accuse réception clairement ("J'ai lu ton document...").
   - Ne corrige pas l'orthographe tout de suite.
   - Pose une question de VÉRIFICATION pour s'assurer qu'il a compris ce qu'il a fait (ex: "Pourquoi as-tu choisi cet outil ?", "Explique-moi cette étape").

2. Si l'élève parle en CHAT :
   - Demande-lui de décrire son activité étape par étape.
   - Une seule question à la fois.

3. SÉCURITÉ :
   - Si tu détectes de vrais noms de famille ou données sensibles, rappelle la règle : "Attention, utilise des données fictives uniquement."
"""

MENU_AGORA = """
**Bonjour Opérateur.** Je suis ton Superviseur.

Tu peux :
1. **Discuter** avec moi ici pour décrire ton activité.
2. **Déposer ton compte-rendu Word** (menu de gauche) pour que je l'analyse.

**Pour commencer :**
Indique le BLOC concerné (GRCU, OSP, AP) ou dépose ton fichier.
"""

def get_fallback_response(last_user_msg):
    return "J'ai bien reçu ton message. Cependant, mes systèmes sont très sollicités. Peux-tu reformuler ou détailler les outils utilisés ?"

# --- 6. INTERFACE UTILISATEUR ---
st.title("🏢 Agence Pro'AGOrA")

# Indicateur discret de connexion (pour le prof uniquement)
if "groq_keys" in st.secrets and len(st.secrets["groq_keys"]) > 0:
    st.caption(f"🟢 Système actif ({len(st.secrets['groq_keys'])} clés)")
else:
    st.error("🔴 Aucune clé API trouvée dans les Secrets !")

# Message d'accueil au démarrage
if not st.session_state.messages:
    st.session_state.messages.append({"role": "assistant", "content": MENU_AGORA})

# --- BARRE LATÉRALE (SIDEBAR) ---
with st.sidebar:
    st.header("👤 Espace Élève")
    student_id = st.text_input("Ton Prénom :", placeholder="Ex: Alex")
    
    st.markdown("---")
    
    # ZONE DÉPÔT WORD
    st.subheader("📄 Déposer un compte-rendu")
    uploaded_docx = st.file_uploader("Format Word (.docx)", type=['docx'])
    
    # Traitement du fichier Word
    if uploaded_docx is not None and not st.session_state.file_processed:
        if not student_id:
            st.warning("⚠️ Entre ton prénom avant de déposer le fichier !")
        else:
            with st.spinner("Lecture du document en cours..."):
                # 1. Extraction du texte
                doc_text = extract_text_from_docx(uploaded_docx)
                
                # 2. On tronque si trop long (pour éviter crash API)
                if len(doc_text) > 10000:
                    doc_text = doc_text[:10000] + "\n...[Suite tronquée]"
                
                # 3. Injection dans le chat comme si l'élève l'avait écrit
                user_msg = f"Voici mon compte-rendu d'activité (Fichier Importé) :\n\n{doc_text}"
                st.session_state.messages.append({"role": "user", "content": user_msg})
                save_log(student_id, "Eleve (Doc)", "Envoi Fichier Word")
                
                # 4. On marque le fichier comme traité
                st.session_state.file_processed = True
                st.rerun() # Recharge la page pour déclencher la réponse IA

    # Reset du flag si on enlève le fichier
    if st.session_state.file_processed and not uploaded_docx:
        st.session_state.file_processed = False

    st.markdown("---")
    
    # Gestion Session (Sauvegarde/Reprise)
    st.caption("Gestion Session")
    if st.session_state.conversation_log:
        df = pd.DataFrame(st.session_state.conversation_log)
        st.download_button("💾 Sauvegarder (CSV)", df.to_csv(index=False, sep=';').encode('utf-8-sig'), f"agora_{student_id}.csv", "text/csv")
    
    uploaded_csv = st.file_uploader("Reprendre session (CSV)", type=['csv'])
    if uploaded_csv:
        try:
            s_data = StringIO(uploaded_csv.getvalue().decode('utf-8-sig')).read()
            load_session_from_df(pd.read_csv(StringIO(s_data), sep=';'))
        except: st.error("Fichier CSV invalide")

    if st.button("🗑️ Nouvelle Session"):
        st.session_state.messages = [{"role": "assistant", "content": MENU_AGORA}]
        st.session_state.conversation_log = []
        st.session_state.file_processed = False
        st.rerun()

# --- 7. ZONE DE CHAT CENTRALE ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        # Si c'est un très long message (document), on le cache dans un accordéon
        if "Voici mon compte-rendu d'activité (Fichier Importé)" in msg["content"]:
            with st.expander("📄 Voir le contenu du document envoyé"):
                st.write(msg["content"])
        else:
            st.write(msg["content"])

# Détection : Est-ce à l'IA de répondre ? (Si dernier message = user)
last_msg_is_user = len(st.session_state.messages) > 0 and st.session_state.messages[-1]["role"] == "user"

if prompt := st.chat_input("Écris ta réponse ici..."):
    if not student_id:
        st.toast("⚠️ N'oublie pas ton prénom à gauche !")
    else:
        st.chat_message("user").write(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        save_log(student_id, "Eleve", prompt)
        last_msg_is_user = True
        st.rerun() # Force le rafraîchissement pour lancer l'IA

# Réponse IA (Automatique après Chat OU Upload Word)
if last_msg_is_user:
    with st.chat_message("assistant"):
        with st.spinner("Le superviseur analyse ton travail..."):
            
            # Préparation historique (8 derniers messages)
            messages_api = [{"role": "system", "content": SYSTEM_PROMPT}]
            recent_history = st.session_state.messages[-8:] 
            for m in recent_history:
                messages_api.append({"role": m["role"], "content": m["content"]})
            
            # Appel API
            reply, info_debug = query_groq_with_rotation(messages_api)
            
            if not reply:
                reply = get_fallback_response("Erreur")
            
            st.write(reply)
    
    st.session_state.messages.append({"role": "assistant", "content": reply})
    save_log(student_id, "Assistant", reply)
