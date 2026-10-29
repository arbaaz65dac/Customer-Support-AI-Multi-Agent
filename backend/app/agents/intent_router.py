
import re

from app.agents.graph_state import AgentName, Intent


# Each intent has patterns that may indicate the customer's request.
# More specific intents should be checked before broader patterns.
INTENT_PATTERNS: dict[Intent, list[str]] = {
    "order_status": [
        r"\bwhere is my order\b",
        r"\btrack (?:my |an? )?order\b",
        r"\border status\b",
        r"\bdelivery status\b",
        r"\bwhen will my order arrive\b",
        r"\bwhen (?:will|can) (?:i )?receive my order\b",
        r"\bhas my order shipped\b",
        r"\bcheck my order\b",
    ],

    "product_search": [
        # Explicit product searches
        r"\bfind(?:\s+me)?(?:\s+(?:a|an))?\s+products?\b",
        r"\bsearch(?:\s+for)?(?:\s+(?:a|an))?\s+products?\b",
        r"\bshow(?:\s+me)?\s+(?:all\s+)?products?\b",
        r"\blist\s+(?:all\s+)?products?\b",

        # Natural-language product searches
        r"\bfind(?:\s+me)?\s+.+",
        r"\bsearch\s+for\s+.+",
        r"\blooking\s+for\s+.+",
        r"\bi\s+want\s+(?:to\s+buy\s+)?(?:a\s+|an\s+)?\w+",
        r"\bi\s+need\s+(?:a\s+|an\s+)?\w+",
        r"\bdo\s+you\s+have\s+.+",
        r"\bshow\s+me\s+.+",

        # Price-based searches
        r"\bproducts?\s+under\b",
        r"\bproducts?\s+below\b",
        r"\bproducts?\s+less\s+than\b",
        r"\bproducts?\s+below\s+or\s+equal\s+to\b",
        r"\bproducts?\s+within\s+(?:my\s+)?budget\b",
        r"\bunder\s+\d+(?:\.\d+)?\b",
        r"\bbelow\s+\d+(?:\.\d+)?\b",
        r"\b(?:cheapest|affordable|budget)\s+products?\b",

        # Availability and category searches
        r"\bavailable\s+products?\b",
        r"\bproducts?\s+available\b",
        r"\bshow\s+available\s+.+",
        r"\b(?:laptops?|phones?|mobiles?|mouse|mice|keyboards?|"
        r"headphones?|monitors?|chargers?|tablets?)\b",
    ],

    "create_ticket": [
        r"\bcreate\s+(?:a\s+)?support ticket\b",
        r"\bopen\s+(?:a\s+)?support ticket\b",
        r"\braise\s+(?:a\s+)?ticket\b",
        r"\bsubmit\s+(?:a\s+)?ticket\b",
        r"\bcontact support\b",
        r"\bneed help from support\b",
        r"\breport (?:an? )?issue\b",
        r"\bcomplaint\b",
    ],

    "policy_question": [
        r"\breturn policy\b",
        r"\brefund policy\b",
        r"\bdelivery policy\b",
        r"\bshipping policy\b",
        r"\bhow many days.*refund\b",
        r"\bwhat is the process for returning\b",
        r"\bhow (?:do|can) i return\b",
        r"\bhow (?:do|can) i get (?:a )?refund\b",
        r"\bwhat should i do if my delivery is late\b",
        r"\b(?:late|delayed) delivery\b",
        r"\bcan i return\b",
        r"\bcan i get a refund\b",
    ],
}


def classify_intent(question: str) -> Intent:
    """
    Classify a customer's question using deterministic keyword patterns.

    Returns:
        The matching intent, 'unknown' for empty input, or
        'general_question' when no pattern matches.
    """

    normalized = question.strip().lower()

    if not normalized:
        return "unknown"

    # Check order, product, ticket, and policy patterns.
    # Keep these patterns sufficiently specific to avoid false matches.
    for intent, patterns in INTENT_PATTERNS.items():
        if any(re.search(pattern, normalized) for pattern in patterns):
            return intent

    return "general_question"


def select_agent(intent: Intent) -> AgentName:
    """
    Select the agent responsible for the classified intent.
    """

    if intent == "policy_question":
        return "knowledge"

    if intent in {
        "product_search",
        "order_status",
        "create_ticket",
    }:
        return "product_order"

    return "general"
