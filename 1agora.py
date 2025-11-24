import streamlit as st
import pandas as pd
import os
import re
from datetime import datetime
import io

# --- GESTION DES DÉPENDANCES OPTIONNELLES ---
# Permet à l'app de se lancer même si ces modules manquent (fonctionnalités désactivées)
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

try:
    from gtts import gTTS
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False

try:
    import docx
    from pypdf import PdfReader
    DOCS_AVAILABLE = True
except ImportError:
    DOCS_AVAILABLE = False

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="1AGORA", page_icon="🏢", initial_sidebar_state="expanded")

# --- 2. GESTION DU STYLE (ACCESSIBILITÉ) ---
if "mode_dys" not in st.session_state:
    st.session_state.mode_dys = False
if "mode_simple" not in st.session_state:
    st.session_state.mode_simple = False
if "mode_audio" not in st.session_state:
    st.session_state.mode_audio = False

if st.session_state.mode_dys:
    st.markdown("""
    <style>
    html, body, [class*="css"] {
        font-family: 'Verdana', sans-serif !important;
        font-size: 18px !important;
        line-height: 1.8 !important;
        letter-spacing: 0.5px !important;
    }
    </style>
    """, unsafe_allow_html=True)

hide_menu = """
<style>
footer {visibility: hidden;}
header {visibility: visible !important;}
</style>
"""
st.markdown(hide_menu, unsafe_allow_html=True)

st.title("♾️ Agence PRO'AGORA")
st.caption("Simulation Professionnelle Gamifiée & Inclusive")

# --- 3. CONNEXION ---
if GROQ_AVAILABLE:
    try:
        # Supporte les secrets Streamlit OU les variables d'environnement
        api_key = os.environ.get("GROQ_API_KEY") or st.secrets["GROQ_API_KEY"]
        client = Groq(api_key=api_key)
    except:
        st.error("⚠️ Clé API manquante. Configurez GROQ_API_KEY.")
        st.stop()
else:
    st.error("Module 'groq' manquant. Ajoutez-le au requirements.txt")
    st.stop()

# --- 4. FONCTIONS UTILITAIRES ---
def extract_text_from_file(uploaded_file):
    if not DOCS_AVAILABLE:
        return "Modules de lecture de documents (docx/pdf) non installés."
    text = ""
    try:
        if uploaded_file.name.endswith(".docx"):
            doc = docx.Document(uploaded_file)
            for para in doc.paragraphs: text += para.text + "\n"
        elif uploaded_file.name.endswith(".pdf"):
            reader = PdfReader(uploaded_file)
            for page in reader.pages: text += page.extract_text() + "\n"
        elif uploaded_file.name.endswith(".txt"):
            text = uploaded_file.read().decode("utf-8")
        return text
    except Exception as e: return f"Erreur lecture : {e}"

