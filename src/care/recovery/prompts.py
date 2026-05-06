RECOVERY_INSTRUCTION = (
    "Based only on the verified information provided below, answer the question faithfully. "
    "Do not introduce information not present in the context."
)


def wrap_recovery_prompt(context: str, question: str) -> str:
    return f"{RECOVERY_INSTRUCTION}\n\nContext:\n{context}\n\nQuestion: {question}"
