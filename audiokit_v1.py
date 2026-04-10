import streamlit as st
import google.generativeai as genai
from google.generativeai import GenerativeModel
import asyncio
import edge_tts
# (suppression de 'from gtts import gTTS')
import os
import pypdf
import requests
import unicodedata
import re
import json

from pydub import AudioSegment
AudioSegment.converter = "ffmpeg"
AudioSegment.ffprobe = "ffprobe"

st.set_page_config(
    page_title="AudioKit",
    page_icon="🎙️",  # Tu peux mettre un emoji ou le chemin vers un fichier .png
    layout="centered"
)
# --- CONFIGURATION DE L'ICÔNE MOBILE ---
# Note : J'ai ajouté 'raw.githubusercontent.com' pour que l'image soit lisible par le navigateur
URL_LOGO = "https://raw.githubusercontent.com/nyssos2/AudioKit/main/logo.png"

st.markdown(
    f"""
    <link rel="icon" type="image/png" href="{URL_LOGO}">
    <link rel="apple-touch-icon" sizes="180x180" href="{URL_LOGO}">
    <link rel="shortcut icon" type="image/png" href="{URL_LOGO}">
    <meta name="apple-mobile-web-app-title" content="AudioKit">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="theme-color" content="#ffffff">
    """,
    unsafe_allow_html=True
)
def coords_to_country_slug(coords_str):
    """Convertit 'lat, lon' en slug de pays ex: 'japon', 'france'"""
    try:
        # Remplace : lat, lon = [x.strip() for x in coords_str.split(',')]
        # Par cette version robuste :
        parts = [p.strip() for p in coords_str.split(',')]
        lat = parts[0] if len(parts) > 0 else "0"
        lon = parts[1] if len(parts) > 1 else "0"
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json&accept-language=fr"
        r = requests.get(url, headers={"User-Agent": "AudioKit/1.0"}, timeout=5)
        country = r.json().get("address", {}).get("country", "inconnu")
        # Convertir en slug : "Japon" → "japon", "Côte d'Ivoire" → "cote-d-ivoire"
        slug = unicodedata.normalize('NFD', country)
        slug = slug.encode('ascii', 'ignore').decode('utf-8')
        slug = re.sub(r'[^a-z0-9]+', '-', slug.lower()).strip('-')
        return slug, country
    except:
        return "inconnu", "Inconnu"

def push_to_audiomap(nom_mp3, slug, nom_affiche, script, coords_str, sujet, duree, public, personnalite):
    """Envoie le MP3 et le JSON vers le repo GitHub AudioMap"""
    token = st.secrets["GITHUB_TOKEN"]
    repo  = "nyssos2/AudioMap"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json"
    }
    # Remplace : lat, lon = [x.strip() for x in coords_str.split(',')]
    # Par cette version robuste :
    parts = [p.strip() for p in coords_str.split(',')]
    lat = parts[0] if len(parts) > 0 else "0"
    lon = parts[1] if len(parts) > 1 else "0"

    base_url = f"https://api.github.com/repos/{repo}/contents/audioguides/{slug}"

    # Nom de base du fichier (sans espaces ni accents)
    def slugify(s):
        s = unicodedata.normalize('NFD', str(s)).encode('ascii','ignore').decode().lower()
        return re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    
    nom_base = f"{slugify(sujet)}_{duree}min_{slugify(public)}_{slugify(personnalite)}"

    # ── 1. Envoyer le MP3 ──
    with open(nom_mp3, "rb") as f:
        mp3_b64 = __import__('base64').b64encode(f.read()).decode()

    mp3_path = f"{base_url}/{nom_base}.mp3"
    mp3_check = requests.get(mp3_path, headers=headers)
    mp3_payload = {
        "message": f"AudioKit : ajout {sujet}",
        "content": mp3_b64,
    }
    if mp3_check.status_code == 200:
        mp3_payload["sha"] = mp3_check.json()["sha"]
    requests.put(mp3_path, headers=headers, json=mp3_payload)

    # ── 3. Mettre à jour index.json ──
    index_url = f"https://api.github.com/repos/{repo}/contents/audioguides/index.json"
    index_res = requests.get(index_url, headers=headers)
    index_data = json.loads(__import__('base64').b64decode(
        index_res.json()["content"]).decode('utf-8'))
    index_sha  = index_res.json()["sha"]

    # Trouver ou créer la destination
    dest = next((d for d in index_data["destinations"] if d["key"] == slug), None)
    if not dest:
        dest = {"key": slug, "nom": nom_affiche, "sites": []}
        index_data["destinations"].append(dest)

    # Ajouter ou mettre à jour le site
    existing = next((s for s in dest["sites"] if s["fichier"] == f"{nom_base}.mp3"), None)
    if existing:
        existing.update({"nom": sujet, "sous_titre": nom_affiche,
                         "lat": float(lat), "lng": float(lon),
                         "transcription": script})
    else:
        dest["sites"].append({
            "nom": sujet, "sous_titre": nom_affiche,
            "lat": float(lat), "lng": float(lon),
            "fichier": f"{nom_base}.mp3", "duree": "?:??",
            "transcription": script
        })

    new_index_b64 = __import__('base64').b64encode(
        json.dumps(index_data, ensure_ascii=False, indent=2).encode('utf-8')
    ).decode()
    requests.put(index_url, headers=headers, json={
        "message": f"AudioKit : index mis à jour ({sujet})",
        "content": new_index_b64,
        "sha": index_sha
    })
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
st.markdown(
    f"""
    <div style="display:flex; align-items:center; gap:14px; margin-bottom:0px;">
        <img src="{URL_LOGO}" style="height:64px; width:64px; object-fit:contain; border-radius:12px;">
        <span style="font-size:2em; font-weight:800; line-height:1;">AudioKit</span>
    </div>
    """,
    unsafe_allow_html=True
)
st.markdown("### Ma fabrique à audioguides perso")
st.markdown("##### Crée tes audioguides immersifs et captivants quel que soit le lieu à visiter !")
# On utilise du HTML simple dans le markdown pour réduire la taille et griser le texte
st.markdown(f"<p style='font-size: 0.8em; color: gray;'>Propulsé par Gemini 2.5 Flash</p>", unsafe_allow_html=True)

