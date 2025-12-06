from langgraph.graph import StateGraph, START, END
from agent.state import ChatState
from agent.nodes.router_node import supervisor_node
from agent.nodes.search_node import researcher_node
from agent.nodes.chat_node import general_assistant_node
from agent.nodes.notion_node import notion_node
from agent.nodes.tools_node import tools_node
from agent.nodes.common_nodes import retrieve_data_node, save_conversation_node, summarize_conversation_node

# Define Graph
workflow = StateGraph(ChatState)

# Add Nodes
workflow.add_node("retrieve_data", retrieve_data_node)
workflow.add_node("Supervisor", supervisor_node)
workflow.add_node("Researcher", researcher_node)
workflow.add_node("GeneralAssistant", general_assistant_node)
workflow.add_node("NotionSearch", notion_node) # New Notion Node
workflow.add_node("tools", tools_node)
workflow.add_node("save_conversation", save_conversation_node)
workflow.add_node("summarize_conversation", summarize_conversation_node)

# Edges
workflow.add_edge(START, "retrieve_data")
workflow.add_edge("retrieve_data", "Supervisor")

# Conditional edge from Supervisor
workflow.add_conditional_edges(
    "Supervisor",
    lambda x: x["next"],
    {
        "Researcher": "Researcher",
        "GeneralAssistant": "GeneralAssistant",
        "NotionSearch": "NotionSearch",
        "FINISH": "save_conversation",
    },
)

# Researcher flow
def route_researcher(state):
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tools"
    return "Supervisor"

workflow.add_conditional_edges("Researcher", route_researcher, {"tools": "tools", "Supervisor": "Supervisor"})
workflow.add_edge("tools", "Researcher")

# GeneralAssistant flow
workflow.add_edge("GeneralAssistant", "Supervisor")

# NotionSearch flow
workflow.add_edge("NotionSearch", "Supervisor")

# End flow
workflow.add_edge("save_conversation", "summarize_conversation")
workflow.add_edge("summarize_conversation", END)

graph = workflow.compile()
