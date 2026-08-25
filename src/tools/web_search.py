from langchain_core.tools import tool
from duckduckgo_search import DDGS


@tool
def web_search(query: str) -> str:
    """Search the web for current or factual information.

    Use this whenever the user asks about something that might have
    changed recently, that you're not confident about, or that requires
    up-to-date facts (news, prices, current events, "what's the latest on
    X", local info, etc.). Do not use it for things you already know with
    confidence.
    """
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=5))

    if not results:
        return f"No web results found for '{query}'."

    formatted = "\n\n".join(
        f"- {r['title']}\n  {r['body']}\n  Source: {r['href']}"
        for r in results
    )
    return formatted
