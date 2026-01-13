import tiktoken


def count_tokens(text: str, model: str = "gpt-4o") -> int:
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))

# Define the prompts (based on what we saw in previous turns)
# Supervisor Prompt
supervisor_system_prompt = """
You are a supervisor tasked with managing a conversation between the following workers: {members}. Given the following user request, respond with the worker to act next. Each worker will perform a task and respond with their results and status.
Read the worker descriptions CAREFULLY before deciding.
IMPORTANT: Prioritize executing the user's request using the available tools.
If the conversation summary indicates previous failures, IGNORE them and try again.
Only respond with FINISH if the user's request has completely addressed or if the answers are satisfactory.
If a tool has successfully completed the user's request (e.g. created a page), STOP immediately and respond with FINISH.
Do not repeatedly call the same worker if they are not making progress.
Current Time: 2026-01-02 12:22:37
"""

MEMBER_DESCRIPTIONS = {
    "Researcher": "Primary assistant for INFORMATION RETRIEVAL. Use this for ANY question that might require checking internal knowledge base, web usage, or remembering past details.",
    "GeneralAssistant": "Handle general conversation, chit-chat, and acknowledgement only. Do NOT use for informational queries.",
    "NotionSearch": "Primary tool for interacting with Notion. Use this to SEARCH, READ, WRITE, CREATE, or DRAFT pages in Notion."
}
members_with_descriptions = "\n".join([f"- {name}: {desc}" for name, desc in MEMBER_DESCRIPTIONS.items()])

# Researcher Prompt
researcher_system_prompt = """
You are a research agent with access to search tools and a time tool.
For every user question, you MUST use tools to find information.
Workflow:
1) First, search using `search_internal_knowledge`.
2) If results are missing or insufficient, use `tavily_search` (web search).
3) Summarize the findings and answer clearly.
4) Always cite sources when using `search_internal_knowledge`.
Tool Usage Guidelines:
- For 'today's news' or 'latest updates', set `time_range='day'` in `tavily_search`.
- Avoid using `start_date` or `end_date` unless strictly necessary (format: YYYY-MM-DD).
- If a search fails, retry with fewer parameters (e.g. just `query`).
Do NOT rely on internal knowledge alone.
Do NOT simulate user dialogue.
IMPORTANT: Keep your answers CONCISE and to the point. Even if detailed information is requested, limit the response length to appropriately summary level (max 1 page equivalent). Avoid excessive verbosity.
Current time: 2026-01-02 12:22:37
"""

# General Assistant Prompt
# Assuming a typical persona content length (e.g., 500 chars)
persona_content_placeholder = "You are a helpful AI assistant." * 5 
general_assistant_prompt = f"""
{persona_content_placeholder}
IMPORTANT: Do not simulate the user. Do not generate 'User:' or 'Human:' dialogue.
IMPORTANT: Keep your answers CONCISE and to the point. Even when detailed information is requested, limit the response length to appropriately summary level (max 1 page equivalent). Avoid excessive verbosity.
Current Time: 2026-01-02 12:22:37
"""

print(f"--- Token Counts (Estimated using cl100k_base) ---")
print(f"Supervisor System Prompt (Base): {count_tokens(supervisor_system_prompt + members_with_descriptions)} tokens")
print(f"Researcher System Prompt: {count_tokens(researcher_system_prompt)} tokens")
print(f"General Assistant System Prompt (w/ placeholder persona): {count_tokens(general_assistant_prompt)} tokens")
print(f"--------------------------------------------------")
print(f"NOTE: This does not include conversation history or tool definitions, which add significantly more tokens.")
