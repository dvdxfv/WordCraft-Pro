import json
from pathlib import Path

d = json.loads(Path(r'G:/开发项目/wordcraft-pro/tests/artifacts/compare_v5.json').read_text(encoding='utf-8'))
ms = d['result']['mismatches']
pf = [m for m in ms if m['type'] == 'paragraph_format']

for m in pf[:5]:
    br = m['base'].get('runs')
    er = m['exported'].get('runs')
    if br == er:
        continue
    print('=== idx=', m.get('index'))
    print('  len base=', len(br), 'len exp=', len(er))
    for i in range(min(len(br), len(er))):
        b = br[i]; e = er[i]
        if b != e:
            diffs = {k: (b.get(k), e.get(k)) for k in set(b) | set(e) if b.get(k) != e.get(k)}
            print(f'  run {i} diff:', diffs)
