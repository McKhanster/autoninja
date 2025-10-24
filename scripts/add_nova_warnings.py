#!/usr/bin/env python3
"""Add explicit JSON-only warnings to Nova prompt files."""

import json

# Warning text to add
WARNING_TEXT = """

## MANDATORY OUTPUT RULES - CRITICAL

⚠️ YOUR RESPONSE MUST START WITH { AND END WITH } ⚠️

1. **ONLY OUTPUT RAW JSON** - Your entire response must be valid, parseable JSON
2. **NO MARKDOWN** - Do not use ```json code blocks or any markdown formatting
3. **NO CONVERSATIONAL TEXT** - Do not explain, ask questions, or provide commentary
4. **NO PREAMBLE** - Start immediately with the opening brace {
5. **NO POSTAMBLE** - End immediately with the closing brace }
6. **NO THINKING TAGS** - Do not use <thinking>, <answer>, or any XML tags
7. **NO ACTION GROUP RESPONSES** - Do not say "There are no previous tool results" or "Starting the validation process" or similar conversational text
8. **IMMEDIATE JSON RESPONSE** - Your first character MUST be { and your last character MUST be }
9. **DO NOT WAIT** - Do not wait for tool results or previous context, immediately output the JSON based on the input provided

## EXAMPLES

✅ CORRECT OUTPUT:
{"key":"value","data":{...}}

❌ INCORRECT OUTPUT (DO NOT DO THIS):
There are no previous tool results. Starting the process...

❌ INCORRECT OUTPUT (DO NOT DO THIS):
<thinking>Let me analyze...</thinking>
<answer>{...}</answer>

❌ INCORRECT OUTPUT (DO NOT DO THIS):
```json
{...}
```

⚠️ REMEMBER: First character = {, Last character = } ⚠️
"""

files = [
    'infrastructure/cloudformation/prompts/ra-nova.json',
    'infrastructure/cloudformation/prompts/sa-nova.json',
    'infrastructure/cloudformation/prompts/cg-nova.json',
    'infrastructure/cloudformation/prompts/dm-nova.json',
]

for filepath in files:
    print(f"Processing {filepath}...")
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    # Add warning before $prompt_session_attributes$
    system_text = data['system'][0]['text']
    
    if '## MANDATORY OUTPUT RULES - CRITICAL' in system_text:
        print(f"  ✓ Already has warnings, skipping")
        continue
    
    # Insert before $prompt_session_attributes$
    if '$prompt_session_attributes$' in system_text:
        system_text = system_text.replace('$prompt_session_attributes$', WARNING_TEXT + '\n\n$prompt_session_attributes$')
    else:
        # Add at the end
        system_text += WARNING_TEXT
    
    data['system'][0]['text'] = system_text
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"  ✓ Updated")

print("\nDone! Updated all Nova prompt files.")
