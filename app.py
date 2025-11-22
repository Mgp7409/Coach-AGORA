import streamlit as st
import pandas as pd
import os
from groq import Groq
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Assistant AGOrA", page_icon="🎓")
st.title("🎓 Assistant PFMP AGOrA")

# Récupération de la clé Groq
try:
    api_key = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=api_key)
except:
    st.error("Clé API manquante. Configurez GROQ_API_KEY dans les Secrets.")
    st.stop()

# --- LE CERVEAU (PROMPT SYSTÈME) ---
SYSTEM_PROMPT = """
Tu es un Assistant Pédagogique Interactif (API), strictement dédié à l'entraînement des élèves de Bac Pro AGOrA.
Ta mission : aider l’élève à structurer sa PFMP sans jamais faire le travail à sa place.

RÈGLES ABSOLUES :
1. Tu ne rédiges JAMAIS à la place de l'élève.
2. Tu poses UNE SEULE question à la fois.
3. Tu attends toujours la réponse avant de continuer.
4. Ton ton est bienveillant, direct et encourageant (utilise des emojis).

DÉROULEMENT :
1. ACCUEIL : Demande l'activité.
2. CONTEXTE : Demande le Lieu et le Service.
3. DÉVELOPPEMENT : Demande étapes, outils, procédures.
4. ANALYSE : Demande justification et initiatives.
5. CONCLUSION : Synthèse et piste de progrès.
"""

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
    student_id = st.text_input("Identifiant Élève :")
    
    if st.session_state.conversation_log:
        df = pd.DataFrame(st.session_state.conversation_log)
        csv = df.to_csv(index=False, sep=';').encode('utf-8-sig')
        st.download_button("📥 Télécharger CSV", csv, "suivi_agora.csv", "text/csv")

# --- CHAT ---
if "messages" not in st.session_state:
    st.session_state.messages = []
    # Message d'accueil (ajouté visuellement seulement)
    st.session_state.messages.append({"role": "assistant", "content": "Bonjour ! Je suis ton coach pour la PFMP. Quelle activité veux-tu préparer ?"})

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input("Ta réponse..."):
    if not student_id:
        st.warning("⚠️ Entre ton prénom à gauche !")
    else:
        # 1. Message Élève
        st.chat_message("user").write(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        save_log(student_id, "Eleve", prompt)

        # 2. Réponse IA (Via Groq)
        try:
            # On prépare l'historique avec le System Prompt au début
            messages_for_api = [{"role": "system", "content": SYSTEM_PROMPT}]
            # On ajoute la conversation
            for m in st.session_state.messages:
                # Groq attend 'assistant' ou 'user', c'est compatible avec notre format
                messages_for_api.append({"role": m["role"], "content": m["content"]})

            chat_completion = client.chat.completions.create(
                messages=messages_for_api,
                model="llama3-8b-8192", # Modèle gratuit, rapide et très bon
                temperature=0.7,
            )
            
            bot_reply = chat_completion.choices[0].message.content
            
            st.chat_message("assistant").write(bot_reply)
            st.session_state.messages.append({"role": "assistant", "content": bot_reply})
            save_log(student_id, "Assistant", bot_reply)
            
        except Exception as e:
            st.error(f"Erreur connexion : {e}")
