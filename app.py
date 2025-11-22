import streamlit as st
import pandas as pd
import google.generativeai as genai
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Assistant AGOrA", page_icon="🎓")
st.title("🎓 Assistant PFMP AGOrA")

# Récupération clé
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("Clé API manquante dans les Secrets.")
    st.stop()

# --- LE CERVEAU (PROMPT) ---
SYSTEM_PROMPT = """
Tu es un Assistant Pédagogique Interactif (API), strictement dédié à l'entraînement des élèves de Bac Pro AGOrA.
Ta mission : aider l’élève à structurer sa PFMP sans jamais faire le travail à sa place.
RÈGLES : Ne rédige jamais à sa place. Une seule question à la fois. Ton encourageant.
"""

# --- SÉLECTION AUTOMATIQUE DU MODÈLE (La partie magique) ---
# On ne force pas un nom, on cherche ce qui est disponible
if "valid_model_name" not in st.session_state:
    try:
        # On demande la liste des modèles disponibles pour CETTE clé
        available_models = list(genai.list_models())
        valid_models = []
        for m in available_models:
            # On garde ceux qui savent générer du texte
            if 'generateContent' in m.supported_generation_methods:
                valid_models.append(m.name)
        
        if not valid_models:
            st.error("❌ Aucun modèle accessible avec cette clé/région. Vérifiez votre compte Google AI Studio.")
            st.stop()
        
        # On essaie de trouver un modèle "Flash" ou "Pro" en priorité
        chosen_model = None
        for m in valid_models:
            if "flash" in m and "1.5" in m:
                chosen_model = m
                break
        
        # Si pas de Flash, on prend le premier de la liste (ex: gemini-pro)
        if not chosen_model:
            chosen_model = valid_models[0]
            
        st.session_state["valid_model_name"] = chosen_model
        # On affiche un petit message discret pour savoir lequel a été choisi
        st.toast(f"Connecté au modèle : {chosen_model}", icon="✅")

    except Exception as e:
        st.error(f"Erreur de connexion Google : {e}")
        st.stop()

# Configuration du modèle avec le nom trouvé automatiquement
model = genai.GenerativeModel(
    model_name=st.session_state["valid_model_name"],
    system_instruction=SYSTEM_PROMPT
)

# --- GESTION DONNÉES & INTERFACE (Reste inchangé) ---
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

with st.sidebar:
    st.header("Espace Professeur")
    student_id = st.text_input("Identifiant Élève :")
    if st.session_state.conversation_log:
        df = pd.DataFrame(st.session_state.conversation_log)
        csv = df.to_csv(index=False, sep=';').encode('utf-8-sig')
        st.download_button("📥 Télécharger CSV", csv, "suivi_agora.csv", "text/csv")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Bonjour ! Je suis ton coach PFMP. Quelle activité veux-tu travailler ?"}]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input("Ta réponse..."):
    if not student_id:
        st.warning("⚠️ Entre ton identifiant à gauche !")
    else:
        st.chat_message("user").write(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        save_log(student_id, "Eleve", prompt)

        try:
            # On nettoie l'historique pour éviter les conflits de format
            history_gemini = []
            for m in st.session_state.messages:
                role = "user" if m["role"] == "user" else "model"
                history_gemini.append({"role": role, "parts": [m["content"]]})

            response = model.generate_content(history_gemini)
            bot_reply = response.text
            
            st.chat_message("assistant").write(bot_reply)
            st.session_state.messages.append({"role": "assistant", "content": bot_reply})
            save_log(student_id, "Assistant", bot_reply)
            
        except Exception as e:
            st.error(f"Erreur : {e}")
