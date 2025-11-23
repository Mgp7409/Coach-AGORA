import streamlit as st
import pandas as pd
from groq import Groq
from datetime import datetime
from gtts import gTTS
import io

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="1AGORA - Inclusive", page_icon="🏢")

# --- 2. GESTION DE LA DIFFÉRENCIATION (CSS DYNAMIQUE) ---
if "mode_dys" not in st.session_state:
    st.session_state.mode_dys = False

# Style standard ou Style DYS
if st.session_state.mode_dys:
    # Police plus grande, interligne fort, sans serif (type Arial/Verdana)
    dys_style = """
    <style>
    html, body, [class*="css"] {
        font-family: 'Verdana', sans-serif !important;
        font-size: 18px !important;
        line-height: 1.8 !important;
        letter-spacing: 0.5px !important;
    }
    </style>
    """
    st.markdown(dys_style, unsafe_allow_html=True)

# Masquer le menu technique
hide_menu = """<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}</style>"""
st.markdown(hide_menu, unsafe_allow_html=True)

st.title("♾️ Agence PRO'AGORA")

# --- 3. CONNEXION ---
try:
    api_key = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=api_key)
except:
    st.error("⚠️ Clé API manquante.")
    st.stop()

# --- 4. STRUCTURE DU LIVRE ---
DB_PREMIERE = {
    "SP1 : GESTION DES ESPACES": {
        "Chap 1 : Aménagement": "COMPÉTENCE : Proposer aménagement ergonomique.",
        "Chap 2 : Environnement numérique": "COMPÉTENCE : Matériel informatique et RGPD.",
        "Chap 3 : Ressources partagées": "COMPÉTENCE : Stocks fournitures et Réservations.",
        "Chap 4 : Partage info": "COMPÉTENCE : Com interne et Outils collaboratifs."
    },
    "SP2 : RELATIONS PARTENAIRES": {
        "Chap 5 : Vente & Produit": "COMPÉTENCE : Planigramme, Négociation, Com commerciale.",
        "Chap 6 : Réunions": "COMPÉTENCE : Convocation, Ordre du jour, Compte-Rendu.",
        "Chap 7 : Déplacement": "COMPÉTENCE : Réservation Transport/Hôtel, Ordre de Mission."
    },
    "SP3 : RESSOURCES HUMAINES": {
        "Chap 8 : Recrutement": "COMPÉTENCE : Profil de poste, Annonce, Tri CV.",
        "Chap 9 : Intégration": "COMPÉTENCE : Livret d'accueil, Parcours d'intégration.",
        "Chap 10 : Admin RH": "COMPÉTENCE : Contrat, Registre personnel, Avenant."
    },
    "TRANSVERSAL": {
        "Mission 1 : Réorganisation": "COMPÉTENCE : Projet déménagement.",
        "Mission 2 : Campagne RH": "COMPÉTENCE : Projet recrutement complet."
    }
}

DB_SECONDE = {
    "Révisions 2nde": {
        "Accueil": "COMPÉTENCE : Accueil physique/téléphonique.",
        "Courrier": "COMPÉTENCE : Tri et Enregistrement.",
        "Classement": "COMPÉTENCE : Arborescence numérique."
    }
}

