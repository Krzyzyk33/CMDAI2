import json, codecs, re

with open('agent_dump.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

def find_agent_code(d):
    if isinstance(d, dict):
        for k, v in d.items():
            res = find_agent_code(v)
            if res: return res
    elif isinstance(d, list):
        for v in d:
            res = find_agent_code(v)
            if res: return res
    elif isinstance(d, str):
        if 'class Agent:' in d and 'import os' in d:
            return d
    return None

code = find_agent_code(data)

if code.startswith('"') and code.endswith('"'):
    code = code[1:-1]
elif code.startswith("'") and code.endswith("'"):
    code = code[1:-1]

decoded = codecs.decode(code, 'unicode_escape')

lines = decoded.split('\n')
clean_lines = []
for line in lines:
    clean_line = re.sub(r'^\d+:\s', '', line)
    clean_lines.append(clean_line)
    
with open('src/agent.py', 'w', encoding='utf-8') as f:
    f.write('\n'.join(clean_lines))
print('Done decoding!')
