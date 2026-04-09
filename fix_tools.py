with open('tools.json', 'r') as f:
    content = f.read()

good_part = content[:content.find('  ]\n}\n          "properties": {')]
good_part += '  ]\n}\n'

with open('tools.json', 'w') as f:
    f.write(good_part)
