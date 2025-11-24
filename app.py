import streamlit as st
import pandas as pd
import os
import random
import time
from groq import Groq, RateLimitError, APIConnectionError
from datetime import datetime
from io import StringIO

# --- 0. IMPORTATION SPÉCIALE WORD ---
try:
    from docx import Document
except ImportError:
    st.error("⚠️ Le module 'python-docx' n'est pas installé. Ajoutez 'python-docx' à votre fichier requirements.txt")

# --- 1. CONFIGURATION ---
st.set_page_config(
    page_title="Agence Pro'AGOrA", 
    page_icon="🏢",
    initial_sidebar_state="expanded"
)

# --- 2. CSS ---
hide_css = """
<style>
footer {visibility: hidden;}
header {visibility: visible !important;}
</style>
"""
st.markdown(hide_css, unsafe_allow_html=True)

# --- 3. GESTION DES CLÉS ---
def get_api_keys_list():
    if "groq_keys" in st.secrets:
        return st.secrets["groq_keys"]
    single_key = os.environ.get("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY")
    if single_key:
        return [single_key]
    return []

def query_groq_with_rotation(messages):
    available_keys = get_api_keys_list()
    if not available_keys:
        return None, "Aucune clé"
    
    keys_to_try = list(available_keys)
    random.shuffle(keys_to_try)
    
    # On ajoute Llama 3.3 qui gère très bien les textes longs (comme les Word)
    models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"]

    for key in keys_to_try:
        client = Groq(api_key=key)
        for model in models:
            try:
                chat = client.chat.completions.create(
                    messages=messages,
                    model=model,
                    temperature=0.6,
                    max_tokens=800, # Augmenté pour répondre aux rapports
                )
                return chat.choices[0].message.content, model
            except:
                continue
    return None, "Erreur Totale"

# --- 4. DATA & FONCTIONS FICHIERS ---
if "conversation_log" not in st.session_state:
    st.session_state.conversation_log = []

if "messages" not in st.session_state:
    st.session_state.messages = []

# Nouvelle variable pour éviter que le fichier soit analysé en boucle
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

def extract_text_from_docx(file):
    """Lit un fichier Word et retourne le texte brut."""
    try:
        doc = Document(file)
        full_text = []
        for para in doc.paragraphs:
            if para.text.strip(): # On ignore les lignes vides
                full_text.append(para.text)
        return "\n".join(full_text)
    except Exception as e:
        return f"Erreur de lecture du fichier : {e}"

# --- 5. CERVEAU SUPERVISEUR ---
SYSTEM_PROMPT = """
Tu es le Superviseur Virtuel de l'Agence Pro'AGOrA.
Ton rôle est d'aider l'élève à ANALYSER l'activité qu'il a réalisée (décrite par chat ou via un fichier Word importé).

RÈGLES STRICTES :
1. Si l'élève envoie un TEXTE LONG (rapport/compte-rendu) :
   - Lis-le attentivement.
   - Confirme la réception ("J'ai lu ton document sur...").
   - Ne corrige pas tout de suite l'orthographe.
   - Pose une question précise pour vérifier si l'élève maîtrise ce qu'il a écrit (ex: "Pourquoi as-tu utilisé cet outil ?" ou "Peux-tu détailler l'étape X ?").

2. Si l'échange est verbal (chat court) :
   - Demande de décrire l'activité étape par étape.

3. Règle d'Or : Données fictives uniquement. Si le document contient de vrais noms, alerte l'élève.
"""

MENU_AGORA = """
**Bonjour Opérateur.** Je suis ton Superviseur.

Tu peux soit **discuter** avec moi, soit **déposer ton compte-rendu Word** (à gauche) pour que je l'analyse.

**Pour commencer :**
1. Choisis ton BLOC (GRCU, OSP, AP).
2. Ou dépose ton fichier `.docx`.
"""

def get_fallback_response(last_user_msg):
    """Mode Secours."""
    return "J'ai bien reçu ton message. Cependant, mes systèmes d'analyse sont momentanément saturés. Peux-tu reformuler ou détailler les outils utilisés ?"

