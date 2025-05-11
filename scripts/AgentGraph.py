from langgraph.graph import StateGraph, END
from langchain.prompts import PromptTemplate
from typing import TypedDict
import json

from scripts.RAGGraph import CRagGraph
from scripts.MemoryManager import CMemoryManager
from scripts.Initialize import CInitialize
from scripts.config import load_config


# ----- Graph State -----
class AgentGraphState(TypedDict):
    question: str
    route: str
    answer: str
    memory: str


# ----- AgentGraphBuilder Class -----
class AgentGraphBuilder:
    def __init__(self, namespace: str):
        self.namespace = namespace
        self.config = load_config()
        self.init = CInitialize()
        self.llm = self.init.MInitializeLLM()
        self.embeddings = self.init.MInitializeEmbeddings()
        self.pinecone = self.init.MInitializePinecone(self.config["MineaiIndexName"])
        self.memory = CMemoryManager(self.embeddings)

    def build_master_agent(self):
        prompt = PromptTemplate.from_template("""
        You are a helpful general AI assistant.
        Answer the following question:
        {input}
        """)
        return prompt | self.llm

    def router_node(self):
        def node(state: AgentGraphState):
            prompt = f"""
You are a router that selects the best agent to handle a user query.

Here is Conversation History:
{state['memory']}

DO NOT GIVE ANY OTHER EXPLANATION OR OUTPUT JUST VALID JSON.
Your output must be a valid JSON object with this format:
{{"route": "<agent_key>"}}

Valid options:
- qa: For questions related to the uploaded document
- master: For general-purpose questions
- summarize: When user wants a summary of the uploaded document
Valid agent_key values are: "qa", "master", "summarize"

User Question: "{state['question']}"
            """
            result = self.llm.invoke(prompt).content.strip()
            try:
                route = json.loads(result).get("route", "master")
            except Exception:
                route = "master"
            print("[Router Output]", result, "->", route)
            return {"route": route}
        return node

    def qa_agent_node(self):
        graph = CRagGraph(self.memory, self.namespace).MBuildGraph()
        def node(state: AgentGraphState):
            result = graph.invoke({"question": state["question"]})
            return {"answer": result["answer"]}
        return node

    def master_agent_node(self):
        master_agent = self.build_master_agent()
        def node(state: AgentGraphState):
            result = master_agent.invoke({"input": state["question"]})
            return {"answer": result.content}
        return node

    def get_memory_node(self):
        def node(state: AgentGraphState):
            context = self.memory.MGetConversationContext(state["question"])
            return {"memory": context}
        return node

    def save_memory_node(self):
        def node(state: AgentGraphState):
            self.memory.MSaveConversation(state["question"], state["answer"])
            return {}
        return node

    def summarize_node(self):
        index = self.pinecone.Index(self.config["MineaiIndexName"])
        results = index.query(
            vector=[0] * 384,
            namespace=self.namespace,
            top_k=20,
            include_metadata=True
        )
        all_texts = [m["metadata"].get("text", "") for m in results["matches"]]
        document_text = "\n".join(all_texts)

        def node(state: AgentGraphState):
            prompt = f"Summarize the following document:\n\n{document_text}"
            summary = self.llm.invoke(prompt).content
            return {"answer": summary}
        return node

    def build(self):
        graph = StateGraph(AgentGraphState)

        graph.add_node("get_memory", self.get_memory_node())
        graph.add_node("router", self.router_node())
        graph.add_node("qa", self.qa_agent_node())
        graph.add_node("master", self.master_agent_node())
        graph.add_node("summarize", self.summarize_node())
        graph.add_node("save_memory", self.save_memory_node())

        graph.set_entry_point("get_memory")
        graph.add_edge("get_memory", "router")

        def route_condition(state: AgentGraphState):
            return state["route"]

        graph.add_conditional_edges(
            "router",
            route_condition,
            {
                "qa": "qa",
                "master": "master",
                "summarize": "summarize"
            },
        )

        graph.add_edge("qa", "save_memory")
        graph.add_edge("master", "save_memory")
        graph.add_edge("summarize", "save_memory")
        graph.add_edge("save_memory", END)

        return graph.compile()
