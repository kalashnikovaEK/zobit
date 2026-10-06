# [NEW v18] Python 3.14 Windows installation profile.
# [NEW v15] Check integrated imports without launching Streamlit or requiring Ollama.
import sys
from pathlib import Path
if sys.version_info[:2] != (3, 14):
    raise SystemExit("Use Python 3.14 for this tested installation profile.")
# [NEW v18] Report actual interpreter for diagnosis.
print('Python:', sys.version, 'Executable:', sys.executable)
# [NEW v17] Never import potentially crashing native acceleration directly.
from runtime_v17 import STATUS
print('Solver backend:', STATUS)
import numpy, scipy, pandas, sklearn, plotly, requests
import interactive_server, integrated_api_v14, chat_bridge, measured_api_v14
from core import ROOT
for name in ("interactive.html", "chat_ui.js", "temperature_view.js", "stack_view_v14.js", "workbench_v14.js", "config/material.json", "config/ai_ollama.json", "config/ai_prompt.txt", "config/ai_request_schema.json", "config/llm_profiles_v14.json", "config/ai_guard_policy.json", "artifacts/development_cases.csv"):
    if not (ROOT / name).is_file():
        raise SystemExit("Missing runtime file: " + name)
# [NEW v17] Verify that the fallback/accelerator actually evaluates kinetics.
from core import cure_rate
import math
assert math.isfinite(cure_rate(0.1, 100.0))
print("HTML runtime imports and required files OK. Streamlit is not required.")