# --- INTERFACE ---
with st.sidebar:
    st.header("Paramètres")
    public = st.selectbox(
    "Public cible", 
    ["Enfants (5-10 ans)", "Ados", "Adultes"], 
    index=2
    )
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
    st.session_state.musique_fond = musique_fond

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

# AJOUT : Interface pour le document source (facultatif)
pdf_complement = st.file_uploader("Facultatif : ajouter un document source en PDF texte (pas scanné)", type=["pdf"])

pdf_text = ""
if pdf_complement is not None:
    try:
        reader = pypdf.PdfReader(pdf_complement)
        # Extraction simple du texte de toutes les pages
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pdf_text += text + "\n"
        
        if pdf_text:
            st.success("✅ Document PDF analysé et prêt à enrichir le script !")
        else:
            st.warning("⚠️ Le PDF semble vide ou illisible (format image ?).")
    except ImportError:
        st.error("La bibliothèque pypdf n'est pas installée. Veuillez l'ajouter à vos dépendances.")
    except Exception as e:
        st.error(f"Erreur lors de la lecture du PDF : {e}")

# --- 4. GÉNÉRATION ---
# On utilise le session_state pour se souvenir du script entre les clics
if "script_final" not in st.session_state:
    st.session_state.script_final = ""
if "mp3_bytes" not in st.session_state:
    st.session_state.mp3_bytes = None
if "nom_mp3" not in st.session_state:
    st.session_state.nom_mp3 = ""

