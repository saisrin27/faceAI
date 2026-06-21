with open('frontend/app.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Let's define the replacements for the CSS style block
replacements = {
    # 1. Colors
    "background-color: #000000 !important;": "background-color: #2563EB !important;",
    "background: #000000 !important;": "background: #2563EB !important;",
    "border: 1px solid #000000 !important;": "border: 1px solid #60A5FA !important;",
    "border-left: 6px solid #000000 !important;": "border-left: 6px solid #2563EB !important;",
    "border-right: 1px solid #000000 !important;": "border-right: 1px solid #60A5FA !important;",
    "border-bottom: 2px solid #000000 !important;": "border-bottom: 2px solid #2563EB !important;",
    "border-bottom: 1px solid #000000 !important;": "border-bottom: 1px solid #60A5FA !important;",
    "border-color: #000000 !important;": "border-color: #2563EB !important;",
    "box-shadow: 0 0 0 1px #000000 !important;": "box-shadow: 0 0 0 1px #2563EB !important;",
    "color: #000000 !important;": "color: #1F2937 !important;",
    "color: #000000": "color: #1F2937",
    "color: '#000000'": "color: '#1F2937'",
    "color: \"#000000\"": "color: \"#1F2937\"",
    "border: 1px solid transparent !important;": "border: 1px solid transparent !important;", # keep
    
    # 2. Tabs
    "button[data-baseweb=\"tab\"] {\n        background-color: #FFFFFF !important;\n        color: #000000 !important;": "button[data-baseweb=\"tab\"] {\n        background-color: #FFFFFF !important;\n        color: #1F2937 !important;",
    
    # 3. Specific overrides for active elements
    "button[data-baseweb=\"tab\"][aria-selected=\"true\"] {\n        background-color: #000000 !important;\n        color: #FFFFFF !important;\n        border: 1px solid #000000 !important;": "button[data-baseweb=\"tab\"][aria-selected=\"true\"] {\n        background-color: #2563EB !important;\n        color: #FFFFFF !important;\n        border: 1px solid #2563EB !important;",
    
    # Header active primary button text color
    "button[data-testid=\"baseButton-primary\"] {\n        background-color: #FFFFFF !important;\n        color: #000000 !important;": "button[data-testid=\"baseButton-primary\"] {\n        background-color: #FFFFFF !important;\n        color: #2563EB !important;",
    
    # Global button hover
    "background-color: #FFFFFF !important;\n        background: #FFFFFF !important;\n        color: #000000 !important;\n        border: 1px solid #000000 !important;": "background-color: #FFFFFF !important;\n        background: #FFFFFF !important;\n        color: #2563EB !important;\n        border: 1px solid #2563EB !important;",
    "color: #000000 !important;\n        background-color: transparent !important;": "color: #2563EB !important;\n        background-color: transparent !important;",
}

# Apply replacements to the CSS block inside code
for target, replacement in replacements.items():
    code = code.replace(target, replacement)

# Write updated code
with open('frontend/app.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Applied theme colors to app.py successfully!")
