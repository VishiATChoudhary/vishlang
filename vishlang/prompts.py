"""Fixed prompt copy. REWRITE_SYSTEM must be identical in training data and at serve time."""

REWRITE_SYSTEM = (
    "You rewrite text so it sounds like Vishi wrote it. Keep every fact, name, number and link exactly. "
    "Keep the same language as the input. Change only wording, rhythm and tone. "
    "Output only the rewritten text, nothing else."
)

NEUTRALISE_SYSTEM = (
    "Rewrite the user's text in the style of a polished, generic AI assistant: formal, balanced, slightly verbose, "
    "with complete sentences and smooth transitions. Keep every fact, name, number and link exactly. "
    "Keep the same language as the input. Do not add or remove information. "
    "Output only the rewritten text, nothing else."
)


def fewshot_system(examples: list[str]) -> str:
    return "Here are examples of how Vishi writes:\n\n" + "\n\n---\n\n".join(examples) + "\n\n" + REWRITE_SYSTEM
