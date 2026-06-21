import re
import os

def check_file(filepath):
    print(f"Checking {filepath}...")
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Simple regex to find execute statement lines
    lines = content.split('\n')
    for idx, line in enumerate(lines):
        if 'cursor.execute' in line:
            # check if there is an f-string or string concatenation or formatting inside the statement
            # E.g., cursor.execute(f"...") or cursor.execute("..." % ...) or cursor.execute("..." + ...)
            # excluding date formatting like %Y-%m-%d
            if ('f"' in line or "f'" in line or 'format(' in line or ' + ' in line) and not 'DATE_FORMAT' in line:
                print(f"  Line {idx+1}: {line.strip()}")

check_file('backend/main.py')
check_file('backend/database/db.py')
