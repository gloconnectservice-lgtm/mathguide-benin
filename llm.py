"""
Client LLM générique de MathGuide Bénin.
Compatible xAI (Grok), OpenAI, Mistral et tout endpoint compatible avec le SDK `openai`,
via LLM_PROVIDER / LLM_BASE_URL / LLM_API_KEY / LLM_MODEL (voir config.py).
"""
from typing import List, Optional
from openai import AsyncOpenAI

from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
from app.prompts import SYSTEM_PROMPT, build_context_prefix
from app.models import ChatMessage

_client: Optional[AsyncOpenAI] = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
    return _client


async def generer_reponse(
    message: str,
    classe: str,
    serie: Optional[str],
    historique: List[ChatMessage],
    rag_context: Optional[str] = None,
    image_description: Optional[str] = None,
) -> str:
    """Génère la réponse socratique du tuteur, sans jamais donner la solution finale."""
    client = get_client()

    context_prefix = build_context_prefix(classe, serie, rag_context, image_description)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # historique de conversation (borné aux ~12 derniers messages pour rester léger)
    for m in historique[-12:]:
        messages.append({"role": m.role, "content": m.content})

    user_content = f"{context_prefix}\n\n[Message de l'élève] :\n{message}" if context_prefix else message
    messages.append({"role": "user", "content": user_content})

    response = await client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        temperature=0.6,
        max_tokens=900,
    )
    return response.choices[0].message.content or ""


async def generer_exercice(classe: str, serie: Optional[str], domaine: str, rag_context: Optional[str] = None) -> str:
    """Génère l'énoncé d'un nouvel exercice adapté au niveau et à la compétence ciblée."""
    client = get_client()

    consigne = (
        f"Propose UN SEUL énoncé d'exercice de mathématiques adapté à la classe de {classe}"
        + (f" (série {serie})" if serie else "")
        + f", sur le domaine « {domaine} », conforme au programme officiel béninois.\n"
        "Donne uniquement l'énoncé (pas de solution, pas d'indice). "
        "Formate-le clairement, avec les données nécessaires."
    )
    if rag_context:
        consigne += f"\n\nExtraits du programme officiel à respecter :\n{rag_context}"

    response = await client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": "Tu es un professeur de mathématiques béninois qui rédige des énoncés d'exercices, sans jamais fournir de solution."},
            {"role": "user", "content": consigne},
        ],
        temperature=0.8,
        max_tokens=400,
    )
    return response.choices[0].message.content or ""
