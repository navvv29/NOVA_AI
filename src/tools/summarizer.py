from langchain_core.tools import tool


@tool
def summarize_text(
    text: str,
    style: str = "concise",
    focus: str = "",
) -> str:
    """Summarize any text, document, or content.

    This tool prepares summarization parameters for the LLM to process.
    Use it for lecture notes, articles, code documentation, research papers, etc.

    Parameters:
    - text: The text to summarize
    - style: 'concise' (brief), 'detailed' (comprehensive), 'bullets' (key points), or 'eli5' (explain like I'm 5)
    - focus: Optional focus area (e.g., "focus on algorithms" or "focus on security implications")
    """
    valid_styles = ("concise", "detailed", "bullets", "eli5")
    style = style.lower() if style.lower() in valid_styles else "concise"

    focus_instruction = f" Focus specifically on: {focus}." if focus.strip() else ""

    return (
        f"SUMMARIZATION_REQUEST\n"
        f"style: {style}\n"
        f"text_length: {len(text)} characters\n"
        f"{f'focus: {focus}' if focus.strip() else ''}\n\n"
        f"Summarize the following text in {style} style.{focus_instruction}\n\n"
        f"---\n{text[:5000]}\n---"
    )
