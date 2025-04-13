import os
from typing import List
import fitz  # PyMuPDF
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()

# Чтение текста из PDF с ограничением по страницам
def extract_text_from_pdf(pdf_path: str, max_pages: int = None) -> List[str]:
    doc = fitz.open(pdf_path)
    chunks = []
    for i, page in enumerate(doc):
        if max_pages is not None and i >= max_pages:
            break
        text = page.get_text().strip()
        if text:
            chunks.append(text)
    return chunks

# Получение эмбеддингов из OpenAI
def embed_chunks(chunks: List[str]) -> List[List[float]]:
    response = client.embeddings.create(
        model="text-embedding-3-large",
        input=chunks
    )
    return [e.embedding for e in response.data]

# Получение эмбеддинга для запроса
def embed_query(query: str) -> List[float]:
    response = client.embeddings.create(
        model="text-embedding-3-large",
        input=[query]
    )
    return response.data[0].embedding

# Косинусное сходство
def cosine_similarity(a: List[float], b: List[float]) -> float:
    import numpy as np
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

# Получение релевантного контекста
def get_top_k_context(chunks: List[str], vectors: List[List[float]], query_embedding: List[float], k=5) -> str:
    scored = [(text, cosine_similarity(vec, query_embedding)) for text, vec in zip(chunks, vectors)]
    top = sorted(scored, key=lambda x: x[1], reverse=True)[:k]
    return "\n\n".join([text for text, _ in top])

# Главная функция с параметром max_pages
def ask_ai_from_pdf(pdf_path: str, question: str, max_pages: int = None) -> str:
    chunks = extract_text_from_pdf(pdf_path, max_pages=max_pages)
    chunk_vectors = embed_chunks(chunks)
    query_vector = embed_query(question)
    context = get_top_k_context(chunks, chunk_vectors, query_vector)

    system_prompt = f"""
    You are a helpful assistant that answers questions based on the provided context.
Use only the information from the context to answer questions. If you're unsure or the context
doesn't contain the relevant information, say so

Контекст:
{context}
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.7
    )

    return response.choices[0].message.content.strip()




# from typing import List
# import numpy as np
# import os
# from dotenv import load_dotenv
# from openai import OpenAI
# from docling.chunking import HybridChunker
# from docling.document_converter import DocumentConverter
# from utils.tokenizer import OpenAITokenizerWrapper

# load_dotenv()
# client = OpenAI()
# tokenizer = OpenAITokenizerWrapper()
# MAX_TOKENS = 8191


# def get_embedding(text: str) -> List[float]:
#     response = client.embeddings.create(
#         model="text-embedding-3-small",
#         input=text,
#     )
#     return response.data[0].embedding


# def cosine_similarity(a: List[float], b: List[float]) -> float:
#     a = np.array(a)
#     b = np.array(b)
#     return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


# def ask_from_pdf(pdf_path: str, question: str, top_k: int = 5) -> str:
#     # 1. Конвертация PDF → текст
#     converter = DocumentConverter()
#     result = converter.convert(pdf_path)

#     # 2. Чанкинг текста
#     chunker = HybridChunker(tokenizer=tokenizer, max_tokens=MAX_TOKENS, merge_peers=True)
#     chunks = list(chunker.chunk(dl_doc=result.document))
#     texts = [chunk.text for chunk in chunks]

#     # 3. Эмбеддинги
#     chunk_embeddings = [get_embedding(text) for text in texts]
#     question_embedding = get_embedding(question)

#     # 4. Поиск релевантных чанков
#     similarities = [cosine_similarity(question_embedding, emb) for emb in chunk_embeddings]
#     top_indices = np.argsort(similarities)[-top_k:][::-1]
#     context = "\n\n".join([texts[i] for i in top_indices])

#     # 5. Ответ от GPT
#     system_prompt = f"""You are a helpful assistant that answers questions based on the provided context.
# Use only the information from the context to answer questions. If you're unsure or the context doesn't contain the relevant information, say so.

