
from app.database import SessionLocal
from app.services.tool_agent_service import answer_with_tools


db = SessionLocal()

try:
    answer = answer_with_tools(
        "Find products under 2000",
        db,
    )
    print("Answer:", answer)

except Exception as exc:
    print("Error type:", type(exc).__name__)
    print("Error message:", str(exc))

finally:
    db.close()
