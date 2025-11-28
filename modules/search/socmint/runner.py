import subprocess
import json
import os
from .tools import TOOLS, is_tool_available

def run_subprocess(cmd: list, timeout=30):
    env = os.environ.copy()
    env.pop('PYTHONPATH', None)
    env.pop('PYTHONHOME', None)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=timeout,
            env=env
        )
        return {
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode,
            "success": result.returncode in (0,1)
        }
    except subprocess.TimeoutExpired:
        return {"error": "timeout"}
    except Exception as e:
        return {"error": str(e)}

def run_socmint_tool(tool: str, username: str):
    info = TOOLS[tool]

    if not is_tool_available(tool):
        return {
            "success": False,
            "installed": False,
            "error": f"{tool} no está disponible"
        }

    proc = run_subprocess(info["args"](username))

    if "error" in proc:
        return {"success": False, "error": proc["error"]}

    if info.get("parse_json"):
        try:
            data = json.loads(proc["stdout"])
            return {"success": True, "data": data, "raw_output": proc["stdout"]}
        except:
            return {"success": False, "raw_output": proc["stdout"]}

    return {"success": proc["success"], "raw_output": proc["stdout"]}