# ÉTAPE 1 : RÉDACTION
if st.button("✍️ Etape 1/3 : Rédiger le script"):
    try:
        progress = st.progress(10, text="✍️ Rédaction du script en cours...")
        with st.status(f"Rédaction en mode {personnalite}..."):
            # CALCUL DU VOLUME DE TEXTE
            # 145 mots/min est une bonne moyenne pour une élocution posée
            mots_attendus = duree * 145
            
            # Préparation du bloc de contexte PDF (si présent)
            contexte_pdf = ""
            if pdf_text:
                contexte_pdf = f"""
                CONTEXTE SUPPLÉMENTAIRE (Issu du document PDF fourni par l'utilisateur) :
                {pdf_text[:12000]} 
                
                CONSIGNE SPÉCIFIQUE : Utilise prioritairement les informations, les chiffres et les anecdotes présents dans ce document pour enrichir ton récit. Si le document contient des détails techniques ou historiques précis, intègre-les de manière fluide dans le style choisi.
                """
                
            # Prompt enrichi avec contrainte explicite de longueur et contexte PDF
            prompt = f"""
            TU ES UN GUIDE TOURISTIQUE DONT LE STYLE EST : {personnalite}.
            Sujet : {sujet}. Public : {public}. 
            DURÉE CIBLE : {duree} minutes.
            NOMBRE DE MOTS MINIMUM : {mots_attendus} mots.
            
            STRUCTURE DU SCRIPT (OBLIGATOIRE) :
            1. INTRODUCTION HISTORIQUE RICHE : Commence par recontextualiser le lieu. Explique ce qu'il s'y passait à l'époque de sa création (ex: 11e siècle pour Angkor) et fais un parallèle avec ce qu'il se passait ailleurs dans le monde à la même époque pour donner des points de repère (ex: "Pendant qu'ici on bâtissait ceci, en Europe on achevait les premières cathédrales...").
            2. VISITE SPATIALE : si possible et si tu trouves les informations fiables et vérifiées nécessaires, guide l'auditeur physiquement dans l'espace. Utilise des indications directionnelles ("Si vous regardez à votre droite", "En passant sous le portique", "Cherchez du regard tel détail sur le fronton").
            3. ANECDOTES ET DÉTAILS : Intègre des éléments sur l'architecture, la vie quotidienne ou les secrets du lieu. Ne propose que des informations qui ont été vérifiées.
            4. NOTICES BIOGRAPHIQUES : Si une ou plusieurs personnalités sont déterminantes dans l'histoire du lieu visité, intègre des éléments biographiques les concernant. Exemple : Claunde-Nicolas LEDOUX pour les salines royales d'Arc et Senans.
            5. ADAPTE LA GRANULARITÉ A LA LONGUEUR :
               -Tu DOIS impérativement atteindre environ {mots_attendus} mots pour que la lecture dure {duree} minutes. 
               -Si la durée est longue, n'hésite pas à décrire très précisément les décors, l'ambiance et à multiplier les anecdotes historiques.
            6. RESPECTE AU MAXIMUM LA DUREE DEMANDEE (duree).
               
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
            """
            response = model.generate_content(prompt)
            progress.progress(70, text="🗺️ Récupération des coordonnées GPS...")
            # On demande discrètement les coordonnées GPS à Gemini à côté
            gps_prompt = f"Donne moi uniquement les coordonnées GPS (latitude, longitude) de {sujet} ET le nom de la ville/région sous le format 'lat, lon, destination'. Exemple: '35.01, 135.67, Kyoto'. Rien d'autre, sans les inventer."
            gps_res = model.generate_content(gps_prompt)
            st.session_state.coords_gps = gps_res.text.strip()
            # Nettoyage de sécurité pour enlever les éventuels résidus de Markdown
            st.session_state.script_final = response.text.replace("**", "").replace("#", "")
            progress.progress(100, text="✅ Script prêt !")
            st.success("Script rédigé !")
    except Exception as e:
        if "quota" in str(e).lower() or "429" in str(e) or "resource exhausted" in str(e).lower():
            st.warning("⏳ Vous avez atteint votre limite quotidienne de scripts gratuits. Veuillez réessayer ultérieurement.")
        else:
            st.error(f"Erreur rédaction : {e}")

# ÉTAPE 2 : ÉDITION (La boîte de dialogue toujours visible si un script existe)
if st.session_state.script_final:
    st.subheader("📝 Etape 2/3 : Révision du script")
    script_edite = st.text_area(
        "Vous pouvez corriger le texte avant de créer l'audio :", 
        value=st.session_state.script_final, 
        height=300
    )
    # On met à jour le session_state avec les modifs de l'utilisateur
    st.session_state.script_final = script_edite

