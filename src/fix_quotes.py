with open('src/agent.py', 'r', encoding='utf-8') as f:
    text = f.read()

if text.startswith('"'):
    text = text[1:]
if text.endswith('"'):
    text = text[:-1]
if text.endswith('"\n'):
    text = text[:-2]

with open('src/agent.py', 'w', encoding='utf-8') as f:
    f.write(text)
print('Fixed quotes!')
