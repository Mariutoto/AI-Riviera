import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.answer import answer_from_sources, llm_status, test_mistral_connection
from app.config import CHUNKS_PATH, DOCUMENTS_ROOT, INDEX_DIR
from app.ingest import build_index
from app.retrieval import load_chunks, search
from app.structured import answer_structured_question


st.set_page_config(page_title="AI Riviera", page_icon="🏛️", layout="wide")

st.title("AI Riviera")
st.caption("Chatbot local sur les documents communaux de La Tour-de-Peilz")

with st.sidebar:
    st.header("Documents")
    st.write(f"Dossier: `{DOCUMENTS_ROOT}`")
    status = llm_status()
    st.header("LLM")
    st.write(f"Provider: `{status['provider']}`")
    st.write(f"Actif: `{status['active']}`")
    st.write(f"Mistral key: `{'oui' if status['has_mistral_key'] else 'non'}`")
    st.write(f"OpenAI key: `{'oui' if status['has_openai_key'] else 'non'}`")
    if status["active"] == "mistral":
        st.write(f"Modèle: `{status['mistral_model']}`")
    elif status["active"] == "openai":
        st.write(f"Modèle: `{status['openai_model']}`")
    if st.button("Tester Mistral"):
        ok, message = test_mistral_connection()
        if ok:
            st.success(message)
        else:
            st.error(message)

    if st.button("Réindexer les documents"):
        load_chunks.cache_clear()
        with st.spinner("Indexation en cours..."):
            stats = build_index()
        st.success(f"{stats['documents_indexed']} documents, {stats['chunks_indexed']} passages indexés.")

    if CHUNKS_PATH.exists():
        st.success(f"Index prêt: `{CHUNKS_PATH}`")
        st.write(f"Dossier index: `{INDEX_DIR}`")
    else:
        st.warning("Aucun index trouvé. Clique sur Réindexer les documents.")


def documents_changed_after_index() -> bool:
    if not CHUNKS_PATH.exists():
        return True

    index_mtime = CHUNKS_PATH.stat().st_mtime
    for path in DOCUMENTS_ROOT.rglob("*.txt"):
        if path.stat().st_mtime > index_mtime:
            return True
    for path in DOCUMENTS_ROOT.rglob("*.json"):
        if path.stat().st_mtime > index_mtime:
            return True
    return False


def ensure_index_ready() -> None:
    if documents_changed_after_index():
        with st.spinner("Mise à jour de l'index des documents..."):
            build_index()
            load_chunks.cache_clear()


def group_results_by_document(results: list[dict]) -> list[dict]:
    grouped = {}
    for result in results:
        metadata = result["metadata"]
        document_key = (
            metadata.get("pdf_url")
            or metadata.get("text_path")
            or result.get("relative_text_path")
            or metadata.get("filename")
            or result["id"].split("#", 1)[0]
        )
        if document_key not in grouped:
            grouped[document_key] = {
                "metadata": metadata,
                "relative_text_path": result.get("relative_text_path", ""),
                "score": result.get("score", 0),
                "passages": [],
            }
        grouped[document_key]["score"] = max(grouped[document_key]["score"], result.get("score", 0))
        grouped[document_key]["passages"].append(result)
    return sorted(grouped.values(), key=lambda item: item["score"], reverse=True)


if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

question = st.chat_input("Pose une question sur les documents...")

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    ensure_index_ready()

    structured_answer = answer_structured_question(question)
    if structured_answer:
        results = []
        answer = structured_answer
    else:
        results = search(question, limit=14)
        answer = answer_from_sources(question, results)

    with st.chat_message("assistant"):
        st.markdown(answer)

        if results:
            st.divider()
            st.subheader("Sources")
            for index, source in enumerate(group_results_by_document(results), start=1):
                metadata = source["metadata"]
                filename = metadata.get("filename", source.get("relative_text_path", "document"))
                year = metadata.get("year", "")
                category = metadata.get("category", "")
                pdf_url = metadata.get("pdf_url", "")
                passages = source["passages"]
                passage_label = "passage" if len(passages) == 1 else "passages"
                label = f"{index}. {filename} — {year} / {category} ({len(passages)} {passage_label})"
                with st.expander(label):
                    if pdf_url:
                        st.markdown(f"[Ouvrir le PDF source]({pdf_url})")
                    for passage_index, passage in enumerate(passages[:3], start=1):
                        if len(passages) > 1:
                            st.caption(f"Passage {passage_index}")
                        st.code(passage["text"][:1800], language="text")

    st.session_state.messages.append({"role": "assistant", "content": answer})
