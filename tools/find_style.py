with open('frontend/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re
matches = re.finditer(r'<style>', content)
for m in matches:
    start_pos = max(0, m.start() - 100)
    end_pos = min(len(content), m.end() + 200)
    print(f"Match at index {m.start()}:\n{content[start_pos:end_pos]}\n{'-'*50}")
