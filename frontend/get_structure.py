import re
import sys
sys.stdout.reconfigure(encoding="utf-8")

with open("app.py", "r", encoding="utf-8") as f:
    text = f.read()

# Let's search for "st.set_page_config" or similar config calls
match = re.search(r"st\.set_page_config", text)
if match:
    start_pos = max(0, match.start() - 200)
    end_pos = min(len(text), match.end() + 1000)
    print(text[start_pos:end_pos])
else:
    print("set_page_config not found")
