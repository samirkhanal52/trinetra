import logging

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_community.chat_models import ChatOllama

import src.config as config

RAG_PROMPT_TEMPLATE = """
**Persona:** You are an AI assistant with a perfect memory, answering questions based on a user's past screen activity.

**Objective:** Use the following retrieved "Action Logs" to answer the user's question. Your answer must be based *only* on the provided context. If the context is insufficient, say so. Do not make up information. Synthesize the logs into a coherent, human-readable response.

**Context from Action Logs:**
{context}

**User's Question:**
{question}

**Answer:**
"""


def query_trinetra(question: str):
    """
    Performs a RAG query against the user's indexed activity.
    """
    logging.info(f"Received query: {question}")

    # 1. Initialize components
    llm = ChatOllama(
        model="llama3.2",
        base_url="http://host.docker.internal:11434",
        temperature=0.1
    )
    embedding_model = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    vector_store = Chroma(
        persist_directory=config.CHROMA_DB_PATH, embedding_function=embedding_model
    )
    retriever = vector_store.as_retriever(
        search_kwargs={"k": 10}
    )  # Retrieve top 10 most relevant docs
    prompt = ChatPromptTemplate.from_template(RAG_PROMPT_TEMPLATE)

    # 2. Construct the RAG chain using LangChain Expression Language (LCEL)
    rag_chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    logging.info("Invoking RAG chain...")
    response = rag_chain.invoke(question)

    return response
