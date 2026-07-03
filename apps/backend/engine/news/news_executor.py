from engine.tools.registry import registry
from engine.news.news_normalizer import normalize_news

class NewsExecutor:

    def execute(self, tool: str, args: dict):

        result = registry.run(tool, **args)

        if not result.success:
            return {
                "error": result.error,
                "evidence": []
            }

        if tool == "news_search":

            obs = normalize_news(
                args["query"],
                result.data["results"],
                top_k=5,
            )

            obs["search_query"] = args["query"]

            return obs

        return result.data
    
    
    def valid_tools(self):
        return registry.list_tools()
