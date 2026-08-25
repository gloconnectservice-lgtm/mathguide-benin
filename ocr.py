"""
Module OCR de MathGuide Bénin.
Extrait le texte d'une image d'exercice (énoncé manuscrit ou imprimé) et
fournit une description sommaire de la figure éventuelle (géométrie, graphique...).
"""
import io
from typing import Optional
from PIL import Image

from app.config import OCR_ENGINE, OCR_LANGUAGES
from app.models import OCRResult

_easyocr_reader = None


def _get_easyocr_reader():
    global _easyocr_reader
    if _easyocr_reader is None:
        import easyocr
        _easyocr_reader = easyocr.Reader(OCR_LANGUAGES, gpu=False)
    return _easyocr_reader


def _extraire_avec_easyocr(image: Image.Image) -> tuple[str, float]:
    import numpy as np
    reader = _get_easyocr_reader()
    resultats = reader.readtext(np.array(image))
    if not resultats:
        return "", 0.0
    textes = [r[1] for r in resultats]
    confiances = [r[2] for r in resultats]
    confiance_moyenne = sum(confiances) / len(confiances) if confiances else 0.0
    return "\n".join(textes), confiance_moyenne


def _extraire_avec_tesseract(image: Image.Image) -> tuple[str, float]:
    import pytesseract
    texte = pytesseract.image_to_string(image, lang="fra")
    return texte.strip(), 0.0  # tesseract ne fournit pas de score simple ici


def _detecter_figure(image: Image.Image) -> Optional[str]:
    """Heuristique légère : signale la présence probable d'une figure géométrique
    (beaucoup de traits / peu de texte dense). Reste volontairement simple ;
    la description fine est laissée au LLM à partir du texte extrait + du contexte élève."""
    largeur, hauteur = image.size
    ratio = largeur / hauteur if hauteur else 1
    if ratio < 0.6 or ratio > 1.8:
        return None
    return (
        "L'image contient possiblement un schéma ou une figure géométrique en plus du texte "
        "(à confirmer avec l'élève si besoin)."
    )


def traiter_image(contenu_image: bytes) -> OCRResult:
    """Point d'entrée principal : bytes d'image -> texte + description."""
    image = Image.open(io.BytesIO(contenu_image)).convert("RGB")

    if OCR_ENGINE == "tesseract":
        texte, confiance = _extraire_avec_tesseract(image)
    else:
        texte, confiance = _extraire_avec_easyocr(image)

    description_figure = _detecter_figure(image) if len(texte) < 400 else None

    return OCRResult(
        texte_extrait=texte.strip() or "(aucun texte détecté — vérifie la netteté de la photo)",
        description_figure=description_figure,
        confiance=round(confiance, 2) if confiance else None,
    )
