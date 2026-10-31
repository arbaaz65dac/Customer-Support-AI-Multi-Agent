import re

from app.agents.graph_state import AgentName, Intent


INTENT_PATTERNS: dict[Intent, list[str]] = {
    "refund_request": [
        r"^(?:please )?(?:submit|file|request) (?:a )?(?:refund|return)\b",
        r"^(?:please )?i want (?:a )?(?:refund|return)\b",
        r"^(?:please )?refund my order\b",
        r"^(?:please )?return my (?:order|item|product)\b",
    ],
    "order_status": [
        r"\bwhere is my order\b",
        r"\bwhat (?:is|are) (?:the )?status of (?:my|the) orders?\b",
        r"\btrack (?:my |the )?order\b",
        r"\border status\b",
        r"\bdelivery status\b",
        r"\bwhen will my order arrive\b",
        r"\bwhen (?:will|can) i receive my order\b",
        r"\bhas my order shipped\b",
        r"\bcheck my order\b",
        r"\bhow (?:do|can) i (?:check|track) (?:the )?status of my order\b",
        r"\b(?:help|question) (?:with|about) my order\b",
        r"\b(?:list|show) my orders?\b",
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
        r"\bticket status\b",
        r"\b(?:list|show) my tickets\b",
        r"\b(?:broken|stopped working|arrived damaged|defective|wrong item)\b",
    ],
    "policy_question": [
        r"\breturn(?:s|ing)? policy\b",
        r"\brefund(?:s|ing)? policy\b",
        r"\bdelivery policy\b",
        r"\bshipping policy\b",
        r"\bwarranty\b",
        r"\bhow long\b.*\b(?:shipping|delivery|refund|return)\b",
        r"\b(?:shipping|delivery|refund|return)\b.*\b(?:usually|typically|take)\b",
        r"\bcontact customer support\b",
        r"\b(?:cash on delivery|cod)\b.*\brefunds?\b",
        r"\brefunds?\b.*\b(?:cash on delivery|cod)\b",
        r"\bdoes (?:the )?store (?:guarantee|have|offer)\b.*"
        r"\b(?:delivery|support office)\b",
        r"\bsupport office\b",
        r"\bhow many days.*refund\b",
        r"\bwhat is the process for returning\b",
        r"\bhow (?:do|can) i return\b",
        r"\bhow (?:do|can) i get (?:a )?refund\b",
        r"\bhow (?:do|can) i request (?:a )?(?:refund|return)\b",
        r"\bwhat should i do if my delivery is late\b",
        r"\b(?:late|delayed) delivery\b",
        r"\bcan i return\b",
        r"\bcan i get a refund\b",
        r"\brefund timeline\b",
        r"\breturn window\b",
        r"\b(?:explain|tell me about|what is|what are)\b.*"
        r"\b(?:refund|return|delivery|shipping) policy\b",
        r"\b(?:shipping|delivery|refund|return) (?:fee|charge|time|days)\b",
    ],
    "product_search": [
        r"\bfind (?:me )?(?:a |an )?products?\b",
        r"\bsearch (?:for )?(?:a |an )?products?\b",
        r"\bshow me (?:all )?products?\b",
        r"\blist (?:all )?products?\b",
        r"\b(?:find|show|search for) (?:me )?(?:a |an |some )?"
        r"(?:(?:affordable|budget|wireless|cheap) )*"
        r"(?:laptops?|phones?|mobiles?|mice|mouse|"
        r"keyboards?|headphones?|monitors?|chargers?|tablets?)\b",
        r"\b(?:looking for|i want|i need|do you have)\b.*"
        r"\b(?:laptops?|phones?|mobiles?|mice|mouse|keyboards?|"
        r"headphones?|monitors?|chargers?|tablets?|products?)\b",
        r"\bproducts? (?:under|below|within)\b",
        r"\bproducts? less than\b",
        r"\b(?:under|below) ₹?\s?\d+(?:\.\d+)?\b",
        r"\b(?:cheapest|affordable|budget) products?\b",
        r"\bavailable products?\b",
        r"\bproducts? available\b",
        r"\bproduct (?:details?|price|stock|availability)\b",
    ],
    "account_help": [
        r"\b(?:my|customer|shopping) account\b",
        r"\b(?:sign ?in|log ?in)\b",
        r"\b(?:reset|change|forgot|update) (?:my )?password\b",
        r"\bprofile (?:details|update|change)\b",
        r"\b(?:activate|deactivate) my account\b",
    ],
}

GREETING_PATTERNS = [
    r"^(?:hi|hello|hey)(?: there)?[!. ]*$",
    r"^(?:good morning|good afternoon|good evening)[!. ]*$",
    r"^(?:thanks|thank you|bye|goodbye)[!. ]*$",
]

INJECTION_PATTERNS = [
    r"\bignore (?:all )?(?:previous|prior|above) instructions\b",
    r"\bdisregard (?:all )?(?:previous|prior|above) instructions\b",
    r"\bforget (?:all )?(?:previous|prior|above) instructions\b",
    r"\b(?:reveal|show|print|repeat).{0,30}\b(?:system|developer) prompt\b",
    r"\bact as (?:an? )?(?:unrestricted|different|new) ",
    r"\b(?:jailbreak|prompt injection)\b",
]

OUT_OF_DOMAIN_PATTERNS = [
    r"\btell me (?:a )?joke\b",
    r"\b(?:write|debug|explain|review) (?:some )?(?:python|javascript|"
    r"typescript|java|code|programming)\b",
    r"\b(?:latest )?(?:news|weather|sports|score|match)\b",
    r"\bwho is (?!my\b|your\b)",
    r"\bwhat is \d+\s*[+\-*/]\s*\d+",
]


def _matches_any(patterns: list[str], normalized: str) -> bool:
    return any(re.search(pattern, normalized) for pattern in patterns)


def classify_intent(question: str) -> Intent:
    """Classify supported requests before routing any agent or tool."""
    normalized = question.strip().lower()

    if not normalized:
        return "unknown"

    # Treat explicit attempts to override assistant rules as unsupported input.
    if _matches_any(INJECTION_PATTERNS, normalized):
        return "out_of_domain"
    if _matches_any(OUT_OF_DOMAIN_PATTERNS, normalized):
        return "out_of_domain"

    matched = [
        intent
        for intent, patterns in INTENT_PATTERNS.items()
        if _matches_any(patterns, normalized)
    ]
    if "policy_question" in matched and any(
        intent != "policy_question" for intent in matched
    ):
        return "mixed"
    if matched:
        for intent in (
            "refund_request",
            "order_status",
            "create_ticket",
            "account_help",
            "product_search",
            "policy_question",
        ):
            if intent in matched:
                return intent
    if _matches_any(GREETING_PATTERNS, normalized):
        return "general_question"
    return "out_of_domain"


def select_agent(intent: Intent) -> AgentName:
    """Map the router classification to the bounded graph path."""
    if intent == "policy_question":
        return "knowledge"
    if intent in {
        "product_search",
        "order_status",
        "create_ticket",
        "refund_request",
        "account_help",
    }:
        return "product_order"
    if intent == "mixed":
        return "mixed"
    if intent == "out_of_domain":
        return "out_of_domain"
    return "general"
