"""
Module de progression de MathGuide Bénin.

Stocke, par élève, l'avancement sur les différents domaines de compétences.

- Si SUPABASE_URL / SUPABASE_KEY sont renseignés (.env) : persistance dans Supabase
  (tables `eleves` et `competences_progress`, voir data/supabase_migration.sql).
  Recommandé pour un déploiement sur un hébergeur au système de fichiers éphémère
  (Render, Railway, etc.).
- Sinon : repli automatique sur un fichier JSON local (data/progress.json),
  pratique pour le développement en local.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Dict, Optional

from app.config import PROGRESS_DB_PATH, USE_SUPABASE, SUPABASE_URL, SUPABASE_KEY
from app.models import EleveProgress, CompetenceProgress

_lock = Lock()
_cache: Dict[str, EleveProgress] = {}
_charge = False

_supabase_client = None


def _get_supabase_client():
    global _supabase_client
    if _supabase_client is None:
        from supabase import create_client
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase_client


# ---------------------------------------------------------------------------
# Backend Supabase
# ---------------------------------------------------------------------------

def _supabase_get_progression(eleve_id: str, classe: str, serie: Optional[str]) -> EleveProgress:
    client = _get_supabase_client()

    eleve_res = client.table("eleves").select("*").eq("eleve_id", eleve_id).execute()
    if not eleve_res.data:
        client.table("eleves").insert({
            "eleve_id": eleve_id, "classe": classe, "serie": serie, "total_sessions": 0
        }).execute()
        total_sessions = 0
    else:
        row = eleve_res.data[0]
        total_sessions = row.get("total_sessions", 0)
        # garde la classe/série à jour si l'élève a changé de niveau
        if row.get("classe") != classe or row.get("serie") != serie:
            client.table("eleves").update({"classe": classe, "serie": serie}).eq("eleve_id", eleve_id).execute()

    comp_res = client.table("competences_progress").select("*").eq("eleve_id", eleve_id).execute()
    competences = [
        CompetenceProgress(
            domaine=c["domaine"],
            nb_sessions=c.get("nb_sessions", 0),
            niveau_maitrise=float(c.get("niveau_maitrise", 0.0)),
            dernier_travail=c.get("dernier_travail"),
        )
        for c in (comp_res.data or [])
    ]

    return EleveProgress(
        eleve_id=eleve_id, classe=classe, serie=serie,
        competences=competences, total_sessions=total_sessions,
    )


def _supabase_enregistrer_progres(eleve_id: str, classe: str, serie: Optional[str], domaine: str, a_progresse: bool) -> CompetenceProgress:
    client = _get_supabase_client()
    eleve = _supabase_get_progression(eleve_id, classe, serie)
    competence = eleve.get_or_create_competence(domaine)
    competence.nb_sessions += 1
    competence.dernier_travail = datetime.now(timezone.utc)
    if a_progresse:
        increment = 0.15 * (1 - competence.niveau_maitrise)
        competence.niveau_maitrise = min(1.0, round(competence.niveau_maitrise + increment, 3))

    client.table("competences_progress").upsert({
        "eleve_id": eleve_id,
        "domaine": domaine,
        "nb_sessions": competence.nb_sessions,
        "niveau_maitrise": competence.niveau_maitrise,
        "dernier_travail": competence.dernier_travail.isoformat(),
    }, on_conflict="eleve_id,domaine").execute()

    client.table("eleves").update({
        "total_sessions": eleve.total_sessions + 1,
    }).eq("eleve_id", eleve_id).execute()

    return competence


# ---------------------------------------------------------------------------
# Backend JSON local (repli si Supabase non configuré)
# ---------------------------------------------------------------------------

def _json_charger() -> None:
    global _charge
    if _charge:
        return
    PROGRESS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if PROGRESS_DB_PATH.exists():
        try:
            data = json.loads(PROGRESS_DB_PATH.read_text(encoding="utf-8"))
            for eleve_id, payload in data.items():
                _cache[eleve_id] = EleveProgress(**payload)
        except Exception as e:
            print(f"[Progress] Erreur de lecture de {PROGRESS_DB_PATH} : {e}")
    _charge = True


def _json_sauvegarder() -> None:
    PROGRESS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = {eleve_id: json.loads(p.model_dump_json()) for eleve_id, p in _cache.items()}
    PROGRESS_DB_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def _json_get_progression(eleve_id: str, classe: str, serie: Optional[str]) -> EleveProgress:
    _json_charger()
    with _lock:
        if eleve_id not in _cache:
            _cache[eleve_id] = EleveProgress(eleve_id=eleve_id, classe=classe, serie=serie)
        else:
            _cache[eleve_id].classe = classe
            _cache[eleve_id].serie = serie
        return _cache[eleve_id]


def _json_enregistrer_progres(eleve_id: str, classe: str, serie: Optional[str], domaine: str, a_progresse: bool) -> CompetenceProgress:
    _json_charger()
    with _lock:
        eleve = _json_get_progression(eleve_id, classe, serie)
        competence = eleve.get_or_create_competence(domaine)
        competence.nb_sessions += 1
        competence.dernier_travail = datetime.now(timezone.utc)
        if a_progresse:
            increment = 0.15 * (1 - competence.niveau_maitrise)
            competence.niveau_maitrise = min(1.0, round(competence.niveau_maitrise + increment, 3))
        eleve.total_sessions += 1
        _json_sauvegarder()
        return competence


# ---------------------------------------------------------------------------
# API publique (dispatch Supabase / JSON local)
# ---------------------------------------------------------------------------

def get_progression(eleve_id: str, classe: str, serie: Optional[str] = None) -> EleveProgress:
    if USE_SUPABASE:
        return _supabase_get_progression(eleve_id, classe, serie)
    return _json_get_progression(eleve_id, classe, serie)


def enregistrer_progres(eleve_id: str, classe: str, serie: Optional[str], domaine: str, a_progresse: bool = True) -> CompetenceProgress:
    if USE_SUPABASE:
        return _supabase_enregistrer_progres(eleve_id, classe, serie, domaine, a_progresse)
    return _json_enregistrer_progres(eleve_id, classe, serie, domaine, a_progresse)


def domaine_prioritaire(eleve_id: str, classe: str, serie: Optional[str], domaines_disponibles: list[str]) -> str:
    """Suggère le domaine le moins travaillé / le moins maîtrisé pour cet élève,
    afin de proposer un exercice pertinent selon sa progression."""
    eleve = get_progression(eleve_id, classe, serie)
    travailles = {c.domaine: c.niveau_maitrise for c in eleve.competences}

    non_abordes = [d for d in domaines_disponibles if d not in travailles]
    if non_abordes:
        return non_abordes[0]

    domaines_tries = sorted(domaines_disponibles, key=lambda d: travailles.get(d, 0.0))
    return domaines_tries[0] if domaines_tries else domaines_disponibles[0]


def resume_progression(eleve_id: str, classe: str, serie: Optional[str] = None) -> EleveProgress:
    return get_progression(eleve_id, classe, serie)