def clean_text_for_audio(text):
    text = re.sub(r'[\*_]{1,3}', '', text)
    text = re.sub(r'#+', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    text = re.sub(r'^\s*-\s+', '', text, flags=re.MULTILINE)
    return text

# --- 5. STRUCTURE DU LIVRE ---
DB_PREMIERE = {
    "GESTION DES ESPACES DE TRAVAIL": {
        "Aménagement des espaces": "COMPÉTENCE : Proposer un aménagement ergonomique.",
        "Environnement numérique": "COMPÉTENCE : Matériel informatique et RGPD.",
        "Ressources partagées": "COMPÉTENCE : Stocks fournitures et Réservations.",
        "Partage de l'information": "COMPÉTENCE : Com interne et Outils collaboratifs."
    },
    "RELATIONS PARTENAIRES": {
        "Lancement produit / Vente": "COMPÉTENCE : Planigramme, Négociation.",
        "Organisation de réunions": "COMPÉTENCE : Convocation, Ordre du jour, CR.",
        "Organisation déplacement": "COMPÉTENCE : Transport/Hôtel, Ordre de Mission."
    },
    "RESSOURCES HUMAINES": {
        "Recrutement": "COMPÉTENCE : Profil de poste, Annonce, Tri CV.",
        "Intégration du personnel": "COMPÉTENCE : Livret d'accueil, Parcours.",
        "Dossiers du personnel": "COMPÉTENCE : Contrat, Registre personnel."
    },
    "SCÉNARIOS TRANSVERSAUX": {
        "Réorganisation complète": "COMPÉTENCE : Projet global déménagement.",
        "Campagne de Recrutement": "COMPÉTENCE : Projet global recrutement."
    }
}

DB_SECONDE = {
    "Révisions 2nde": {
        "Accueil physique/téléphonique": "COMPÉTENCE : Filtrage, Prise de message.",
        "Gestion du courrier": "COMPÉTENCE : Tri et Enregistrement.",
        "Classement": "COMPÉTENCE : Arborescence numérique."
    }
}

# --- 6. GAMIFICATION ---
GRADES = {
    0: "👶 Stagiaire",
    100: "👦 Assistant(e) Junior",
    300: "👨‍💼 Assistant(e) Confirmé(e)",
    600: "👩‍💻 Responsable de Pôle",
    1000: "👑 Assistant(e) de Direction"
}

if "xp" not in st.session_state: st.session_state.xp = 0

def get_grade(xp):
    current_grade = "Stagiaire"
    for palier, titre in GRADES.items():
        if xp >= palier:
            current_grade = titre
    return current_grade

def ajouter_xp():
    st.session_state.xp += 50
    st.balloons()
    st.toast("Mission terminée ! +50 XP 🚀", icon="⭐")

# --- 7. CERVEAU (PROMPT RENFORCÉ) ---
def get_system_prompt(simplified_mode):
    # C'est ici que nous intégrons les garde-fous stricts
    base_prompt = """
    TU ES : Le Superviseur de l'Agence PRO'AGORA.
    TON RÔLE : Guider l'opérateur (l'élève) dans la réalisation de sa mission professionnelle.
    
    🚨 RÈGLES D'OR (GARDE-FOUS) - NON NÉGOCIABLES :
    1. TU NE RÉDIGES JAMAIS À LA PLACE DE L'ÉLÈVE. Même s'il te le demande, refuse poliment et renvoie-le à la réflexion. (Ex: "Je ne peux pas rédiger le mail pour toi, mais quels sont les éléments clés que tu dois y mettre ?")
    2. TU NE CORRIGES PAS DIRECTEMENT. Tu soulignes les erreurs et guides vers la correction.
    3. TU INVENTES UN SCÉNARIO D'ENTREPRISE RÉALISTE (Nom, Chiffres, Contexte) dès le premier message pour immerger l'élève.
    4. TU RESTES DANS TON RÔLE DE SUPERVISEUR (Vouvoiement professionnel, exigeant mais bienveillant).

    DÉROULEMENT DE LA MISSION :
    - Étape 1 : Donne le contexte et les données brutes (chiffres, dates, noms).
    - Étape 2 : Guide pas à pas sans faire le travail.
    - Étape 3 (FIN) : Quand la mission est finie, tu DOIS générer un BILAN STRUCTURÉ.

    FORMAT DU BILAN FINAL (Obligatoire à la fin) :
    ---------------------------------------------------
    🏁 BILAN DE FIN DE MISSION
    📊 Niveau atteint : [DÉBUTANT / CONFIRMÉ / EXPERT]
    ✅ Points Forts : [Liste 2 ou 3 réussites concrètes]
    💡 Axes de Progrès : [Conseil précis pour s'améliorer]
    ---------------------------------------------------
    """
    
    if simplified_mode:
        base_prompt += """
        ⚠️ MODE ACCESSIBILITÉ ACTIVÉ :
        - Fais des phrases très courtes.
        - Utilise des listes à puces systématiquement.
        - Mets les mots clés en **GRAS**.
        - Explique les termes techniques complexes entre parenthèses.
        """
    return base_prompt

# --- 8. LOGS ---
if "conversation_log" not in st.session_state: st.session_state.conversation_log = []
if "messages" not in st.session_state: st.session_state.messages = []

def save_log(student_id, role, content):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.conversation_log.append({
        "Heure": ts,
        "Eleve": student_id,
        "Role": role,
        "Message": content,
        "XP_Sauvegarde": st.session_state.xp
    })

def lancer_mission():
    base = DB_PREMIERE if st.session_state.niveau_select == "1ère (Livre Foucher)" else DB_SECONDE
    theme = st.session_state.theme_select
    dossier = st.session_state.dossier_select
    competence = base[theme][dossier]
    
    st.session_state.messages = []
    # Le prompt de démarrage force l'IA à lancer le scénario
    prompt_demarrage = f"Je suis l'élève. La mission est : '{dossier}'. Compétence visée : {competence}. Lance le scénario, donne-moi le contexte de l'entreprise fictive et ma première instruction."
    
    try:
        msgs = [{"role": "system", "content": get_system_prompt(st.session_state.mode_simple)}]
        msgs.append({"role": "user", "content": prompt_demarrage})
        
        completion = client.chat.completions.create(messages=msgs, model="llama-3.3-70b-versatile", temperature=0.7)
        intro_bot = completion.choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": intro_bot})
    except Exception as e:
        st.error(f"Erreur IA : {e}")

# --- 9. INTERFACE SIDEBAR ---
with st.sidebar:
    st.header("👤 Mon Profil")
    student_id = st.text_input("Prénom :", key="prenom_eleve", placeholder="Ex: Julie")
    
    grade_actuel = get_grade(st.session_state.xp)
    st.metric("Niveau & XP", value=f"{st.session_state.xp} XP", delta=grade_actuel)
    progress_val = min(st.session_state.xp / 1000, 1.0)
    st.progress(progress_val)
    
    st.markdown("---")
    st.header("♿ Accessibilité")
    st.session_state.mode_dys = st.checkbox("👁️ DYS (Gros caractères)")
    st.session_state.mode_simple = st.checkbox("🧠 Consignes Simplifiées")
    if AUDIO_AVAILABLE:
        st.session_state.mode_audio = st.checkbox("🔊 Lecture Audio")
    else:
        st.caption("🚫 Module Audio non installé")

    st.markdown("---")
    st.header("🗂️ Missions")
    niveau = st.radio("Livre :", ["1ère (Livre Foucher)", "2nde (Révisions)"], key="niveau_select")
    base_active = DB_PREMIERE if niveau == "1ère (Livre Foucher)" else DB_SECONDE
    theme = st.selectbox("Thème :", list(base_active.keys()), key="theme_select")
    dossier = st.selectbox("Mission :", list(base_active[theme].keys()), key="dossier_select")
    
    col1, col2 = st.columns(2)
    with col1:
        st.button("🚀 LANCER", type="primary", on_click=lancer_mission)
    with col2:
        st.button("✅ FINIR", on_click=ajouter_xp)

    st.markdown("---")
    st.subheader("💾 Sauvegarde")
    if st.session_state.conversation_log:
        df = pd.DataFrame(st.session_state.conversation_log)
        csv = df.to_csv(index=False, sep=';').encode('utf-8-sig')
        st.download_button("📥 Télécharger (CSV)", csv, "suivi_1agora.csv", "text/csv")
    
    uploaded_csv = st.file_uploader("Reprendre (CSV)", type=['csv'])
    if uploaded_csv and st.button("🔄 Restaurer"):
        try:
            df_hist = pd.read_csv(uploaded_csv, sep=';')
            st.session_state.messages = []
            st.session_state.conversation_log = []
            if 'XP_Sauvegarde' in df_hist.columns:
                st.session_state.xp = int(df_hist['XP_Sauvegarde'].iloc[-1])
            for _, row in df_hist.iterrows():
                role_chat = "user" if row['Role'] == "Eleve" else "assistant"
                st.session_state.messages.append({"role": role_chat, "content": row['Message']})
                save_log(row.get('Eleve', student_id), row['Role'], row['Message'])
            st.success(f"Restauré ! Niveau : {st.session_state.xp} XP")
            st.rerun()
        except: st.error("Fichier invalide.")

# --- 10. CHAT & INTERACTION ---
if not st.session_state.messages:
    st.info("👋 Bonjour ! Configure tes options d'accessibilité à gauche, choisis une mission et clique sur LANCER.")
else:
    for i, msg in enumerate(st.session_state.messages):
        st.chat_message(msg["role"]).write(msg["content"])
        
        # LECTEUR AUDIO AVEC TEXTE NETTOYÉ
        if st.session_state.mode_audio and AUDIO_AVAILABLE and msg["role"] == "assistant":
            if f"audio_{i}" not in st.session_state:
                try:
                    clean_text = clean_text_for_audio(msg["content"])
                    tts = gTTS(text=clean_text, lang='fr')
                    audio_buffer = io.BytesIO()
                    tts.write_to_fp(audio_buffer)
                    st.session_state[f"audio_{i}"] = audio_buffer
                except: pass
            
            if f"audio_{i}" in st.session_state:
                st.audio(st.session_state[f"audio_{i}"], format="audio/mp3")

    # ZONE DE DÉPÔT DE FICHIERS (Optionnelle)
    if DOCS_AVAILABLE:
        with st.expander("📎 Joindre un fichier (Word/PDF/Txt) pour correction"):
            uploaded_doc = st.file_uploader("Fichier à analyser", type=['docx', 'pdf', 'txt'], key="doc_upload")
            if uploaded_doc and st.button("Envoyer le fichier"):
                content = extract_text_from_file(uploaded_doc)
                user_msg = f"Voici mon fichier **{uploaded_doc.name}**. Analyse-le s'il te plaît.\n\nCONTENU:\n{content}"
                st.session_state.messages.append({"role": "user", "content": user_msg})
                save_log(student_id, "Eleve", f"[FICHIER] {uploaded_doc.name}")
                
                # Déclenchement réponse IA
                try:
                    msgs = [{"role": "system", "content": get_system_prompt(st.session_state.mode_simple)}] + [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
                    completion = client.chat.completions.create(messages=msgs, model="llama-3.3-70b-versatile", temperature=0.7)
                    rep = completion.choices[0].message.content
                    st.session_state.messages.append({"role": "assistant", "content": rep})
                    save_log(student_id, "Superviseur", rep)
                    st.rerun()
                except Exception as e: st.error(f"Erreur : {e}")

    # ZONE DE SAISIE TEXTE
    if prompt := st.chat_input("Votre réponse..."):
        if not student_id:
            st.warning("⚠️ Prénom requis dans la barre latérale !")
        else:
            st.chat_message("user").write(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})
            save_log(student_id, "Eleve", prompt)

            try:
                msgs = [{"role": "system", "content": get_system_prompt(st.session_state.mode_simple)}]
                # On passe tout l'historique pour garder le contexte
                msgs += [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
                
                completion = client.chat.completions.create(messages=msgs, model="llama-3.3-70b-versatile", temperature=0.7)
                rep = completion.choices[0].message.content
                
                st.chat_message("assistant").write(rep)
                st.session_state.messages.append({"role": "assistant", "content": rep})
                save_log(student_id, "Superviseur", rep)
                st.rerun()
            except Exception as e: st.error(f"Erreur : {e}")
