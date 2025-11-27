import streamlit as st
import pandas as pd
import random
import os
import re
import base64
from datetime import datetime
from io import BytesIO, StringIO
from groq import Groq

# --- 0. DÉPENDANCES & SÉCURITÉ ---
try:
    from docx import Document
    from docx.shared import RGBColor # <--- AJOUT IMPORTANT ICI
except ImportError:
    st.error("⚠️ ERREUR CRITIQUE : Le module 'python-docx' manque. Ajoutez 'python-docx' au fichier requirements.txt")
    st.stop()

try:
    from gtts import gTTS
    HAS_AUDIO = True
except ImportError:
    HAS_AUDIO = False

# --- 1. CONFIGURATION DE LA PAGE ---
PAGE_ICON = "logo_agora.png" if os.path.exists("logo_agora.png") else "🎓"

st.set_page_config(
    page_title="Restitution PFMP - Pro'AGOrA",
    page_icon=PAGE_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. STYLE CSS (FUSION A & B) ---
st.markdown("""
<style>
    /* POLICE & STYLE GLOBAL */
    html, body, [class*="css"] {
        font-family: 'Segoe UI', 'Roboto', Helvetica, Arial, sans-serif;
        font-size: 16px;
    }

    /* ALERTE ROUGE (Issue du Code A) */
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
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    /* FOOTER FIXE */
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
    }
    
    /* REMONTER LA BARRE DE CHAT */
    [data-testid="stBottom"] {
        bottom: 50px !important;
        padding-bottom: 0px !important;
    }
    
    /* HEADERS */
    header {background-color: transparent !important;}
</style>
""", unsafe_allow_html=True)

# --- 3. GESTION ÉTAT (SESSION STATE) ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "xp" not in st.session_state:
    st.session_state.xp = 0
if "grade" not in st.session_state:
    st.session_state.grade = "👶 Stagiaire"

# SYSTÈME DE GRADES (Gamification)
GRADES = {
    0: "👶 Stagiaire",
    100: "👦 Assistant(e) Junior",
    300: "👨‍💼 Assistant(e) Confirmé(e)",
    600: "👩‍💻 Responsable de Pôle",
    1000: "👑 Directeur(trice)"
}

def update_xp(amount: int):
    st.session_state.xp += amount
    current_grade = "👶 Stagiaire"
    for palier, titre in GRADES.items():
        if st.session_state.xp >= palier:
            current_grade = titre
    
    if current_grade != st.session_state.grade:
        st.session_state.grade = current_grade
        st.toast(f"PROMOTION ! Tu es maintenant {current_grade} !", icon="🎉")
        st.balloons()
    else:
        st.toast(f"+{amount} XP", icon="⭐")

# --- 4. OUTILS IA (GROQ) ---
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
    
    keys = list(available_keys)
    random.shuffle(keys)
    models = ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "llama-3.1-8b-instant"]

    for key in keys:
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

# --- 5. OUTILS FICHIERS (LECTURE & ÉCRITURE) ---

def extract_text_from_file(uploaded_file) -> str:
    """Lit Word, Excel ou CSV"""
    try:
        filename = uploaded_file.name.lower()
        if filename.endswith(".docx"):
            doc = Document(uploaded_file)
            return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])[:15000]
        elif filename.endswith(".xlsx") or filename.endswith(".xls"):
            df = pd.read_excel(uploaded_file)
            return df.to_string()[:15000]
        elif filename.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
            return df.to_string()[:15000]
        else:
            return "Format non supporté."
    except Exception as e:
        return f"Erreur de lecture : {str(e)}"

