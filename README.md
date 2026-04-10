<div align="center">

<img src="https://raw.githubusercontent.com/nyssos2/AudioKit/main/logo.png" alt="AudioKit Logo" width="120" />

# 🎙️ AudioKit `v5.9+`

**Transformez n'importe quel sujet en audio-guide immersif de qualité professionnelle.**

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Gemini](https://img.shields.io/badge/Google-Gemini_1.5-4285F4?style=flat-square&logo=google&logoColor=white)](https://deepmind.google/technologies/gemini/)
[![Edge-TTS](https://img.shields.io/badge/Edge--TTS-Voix_Naturelles-0078D4?style=flat-square&logo=microsoft&logoColor=white)](https://github.com/rany2/edge-tts)
[![License](https://img.shields.io/badge/Licence-MIT-22C55E?style=flat-square)](LICENSE)

*Un outil conçu pour les voyageurs et les curieux du patrimoine. ❤️*

---

</div>

## 🌟 Présentation

AudioKit est une application intelligente conçue pour **transformer n'importe quel sujet ou document PDF** en un audio-guide immersif de qualité professionnelle.

Le pipeline est entièrement automatisé :

```
Sujet (+ PDF)  →  Script IA  →  Synthèse vocale  →  Mixage audio  →  Publication AudioMap
```

---

## ✨ Fonctionnalités

| Fonctionnalité | Détail |
|---|---|
| 🧠 **Intelligence Artificielle** | Rédaction de scripts personnalisés via **Google Gemini 2.5 Flash** |
| 🗣️ **Synthèse Vocale Premium** | Voix naturelles (Henri, Denise…) propulsées par **Edge-TTS** |
| 🎵 **Mixage Automatique** | Superposition intelligente voix + ambiance sonore (Nature, Intérieur, Urbain) avec **Pydub** |
| 📄 **Analyse de Documents** | Import de fichiers **PDF** pour enrichir le script généré |
| 🌍 **Géolocalisation** | Extraction automatique des coordonnées GPS pour les métadonnées |
| 🗺️ **Intégration AudioMap** | Publication directe vers le repo GitHub d'**AudioMap** |
| 📱 **Mobile Friendly** | Interface optimisée smartphone, **PWA ready** |

---

## 🛠️ Installation & Configuration

### 1. Prérequis

- **Python** `3.9+`
- **FFmpeg** (outil système requis pour le traitement audio)

### 2. Dépendances Python

Installez les dépendances via `pip` :

```bash
pip install -r requirements.txt
```

**`requirements.txt`**
```
streamlit
google-generativeai
edge-tts
pydub
pypdf
requests
eyed3
```

### 3. Dépendances système (déploiement Streamlit Cloud)

**`packages.txt`**
```
ffmpeg
```

> ⚠️ Ce fichier est **obligatoire** pour un déploiement sur Streamlit Cloud.

### 4. Variables d'environnement

Configurez vos clés dans `.streamlit/secrets.toml` :

```toml
GOOGLE_API_KEY = "VOTRE_CLE_GEMINI"
GITHUB_TOKEN  = "VOTRE_TOKEN_GITHUB"
APP_PASSWORD  = "VOTRE_MOT_DE_PASSE_APP"
```

> 💡 Ne commitez jamais ce fichier — ajoutez-le à votre `.gitignore`.

---

## 🚀 Utilisation

```bash
streamlit run audiokit_v5.8.py
```

Ensuite, dans l'interface :

1. **Saisissez un sujet** — ex : *"Le temple Fushimi Inari à Kyoto"*
2. **Choisissez un narrateur** et une ambiance sonore
3. **Uploadez un PDF** *(optionnel)* si vous avez des notes spécifiques
4. Cliquez sur **Générer** — AudioKit rédige, enregistre et mixe le tout automatiquement
5. Cliquez sur **Publier** — envoyez directement le résultat sur votre carte [AudioMap](https://github.com/nyssos2/AudioMap) 🗺️

---

## 🛡️ Structure du Projet

```
audiokit/
├── audiokit_v5.8.py      # 🧠 Cœur de l'application Streamlit
├── logo.png              # 🎨 Identité visuelle (favicon, icônes iOS/Android)
├── requirements.txt      # 📦 Dépendances Python
├── packages.txt          # ⚙️  Dépendances système (Streamlit Cloud)
├── .streamlit/
│   └── secrets.toml      # 🔐 Variables d'environnement (non versionné)
└── temp_voix.mp3         # 🔄 Fichier de travail temporaire (supprimé après mixage)
```

---

## 🔗 Projets liés

- **[AudioMap](https://github.com/nyssos2/AudioMap)** — La carte interactive qui affiche et joue les audio-guides générés par AudioKit.

---

## 👨‍💻 Auteur

Développé avec ❤️ par **[Nyssos](https://github.com/nyssos2)**

---

<div align="center">

*Un outil conçu pour les voyageurs et les curieux du patrimoine.*

</div>
