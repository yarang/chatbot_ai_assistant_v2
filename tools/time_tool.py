from datetime import datetime
from langchain_core.tools import Tool

def get_current_time(query: str = "") -> str:
    """Returns the current local time."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_time_tool():
    """
    Returns a tool that provides the current time.
    """
    return Tool(
        name="current_time",
        func=get_current_time,
        description="Useful for when you need to know the current time."
    )
