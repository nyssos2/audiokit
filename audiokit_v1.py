import streamlit as st
import google.generativeai as genai
from google.generativeai import GenerativeModel
import asyncio
import edge_tts
# (suppression de 'from gtts import gTTS')
import os
import datetime
from pydub import AudioSegment

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

# On choisit le modèle le plus performant de ta liste
# gemini-2.5-flash est parfait pour la rédaction rapide
ID_MODEL = "models/gemini-2.5-flash"

model = GenerativeModel(model_name=ID_MODEL)

# --- TITRE ET SOUS-TITRE ---
st.title("🎙️ Ma fabrique à audio-guides perso")
st.markdown("##### Crée tes audio-guides immersifs et captivants !")
# On utilise du HTML simple dans le markdown pour réduire la taille et griser le texte
st.markdown(f"<p style='font-size: 0.8em; color: gray;'>Modèle propulsé par : Gemini 2.5 Flash</p>", unsafe_allow_html=True)

# --- INTERFACE ---
with st.sidebar:
    st.header("Paramètres")
    public = st.selectbox("Public cible", ["Enfants (5-10 ans)", "Ados", "Adultes"])
    duree = st.select_slider(
        "Durée souhaitée (minutes)", 
        options=[5, 10, 15, 20, 30], 
        value=10,
    )
    vitesse = st.select_slider(
        "Vitesse de visite", 
        options=["Normale", "Rapide"]
    )
    personnalite = st.selectbox(
        "Style du guide", 
        ["Guide-conférencier (classique)", 
         "Vieux sage (légendes et mystères)", 
         "Indiana Jones (aventure et action)",
         "Local (anecdotes et secrets)"]
    )
    genre_voix = st.radio("Voix du guide", ["Féminine", "Masculine"])
    
    st.divider()
    st.subheader("🎵 Ambiance Sonore")
    musique_fond = st.checkbox("Ajouter une ambiance sonore", value=False)

    if musique_fond:
        categories_traduction = {
            "Nature": "Nature",
            "Urbain": "Urbain",
            "Intérieur": "Interieur"
        }
        
        nom_affiche = st.selectbox("Catégorie", list(categories_traduction.keys()))
        nom_dossier = categories_traduction[nom_affiche]
        chemin_dossier = os.path.join("sounds_library", nom_dossier)
        
        try:
            sons_disponibles = [f for f in os.listdir(chemin_dossier) if f.endswith(('.mp3', '.wav'))]
            
            if sons_disponibles:
                son_choisi = st.selectbox("Choisir un son", sons_disponibles)
                # ON ENREGISTRE DANS LE POST-IT (Session State)
                st.session_state.chemin_son_complet = os.path.join(chemin_dossier, son_choisi)
                st.audio(st.session_state.chemin_son_complet)
            else:
                st.warning(f"Le dossier {nom_affiche} est vide.")
                st.session_state.chemin_son_complet = None
        except FileNotFoundError:
            st.error(f"Dossier introuvable : {chemin_dossier}")
            st.session_state.chemin_son_complet = None
    else:
        st.session_state.chemin_son_complet = None

# On sort de la sidebar pour le champ principal
sujet = st.text_input("Quel monument ou lieu voulez-vous visiter ?")

# --- 4. GÉNÉRATION ---
# On utilise le session_state pour se souvenir du script entre les clics
if "script_final" not in st.session_state:
    st.session_state.script_final = ""