def create_docx_history(messages, student_name):
    """Génère un fichier Word propre de la conversation"""
    doc = Document()
    doc.add_heading(f"Restitution PFMP - {student_name}", 0)
    doc.add_paragraph(f"Date : {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    doc.add_paragraph("---")

    for msg in messages:
        if msg["role"] == "system":
            continue
        
        role_name = "SUPERVISEUR (IA)" if msg["role"] == "assistant" else student_name.upper()
        p = doc.add_paragraph()
        runner = p.add_run(f"{role_name} :")
        runner.bold = True
        
        # --- CORRECTION COULEUR ICI ---
        if msg["role"] == "assistant":
            runner.font.color.rgb = RGBColor(0, 0, 255) # Bleu IA
        else:
            runner.font.color.rgb = RGBColor(0, 100, 0) # Vert Élève
        
        doc.add_paragraph(msg["content"])
        doc.add_paragraph("") # Espace
        
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def clean_text_for_audio(text: str) -> str:
    text = re.sub(r"[\*_]{1,3}", "", text) # Enlève le gras/italique
    text = re.sub(r"\[.*?\]", "", text)     # Enlève les crochets
    return text[:500] # Limite pour l'audio

# --- 6. PROMPT SYSTÈME (RETOUR D'EXPÉRIENCE) ---
SYSTEM_PROMPT = """
RÔLE : Tu es le Superviseur Professionnel de l'élève (Bac Pro AGOrA).
TON : Professionnel, encourageant, exigeant sur le vocabulaire technique.
OBJECTIF : Aider l'élève à analyser son vécu en entreprise (PFMP) et à structurer son compte-rendu.

RÈGLES CRITIQUES (SÉCURITÉ) :
1. Si l'élève mentionne un vrai nom de famille (client, collègue) ou des données confidentielles (CA précis, codes d'accès), stoppe-le IMMÉDIATEMENT et demande d'anonymiser.
2. Ne fais jamais le travail de rédaction à sa place. Pose des questions pour lui faire trouver les réponses.

MÉTHODE PÉDAGOGIQUE :
1. Demande d'abord le contexte (Type d'entreprise, Service, Tâches réalisées).
2. Si l'élève envoie un document, analyse-le :
   - Points forts.
   - Points faibles (orthographe, structure, vocabulaire trop familier).
   - Manques (Outils numériques utilisés ? Procédures respectées ?).
3. Guide-le vers les compétences du référentiel (Accueil, Gestion administrative, Projets...).

FORMAT DE RÉPONSE :
- Utilise des listes à puces.
- Sois concis.
"""

INITIAL_MESSAGE = """
👋 **Bonjour.**

Je suis ton Superviseur Virtuel. Nous allons travailler sur ton **Retour d'Expérience de Stage (PFMP)**.

Tu peux :
1. **Télécharger ton brouillon** (Word, Excel) via le menu de gauche.
2. Ou commencer par me décrire ton entreprise et tes missions ici.

*Rappel : Utilise des noms fictifs pour les personnes.*
"""

if not st.session_state.messages:
    st.session_state.messages.append({"role": "assistant", "content": INITIAL_MESSAGE})

# --- 7. INTERFACE GRAPHIQUE ---

st.title("🎓 Restitution PFMP & Analyse de Pratique")

# A. BARRE LATÉRALE
with st.sidebar:
    if os.path.exists(PAGE_ICON):
        st.image(PAGE_ICON, width=80)
    else:
        st.header("Profil Élève")

    # --- ZONE 1 : PROFIL & GAMIFICATION ---
    st.markdown(f"### 🏆 {st.session_state.grade}")
    st.progress(min(st.session_state.xp / 1000, 1.0))
    student_name = st.text_input("Ton Prénom :", placeholder="Ex: Thomas")
    
    st.divider()

    # --- ZONE 2 : SÉCURITÉ (CODE A) ---
    st.markdown("""
    <div class="sidebar-alert">
    🚫 <b>RÈGLE D'OR</b><br>
    Ne jamais saisir de données personnelles réelles (Noms de clients, Numéros de téléphone, Mots de passe).
    <br><b>ANONYMISE TOUT !</b>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # --- ZONE 3 : IMPORT DOC ---
    st.subheader("📂 Analyser un travail")
    uploaded_file = st.file_uploader("Ton rapport/brouillon (Word, Excel)", type=['docx', 'xlsx', 'xls', 'csv'])
    
    if uploaded_file and student_name:
        if st.button("🚀 Envoyer à l'analyse"):
            with st.spinner("Lecture du document..."):
                text_content = extract_text_from_file(uploaded_file)
                prompt_analysis = f"Voici mon travail (Fichier {uploaded_file.name}) : \n\n{text_content}"
                st.session_state.messages.append({"role": "user", "content": prompt_analysis})
                update_xp(50) # Bonus pour upload
                st.rerun()
    elif uploaded_file:
        st.warning("Indique ton prénom d'abord.")

    st.divider()

    # --- ZONE 4 : EXPORT (CODE B + WORD) ---
    st.subheader("💾 Sauvegarder")
    
    if student_name and len(st.session_state.messages) > 1:
        # Export Word
        docx_file = create_docx_history(st.session_state.messages, student_name)
        st.download_button(
            label="📄 Télécharger en Word (.docx)",
            data=docx_file,
            file_name=f"Restitution_PFMP_{student_name}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        
        # Export CSV (Technique)
        chat_df = pd.DataFrame(st.session_state.messages)
        csv_data = chat_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="🛠️ Sauvegarde Technique (.csv)",
            data=csv_data,
            file_name=f"backup_{student_name}.csv",
            mime="text/csv"
        )
    
    # Bouton Reset
    if st.button("🗑️ Nouvelle Session"):
        st.session_state.messages = [{"role": "assistant", "content": INITIAL_MESSAGE}]
        st.session_state.xp = 0
        st.rerun()

# B. ZONE DE CHAT
chat_container = st.container()
with chat_container:
    for i, msg in enumerate(st.session_state.messages):
        role_avatar = "🤖" if msg["role"] == "assistant" else "🧑‍🎓"
        with st.chat_message(msg["role"], avatar=role_avatar):
            # Affichage conditionnel pour ne pas polluer avec le texte brut du fichier
            if "Voici mon travail (Fichier" in msg["content"]:
                st.info(f"📄 *Document envoyé pour analyse.*")
            else:
                st.markdown(msg["content"])
                
                # Option Lecture Audio (TTS) si module présent
                if msg["role"] == "assistant" and HAS_AUDIO:
                    col_audio, _ = st.columns([1, 5])
                    with col_audio:
                        if st.button("🔊", key=f"tts_{i}", help="Lire ce message"):
                            try:
                                tts = gTTS(clean_text_for_audio(msg["content"]), lang="fr")
                                buf = BytesIO()
                                tts.write_to_fp(buf)
                                st.audio(buf, format="audio/mp3", start_time=0)
                            except:
                                st.warning("Audio indisponible.")

    st.write("<br><br>", unsafe_allow_html=True) # Espace pour le footer

# C. FOOTER PERMANENT
st.markdown("""
<div class="fixed-footer">
    ℹ️ <b>Outil Pédagogique (IA)</b> - Vérifiez toujours les informations avec votre professeur. - <b>Aucune donnée personnelle ne doit être saisie.</b>
</div>
""", unsafe_allow_html=True)

# D. SAISIE UTILISATEUR
if user_input := st.chat_input("Réponds au superviseur ici..."):
    if not student_name:
        st.toast("⚠️ Indique ton prénom dans le menu de gauche !", icon="👉")
    else:
        # Ajout message utilisateur
        st.session_state.messages.append({"role": "user", "content": user_input})
        update_xp(10) # XP par interaction
        
        # Réponse IA
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Analyse pédagogique..."):
                # Construction du contexte pour l'IA
                messages_payload = [{"role": "system", "content": SYSTEM_PROMPT}]
                # On garde les 8 derniers messages pour la mémoire contextuelle
                messages_payload.extend(st.session_state.messages[-8:])
                
                response_content, model_used = query_groq_with_rotation(messages_payload)
                
                if not response_content:
                    response_content = "⚠️ Désolé, le service est momentanément saturé. Réessaie."
                
                st.markdown(response_content)
        
        st.session_state.messages.append({"role": "assistant", "content": response_content})
        st.rerun()
