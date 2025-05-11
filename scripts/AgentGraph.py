from langgraph.graph import StateGraph, END
from langchain.prompts import PromptTemplate
from typing import TypedDict
import json

from RAGGraph import CRagGraph
from MemoryManager import CMemoryManager
from Initialize import CInitialize
from config import load_config

# ----- Shared Setup -----
config = load_config()
init = CInitialize()
llm = init.MInitializeLLM()
embeddings = init.MInitializeEmbeddings()
pinecone = init.MInitializePinecone(config["MineaiIndexName"])

# ----- Graph State Definition -----
class AgentGraphState(TypedDict):
    question: str
    route: str
    answer: str

# ----- Master Agent -----
def build_master_agent():
    master_prompt = PromptTemplate.from_template("""
    You are a helpful general AI assistant.
    Answer the following question:
    {input}
    """)
    
    return master_prompt | llm

# ----- Graph Nodes -----
def router_node(state: AgentGraphState) -> dict:
    prompt = f"""
You are a router that selects the best agent to handle a user query.
DO NOT GIVE ANY OTHER EXPLANATION OR OUTPUT JUST VALID JSON.
Your output must be a valid JSON object with this format:
{{"route": "<agent_key>"}}

Valid options:
- qa: For questions related to the uploaded document
- master: For general-purpose questions

Valid agent_key values are: "qa", "master"

User Question: "{state['question']}"
    """
    result = llm.invoke(prompt).content.strip()
    try:
        route = json.loads(result).get("route", "master")
    except Exception:
        route = "master"
    
    print("[Router Output]", result, "->", route)
    return {"route": route}

def qa_agent_node_builder(namespace):
    memory = CMemoryManager(embeddings)
    graph = CRagGraph(memory, namespace).MBuildGraph()

    def node(state: AgentGraphState):
        result = graph.invoke({"question": state["question"]})
        return {"answer": result["answer"]}
    return node

def master_agent_node_builder():
    master_agent = build_master_agent()

    def node(state: AgentGraphState):
        result = master_agent.invoke({"input": state["question"]})
        return {"answer": result.content}
    
    return node

# ----- Build LangGraph -----
def build_agent_graph(namespace: str):
    graph = StateGraph(AgentGraphState)

    graph.add_node("router", router_node)
    graph.add_node("qa", qa_agent_node_builder(namespace))
    graph.add_node("master", master_agent_node_builder())

    graph.set_entry_point("router")

    # Route based on 'route' key from router node
    def route_condition(state: AgentGraphState):
        return state["route"]

    graph.add_conditional_edges(
        "router",
        route_condition,
        {
            "qa": "qa",
            "master": "master"
        },
    )

    graph.add_edge("qa", END)
    graph.add_edge("master", END)

    return graph.compile()