# ÉTAPE 1 : RÉDACTION
if st.button("✍️ Rédiger le script"):
    try:
        with st.status(f"Rédaction en mode {personnalite}..."):
            # Prompt enrichi
            prompt = f"""
            TU ES UN GUIDE TOURISTIQUE DONT LE STYLE EST : {personnalite}.
            Sujet : {sujet}. Public : {public}. 
            DURÉE CIBLE : {duree} minutes.
            
            STRUCTURE DU SCRIPT (OBLIGATOIRE) :
            1. INTRODUCTION HISTORIQUE RICHE : Commence par recontextualiser le lieu. Explique ce qu'il s'y passait à l'époque de sa création (ex: 11e siècle pour Angkor) et fais un parallèle avec ce qu'il se passait ailleurs dans le monde à la même époque pour donner des points de repère (ex: "Pendant qu'ici on bâtissait ceci, en Europe on achevait les premières cathédrales...").
            2. VISITE SPATIALE : si possible et si tu trouves les informations fiables et vérifiées nécessaires, guide l'auditeur physiquement dans l'espace. Utilise des indications directionnelles ("Si vous regardez à votre droite", "En passant sous le portique", "Cherchez du regard tel détail sur le fronton").
            3. ANECDOTES ET DÉTAILS : Intègre des éléments sur l'architecture, la vie quotidienne ou les secrets du lieu. Ne propose que des informations qui ont été vérifiées.

            CONSIGNES DE STYLE :
            - Si 'Le Vieux Sage' : Ton mystérieux, parle de folklore, de spiritualité, commence par 'On raconte que...'.
            - Si 'Indiana Jones' : Ton épique, insiste sur l'aventure, les découvertes, utilise des verbes d'action.
            - Si 'Le Local' : Ton amical, parle de 'nous' (les habitants), donne des conseils de resto ou de coins cachés.
            - Si 'Le Guide Conférencier' : Ton noble, historique, précis et très structuré.
            
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
            # On demande discrètement les coordonnées GPS à Gemini à côté
            gps_prompt = f"Donne moi uniquement les coordonnées GPS (latitude, longitude) de {sujet} sous le format 'lat, lon'. Rien d'autre."
            gps_res = model.generate_content(gps_prompt)
            st.session_state.coords_gps = gps_res.text.strip()
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
if st.session_state.script_final:
    if st.button("🔊 Créer l'Audio final"):
        try:
            with st.status("Génération de l'expérience audio..."):
                # 1. Nom du fichier
                sujet_propre = "".join(x for x in sujet if x.isalnum() or x in "._- ").replace(" ", "_")
                fichiers_existants = [f for f in os.listdir(".") if f.startswith(f"guide_{sujet_propre}")]
                index = len(fichiers_existants) + 1
                nom_mp3 = f"guide_{sujet_propre}_final_{index}.mp3"

                # 2. GÉNÉRATION DE LA VOIX (Henri ou Denise)
                async def generate_voice():
                    voice = "fr-FR-DeniseNeural" if genre_voix == "Féminine" else "fr-FR-HenriNeural"
                    texte_complet = " . . . " + st.session_state.script_final
                    communicate = edge_tts.Communicate(texte_complet, voice)
                    await communicate.save(nom_mp3)

                asyncio.run(generate_voice())

                # 3. MIXAGE AVEC L'AMBIANCE
                if musique_fond and st.session_state.get('chemin_son_complet'):
                    try:
                        son_voix = AudioSegment.from_file(nom_mp3)
                        son_ambiance = AudioSegment.from_file(st.session_state.chemin_son_complet)

                        # Réglage de la discrétion
                        son_ambiance_calme = son_ambiance - 25 
                        audio_mixe = son_voix.overlay(son_ambiance_calme, loop=True)
                        audio_mixe.export(nom_mp3, format="mp3")
                        
                    except Exception as e_mix:
                        st.warning(f"Le mixage a échoué, voix seule conservée. Erreur : {e_mix}")

                # --- AJOUT DES MÉTADONNÉES GPS ---
                try:  
                    import eyed3
                    audio_file = eyed3.load(nom_mp3)
                    if audio_file.tag is None:
                        audio_file.initTag()
                        
                    # On stocke les coordonnées (récupérées à l'étape 1)
                    coords = st.session_state.get('coords_gps', '0, 0')
                    audio_file.tag.comments.set(coords)
                    
                    # On ajoute le titre
                    audio_file.tag.title = f"Guide : {sujet}"
                    audio_file.tag.save()
                except Exception as e_gps:
                    st.info(f"Note : Métadonnées GPS non inscrites ({e_gps})")

            # On sort enfin du "with st.status" pour afficher le résultat
            st.success("🎉 Ton audio-guide immersif est prêt !")
            st.audio(nom_mp3)
            
            with open(nom_mp3, "rb") as file:
                st.download_button("📥 Télécharger le MP3", data=file, file_name=nom_mp3)

        except Exception as e:
            # C'est ici qu'on ferme le tout premier "try" du bouton
            st.error(f"Erreur lors de la création de l'audio : {e}")
# --- HISTORIQUE AVANCÉ ---
st.divider()
st.subheader("📚 Bibliothèque de tes audio-guides")

# Liste des fichiers MP3
fichiers = [f for f in os.listdir(".") if f.endswith(".mp3")]
fichiers.sort(reverse=True)

if not fichiers:
    st.write("Aucun guide dans la bibliothèque.")

for f in fichiers:
    # On crée un cadre pour chaque ligne d'audio
    with st.container(border=True):
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            st.write(f"📖 **{f}**")
            st.audio(f)
            
        with col2:
            # Bouton de téléchargement
            with open(f, "rb") as file:
                st.download_button(
                    label="📥", 
                    data=file, 
                    file_name=f, 
                    key=f"dl_{f}",
                    help="Télécharger ce guide"
                )
                
        with col3:
            # Bouton Supprimer avec confirmation via Popover
            confirm = st.popover("🗑️", help="Supprimer ce fichier")
            confirm.warning("Supprimer définitivement ?")
            if confirm.button("Confirmer la suppression", key=f"del_{f}"):
                os.remove(f)
                st.rerun() # Relance l'app pour mettre à jour la liste immédiatement