# ÉTAPE 3 : AUDIO
if st.session_state.script_final:
    if st.button("🔊 Etape 3/3 : Créer l'audio final"):
        try:
            with st.status("Génération de l'expérience audio..."):
                # 1. Nom du fichier enrichi avec le public
                sujet_propre = "".join(x for x in sujet if x.isalnum() or x in "._- ").replace(" ", "_")
                # On nettoie le nom du public pour éviter les caractères spéciaux (ex: parenthèses)
                public_propre = "".join(x for x in public if x.isalnum())
                
                nom_base = f"guide_{sujet_propre}_{public_propre}"
                fichiers_existants = [f for f in os.listdir(".") if f.startswith(nom_base)]
                index = len(fichiers_existants) + 1
                nom_mp3 = f"{nom_base}_final_{index}.mp3"
                # Création du fichier temporaire pour la voix seule
                temp_voix = f"temp_voix_{index}.mp3"
                
                # 2. GÉNÉRATION DE LA VOIX
                async def generate_voice():
                    voice = "fr-FR-DeniseNeural" if genre_voix == "Féminine" else "fr-FR-HenriNeural"
                    # On ajoute un petit silence au début
                    texte_complet = " ... ..." + st.session_state.script_final
                    communicate = edge_tts.Communicate(texte_complet, voice)
                    await communicate.save(temp_voix)

                asyncio.run(generate_voice())

                # 3. MIXAGE AVEC L'AMBIANCE
                # st.write(f"DEBUG — musique_fond={musique_fond} | chemin={st.session_state.get('chemin_son_complet')}") # Ligne temporaire de débogage
                if st.session_state.get('musique_fond') and st.session_state.get('chemin_son_complet'):
                    try:
                        import time
                        time.sleep(1.0)  # Petit dodo pour laisser Windows libérer le fichier
                        
                        # On charge la voix fraîchement créée
                        son_voix = AudioSegment.from_file(temp_voix)
                        
                        # On charge la musique d'ambiance choisie dans la sidebar
                        son_ambiance = AudioSegment.from_file(st.session_state.chemin_son_complet)

                        # Réglage du volume d'ambiance (-25dB)
                        son_ambiance_calme = son_ambiance - 25

                        # Adapter la durée de l'ambiance à celle de la voix
                        if len(son_ambiance_calme) < len(son_voix):
                            repetition = len(son_voix) // len(son_ambiance_calme) + 1
                            son_ambiance_calme = son_ambiance_calme * repetition

                        # Couper à la même durée que la voix
                        son_ambiance_calme = son_ambiance_calme[:len(son_voix)]
                        
                        # Mixage
                        audio_mixe = son_voix.overlay(son_ambiance_calme)                        
                        
                        # Exportation finale
                        audio_mixe.export(nom_mp3, format="mp3", bitrate="192k")
                       
                        # Nettoyage du fichier temporaire
                        if os.path.exists(temp_voix):
                            os.remove(temp_voix)
                        
                    except Exception as e_mix:
                        st.error(f"Erreur mixage : {e_mix}")
                        # Si le mixage échoue, on renomme la voix temp en fichier final
                        if os.path.exists(temp_voix):
                            os.rename(temp_voix, nom_mp3)
                        print(f"--- ERREUR MIXAGE : {e_mix}")
                else:
                    # Pas de musique de fond, on renomme simplement
                    if os.path.exists(temp_voix):
                        os.rename(temp_voix, nom_mp3)

                # 4. AJOUT DES MÉTADONNÉES GPS (Version robuste)
                try:
                    import eyed3
                    # Petit délai pour laisser le fichier se stabiliser
                    audio_file = eyed3.load(nom_mp3)
                    if audio_file.tag is None:
                        audio_file.initTag()
                    
                    # On s'assure que les coordonnées sont bien là
                    coords = st.session_state.get('coords_gps', 'Non renseigné')
                    
                    # On écrit dans le titre ET dans le commentaire (pour Windows)
                    audio_file.tag.title = f"{sujet} | {coords}"
                    audio_file.tag.comments.set(coords)
                    
                    # On ajoute le public dans le champ 'Album' pour le tri
                    audio_file.tag.album = f"Public : {public}"
                    audio_file.tag.save(encoding='utf-8')
                    
                except Exception as e_gps:
                    st.info(f"Note : Métadonnées GPS non inscrites ({e_gps})")

            # Affichage final
            st.session_state.nom_mp3 = nom_mp3
            with open(nom_mp3, "rb") as f:
                st.session_state.mp3_bytes = f.read()
            st.success("🎉 Ton audioguide immersif est prêt !")
            st.info("💡 Pensez à télécharger votre audioguide, il ne sera pas conservé après fermeture de l'application.")
                
        except Exception as e:
            st.error(f"Erreur globale : {e}")   
    # ── AFFICHAGE PERSISTANT DU RÉSULTAT ──
    if st.session_state.mp3_bytes is not None:
        st.audio(st.session_state.mp3_bytes, format="audio/mp3")
        st.download_button("📥 Télécharger le MP3", data=st.session_state.mp3_bytes, file_name=st.session_state.nom_mp3)

        st.markdown("---")
        envoyer = st.checkbox("🗺️ Envoyer cet audioguide vers AudioMap")
        if envoyer:
            coords = st.session_state.get('coords_gps', '')
            if coords and coords != 'Non renseigné':
                slug, country = coords_to_country_slug(coords)
            else:
                slug, country = 'inconnu', 'Inconnu'
            st.info(f"📍 Destination détectée : **{country}** → dossier `{slug}`")
            slug_edite = st.text_input(
                "Modifier le nom du dossier si besoin (minuscules, sans accents) :",
                value=slug
            )
            st.warning("⚠️ Ce fichier sera publié sur le repo GitHub AudioMap. Cette action est irréversible.")
            if st.button("🚀 Confirmer l'envoi vers AudioMap"):
                with st.spinner("Envoi en cours…"):
                    try:
                        push_to_audiomap(
                            nom_mp3      = st.session_state.nom_mp3,
                            slug         = slug_edite,
                            nom_affiche  = country,
                            script       = st.session_state.script_final,
                            coords_str   = coords,
                            sujet        = sujet,
                            duree        = duree,
                            public       = public,
                            personnalite = personnalite
                        )
                        st.success(f"✅ Audio-guide envoyé dans `audioguides/{slug_edite}/` !")
                        st.markdown("[🗺️ Voir sur AudioMap](https://nyssos2.github.io/AudioMap)")
                    except Exception as e:
                        st.error(f"❌ Erreur lors de l'envoi : {e}") 
                    
if st.button("🗑️ Effacer et recommencer"):
    st.session_state.script_final = ""
    st.rerun()
