import functools

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from .nodes import categorize, compose, details, impacts, normalize, score
from .schemas import AnalysisState


@functools.cache
def build_graph() -> CompiledStateGraph:
    builder = StateGraph(AnalysisState)
    builder.add_node("normalize", normalize)
    builder.add_node("categorize", categorize)
    builder.add_node("details", details)
    builder.add_node("impacts", impacts)
    builder.add_node("score", score)
    builder.add_node("compose", compose)

    builder.add_edge(START, "normalize")
    builder.add_edge("normalize", "categorize")
    builder.add_edge("categorize", "details")
    builder.add_edge("categorize", "impacts")
    builder.add_edge(["details", "impacts"], "score")
    builder.add_edge("score", "compose")
    builder.add_edge("compose", END)

    return builder.compile()


def run(text: str) -> dict:
    return build_graph().invoke({"input_text": text})["result"]