# Context:
# {context}
# """
#     messages = [
#         {"role": "system", "content": system_prompt},
#         {"role": "user", "content": question}
#     ]

#     response = client.chat.completions.create(
#         model="gpt-4o-mini",
#         messages=messages,
#         temperature=0.7
#     )

#     return response.choices[0].message.content.strip()






# from typing import List
# import os
# import lancedb
# from docling.chunking import HybridChunker
# from docling.document_converter import DocumentConverter
# from dotenv import load_dotenv
# from lancedb.embeddings import get_registry
# from lancedb.pydantic import LanceModel, Vector
# from openai import OpenAI
# from utils.tokenizer import OpenAITokenizerWrapper

# load_dotenv()

# class DoclingQA:
#     def __init__(self, pdf_path: str, db_path: str = "data/lancedb", table_name: str = "docling"):
#         self.pdf_path = pdf_path
#         self.db_path = db_path
#         self.table_name = table_name
#         self.tokenizer = OpenAITokenizerWrapper()
#         self.client = OpenAI()
#         self.MAX_TOKENS = 8191
#         self.func = get_registry().get("openai").create(name="text-embedding-3-large")

#         self.db = lancedb.connect(self.db_path)
#         self._prepare_table()
#         self.table = self.db.open_table(self.table_name)

#     def _prepare_table(self):
#         converter = DocumentConverter()
#         result = converter.convert(self.pdf_path)

#         chunker = HybridChunker(
#             tokenizer=self.tokenizer,
#             max_tokens=self.MAX_TOKENS,
#             merge_peers=True,
#         )
#         chunks = list(chunker.chunk(dl_doc=result.document))

#         class ChunkMetadata(LanceModel):
#             filename: str | None
#             page_numbers: List[int] | None
#             title: str | None

#         class Chunks(LanceModel):
#             text: str = self.func.SourceField()
#             vector: Vector(self.func.ndims()) = self.func.VectorField()  # type: ignore
#             metadata: ChunkMetadata

#         processed_chunks = [
#             {
#                 "text": chunk.text,
#                 "metadata": {
#                     "filename": chunk.meta.origin.filename,
#                     "page_numbers": list(sorted({prov.page_no for item in chunk.meta.doc_items for prov in item.prov})) or None,
#                     "title": chunk.meta.headings[0] if chunk.meta.headings else None,
#                 },
#             }
#             for chunk in chunks
#         ]

#         self.db.create_table(self.table_name, schema=Chunks, mode="overwrite")
#         table = self.db.open_table(self.table_name)
#         table.add(processed_chunks)

#     def _get_context(self, query: str, num_results: int = 5) -> str:
#         results = self.table.search(query).limit(num_results).to_pandas()
#         contexts = []

#         for _, row in results.iterrows():
#             metadata = row.get("metadata", {})
#             filename = metadata.get("filename", "")
#             page_numbers = metadata.get("page_numbers", [])
#             title = metadata.get("title", "")

#             source_parts = []
#             if filename:
#                 source_parts.append(filename)
#             if page_numbers:
#                 source_parts.append(f"p. {', '.join(str(p) for p in page_numbers)}")

#             source = f"\nSource: {' - '.join(source_parts)}"
#             if title:
#                 source += f"\nTitle: {title}"

#             contexts.append(f"{row['text']}{source}")

#         return "\n\n".join(contexts)

#     def ask(self, user_input: str) -> str:
#         context = self._get_context(user_input)

#         system_prompt = f"""You are a helpful assistant that answers questions based on the provided context.
# Use only the information from the context to answer questions. If you're unsure or the context
# doesn't contain the relevant information, say so.

# Context:
# {context}
# """

#         messages = [
#             {"role": "system", "content": system_prompt},
#             {"role": "user", "content": user_input}
#         ]

#         response = self.client.chat.completions.create(
#             model="gpt-4o-mini",
#             messages=messages,
#             temperature=0.7
#         )

#         return response.choices[0].message.content.strip()