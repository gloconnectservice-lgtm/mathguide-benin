"""
Modèles de données (Pydantic) de MathGuide Bénin.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant" | "system"
    content: str


class ChatRequest(BaseModel):
    session_id: str
    eleve_id: str = "eleve_defaut"
    classe: str
    serie: Optional[str] = None
    message: str
    historique: List[ChatMessage] = Field(default_factory=list)
    image_description: Optional[str] = None  # texte OCR + description de figure, si fourni


class ChatResponse(BaseModel):
    reponse: str
    sources_rag: List[str] = Field(default_factory=list)
    competence_detectee: Optional[str] = None


class OCRResult(BaseModel):
    texte_extrait: str
    description_figure: Optional[str] = None
    confiance: Optional[float] = None


class ExerciceRequest(BaseModel):
    eleve_id: str = "eleve_defaut"
    classe: str
    serie: Optional[str] = None
    domaine: Optional[str] = None  # si non fourni, choisi selon la progression


class Exercice(BaseModel):
    id: str
    classe: str
    serie: Optional[str] = None
    domaine: str
    enonce: str


class CompetenceProgress(BaseModel):
    domaine: str
    nb_sessions: int = 0
    dernier_travail: Optional[datetime] = None
    niveau_maitrise: float = 0.0  # 0.0 -> 1.0, estimation heuristique


class EleveProgress(BaseModel):
    eleve_id: str
    classe: str
    serie: Optional[str] = None
    competences: List[CompetenceProgress] = Field(default_factory=list)
    total_sessions: int = 0

    def get_or_create_competence(self, domaine: str) -> CompetenceProgress:
        for c in self.competences:
            if c.domaine == domaine:
                return c
        c = CompetenceProgress(domaine=domaine)
        self.competences.append(c)
        return c


class ProgressUpdateRequest(BaseModel):
    eleve_id: str = "eleve_defaut"
    classe: str
    serie: Optional[str] = None
    domaine: str
    a_progresse: bool = True  # heuristique simple : l'échange a fait avancer l'élève
