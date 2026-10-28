# Import LangChain's Groq chat model integration.
from langchain_groq import ChatGroq

# Import a reusable prompt template.
from langchain_core.prompts import ChatPromptTemplate

# Convert the model's message object into plain text.
from langchain_core.output_parsers import StrOutputParser

# Read the configuration from our existing config module.
from app.core.config import GROQ_API_KEY, GROQ_MODEL


def generate_answer(message: str) -> str:
    """
    Send a user's message to the configured LLM
    and return the generated response as plain text.
    """

    # Fail early with a clear message if configuration is missing.
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not configured")

    # Create the model when needed, rather than during module import.
    # This also makes the service easier to test.
    llm = ChatGroq(
        model=GROQ_MODEL,
        temperature=0.2,
        max_tokens=500,
        api_key=GROQ_API_KEY,
        timeout=30,
        max_retries=1,
    )

    # Define the assistant's role and the user's message.
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a helpful customer support assistant. "
                "Give clear, polite, concise answers. "
                "Do not claim to have accessed customer accounts, "
                "orders, or company policies unless evidence is "
                "provided in the conversation.",
            ),
            ("human", "{user_message}"),
        ]
    )

    # Compose prompt -> LLM -> plain-text output.
    chain = prompt | llm | StrOutputParser()

    # Invoke the chain with the user's message.
    answer = chain.invoke({"user_message": message})

    # Avoid returning an empty result to the API caller.
    if not answer or not answer.strip():
        raise RuntimeError("The LLM returned an empty response")

    return answer.strip()