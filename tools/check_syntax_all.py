import py_compile
import os
import sys

errors = []
for root, dirs, files in os.walk('.'):
    # skip virtual envs and .git
    if any(p in root for p in ['.venv', 'venv', '__pycache__', '.git']):
        continue
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            try:
                py_compile.compile(path, doraise=True)
            except py_compile.PyCompileError as e:
                errors.append((path, str(e)))

if errors:
    print('SYNTAX_ERRORS_FOUND')
    for p, e in errors:
        print(p)
        print(e)
    sys.exit(2)
else:
    print('ALL_PY_FILES_COMPILED_OK')
    sys.exit(0)
