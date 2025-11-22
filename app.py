import streamlit as st
import google.generativeai as genai

st.title("🛠️ Mode Diagnostic")

# 1. Vérification de la Clé
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    # On affiche les 4 premiers caractères pour voir si elle est bien lue (sans tout dévoiler)
    st.write(f"Clé détectée : {api_key[:4]}...")
    genai.configure(api_key=api_key)
except Exception as e:
    st.error(f"Problème de lecture de la clé : {e}")
    st.stop()

# 2. Demander à Google "Quels modèles sont disponibles pour moi ?"
if st.button("Lancer le test de connexion"):
    try:
        st.info("Interrogation des serveurs Google...")
        list_models = genai.list_models()
        
        found_models = []
        for m in list_models:
            # On cherche les modèles qui savent générer du texte
            if 'generateContent' in m.supported_generation_methods:
                found_models.append(m.name)
        
        if found_models:
            st.success("✅ Connexion RÉUSSIE ! Voici les modèles exacts que votre clé peut utiliser :")
            for model_name in found_models:
                st.code(model_name)
        else:
            st.warning("⚠️ Connexion réussie, mais aucun modèle trouvé. Votre clé API est peut-être restreinte.")
            
    except Exception as e:
        st.error(f"❌ ÉCHEC TOTAL : {e}")
        st.write("Cela signifie souvent que la Clé API est invalide ou mal copiée.")
