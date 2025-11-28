from .runner import run_socmint_tool
from .tools import TOOLS
import time

class SocmintSearcher:

    def search(self, username: str, platforms=None):
        platforms = platforms or TOOLS.keys()

        results = {}
        all_ok = True

        for tool in platforms:
            r = run_socmint_tool(tool, username)
            results[tool] = r
            if not r.get("success", False):
                all_ok = False

        return {
            "query": username,
            "timestamp": time.time(),
            "results": results,
            "all_tools_ok": all_ok
        }


socmint_searcher = SocmintSearcher()


def search_social_profiles(username: str, platforms=None):
    return socmint_searcher.search(username, platforms)
