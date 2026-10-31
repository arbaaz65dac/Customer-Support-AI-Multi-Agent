from pydantic import BaseModel, Field


class RAGRequest(BaseModel):
    # The question to answer using the support knowledge base.
    question: str = Field(min_length=1, max_length=2000)


class RAGCitation(BaseModel):
    source: str
    policy: str
    version: str
    effective_date: str
    excerpt: str


class RAGResponse(BaseModel):
    # The generated answer based on retrieved documents.
    answer: str

    # Filenames of the documents used as evidence.
    sources: list[str]

    # Evidence excerpts paired with versioned source metadata.
    citations: list[RAGCitation] = Field(default_factory=list)

    # Number of chunks passed to the model.
    retrieved_chunks: int

    # Chroma distance scores for debugging retrieval quality.
    # These are distances, not confidence percentages.
    retrieval_distances: list[float] = Field(default_factory=list)