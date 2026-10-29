
import re

from app.agents.graph_state import AgentName, Intent


# Keep specific intents ahead of product searches to avoid
# incorrectly routing policy or support questions.
INTENT_PATTERNS: dict[Intent, list[str]] = {
    "order_status": [
        r"\bwhere is my order\b",
        r"\btrack (?:my |the )?order\b",
        r"\border status\b",
        r"\bdelivery status\b",
        r"\bwhen will my order arrive\b",
        r"\bwhen (?:will|can) i receive my order\b",
        r"\bhas my order shipped\b",
        r"\bcheck my order\b",
    ],

    "create_ticket": [
        r"\bcreate (?:a )?(?:support )?ticket\b",
        r"\bopen (?:a )?(?:support )?ticket\b",
        r"\braise (?:a )?(?:support )?ticket\b",
        r"\bsubmit (?:a )?(?:support )?ticket\b",
        r"\bcontact support\b",
        r"\bwant to contact support\b",
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
        r"\bfind out\b.*\b(?:refund|return|delivery|shipping) policy\b",
        (
            r"\b(?:explain|tell me about|what is|what are)\b.*"
            r"\b(?:refund|return|delivery|shipping) policy\b"
        ),
    ],

    "product_search": [
        # Explicit searches for products.
        r"\bfind (?:me )?(?:a |an )?products?\b",
        r"\bsearch (?:for )?(?:a |an )?products?\b",
        r"\bshow me (?:all )?products?\b",
        r"\blist (?:all )?products?\b",

        # Searches for specific product categories.
        (
            r"\bfind(?: me)? (?:a |an )?"
            r"(?:wireless )?(?:laptops?|phones?|mobiles?|mice|mouse|"
            r"keyboards?|headphones?|monitors?|chargers?|tablets?)\b"
        ),
        (
            r"\bshow me (?:a |an |some )?(?:wireless )?"
            r"(?:laptops?|phones?|mobiles?|mice|mouse|keyboards?|"
            r"headphones?|monitors?|chargers?|tablets?)\b"
        ),
        (
            r"\bsearch for (?:a |an |some )?"
            r"(?:wireless )?(?:laptops?|phones?|mobiles?|mice|mouse|"
            r"keyboards?|headphones?|monitors?|chargers?|tablets?)\b"
        ),

        # Natural-language product requests.
        r"\blooking for (?:a |an )?.+",
        r"\bi want (?:to buy )?(?:a |an )?.+",
        r"\bi need (?:a |an )?.+",
        r"\bdo you have (?:any )?.+",

        # Price-based searches.
        r"\bproducts? (?:under|below|within)\b",
        r"\bproducts? less than\b",
        r"\b(?:under|below) \d+(?:\.\d+)?\b",
        r"\b(?:cheapest|affordable|budget) products?\b",

        # Catalog availability.
        r"\bavailable products?\b",
        r"\bproducts? available\b",
    ],
}


def classify_intent(question: str) -> Intent:
    """
    Classify a customer question using deterministic keyword patterns.

    Empty input returns 'unknown'. Unmatched questions return
    'general_question'.
    """

    normalized = question.strip().lower()

    if not normalized:
        return "unknown"

    # Check specific intents before product-search patterns.
    for intent in (
        "order_status",
        "create_ticket",
        "policy_question",
        "product_search",
    ):
        patterns = INTENT_PATTERNS[intent]

        if any(re.search(pattern, normalized) for pattern in patterns):
            return intent

    return "general_question"


def select_agent(intent: Intent) -> AgentName:
    """Map an intent to the responsible support agent."""

    if intent == "policy_question":
        return "knowledge"

    if intent in {
        "product_search",
        "order_status",
        "create_ticket",
    }:
        return "product_order"

    return "general"
