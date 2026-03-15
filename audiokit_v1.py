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
                st.write(f"DEBUG — musique_fond={musique_fond} | chemin={st.session_state.get('chemin_son_complet')}") # Ligne temporaire de débogage
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
            st.success("🎉 Ton audioguide immersif est prêt !")
            st.info("💡 Pensez à télécharger votre audioguide, il ne sera pas conservé après fermeture de l'application.")
            
# ─────────────────────────────────────────────────────
                
        except Exception as e:
            st.error(f"Erreur globale : {e}")   
    # ── AFFICHAGE PERSISTANT DU RÉSULTAT ──
    if os.path.exists(st.session_state.get('nom_mp3', '')):
        st.audio(st.session_state.nom_mp3)
        with open(st.session_state.nom_mp3, "rb") as file:
            st.download_button("📥 Télécharger le MP3", data=file, file_name=st.session_state.nom_mp3)

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
                            nom_mp3     = st.session_state.nom_mp3,
                            slug        = slug_edite,
                            nom_affiche = country,
                            script      = st.session_state.script_final,
                            coords_str  = coords,
                            sujet       = sujet
                        )
                        st.success(f"✅ Audio-guide envoyé dans `audioguides/{slug_edite}/` !")
                        st.markdown("[🗺️ Voir sur AudioMap](https://nyssos2.github.io/AudioMap)")
                    except Exception as e:
                        st.error(f"❌ Erreur lors de l'envoi : {e}") 
                    
if st.button("🗑️ Effacer et recommencer"):
    st.session_state.script_final = ""
    st.rerun()
