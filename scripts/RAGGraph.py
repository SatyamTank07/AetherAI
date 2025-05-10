from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableLambda
from typing import TypedDict
from Initialize import CInitialize
from config import load_config

config = load_config()
class GraphState(TypedDict):
    question: str
    context: str
    memory: str
    answer: str

class CRagGraph:
    def __init__(self, memory_manager, namespace):
        _objInit = CInitialize()
    
        self.embeddings = _objInit.MInitializeEmbeddings()
        self.pinecone = _objInit.MInitializePinecone(config["MineaiIndexName"])
        self.llm = _objInit.MInitializeLLM()
        self.memory_manager = memory_manager
        self.namespace = namespace
    
    def MGetContextNode(self):
        def node(state: GraphState):
            query_embedding = self.embeddings.embed_query(state["question"])
            index = self.pinecone.Index(config["MineaiIndexName"])
            query_result = index.query(
                vector=query_embedding,
                top_k=5,
                include_metadata=True,
                namespace=self.namespace
            )

            context_parts = [
                match["metadata"].get("text", "")
                for match in query_result.get("matches", [])
            ]
            return {"context": "\n\n".join(context_parts)}
        return node
    
    def MGetMemoryNode(self):
        def node(state: GraphState):
            memory = self.memory_manager.MGetConversationContext(state["question"])
            return {"memory": memory}
        return node
    
    def MGenerateAnswerNode(self):
        def node(state: GraphState):
            prompt = f"""
Conversation History:
{state['memory']}

Document Context:
{state['context']}

Question: {state['question']}
Answer:"""
            answer = self.llm.invoke(prompt).content
            return {"answer": answer}
        return node
    
    def MSaveMemoryNode(self):
        def node(state: GraphState):
            self.memory_manager.MSaveConversation(state["question"], state["answer"])
            return {}
        return node
    
    def MBuildGraph(self):
        graph = StateGraph(GraphState)
        
        graph.add_node("load_input", RunnableLambda(lambda state: {"question": state["question"]}))
        graph.add_node("get_context", RunnableLambda(self.MGetContextNode()))
        graph.add_node("get_memory", RunnableLambda(self.MGetMemoryNode()))
        graph.add_node("generate_answer", RunnableLambda(self.MGenerateAnswerNode()))
        graph.add_node("save_memory", RunnableLambda(self.MSaveMemoryNode()))

        graph.set_entry_point("load_input")
        graph.add_edge("load_input", "get_context")
        graph.add_edge("load_input", "get_memory")
        # Merge both into generate_answer
        graph.add_edge("get_context", "generate_answer")
        graph.add_edge("get_memory", "generate_answer")
        graph.add_edge("generate_answer", "save_memory")
        graph.add_edge("save_memory", END)
        
        return graph.compile()