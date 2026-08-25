# MathGuide Bénin

Tuteur IA **socratique** de mathématiques, conforme au programme officiel du Bénin (Approche Par Compétences), de la **6ᵉ à la Terminale** (séries A1, A2, B, C, D et techniques).

MathGuide Bénin ne donne **jamais** la réponse finale : il guide l'élève par des questions, des indices progressifs et des rappels de cours, pour qu'il construise lui-même la solution.

## Fonctionnalités

- 💬 Chat socratique adapté à la classe et à la série de l'élève
- 📷 Upload d'image d'exercice avec OCR (texte manuscrit/imprimé) + détection de figure
- 📚 Base de connaissances RAG indexée automatiquement à partir des PDF des programmes officiels (`data/programmes/`)
- 📈 Suivi de progression par compétence (numérique, géométrie, fonctions, probabilités, etc.)
- 🎯 Bouton "Proposer un exercice selon ma progression"
- 🖥️ Interface web moderne et responsive (mobile compris)

## Installation

### 1. Prérequis
- Python 3.10+
- (Recommandé) un environnement virtuel

```bash
python -m venv venv
source venv/bin/activate       # Windows : venv\Scripts\activate
```

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

> Le premier lancement d'EasyOCR et de sentence-transformers télécharge des modèles (~200-500 Mo). Prévoir une connexion internet la première fois.

### 3. Configurer la clé API

```bash
cp .env.example .env
```

Puis éditer `.env` et renseigner :
- `LLM_PROVIDER` = `groq` (gratuit, recommandé), `xai` (Grok), `openai` ou `mistral`
- La clé correspondante : `GROQ_API_KEY`, `XAI_API_KEY`, `OPENAI_API_KEY` ou `MISTRAL_API_KEY`

#### Où obtenir une clé API gratuitement

| Fournisseur | Gratuit ? | Lien |
|---|---|---|
| **Groq** (recommandé pour démarrer) | Oui, limites généreuses, sans carte bancaire | https://console.groq.com |
| Google Gemini | Oui (~1500 req/jour) — nécessite d'adapter `llm.py` (format d'API différent) | https://aistudio.google.com |
| Mistral (La Plateforme) | Palier "Experiment" gratuit et limité | https://console.mistral.ai |
| xAI (Grok) | Variable selon les périodes, vérifier sur place | https://x.ai/api |

Groq est le plus simple : son API est compatible avec le SDK `openai` utilisé dans `llm.py`, aucune adaptation de code n'est nécessaire.

### 4. Ajouter les programmes officiels (RAG)

Déposer les PDF des programmes officiels béninois dans :

```
data/programmes/
```

Ils seront indexés automatiquement au démarrage de l'application (ChromaDB, persistant — pas besoin de ré-indexer à chaque redémarrage sauf ajout de nouveaux fichiers).

### 5. (Recommandé pour un déploiement) Configurer Supabase pour la progression

Par défaut, la progression des élèves est stockée dans un fichier JSON local (`data/progress.json`) — pratique en développement, mais effacé au redéploiement sur la plupart des hébergeurs gratuits (Render, Railway...).

Pour une persistance fiable :
1. Crée un projet Supabase (https://supabase.com), palier gratuit suffisant.
2. Applique la migration `data/supabase_migration.sql` (SQL editor de Supabase, ou `supabase db push`).
3. Renseigne `SUPABASE_URL` et `SUPABASE_KEY` dans `.env` (clé `service_role` recommandée côté backend).

Si ces deux variables sont vides, l'application bascule automatiquement sur le JSON local — aucune configuration supplémentaire n'est requise pour tester en local.

### 6. Lancer l'application

```bash
uvicorn app.main:app --reload --port 8000
```

Ouvrir ensuite : **http://localhost:8000**

### 7. Déployer le backend

Netlify (souvent utilisé pour tes autres projets) ne fait que du **statique** — il ne peut pas héberger FastAPI. Pour ce projet, utilise un hébergeur Python :

| Hébergeur | Palier gratuit | Notes |
|---|---|---|
| **Render.com** | Oui | Web Service Python, redémarre après inactivité sur le palier gratuit |
| **Railway.app** | Oui (crédit limité/mois) | Déploiement simple depuis GitHub |
| **Fly.io** | Oui (limité) | Plus technique à configurer |

Dans tous les cas, connecte Supabase (étape 5 ci-dessus) pour que la progression des élèves survive aux redémarrages et redéploiements.

## Structure du projet

```
mathguide-benin/
├── app/
│   ├── main.py          # FastAPI app + endpoints
│   ├── config.py        # Configuration + variables d'environnement
│   ├── prompts.py       # SYSTEM_PROMPT socratique
│   ├── llm.py           # Client LLM (xAI / OpenAI / Mistral)
│   ├── ocr.py            # OCR image → texte + description
│   ├── rag.py             # ChromaDB + embeddings des PDF
│   ├── progress.py        # Suivi des compétences par élève
│   └── models.py          # Modèles Pydantic
├── static/
│   └── index.html          # Interface complète (HTML + CSS + JS)
├── data/
│   ├── programmes/          # PDF officiels à indexer (RAG)
│   ├── exercises/            # Banque d'exercices types
│   └── supabase_migration.sql # Schéma Supabase pour la progression
├── .env.example
├── requirements.txt
└── README.md
```

## Principales routes de l'API

| Méthode | Route                          | Description                                      |
|---------|----------------------------------|---------------------------------------------------|
| GET     | `/api/programme`                 | Classes, séries et domaines de compétences        |
| POST    | `/api/chat`                      | Message → réponse socratique du tuteur            |
| POST    | `/api/ocr`                       | Upload image → texte extrait + description figure |
| POST    | `/api/exercice/proposer`         | Génère un exercice adapté à la progression        |
| GET     | `/api/progression/{eleve_id}`    | Progression d'un élève par compétence             |
| POST    | `/api/progression/enregistrer`   | Enregistre un progrès sur une compétence          |

## Notes de conception

- Le `SYSTEM_PROMPT` (dans `app/prompts.py`) impose une structure de réponse en 5 points (reformulation, questions, indice, encouragement, rappel de cours) et interdit formellement de donner la réponse finale.
- Le RAG utilise ChromaDB en mode persistant (`data/chroma_db/`) avec des embeddings multilingues (`sentence-transformers`), adaptés au français.
- L'OCR utilise EasyOCR par défaut (`OCR_ENGINE=easyocr` dans `.env`), avec un repli possible sur Tesseract (`OCR_ENGINE=tesseract`).
- La progression est stockée soit dans Supabase (recommandé en production, tables `eleves` et `competences_progress`), soit dans `data/progress.json` en repli local si Supabase n'est pas configuré.
- `llm.py` fonctionne tel quel avec Groq, xAI, OpenAI et Mistral (tous compatibles avec le SDK `openai` via `base_url`). Gemini nécessiterait une petite adaptation (format d'API différent).
