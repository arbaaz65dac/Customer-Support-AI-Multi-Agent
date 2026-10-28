from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from app.core.config import GROQ_API_KEY, GROQ_MODEL
from app.schemas.chat import ChatAssistantResponse


def generate_structured_answer(message: str) -> ChatAssistantResponse:
    """Generate a customer-support response with validated fields."""

    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not configured")

    # Tell the model what it should do and how to choose an intent.
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
                You are a customer-support assistant.

                Classify the user's primary intent using these definitions:
                - general_question: general help or greetings
                - product_search: finding or comparing products
                - order_status: asking about an existing order
                - create_ticket: explicitly asking to raise or create a ticket
                - policy_question: asking about company policies
                - unknown: intent is unclear

                Choose a suggested action that matches the intent:
                - product_search -> search_products
                - order_status -> check_order
                - create_ticket -> create_support_ticket
                - policy_question -> retrieve_policy
                - general_question or unknown -> none

                Answer politely and concisely.
                Do not claim to have checked an order, searched a catalogue,
                created a ticket, or retrieved a policy.
                Suggesting an action does not mean it has been executed.
                If company-specific information is not provided, say so
                instead of inventing it.
                """,
            ),
            (
                "human",
                "Classify this user message and answer it:\n{message}",
            ),
        ]
    )

    # Configure the model.
    llm = ChatGroq(
        model=GROQ_MODEL,
        temperature=0,
        max_tokens=500,
        api_key=GROQ_API_KEY,
        timeout=30,
        max_retries=1,
    )

    # Ask LangChain to parse the response into our Pydantic schema.
    # The returned value should be a ChatAssistantResponse instance.
    structured_llm = llm.with_structured_output(ChatAssistantResponse)

    # Compose prompt -> structured LLM output.
    chain = prompt | structured_llm

    # Invoke the chain with the user's message.
    result = chain.invoke({"message": message})

    # Defensive check: don't let an unexpected object pass through.
    if not isinstance(result, ChatAssistantResponse):
        raise RuntimeError("The model returned an unexpected response format")

    return result