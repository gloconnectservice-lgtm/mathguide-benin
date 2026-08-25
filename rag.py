"""
Module RAG de MathGuide Bénin.
Indexe automatiquement les PDF des programmes officiels (déposés à la racine du dépôt)
dans une base ChromaDB persistante, et permet la recherche contextuelle.
"""
import hashlib
from pathlib import Path
from typing import List, Optional

import chromadb
from chromadb.utils import embedding_functions

from config import (
    CHROMA_DIR,
    PROGRAMMES_DIR,
    EMBEDDING_MODEL,
    RAG_COLLECTION_NAME,
    RAG_TOP_K,
    RAG_CHUNK_SIZE,
    RAG_CHUNK_OVERLAP,
)

_chroma_client = None
_collection = None
_embedding_fn = None


def _get_embedding_fn():
    global _embedding_fn
    if _embedding_fn is None:
        _embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDING_MODEL
        )
    return _embedding_fn


def _get_collection():
    global _chroma_client, _collection
    if _collection is None:
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        _collection = _chroma_client.get_or_create_collection(
            name=RAG_COLLECTION_NAME,
            embedding_function=_get_embedding_fn(),
        )
    return _collection


def _extraire_texte_pdf(chemin_pdf: Path) -> str:
    from pypdf import PdfReader
    reader = PdfReader(str(chemin_pdf))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _decouper_en_chunks(texte: str, taille: int = RAG_CHUNK_SIZE, chevauchement: int = RAG_CHUNK_OVERLAP) -> List[str]:
    texte = " ".join(texte.split())  # normalise les espaces
    if not texte:
        return []
    chunks = []
    debut = 0
    while debut < len(texte):
        fin = min(debut + taille, len(texte))
        chunks.append(texte[debut:fin])
        debut += taille - chevauchement
    return chunks


def indexer_programmes() -> int:
    """Parcourt le dossier des programmes, découpe chaque PDF en chunks et les indexe
    dans ChromaDB (idempotent : ignore les documents déjà indexés)."""
    PROGRAMMES_DIR.mkdir(parents=True, exist_ok=True)
    collection = _get_collection()

    pdfs = sorted(PROGRAMMES_DIR.glob("*.pdf"))
    if not pdfs:
        print(f"[RAG] Aucun PDF trouvé dans {PROGRAMMES_DIR} — le tuteur fonctionnera sans contexte RAG.")
        return 0

    nb_chunks_ajoutes = 0
    for pdf_path in pdfs:
        try:
            texte = _extraire_texte_pdf(pdf_path)
        except Exception as e:
            print(f"[RAG] Erreur lecture {pdf_path.name} : {e}")
            continue

        chunks = _decouper_en_chunks(texte)
        for i, chunk in enumerate(chunks):
            doc_id = hashlib.sha256(f"{pdf_path.name}-{i}-{chunk[:50]}".encode()).hexdigest()
            existe = collection.get(ids=[doc_id])
            if existe and existe.get("ids"):
                continue
            collection.add(
                ids=[doc_id],
                documents=[chunk],
                metadatas=[{"source": pdf_path.name, "chunk_index": i}],
            )
            nb_chunks_ajoutes += 1

    print(f"[RAG] Indexation terminée : {len(pdfs)} PDF(s), {nb_chunks_ajoutes} nouveau(x) chunk(s) ajouté(s).")
    return nb_chunks_ajoutes


def rechercher_contexte(requete: str, classe: Optional[str] = None, top_k: int = RAG_TOP_K) -> List[str]:
    """Recherche les passages de programme les plus pertinents pour une requête donnée."""
    collection = _get_collection()
    if collection.count() == 0:
        return []

    query_text = f"[{classe}] {requete}" if classe else requete
    resultats = collection.query(query_texts=[query_text], n_results=min(top_k, max(collection.count(), 1)))

    documents = resultats.get("documents", [[]])[0]
    return documents


def rechercher_contexte_formate(requete: str, classe: Optional[str] = None, top_k: int = RAG_TOP_K) -> Optional[str]:
    passages = rechercher_contexte(requete, classe=classe, top_k=top_k)
    if not passages:
        return None
    return "\n---\n".join(passages)
