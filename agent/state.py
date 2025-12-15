from typing import Annotated, List, Optional, Literal
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field

class RouteDecision(BaseModel):
    next_agent: Literal["Researcher", "GeneralAssistant", "NotionSearch", "FINISH"] = Field(
        description="The next agent to act of FINISH."
    )
    reasoning: str = Field(description="The reasoning behind the decision.")

class ChatState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    user_id: str
    chat_room_id: str
    persona_content: Optional[str]
    model_name: Optional[str]
    summary: Optional[str]
    next: str
    input_tokens_used: Optional[int]
    output_tokens_used: Optional[int]
    applied_system_prompt: Optional[str]
