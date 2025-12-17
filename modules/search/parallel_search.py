# modules/search/parallel_search.py
"""
Parallel Search Executor
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Callable


def run_parallel(tasks: Dict[str, Callable[[], Dict[str, Any]]], max_workers=4):
    results = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fn): name for name, fn in tasks.items()}

        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as e:
                results[name] = {
                    "source": name,
                    "results": [],
                    "errors": [str(e)],
                    "has_data": False,
                }

    return results
