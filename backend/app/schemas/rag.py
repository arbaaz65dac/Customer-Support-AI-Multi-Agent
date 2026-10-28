from pydantic import BaseModel, Field


class RAGRequest(BaseModel):
    # The question to answer using the support knowledge base.
    question: str = Field(min_length=1, max_length=2000)


class RAGResponse(BaseModel):
    # The generated answer based on retrieved documents.
    answer: str

    # Filenames of the documents used as evidence.
    sources: list[str]

    # Number of chunks passed to the model.
    retrieved_chunks: int