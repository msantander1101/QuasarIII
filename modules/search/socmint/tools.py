import shutil

def command_exists(cmd):
    return shutil.which(cmd) is not None

TOOLS = {
    "maigret": {
        "module": "maigret",
        "exec": "maigret",
        "args": lambda username: [
            "maigret", username, "--json", "--simple", "--no-color", "--timeout", "10"
        ],
        "parse_json": True
    },
    "sherlock": {
        "module": "sherlock",
        "exec": "sherlock",
        "args": lambda username: [
            "sherlock", username, "--timeout", "10"
        ],
        "parse_json": False
    }
}

def is_tool_available(tool_name: str):
    info = TOOLS[tool_name]
    try:
        __import__(info["module"])
        return True
    except ImportError:
        return command_exists(info["exec"])
