"""
MathGuide Bénin — Application FastAPI principale.
Tuteur IA socratique de mathématiques (programme officiel du Bénin, 6ᵉ à Terminale).
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from config import (
    APP_TITLE,
    CORS_ORIGINS,
    CLASSES,
    SERIES_PAR_CLASSE,
    COMPETENCES_DOMAINES,
    BASE_DIR,
)
from models import (
    ChatRequest,
    ChatResponse,
    OCRResult,
    ExerciceRequest,
    Exercice,
    ProgressUpdateRequest,
    EleveProgress,
)
import llm, ocr, rag, progress


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[MathGuide Bénin] Démarrage : indexation des programmes officiels (RAG)...")
    try:
        rag.indexer_programmes()
    except Exception as e:
        print(f"[MathGuide Bénin] Indexation RAG impossible au démarrage : {e}")
    yield


app = FastAPI(title=APP_TITLE, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Métadonnées programme (classes, séries, domaines de compétences)
# ---------------------------------------------------------------------------

@app.get("/api/programme")
async def get_programme():
    return {
        "classes": CLASSES,
        "series_par_classe": SERIES_PAR_CLASSE,
        "domaines_competences": COMPETENCES_DOMAINES,
    }


# ---------------------------------------------------------------------------
# Chat socratique
# ---------------------------------------------------------------------------

@app.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest):
    if payload.classe not in CLASSES:
        raise HTTPException(status_code=400, detail="Classe inconnue.")

    contexte_rag = rag.rechercher_contexte_formate(payload.message, classe=payload.classe)
    sources = []
    if contexte_rag:
        passages = rag.rechercher_contexte(payload.message, classe=payload.classe)
        sources = [f"extrait {i+1}" for i in range(len(passages))]

    reponse_texte = await llm.generer_reponse(
        message=payload.message,
        classe=payload.classe,
        serie=payload.serie,
        historique=payload.historique,
        rag_context=contexte_rag,
        image_description=payload.image_description,
    )

    return ChatResponse(reponse=reponse_texte, sources_rag=sources)


# ---------------------------------------------------------------------------
# OCR — upload d'image d'exercice
# ---------------------------------------------------------------------------

@app.post("/api/ocr", response_model=OCRResult)
async def upload_image(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Le fichier doit être une image.")
    contenu = await file.read()
    try:
        resultat = ocr.traiter_image(contenu)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur OCR : {e}")
    return resultat


# ---------------------------------------------------------------------------
# Exercices — proposition selon la progression de l'élève
# ---------------------------------------------------------------------------

@app.post("/api/exercice/proposer", response_model=Exercice)
async def proposer_exercice(payload: ExerciceRequest):
    if payload.classe not in CLASSES:
        raise HTTPException(status_code=400, detail="Classe inconnue.")

    domaine = payload.domaine or progress.domaine_prioritaire(
        payload.eleve_id, payload.classe, payload.serie, COMPETENCES_DOMAINES
    )

    contexte_rag = rag.rechercher_contexte_formate(domaine, classe=payload.classe)
    enonce = await llm.generer_exercice(payload.classe, payload.serie, domaine, rag_context=contexte_rag)

    return Exercice(
        id=f"{payload.eleve_id}-{domaine}-{payload.classe}",
        classe=payload.classe,
        serie=payload.serie,
        domaine=domaine,
        enonce=enonce,
    )


# ---------------------------------------------------------------------------
# Progression par compétences
# ---------------------------------------------------------------------------

@app.get("/api/progression/{eleve_id}", response_model=EleveProgress)
async def get_progression(eleve_id: str, classe: str, serie: str | None = None):
    return progress.resume_progression(eleve_id, classe, serie)


@app.post("/api/progression/enregistrer")
async def enregistrer_progression(payload: ProgressUpdateRequest):
    competence = progress.enregistrer_progres(
        payload.eleve_id, payload.classe, payload.serie, payload.domaine, payload.a_progresse
    )
    return {"ok": True, "competence": competence}


# ---------------------------------------------------------------------------
# Fichiers statiques (interface web) — index.html est à la racine du dépôt
# (structure plate, pas de sous-dossier static/)
# ---------------------------------------------------------------------------

@app.get("/")
async def index():
    return FileResponse(str(BASE_DIR / "index.html"))
