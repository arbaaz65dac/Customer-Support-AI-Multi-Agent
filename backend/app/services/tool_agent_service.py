from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_groq import ChatGroq
from sqlalchemy.orm import Session

from app.core.config import GROQ_API_KEY, GROQ_MODEL
from app.services.agent_tools import create_support_tools


def answer_with_tools(message: str, db: Session) -> str:
    """
    Let the LLM request approved tools, execute those tools in Python,
    and use the results to generate a final answer.
    """

    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not configured")

    # Create the explicitly allowed tool list for this request.
    tools = create_support_tools(db)

    # Map tool names to their actual Python implementations.
    tools_by_name = {item.name: item for item in tools}

    llm = ChatGroq(
        model=GROQ_MODEL,
        temperature=0,
        max_tokens=500,
        api_key=GROQ_API_KEY,
        timeout=30,
        max_retries=1,
    )

    # Bind tool descriptions to the model.
    # Binding describes available tools; it doesn't execute them.
    llm_with_tools = llm.bind_tools(tools)

    messages = [
        SystemMessage(
            content=(
                "You are a customer support assistant. "
                "Use the provided tools when product or order data is needed. "
                "Base factual product and order claims on tool results. "
                "If a tool reports no match, say you could not find the record. "
                "Never claim to have performed an action that was not executed. "
                "Do not request or expose passwords, API keys, or other secrets."
            )
        ),
        HumanMessage(content=message),
    ]

    # Limit tool-calling rounds to prevent an endless loop.
    max_rounds = 3

    for _ in range(max_rounds):
        # Ask the model for either a final answer or tool calls.
        ai_message = llm_with_tools.invoke(messages)
        messages.append(ai_message)

        # No tool call means the model has produced its final response.
        if not ai_message.tool_calls:
            if isinstance(ai_message.content, str) and ai_message.content.strip():
                return ai_message.content.strip()

            raise RuntimeError("The model returned an empty response")

        # Execute only the tool names explicitly registered above.
        for tool_call in ai_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_call_id = tool_call["id"]

            selected_tool = tools_by_name.get(tool_name)

            if selected_tool is None:
                # Never execute an unregistered tool.
                tool_result = "Error: requested tool is not permitted."
            else:
                try:
                    tool_result = selected_tool.invoke(tool_args)
                except Exception:
                    # Don't expose database or internal errors to the model.
                    tool_result = (
                        "Error: the requested lookup could not be completed."
                    )

            # Send the result back in the format expected by LangChain.
            messages.append(
                ToolMessage(
                    content=str(tool_result),
                    tool_call_id=tool_call_id,
                )
            )

    raise RuntimeError("The assistant exceeded the tool-calling limit")