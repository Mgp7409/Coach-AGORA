import streamlit as st
import pandas as pd
import random
from groq import Groq
from datetime import datetime
from io import StringIO

# --- 0. SÉCURITÉ & DÉPENDANCES ---
try:
    from docx import Document
except ImportError:
    st.error("⚠️ ERREUR CRITIQUE : Le module 'python-docx' manque. Ajoutez-le au fichier requirements.txt")
    st.stop()

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Superviseur Pro'AGOrA", 
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. STYLE CSS & FOOTER FIXE ---
st.markdown("""
<style>
    footer {visibility: hidden;}
    .reportview-container .main .block-container {padding-top: 2rem;}
    
    /* BANDEAU LÉGAL FIXE EN BAS */
    .fixed-footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #f8f9fa;
        color: #555;
        text-align: center;
        padding: 8px 10px;
        font-size: 12px;
        border-top: 1px solid #e1e4e8;
        z-index: 99999;
        line-height: 1.4;
    }

    /* Remonter la zone de saisie */
    [data-testid="stBottom"] {
        bottom: 60px !important;
        padding-bottom: 0px !important;
    }
    
    /* Alerte Latérale */
    .sidebar-alert {
        padding: 1rem;
        background-color: #ffebee;
        border: 1px solid #ffcdd2;
        color: #c62828;
        border-radius: 5px;
        font-weight: bold;
        font-size: 0.9rem;
        margin-bottom: 1rem;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. GESTION DES CLÉS API (ROTATION) ---
def get_api_keys_list():
    if "groq_keys" in st.secrets:
        return st.secrets["groq_keys"]
    elif "GROQ_API_KEY" in st.secrets:
        return [st.secrets["GROQ_API_KEY"]]
    return []

def query_groq_with_rotation(messages):
    available_keys = get_api_keys_list()
    if not available_keys:
        return None, "ERREUR CONFIG : Aucune clé API trouvée."
    
    keys_to_try = list(available_keys)
    random.shuffle(keys_to_try)
    # Llama 3 70b est le meilleur pour l'analyse de documents
    models = ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "llama-3.1-8b-instant"]

    for key in keys_to_try:
        try:
            client = Groq(api_key=key)
            for model in models:
                try:
                    chat = client.chat.completions.create(
                        messages=messages,
                        model=model,
                        temperature=0.5, # Température basse pour éviter les hallucinations
                        max_tokens=1024, 
                    )
                    return chat.choices[0].message.content, model
                except: continue 
        except: continue
    return None, "SATURATION SERVICE."

# --- 4. TRAITEMENT FICHIERS WORD ---
def extract_text_from_docx(file):
    try:
        doc = Document(file)
        full_text = []
        for para in doc.paragraphs:
            if para.text.strip():
                full_text.append(para.text)
        text = "\n".join(full_text)
        
        # SÉCURITÉ : Limite de taille (environ 2-3 pages max) pour ne pas saturer l'IA
        if len(text) > 8000:
            text = text[:8000] + "\n\n[...TEXTE TRONQUÉ CAR TROP LONG...]"
        return text
    except Exception as e:
        return f"Erreur de lecture : {str(e)}"

# --- 5. INITIALISATION SESSION ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "logs" not in st.session_state:
    st.session_state.logs = []

def log_interaction(student, role, content):
    st.session_state.logs.append({
        "Heure": datetime.now().strftime("%H:%M:%S"),
        "Utilisateur": student,
        "Role": role,
        "Message": content[:50]
    })

# --- 6. LE "SUPER PROMPT" PÉDAGOGIQUE (MODIFIÉ) ---
SYSTEM_PROMPT = """
RÔLE : Tu es le Superviseur Virtuel de l'Agence Pro'AGOrA.
TON : Professionnel, encourageant mais exigeant (Vouvoiement).
CIBLE : Élèves de Première Bac Pro.
MISSION : Guider l'élève pour qu'il analyse sa propre pratique.

⛔ INTERDICTIONS ABSOLUES :
1. NE JAMAIS FAIRE LE TRAVAIL à la place de l'élève (ne rédige pas les mails, ne fais pas les calculs).
2. NE PAS ÉCRIRE DE LONGS PARAGRAPHES. Tes réponses doivent être COURTES (max 3 phrases).
3. Une seule question à la fois.

DÉROULEMENT :
1. Si l'élève envoie un DOCUMENT (Word) : Analyse-le. Vérifie s'il respecte les codes professionnels (orthographe, formules de politesse, mentions obligatoires). Dis ce qui va, et pose UNE question sur ce qui manque.
2. Si l'élève DISCUTE : Guide-le pas à pas.
   - Demande sur quel BLOC (1, 2 ou 3) il travaille.
   - Demande le contexte (Entreprise/Service).
   - Demande les outils utilisés.
   - Vérifie la cohérence.

SÉCURITÉ : Si l'élève utilise un VRAI nom de famille ou une vraie entreprise, demande-lui d'anonymiser immédiatement.
"""

INITIAL_MESSAGE = """
👋 **Bonjour Opérateur/Opératrice.**

Bienvenue à l'Agence Pro'AGOrA. Je suis ton Superviseur Virtuel.

**⚠️ SÉCURITÉ :** Utilise uniquement des données **FICTIVES** (Faux noms, fausses entreprises).

**Pour commencer :**
Sur quel BLOC travailles-tu (1, 2 ou 3) ?
"""

if not st.session_state.messages:
    st.session_state.messages.append({"role": "assistant", "content": INITIAL_MESSAGE})

# --- 7. INTERFACE GRAPHIQUE ---

st.title("🎓 Supervision Agence Pro'AGOrA")

# A. BARRE LATÉRALE
with st.sidebar:
    st.image("https://img.icons8.com/color/96/student-center.png", width=80)
    st.header("Profil Élève")
    
    st.markdown("""
    <div class="sidebar-alert">
    🚫 INTERDIT : Ne jamais saisir de données personnelles réelles.
    </div>
    """, unsafe_allow_html=True)
    
    student_name = st.text_input("Ton Prénom (seulement) :", placeholder="Ex: Thomas")
    
    st.divider()
    
    # --- ZONE DÉPÔT DE PRODUCTION (WORD) ---
    st.subheader("📂 Déposer ma production")
    st.caption("Dépose ton fichier Word (.docx) ici pour correction.")
    uploaded_file = st.file_uploader("Choisir un fichier", type=['docx'], label_visibility="collapsed")
    
    if uploaded_file and student_name:
        if st.button("🚀 Envoyer à la correction"):
            with st.spinner("Lecture et analyse en cours..."):
                text_content = extract_text_from_docx(uploaded_file)
                
                # Injection d'un prompt spécifique pour l'analyse de fichier
                prompt_analysis = f"Voici ma production (Fichier Word : {uploaded_file.name}) :\n\n{text_content}"
                
                st.session_state.messages.append({"role": "user", "content": prompt_analysis})
                log_interaction(student_name, "Eleve", f"Upload: {uploaded_file.name}")
                st.rerun() # On recharge pour laisser l'IA répondre

    st.divider()

    # --- ZONE SAUVEGARDE & REPRISE ---
    st.subheader("💾 Sauvegarde")
    if len(st.session_state.messages) > 1:
        chat_df = pd.DataFrame(st.session_state.messages)
        csv_data = chat_df.to_csv(index=False).encode('utf-8')
        filename = f"agora_{student_name if student_name else 'anonyme'}.csv"
        st.download_button("📥 Télécharger ma session", csv_data, filename, "text/csv")
    
    uploaded_session = st.file_uploader("Reprendre une session (.csv)", type=['csv'])
    if uploaded_session and st.button("🔄 Restaurer"):
        try:
            df_restored = pd.read_csv(uploaded_session)
            if 'role' in df_restored.columns and 'content' in df_restored.columns:
                st.session_state.messages = df_restored.to_dict('records')
                st.success("✅ Session restaurée !")
                st.rerun()
        except: st.error("❌ Fichier invalide.")

    st.divider()
    if st.button("🗑️ Effacer tout"):
        st.session_state.messages = [{"role": "assistant", "content": INITIAL_MESSAGE}]
        st.session_state.logs = []
        st.rerun()

# B. ZONE DE CHAT
chat_container = st.container()
with chat_container:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar="🤖" if msg["role"] == "assistant" else "🧑‍🎓"):
            # Si c'est le contenu brut du fichier Word, on le cache dans un menu déroulant pour ne pas polluer l'écran
            if "Voici ma production (Fichier Word" in msg["content"]:
                with st.expander("📄 Voir le contenu du fichier analysé"):
                    st.write(msg["content"])
            else:
                st.markdown(msg["content"])
    st.write("<br><br><br>", unsafe_allow_html=True)

# C. BANDEAU LÉGAL
st.markdown("""
<div class="fixed-footer">
    ℹ️ <b>Outil Pédagogique Expérimental (IA)</b><br>
    Cet assistant peut commettre des erreurs. Vérifiez toujours avec votre professeur. 
    Aucune donnée personnelle ne doit être saisie ici.
</div>
""", unsafe_allow_html=True)

# D. LOGIQUE DE RÉPONSE IA
# Vérifie si le dernier message vient de l'utilisateur (ou d'un upload fichier)
if st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Analyse du superviseur..."):
            messages_payload = [{"role": "system", "content": SYSTEM_PROMPT}]
            # On garde les 10 derniers messages pour le contexte
            messages_payload.extend(st.session_state.messages[-10:])
            
            response_content, _ = query_groq_with_rotation(messages_payload)
            
            if not response_content:
                response_content = "⚠️ Mes systèmes sont saturés. Peux-tu répéter ?"
            
            st.markdown(response_content)
            
    st.session_state.messages.append({"role": "assistant", "content": response_content})
    # Pas de st.rerun() ici pour éviter une boucle infinie, Streamlit gère l'affichage séquentiel

# E. SAISIE UTILISATEUR (CHAT)
if user_input := st.chat_input("Réponds au superviseur ici..."):
    if not student_name:
        st.toast("⚠️ Indique ton prénom à gauche !", icon="👉")
    else:
        st.session_state.messages.append({"role": "user", "content": user_input})
        log_interaction(student_name, "User", user_input)
        st.rerun()