# --- 6. INTERFACE ---
st.title("🏢 Agence Pro'AGOrA")

# Diagnostic Clés discret
if "groq_keys" in st.secrets and len(st.secrets["groq_keys"]) > 0:
    st.caption(f"🟢 Système connecté ({len(st.secrets['groq_keys'])} clés)")
else:
    st.error("🔴 Aucune clé API trouvée.")

if not st.session_state.messages:
    st.session_state.messages.append({"role": "assistant", "content": MENU_AGORA})

with st.sidebar:
    st.header("👤 Élève")
    student_id = st.text_input("Ton Prénom :", placeholder="Ex: Alex")
    
    st.markdown("---")
    
    # --- ZONE DÉPÔT WORD ---
    st.subheader("📄 Analyse de Document")
    uploaded_docx = st.file_uploader("Dépose ton compte-rendu (.docx)", type=['docx'])
    
    # Logique de traitement du fichier
    if uploaded_docx is not None and not st.session_state.file_processed:
        if not student_id:
            st.error("Indique ton prénom d'abord !")
        else:
            with st.spinner("Lecture du document..."):
                doc_text = extract_text_from_docx(uploaded_docx)
                
                # On limite la taille pour ne pas faire exploser l'IA (env. 3 pages max)
                if len(doc_text) > 8000: 
                    doc_text = doc_text[:8000] + "... (texte tronqué)"
                
                # On crée un message utilisateur artificiel avec le contenu du doc
                user_msg = f"[DOCUMENT IMPORTÉ] Voici mon compte-rendu d'activité :\n\n{doc_text}"
                st.session_state.messages.append({"role": "user", "content": user_msg})
                save_log(student_id, "Eleve (Doc)", "Envoi d'un fichier Word")
                
                # On marque comme traité pour ne pas recharger à chaque clic
                st.session_state.file_processed = True
                st.rerun() # On recharge pour lancer l'analyse IA immédiatement

    # Bouton pour "oublier" le fichier et en mettre un autre
    if st.session_state.file_processed and not uploaded_docx:
        st.session_state.file_processed = False

    st.markdown("---")
    
    if st.session_state.conversation_log:
        df = pd.DataFrame(st.session_state.conversation_log)
        st.download_button("💾 Sauvegarder conversation", df.to_csv(index=False, sep=';').encode('utf-8-sig'), f"agora_{student_id}.csv", "text/csv")
    
    if st.button("🗑️ Nouvelle Session"):
        st.session_state.messages = [{"role": "assistant", "content": MENU_AGORA}]
        st.session_state.conversation_log = []
        st.session_state.file_processed = False
        st.rerun()

# --- 7. CHAT & ANALYSE ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        # Si le message est le gros document, on l'affiche en "fermé" pour ne pas polluer l'écran
        if "[DOCUMENT IMPORTÉ]" in msg["content"]:
            with st.expander("📄 Voir le contenu du document envoyé"):
                st.write(msg["content"])
        else:
            st.write(msg["content"])

# Déclenchement automatique de la réponse IA si le dernier message est un document (User)
last_message_is_user = len(st.session_state.messages) > 0 and st.session_state.messages[-1]["role"] == "user"

if prompt := st.chat_input("Discuter avec le superviseur..."):
    if not student_id:
        st.toast("⚠️ Prénom obligatoire !")
    else:
        st.chat_message("user").write(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        save_log(student_id, "Eleve", prompt)
        last_message_is_user = True

# Si c'est au tour de l'IA de répondre (soit après un chat, soit après un upload Word)
if last_message_is_user:
    # Context (8 derniers messages)
    messages_api = [{"role": "system", "content": SYSTEM_PROMPT}]
    recent_history = st.session_state.messages[-8:] 
    for m in recent_history:
        messages_api.append({"role": m["role"], "content": m["content"]})

    with st.chat_message("assistant"):
        with st.spinner("Analyse en cours..."):
            reply, info = query_groq_with_rotation(messages_api)
            if not reply:
                reply = get_fallback_response("Erreur")
            st.write(reply)
    
    st.session_state.messages.append({"role": "assistant", "content": reply})
    save_log(student_id, "Assistant", reply)
