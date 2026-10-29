
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_groq import ChatGroq
from sqlalchemy.orm import Session

from app.core.config import GROQ_API_KEY, GROQ_MODEL
from app.services.agent_tools import create_support_tools


def answer_with_tools(message: str, db: Session) -> str:
    """
    Answer a customer question using approved support tools.

    Workflow:
    1. Ask the model which tool, if any, should be called.
    2. Execute the requested tool using the database session.
    3. Give the tool results to a fresh, text-only model request.
    4. Return the final customer-facing answer.
    """

    # Ensure the Groq API key is configured.
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not configured")

    # Create the tools with access to the current database session.
    tools = create_support_tools(db)
    tools_by_name = {tool.name: tool for tool in tools}

    # Model used for both tool selection and final answer generation.
    llm = ChatGroq(
        model=GROQ_MODEL,
        temperature=0,
        max_tokens=500,
        api_key=GROQ_API_KEY,
        timeout=30,
        max_retries=1,
    )

    # Bind the approved tools to the model for the first request.
    llm_with_tools = llm.bind_tools(tools)

    # Keep the tool-selection prompt focused on permitted actions.
    system_prompt = """
You are a customer support assistant.

Use the available tools when the customer asks for product information
or order-related information that requires a lookup.

Rules:
- Call only tools that are available to you.
- Provide tool arguments that match the tool's schema.
- Do not invent products, prices, stock, or order information.
- If a tool returns no matching results, report that clearly.
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=message),
    ]

    # Limit tool calls to prevent repeated calls or endless loops.
    max_total_tool_calls = 4
    total_tool_calls = 0
    tool_results = []

    # Request tool selection once. The model may request multiple tools
    # in the same response, subject to the overall tool-call limit.
    ai_message = llm_with_tools.invoke(messages)

    if not ai_message.tool_calls:
        # The model answered directly without requesting a tool.
        if isinstance(ai_message.content, str) and ai_message.content.strip():
            return ai_message.content.strip()

        raise RuntimeError("The model returned an empty response")

    # Execute each requested tool.
    for tool_call in ai_message.tool_calls:
        if total_tool_calls >= max_total_tool_calls:
            break

        total_tool_calls += 1

        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        selected_tool = tools_by_name.get(tool_name)

        if selected_tool is None:
            # Never execute tools that are not explicitly approved.
            tool_result = "Error: requested tool is not permitted."
        else:
            try:
                tool_result = selected_tool.invoke(tool_args)
            except Exception as exc:
                # Avoid returning internal exception details to the customer.
                print(f"Tool execution failed: {type(exc).__name__}")
                tool_result = (
                    "Error: the requested lookup could not be completed."
                )

        # Save results as plain text for final answer generation.
        tool_results.append(
            f"Tool name: {tool_name}\n"
            f"Tool result: {tool_result}"
        )

    if not tool_results:
        raise RuntimeError("No tool results were produced")

    # IMPORTANT:
    # Use a fresh conversation without the original AI tool-call message
    # or ToolMessage objects. This prevents the final request from
    # accidentally continuing the earlier tool-calling sequence.
    final_messages = [
        SystemMessage(
            content=(
                "You are a customer support assistant. "
                "Answer the customer's question using only the supplied "
                "tool results. Do not call tools, invent facts, or claim "
                "that an action succeeded unless the results confirm it. "
                "If the results contain an error or no matching records, "
                "explain that clearly and politely. Keep the answer concise."
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

    # Call the unbound model with plain-text messages only.
    final_response = llm.invoke(final_messages)

    if isinstance(final_response.content, str):
        answer = final_response.content.strip()

        if answer:
            return answer

    raise RuntimeError("The model returned an empty final answer")
