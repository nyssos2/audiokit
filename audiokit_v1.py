import streamlit as st
import google.generativeai as genai
from google.generativeai import GenerativeModel
from gtts import gTTS
import os
import datetime

# --- SÉCURITÉ : MOT DE PASSE ---
def check_password():
    """Retourne True si l'utilisateur a saisi le bon mot de passe."""
    def password_entered():
        # --- MODIFIE LE MOT DE PASSE ICI ---
        if st.session_state["password"] == st.secrets["APP_PASSWORD"]: 
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # On ne garde pas le mot de passe en mémoire
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # Premier affichage : on demande le mot de passe
        st.title("🔒 Accès réservé")
        st.text_input(
            "Veuillez entrer le mot de passe pour accéder à AudioKit", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        if "password_correct" in st.session_state:
            st.error("😕 Mot de passe incorrect")
        return False
    return True

# Si le mot de passe n'est pas bon, on arrête tout ici
if not check_password():
    st.stop()

# --- LA SUITE DE TON CODE (Configuration, Interface, etc.) ---
# --- 2. CONFIGURATION API ---
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# On définit le vrai nom technique pour Google
ID_MODEL_TECHNIQUE = "gemini-1.5-flash"

try:
    model = GenerativeModel(model_name=ID_MODEL_TECHNIQUE)
except:
    model = GenerativeModel(model_name="gemini-pro")

# On garde un joli nom pour l'affichage Streamlit
nom_affichage = "Gemini 1.5 Flash (Rapide)"

# --- TITRE ET SOUS-TITRE ---
st.title("🎙️ Mon Guide Voyage Perso")
st.markdown("##### Crée tes audio-guides immersifs et captivants !")
st.markdown(f"**Modèle utilisé :** `{nom_affichage}`")

# --- INTERFACE ---
with st.sidebar:
    st.header("Paramètres")
    public = st.selectbox("Public cible", ["Enfants (5-10 ans)", "Ados", "Adultes/Experts"])
    duree = st.select_slider(
        "Durée souhaitée (minutes)", 
        options=[5, 10, 15, 20, 30], 
        value=10,
    )
    vitesse = st.select_slider(
        "Vitesse de visite", 
        options=["Lente", "Normale", "Rapide"]
    )

sujet = st.text_input("Quel monument ou lieu voulez-vous visiter ?", "Le Temple d'Or à Kyoto")

# --- 4. GÉNÉRATION ---
# On utilise le session_state pour se souvenir du script entre les clics
if "script_final" not in st.session_state:
    st.session_state.script_final = ""

# ÉTAPE 1 : RÉDACTION
if st.button("✍️ 1. Rédiger le script"):
    try:
        with st.status("Recherche et rédaction..."):
            # Prompt optimisé pour la voix
            prompt = f"""
            TU ES UN GUIDE TOURISTIQUE PROFESSIONNEL.
            Sujet : {sujet}. Public : {public}. 
	    DURÉE CIBLE : {duree} minutes.
            
            CONSIGNES STRICTES :
            1. Ne fais AUCUNE introduction type 'Voici le script' ou 'Bien sûr'. 
            2. Commence DIRECTEMENT par le discours.
            3. N'utilise JAMAIS de symboles spéciaux comme '**' ou '--' ou des listes à puces.
            4. Écris en phrases fluides, comme si tu parlais à quelqu'un.
            5. Comporte-toi comme un véritable guide conférencier spécialiste et qui sait s'adapter à son auditoire.
            6. Inclus des pauses naturelles (indiquées par des virgules ou des points).
            7. Termine par une phrase de conclusion naturelle, sans commentaire méta.
            8. Respecte STRICTEMENT la durée de {duree} minutes.
            9. Calcule ton volume de texte : environ 140 mots par minute de narration. 
               (Exemple : pour 5 min = 700 mots / pour 20 min = 2800 mots).
            10. ADAPTE LA GRANULARITÉ :
               - Si la durée est COURTE (5-10 min) : Sois très synthétique, va à l'essentiel, donne les faits marquants.
               - Si la durée est LONGUE (20-30 min) : Sois exhaustif, raconte des anecdotes détaillées, décris précisément l'architecture et l'histoire.
            """
            response = model.generate_content(prompt)
            # Nettoyage de sécurité pour enlever les éventuels résidus de Markdown
            st.session_state.script_final = response.text.replace("**", "").replace("#", "")
            st.success("Script rédigé !")
    except Exception as e:
        st.error(f"Erreur rédaction : {e}")

# ÉTAPE 2 : ÉDITION (La boîte de dialogue toujours visible si un script existe)
if st.session_state.script_final:
    st.subheader("📝 Révision du script")
    script_edite = st.text_area(
        "Vous pouvez corriger le texte avant de créer l'audio :", 
        value=st.session_state.script_final, 
        height=300
    )
    # On met à jour le session_state avec les modifs de l'utilisateur
    st.session_state.script_final = script_edite

    # ÉTAPE 3 : AUDIO
    if st.button("🔊 2. Créer l'Audio final"):
        try:
            with st.status("Synthèse vocale en cours..."):
                horodatage = datetime.datetime.now().strftime("%Y%m%d_%H%M")
                nom_mp3 = f"guide_{sujet.replace(' ', '_')}_{horodatage}.mp3"
    
    # Ajoute une petite pause de silence au début du script pour laisser le temps à l'utilisateur de mettre ses écouteurs
                texte_avec_pause = " . . . " + st.session_state.script_final
                tts = gTTS(text=texte_avec_pause, lang='fr')
                tts = gTTS(text=st.session_state.script_final, lang='fr')
                tts.save(nom_mp3)
                
            st.success("🎉 Audio prêt !")
            st.audio(nom_mp3)
            
            with open(nom_mp3, "rb") as file:
                st.download_button("📥 Télécharger le MP3", data=file, file_name=nom_mp3)
        except Exception as e:
            st.error(f"Oups ! Une erreur est survenue : {e}")

# --- HISTORIQUE SIMPLE ---
st.divider()
st.subheader("📚 Bibliothèque de tes Audio-Guides")
fichiers = [f for f in os.listdir(".") if f.endswith(".mp3")]
fichiers.sort(reverse=True) # Les plus récents en premier

for f in fichiers:
    col1, col2 = st.columns([3, 1])
    with col1:
        st.write(f"📖 {f}")
        st.audio(f)
    with col2:
        with open(f, "rb") as file:

            st.download_button("📥", data=file, file_name=f, key=f)



