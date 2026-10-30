
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from sqlalchemy.orm import Session

from app.core.config import GROQ_API_KEY, GROQ_MODEL
from app.services.agent_tools import create_support_tools


def answer_with_tools(
    message: str,
    db: Session,
    trusted_customer_id: int | None = None,
) -> str:
    """
    Answer a customer question using approved support tools.

    trusted_customer_id must come from trusted application context,
    never from the LLM or free-form customer input.
    """

    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not configured")

    # Create tools with the trusted customer identity, if available.
    tools = create_support_tools(
        db=db,
        trusted_customer_id=trusted_customer_id,
    )
    tools_by_name = {support_tool.name: support_tool for support_tool in tools}

    llm = ChatGroq(
        model=GROQ_MODEL,
        temperature=0,
        max_tokens=500,
        api_key=GROQ_API_KEY,
        timeout=30,
        max_retries=1,
    )

    llm_with_tools = llm.bind_tools(tools)

    system_prompt = """
You are a helpful customer support assistant.

Available tools:
- search_product_catalog: Search the product catalog and filter by price.
- lookup_order_status: Look up an order belonging to the authenticated customer.
- create_customer_support_ticket: Create a support ticket for the
  authenticated customer.

Rules:
1. Use search_product_catalog for product availability, product details,
   and product price questions that require a database lookup.
2. Use lookup_order_status when the customer asks about a specific order.
3. Use create_customer_support_ticket when the customer explicitly asks
   to raise, create, or register a support ticket, or requests that an
   issue be formally recorded for follow-up.
4. Do not create a ticket merely because the customer asks a general
   question or reports an issue without requesting formal follow-up.
5. Before creating a ticket, ensure the subject and description accurately
   reflect the customer's issue. Do not invent missing details.
6. Never supply or infer a customer ID. Customer identity is provided
   only through trusted application context.
7. Never invent products, prices, stock, order details, or ticket IDs.
8. Report ticket creation as successful only when the tool result confirms
   success. If it fails, explain that the ticket could not be created.
9. If a required lookup or ticket creation needs authentication and no
   trusted customer identity is available, explain that authentication
   is required.
10. Keep responses concise, polite, and relevant.
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=message),
    ]

    max_total_tool_calls = 4
    total_tool_calls = 0
    tool_results = []

    # Ask the model whether a support tool is required.
    ai_message = llm_with_tools.invoke(messages)

    if not ai_message.tool_calls:
        if isinstance(ai_message.content, str) and ai_message.content.strip():
            return ai_message.content.strip()

        raise RuntimeError("The model returned an empty response")

    # Execute only the tools registered by the application.
    for tool_call in ai_message.tool_calls:
        if total_tool_calls >= max_total_tool_calls:
            break

        total_tool_calls += 1

        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        selected_tool = tools_by_name.get(tool_name)

        if selected_tool is None:
            tool_result = "Error: requested tool is not permitted."
        else:
            try:
                tool_result = selected_tool.invoke(tool_args)
            except Exception as exc:
                # Log the exception type without exposing internal details.
                print(f"Tool execution failed: {type(exc).__name__}")
                tool_result = (
                    "Error: the requested lookup could not be completed."
                )

        tool_results.append(
            f"Tool name: {tool_name}\n"
            f"Tool result: {tool_result}"
        )

    if not tool_results:
        raise RuntimeError("No tool results were produced")

    # Use a fresh, text-only conversation for the final response.
    final_messages = [
        SystemMessage(
            content=(
                "You are a customer support assistant. Answer using only "
                "the supplied tool results. Do not invent facts or claim "
                "an action succeeded unless the results confirm it. If a "
                "lookup fails or requires authentication, explain that "
                "clearly and politely. Keep the answer concise."
            )
        ),
        HumanMessage(
            content=(
                f"Customer question:\n{message}\n\n"
                "Results from the support tools:\n"
                f"{chr(10).join(tool_results)}\n\n"
                "Write the final customer-facing answer based only on "
                "the information above."
            )
        ),
    ]

    final_response = llm.invoke(final_messages)

    if isinstance(final_response.content, str):
        answer = final_response.content.strip()
        if answer:
            return answer

    raise RuntimeError("The model returned an empty final answer")
