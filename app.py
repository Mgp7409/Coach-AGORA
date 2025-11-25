import streamlit as st
import pandas as pd
import os
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
    page_title="Restitution Pro'AGOrA", 
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. STYLE CSS & FOOTER FIXE ---
st.markdown("""
<style>
    /* Cache le footer standard Streamlit */
    footer {visibility: hidden;}
    
    /* Ajustement du conteneur principal */
    .reportview-container .main .block-container {padding-top: 2rem;}
    
    /* LE BANDEAU DE BAS DE PAGE (Disclaimer) */
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
        z-index: 99999; /* Toujours au-dessus */
        line-height: 1.4;
    }

    /* ASTUCE CRUCIALE : Remonter la barre de chat pour ne pas qu'elle soit cachée par le footer */
    [data-testid="stBottom"] {
        bottom: 60px !important; /* On remonte la zone de saisie de 60px */
        padding-bottom: 0px !important;
    }
    
    /* Style pour l'alerte latérale */
    .sidebar-alert {
        padding: 1rem;
        background-color: #ffebee;
        border: 1px solid #ffcdd2;
        color: #c62828;
        border-radius: 5px;
        font-weight: bold;
        font-size: 0.9rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. GESTION DES CLÉS API ---
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
    models = ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "llama-3.1-8b-instant"]

    for key in keys_to_try:
        try:
            client = Groq(api_key=key)
            for model in models:
                try:
                    chat = client.chat.completions.create(
                        messages=messages,
                        model=model,
                        temperature=0.5,
                        max_tokens=1024, 
                    )
                    return chat.choices[0].message.content, model
                except: continue 
        except: continue
    return None, "SATURATION SERVICE."

# --- 4. TRAITEMENT FICHIERS ---
def extract_text_from_docx(file):
    try:
        doc = Document(file)
        return "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
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

SYSTEM_PROMPT = """
RÔLE : Tu es le Superviseur Virtuel de l'Agence Pro'AGOrA.
TON : Professionnel, encourageant mais exigeant (Vouvoiement).
MISSION : Guider l'élève (Bac Pro) pour qu'il analyse sa propre pratique. Tu ne fais JAMAIS le travail à sa place.

CADRE RÉGLEMENTAIRE (CRITIQUE) :
1. Tu vérifies si l'élève utilise des données FICTIVES. Si un vrai nom apparaît, stoppe tout et demande l'anonymisation.
2. Tu t'appuies sur le Référentiel Bac Pro AGORA (Indicateurs de compétence).

DÉROULEMENT SÉQUENCÉ :
1. CALIBRAGE : Demande le niveau (Seconde/Première/Terminale) et le Bloc (1, 2 ou 3).
2. CONTEXTE : Demande le lieu (PME, Asso...) et le service.
3. ANALYSE : Demande de décrire les étapes et les outils numériques.
4. ÉVALUATION : Vérifie la pertinence des outils. Si l'élève est bloqué, propose un exemple fictif.
5. BILAN : Synthétise les points forts et donne 1 axe de progrès pour le dossier CCF.

RÈGLE D'OR : Une seule question à la fois. Attends toujours la réponse de l'élève.
"""

INITIAL_MESSAGE = """
👋 **Bonjour Opérateur/Opératrice.**

Bienvenue à l'Agence Pro'AGOrA. Je suis ton Superviseur Virtuel.

**⚠️ RÈGLE DE SÉCURITÉ :** Nous travaillons sur des cas **FICTIFS**. 
N'écris jamais ton vrai nom de famille, ni celui d'une vraie entreprise.

**Pour commencer :**
Es-tu en Seconde, Première ou Terminale ? Et sur quel BLOC travailles-tu (1, 2 ou 3) ?
"""

if not st.session_state.messages:
    st.session_state.messages.append({"role": "assistant", "content": INITIAL_MESSAGE})

# --- 6. INTERFACE GRAPHIQUE ---

st.title("🎓 Restitution PFMP Pro'AGOrA")

# A. BARRE LATÉRALE
with st.sidebar:
    st.image("https://img.icons8.com/color/96/student-center.png", width=80)
    st.header("Profil Élève")
    
    # Alerte Rouge Permanente
    st.markdown("""
    <div class="sidebar-alert">
    🚫 INTERDIT : Ne jamais saisir de données personnelles réelles.
    </div>
    """, unsafe_allow_html=True)
    
    student_name = st.text_input("Ton Prénom (seulement) :", placeholder="Ex: Thomas")
    
    st.divider()
    
    # --- ZONE ANALYSE DOCUMENT ---
    st.subheader("📂 Analyse de Document")
    uploaded_file = st.file_uploader("Fichier .docx uniquement", type=['docx'])
    
    if uploaded_file and student_name:
        if st.button("🚀 Analyser ce document"):
            with st.spinner("Lecture et analyse en cours..."):
                text_content = extract_text_from_docx(uploaded_file)
                prompt_analysis = f"Voici mon compte-rendu écrit (Fichier Word) : \n\n{text_content[:8000]}"
                st.session_state.messages.append({"role": "user", "content": prompt_analysis})
                log_interaction(student_name, "Eleve", "Upload Fichier")
                st.rerun()

    st.divider()

    # --- ZONE SAUVEGARDE & REPRISE (NOUVEAU) ---
    st.subheader("💾 Sauvegarde & Reprise")
    
    # 1. BOUTON SAUVEGARDE
    if len(st.session_state.messages) > 1:
        # On convertit l'historique en DataFrame puis en CSV
        chat_df = pd.DataFrame(st.session_state.messages)
        csv_data = chat_df.to_csv(index=False).encode('utf-8')
        
        filename = f"session_agora_{student_name if student_name else 'anonyme'}.csv"
        
        st.download_button(
            label="📥 Télécharger ma session (.csv)",
            data=csv_data,
            file_name=filename,
            mime="text/csv",
            help="Clique pour enregistrer ton travail et le reprendre plus tard."
        )
    
    # 2. BOUTON REPRISE
    uploaded_session = st.file_uploader("Reprendre un travail (.csv)", type=['csv'])
    if uploaded_session:
        if st.button("🔄 Restaurer l'historique"):
            try:
                # Lecture du CSV
                df_restored = pd.read_csv(uploaded_session)
                # Vérification basique de la structure
                if 'role' in df_restored.columns and 'content' in df_restored.columns:
                    # Conversion en liste de dictionnaires pour la session_state
                    st.session_state.messages = df_restored.to_dict('records')
                    st.success("✅ Session restaurée avec succès !")
                    st.rerun()
                else:
                    st.error("❌ Fichier CSV invalide (colonnes manquantes).")
            except Exception as e:
                st.error(f"❌ Erreur lors de la lecture : {e}")

    st.divider()
    
    if st.button("🗑️ Nouvelle Session (Effacer tout)"):
        st.session_state.messages = [{"role": "assistant", "content": INITIAL_MESSAGE}]
        st.session_state.logs = []
        st.rerun()

# B. ZONE DE CHAT
chat_container = st.container()
with chat_container:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar="🤖" if msg["role"] == "assistant" else "🧑‍🎓"):
            if "Voici mon compte-rendu écrit" in msg["content"]:
                with st.expander("📄 Voir le document envoyé"):
                    st.write(msg["content"])
            else:
                st.markdown(msg["content"])
    
    # Espace vide pour éviter que le dernier message ne soit caché par la zone de saisie remontée
    st.write("<br><br><br>", unsafe_allow_html=True)

# C. INJECTION DU FOOTER (BANDEAU PERMANENT)
st.markdown("""
<div class="fixed-footer">
    ℹ️ <b>Outil Pédagogique Expérimental (IA)</b><br>
    Cet assistant est une Intelligence Artificielle. Il peut commettre des erreurs. 
    Vérifiez toujours les informations avec votre professeur. 
    Aucune donnée personnelle ne doit être saisie ici.
</div>
""", unsafe_allow_html=True)

# D. SAISIE UTILISATEUR
if user_input := st.chat_input("Réponds au superviseur ici..."):
    if not student_name:
        st.toast("⚠️ Indique ton prénom dans le menu de gauche !", icon="👉")
    else:
        st.session_state.messages.append({"role": "user", "content": user_input})
        log_interaction(student_name, "User", user_input)
        
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Analyse pédagogique en cours..."):
                messages_payload = [{"role": "system", "content": SYSTEM_PROMPT}]
                messages_payload.extend(st.session_state.messages[-10:])
                response_content, _ = query_groq_with_rotation(messages_payload)
                if not response_content:
                    response_content = "⚠️ Désolé, je suis surchargé. Reformule ta réponse."
                st.markdown(response_content)
        
        st.session_state.messages.append({"role": "assistant", "content": response_content})
        st.rerun()
