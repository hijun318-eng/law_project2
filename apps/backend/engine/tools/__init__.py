from engine.tools.registry import registry
from engine.tools.news_search_tool import NewsSearchTool

def init_tools():
    registry.register(NewsSearchTool())
