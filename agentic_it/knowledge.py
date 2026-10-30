from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

from .config import KNOWLEDGE_DIR
from .config import API_KEY, MODEL

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


def _tokens(text: str) -> list[str]:
    text = text.lower().replace("ı", "i").replace("ğ", "g").replace("ş", "s").replace("ç", "c").replace("ö", "o").replace("ü", "u")
    stopwords = {"a", "an", "and", "are", "as", "at", "but", "by", "can", "do", "for", "from", "get", "how", "i", "in", "is", "it", "me", "my", "of", "on", "or", "should", "the", "to", "was", "we", "what", "when", "with", "you", "your", "ve", "veya", "bir", "bu", "da", "de", "mi", "mu", "ne", "icin", "için", "sonra", "ama", "ve", "ben", "benim", "biraz"}
    return [token for token in re.findall(r"[a-z0-9]+", text) if token not in stopwords]


@dataclass
class Chunk:
    source: str
    section: str
    text: str
    tokens: list[str]


class KnowledgeBase:
    """Small transparent BM25-like local retriever; no external vector service required."""

    def __init__(self, folder: Path = KNOWLEDGE_DIR):
        self.folder = folder
        self.chunks: list[Chunk] = []
        self.vectors: list[list[float]] = []
        self.embedding_client = OpenAI(api_key=API_KEY) if API_KEY and OpenAI else None
        self.reload()

    def reload(self) -> None:
        chunks: list[Chunk] = []
        for path in sorted(self.folder.glob("*.md")):
            section, body = path.stem, []
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.startswith("## "):
                    if body:
                        text = "\n".join(body).strip()
                        if text:
                            chunks.append(Chunk(path.name, section, text, _tokens(f"{section}\n{text}")))
                    section, body = line[3:].strip(), []
                elif line.startswith("# "):
                    section = line[2:].strip()
                elif line.strip():
                    body.append(line.strip())
            if body:
                text = "\n".join(body).strip()
                if text:
                    chunks.append(Chunk(path.name, section, text, _tokens(f"{section}\n{text}")))
        self.chunks = chunks
        self.vectors = []
        if self.embedding_client and self.chunks:
            try:
                response = self.embedding_client.embeddings.create(
                    model="text-embedding-3-small",
                    input=[f"{chunk.section}\n{chunk.text}" for chunk in self.chunks],
                )
                self.vectors = [item.embedding for item in response.data]
            except Exception:
                # Lexical retrieval remains available if embeddings are unavailable.
                self.vectors = []

    def search(self, query: str, top_k: int = 4) -> list[dict[str, str | float]]:
        query_terms = set(_tokens(query))
        if not query_terms or not self.chunks:
            return []
        n = len(self.chunks)
        scored = []
        query_vector: list[float] | None = None
        if self.embedding_client and self.vectors:
            try:
                query_vector = self.embedding_client.embeddings.create(
                    model="text-embedding-3-small", input=[query]
                ).data[0].embedding
            except Exception:
                query_vector = None
        for chunk in self.chunks:
            terms = chunk.tokens
            length = max(1, len(terms))
            score = 0.0
            for term in query_terms:
                tf = terms.count(term)
                if tf:
                    df = sum(1 for other in self.chunks if term in other.tokens)
                    idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
                    score += idf * (tf * 2.2) / (tf + 1.2 * (0.25 + 0.75 * length / 90))
            if query_vector is not None:
                index = self.chunks.index(chunk)
                vector = self.vectors[index]
                dot = sum(a * b for a, b in zip(query_vector, vector))
                qnorm = math.sqrt(sum(a * a for a in query_vector)) or 1
                vnorm = math.sqrt(sum(a * a for a in vector)) or 1
                semantic = max(0.0, dot / (qnorm * vnorm))
                # Normalize BM25 to 0..1, then blend lexical and semantic retrieval.
                score = 0.45 * (score / (score + 2.0)) + 0.55 * semantic
            if score:
                scored.append((score, chunk))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [{"source": c.source, "section": c.section, "text": c.text, "score": round(score, 3)}
                for score, c in scored[:top_k]]

    def all_sources(self) -> list[dict[str, str]]:
        return [{"name": path.name, "content": path.read_text(encoding="utf-8")}
                for path in sorted(self.folder.glob("*.md"))]

