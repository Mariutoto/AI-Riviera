import streamlit as st

from app.answer import answer_from_sources, llm_status
from app.config import CHUNKS_PATH, DOCUMENTS_ROOT, INDEX_DIR
from app.ingest import build_index
from app.retrieval import load_chunks, search


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

    if not CHUNKS_PATH.exists():
        with st.spinner("Je crée l'index pour la première fois..."):
            build_index()
            load_chunks.cache_clear()

    results = search(question, limit=6)
    answer = answer_from_sources(question, results)

    with st.chat_message("assistant"):
        st.markdown(answer)

        if results:
            st.divider()
            st.subheader("Sources")
            for index, result in enumerate(results, start=1):
                metadata = result["metadata"]
                filename = metadata.get("filename", result.get("relative_text_path", "document"))
                year = metadata.get("year", "")
                category = metadata.get("category", "")
                pdf_url = metadata.get("pdf_url", "")
                label = f"{index}. {filename} — {year} / {category}"
                with st.expander(label):
                    if pdf_url:
                        st.markdown(f"[Ouvrir le PDF source]({pdf_url})")
                    st.code(result["text"][:1800], language="text")

    st.session_state.messages.append({"role": "assistant", "content": answer})
