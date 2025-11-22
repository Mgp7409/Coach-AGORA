import streamlit as st
import pandas as pd
import google.generativeai as genai
from datetime import datetime
import io

# --- CONFIGURATION ---
st.set_page_config(page_title="Assistant AGOrA", page_icon="🎓")
st.title("🎓 Assistant PFMP AGOrA")

# Récupération sécurisée de la clé API
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("La clé API est manquante. Configurez les 'Secrets' dans Streamlit.")
    st.stop()

# --- LE PROMPT AGORA (Votre "Gem") ---
SYSTEM_PROMPT = """
Tu es un Assistant Pédagogique Interactif (API), strictement dédié à l'entraînement des élèves de Bac Pro AGOrA.
Ta mission unique : aider l’élève à structurer sa PFMP sans jamais faire le travail à sa place.

RÈGLES ABSOLUES :
1. Tu ne rédiges JAMAIS à la place de l'élève.
2. Tu poses UNE SEULE question à la fois.
3. Tu attends toujours la réponse avant de continuer.
4. Ton ton est bienveillant, direct et encourageant.

DÉROULEMENT SÉQUENCÉ :
1. ACCUEIL : Demande quelle activité l'élève veut travailler.
2. CONTEXTE : Demande le Lieu et le Service.
3. DÉVELOPPEMENT : Demande les étapes, les outils et la procédure.
4. ANALYSE : Demande de justifier les choix et d'expliquer une difficulté ou initiative.
5. CONCLUSION : Fais une synthèse courte et propose un axe de progrès.
"""

model = genai.GenerativeModel(
   model_name='gemini-1.5-flash-002',
    system_instruction=SYSTEM_PROMPT
)

# --- GESTION DONNÉES ---
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

# --- INTERFACE ---
with st.sidebar:
    st.header("Espace Professeur")
    student_id = st.text_input("Identifiant Élève (Prénom/Groupe) :")
    
    st.markdown("---")
    # Bouton pour télécharger les données
    if st.session_state.conversation_log:
        df = pd.DataFrame(st.session_state.conversation_log)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Télécharger les conversations (CSV)",
            csv,
            "conversations_agora.csv",
            "text/csv"
        )

# --- CHAT ---
if "messages" not in st.session_state:
    st.session_state.messages = []
    # Message d'amorce (invisible dans l'historique envoyé à l'IA pour économiser, mais visible pour l'élève)
    st.session_state.messages.append({"role": "assistant", "content": "Bonjour ! Je suis ton coach pour la PFMP. Quelle activité veux-tu préparer aujourd'hui ?"})

# Affichage
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# Interaction
if prompt := st.chat_input("Ta réponse..."):
    if not student_id:
        st.warning("⚠️ Merci d'entrer ton identifiant dans le menu à gauche avant de commencer !")
    else:
        # 1. Message Élève
        st.chat_message("user").write(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        save_log(student_id, "Eleve", prompt)

        # 2. Réponse IA
        try:
            # On reconstruit l'historique pour Gemini
            chat_history = [{"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]} for m in st.session_state.messages]
            
            response = model.generate_content(chat_history)
            bot_reply = response.text
            
            st.chat_message("assistant").write(bot_reply)
            st.session_state.messages.append({"role": "assistant", "content": bot_reply})
            save_log(student_id, "Assistant", bot_reply)
            
        except Exception as e:
            st.error(f"Erreur de connexion. Réessaie. ({e})")