# --- 5. SYSTÈME DE GAMIFICATION ---
GRADES = {
    0: "👶 Stagiaire en observation",
    100: "👦 Assistant(e) Junior",
    300: "👨‍💼 Assistant(e) Confirmé(e)",
    600: "👩‍💻 Responsable de Pôle",
    1000: "👑 Assistant(e) du Directeur"
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
    st.toast("Bravo ! +50 XP 🚀", icon="⭐")

# --- 6. CERVEAU ADAPTATIF ---
def get_system_prompt(simplified_mode):
    base_prompt = """
    TU ES : Le Superviseur de l'Agence PRO'AGORA.
    RÈGLES :
    1. Invente un scénario d'entreprise aléatoire (Nom, Chiffres, Contexte) dès le début.
    2. Donne toutes les données brutes immédiatement.
    3. Ne fais jamais le travail à la place de l'élève.
    """
    
    if simplified_mode:
        base_prompt += """
        ⚠️ MODE ACCESSIBILITÉ ACTIVÉ :
        - Fais des phrases courtes et simples.
        - Utilise des listes à puces systématiquement.
        - Mets les mots importants en **GRAS**.
        - Explique les termes compliqués entre parenthèses.
        - Une seule consigne à la fois.
        """
    else:
        base_prompt += """
        POSTURE : Professionnel, vouvoiement, vocabulaire technique précis.
        """
    return base_prompt

# --- 7. LOGS ---
if "conversation_log" not in st.session_state: st.session_state.conversation_log = []
if "messages" not in st.session_state: st.session_state.messages = []

def save_log(student_id, role, content):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.conversation_log.append({
        "Heure": ts,
        "Eleve": student_id,
        "Role": role,
        "Message": content,
        "XP_Sauvegarde": st.session_state.xp # On sauvegarde l'XP
    })

def lancer_mission():
    base = DB_PREMIERE if st.session_state.niveau_select == "1ère (Livre Foucher)" else DB_SECONDE
    theme = st.session_state.theme_select
    dossier = st.session_state.dossier_select
    competence = base[theme][dossier]
    
    st.session_state.messages = []
    prompt_demarrage = f"Mission : '{dossier}' ({competence}). Invente le scénario et donne les consignes."
    
    try:
        msgs = [{"role": "system", "content": get_system_prompt(st.session_state.mode_simple)}]
        msgs.append({"role": "user", "content": prompt_demarrage})
        
        completion = client.chat.completions.create(messages=msgs, model="llama-3.3-70b-versatile", temperature=0.8)
        intro_bot = completion.choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": intro_bot})
    except Exception as e:
        st.error(f"Erreur IA : {e}")

# --- 8. INTERFACE SIDEBAR ---
with st.sidebar:
    st.header("👤 Mon Profil")
    student_id = st.text_input("Prénom :", key="prenom_eleve")
    
    # GAMIFICATION DISPLAY
    grade_actuel = get_grade(st.session_state.xp)
    st.metric("Niveau & XP", value=f"{st.session_state.xp} XP", delta=grade_actuel)
    progress_val = min(st.session_state.xp / 1000, 1.0)
    st.progress(progress_val)
    
    st.markdown("---")
    st.header("♿ Accessibilité")
    st.session_state.mode_dys = st.checkbox("👁️ Affichage DYS (Gros caractères)")
    st.session_state.mode_simple = st.checkbox("🧠 Consignes Simplifiées (Facile à lire)")
    st.session_state.mode_audio = st.checkbox("🔊 Lecture Audio (Synthèse vocale)")

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
        st.button("✅ FINIR (+50XP)", on_click=ajouter_xp)

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
            
            # Récupération de l'XP du fichier
            if 'XP_Sauvegarde' in df_hist.columns:
                last_xp = df_hist['XP_Sauvegarde'].iloc[-1]
                st.session_state.xp = int(last_xp)
            
            for _, row in df_hist.iterrows():
                role_chat = "user" if row['Role'] == "Eleve" else "assistant"
                st.session_state.messages.append({"role": role_chat, "content": row['Message']})
                save_log(row.get('Eleve', student_id), row['Role'], row['Message'])
            st.success(f"Restauré ! Niveau récupéré : {st.session_state.xp} XP")
            st.rerun()
        except: st.error("Fichier invalide.")

# --- 9. CHAT & AUDIO ---
if not st.session_state.messages:
    st.info("👋 Bonjour ! Configure tes options d'accessibilité à gauche et lance une mission.")
else:
    for i, msg in enumerate(st.session_state.messages):
        st.chat_message(msg["role"]).write(msg["content"])
        
        # BOUTON AUDIO (Si activé et si c'est un message de l'assistant)
        if st.session_state.mode_audio and msg["role"] == "assistant":
            # On génère un petit lecteur audio sous le message
            # On utilise une clé unique 'audio_i' pour ne pas recharger à chaque fois
            if f"audio_{i}" not in st.session_state:
                try:
                    tts = gTTS(text=msg["content"], lang='fr')
                    audio_buffer = io.BytesIO()
                    tts.write_to_fp(audio_buffer)
                    st.session_state[f"audio_{i}"] = audio_buffer
                except: pass
            
            if f"audio_{i}" in st.session_state:
                st.audio(st.session_state[f"audio_{i}"], format="audio/mp3")

    if prompt := st.chat_input("Votre réponse..."):
        if not student_id:
            st.warning("⚠️ Prénom requis !")
        else:
            st.chat_message("user").write(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})
            save_log(student_id, "Eleve", prompt)

            try:
                msgs = [{"role": "system", "content": get_system_prompt(st.session_state.mode_simple)}]
                msgs += [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
                
                completion = client.chat.completions.create(messages=msgs, model="llama-3.3-70b-versatile", temperature=0.7)
                rep = completion.choices[0].message.content
                
                st.chat_message("assistant").write(rep)
                st.session_state.messages.append({"role": "assistant", "content": rep})
                save_log(student_id, "Superviseur", rep)
                st.rerun()
            except Exception as e: st.error(f"Erreur : {e}")
