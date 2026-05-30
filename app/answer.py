import os

import requests


SYSTEM_PROMPT = """Tu es AI Riviera, un assistant civique.
Réponds uniquement avec les extraits fournis. Si les sources ne permettent pas de répondre, dis-le clairement.
Pour une question générale ou de synthèse, utilise les extraits comme échantillon documentaire: donne une réponse utile, mentionne les grandes catégories observées, et précise les limites au lieu de répondre seulement que c'est impossible.
Réponds en français, de façon concise, et cite les noms de documents pertinents."""


def get_secret(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value:
        return value

    try:
        import streamlit as st

        value = st.secrets.get(name)
        if value:
            return str(value)
    except Exception:
        pass

    return default


def build_context(results: list[dict]) -> str:
    blocks = []
    for index, result in enumerate(results, start=1):
        metadata = result["metadata"]
        title = metadata.get("filename", result.get("relative_text_path", "document"))
        year = metadata.get("year", "")
        category = metadata.get("category", "")
        blocks.append(
            f"[Source {index}] {title} | {year} | {category}\n"
            f"{result['text']}"
        )
    return "\n\n---\n\n".join(blocks)


def answer_with_openai(question: str, results: list[dict]) -> str | None:
    api_key = get_secret("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model=get_secret("OPENAI_MODEL", "gpt-4.1-mini"),
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Question:\n{question}\n\n"
                        f"Extraits disponibles:\n{build_context(results)}"
                    ),
                },
            ],
        )
        return response.output_text
    except Exception as exc:
        return f"Je n'ai pas pu appeler OpenAI pour générer une synthèse: {exc}"


def answer_with_mistral(question: str, results: list[dict]) -> str | None:
    api_key = get_secret("MISTRAL_API_KEY")
    if not api_key:
        return None

    try:
        model = get_secret("MISTRAL_MODEL", "mistral-small-latest")
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"Question:\n{question}\n\n"
                            f"Extraits disponibles:\n{build_context(results)}"
                        ),
                    },
                ],
                "temperature": 0.2,
            },
            timeout=45,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as exc:
        return f"Je n'ai pas pu appeler Mistral pour générer une synthèse: {exc}"


def test_mistral_connection() -> tuple[bool, str]:
    api_key = get_secret("MISTRAL_API_KEY")
    if not api_key:
        return False, "MISTRAL_API_KEY n'est pas visible par l'application."

    model = get_secret("MISTRAL_MODEL", "mistral-small-latest")
    try:
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": "Réponds seulement: OK"}],
                "max_tokens": 8,
                "temperature": 0,
            },
            timeout=30,
        )
        if not response.ok:
            return False, f"Mistral a répondu {response.status_code}: {response.text[:500]}"

        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return True, f"Connexion Mistral OK avec `{model}`. Réponse: {content}"
    except Exception as exc:
        return False, f"Erreur pendant le test Mistral: {exc}"


def answer_with_llm(question: str, results: list[dict]) -> str | None:
    provider = get_secret("LLM_PROVIDER", "auto").lower().strip()

    if provider == "mistral":
        return answer_with_mistral(question, results)
    if provider == "openai":
        return answer_with_openai(question, results)
    if provider in {"none", "off", "extracts"}:
        return None

    return answer_with_mistral(question, results) or answer_with_openai(question, results)


def llm_status() -> dict:
    provider = get_secret("LLM_PROVIDER", "auto").lower().strip()
    has_mistral = bool(get_secret("MISTRAL_API_KEY"))
    has_openai = bool(get_secret("OPENAI_API_KEY"))

    if provider == "mistral":
        active = "mistral" if has_mistral else "missing MISTRAL_API_KEY"
    elif provider == "openai":
        active = "openai" if has_openai else "missing OPENAI_API_KEY"
    elif provider in {"none", "off", "extracts"}:
        active = "extracts only"
    elif has_mistral:
        active = "mistral"
    elif has_openai:
        active = "openai"
    else:
        active = "extracts only"

    return {
        "provider": provider,
        "active": active,
        "has_mistral_key": has_mistral,
        "has_openai_key": has_openai,
        "mistral_model": get_secret("MISTRAL_MODEL", "mistral-small-latest"),
        "openai_model": get_secret("OPENAI_MODEL", "gpt-4.1-mini"),
    }


def answer_from_sources(question: str, results: list[dict]) -> str:
    ai_answer = answer_with_llm(question, results)
    if ai_answer:
        return ai_answer

    if not results:
        return "Je n'ai pas trouvé de passage pertinent dans les documents indexés."

    lines = [
        "J'ai trouvé ces passages pertinents. Ajoute une clé Mistral ou OpenAI plus tard si tu veux une synthèse rédigée automatiquement.",
        "",
    ]
    for index, result in enumerate(results[:3], start=1):
        metadata = result["metadata"]
        filename = metadata.get("filename", result.get("relative_text_path", "document"))
        year = metadata.get("year", "")
        excerpt = result["text"][:650].strip().replace("\n", " ")
        lines.append(f"{index}. {filename} ({year})")
        lines.append(f"   {excerpt}...")
    return "\n".join(lines)
