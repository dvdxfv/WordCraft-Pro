import json
from pathlib import Path

d = json.loads(Path(r'G:/开发项目/wordcraft-pro/tests/artifacts/compare_v5.json').read_text(encoding='utf-8'))
ms = d['result']['mismatches']
pf = [m for m in ms if m['type'] == 'paragraph_format']

cases = []
for m in pf:
    if m['base'].get('runs') != m['exported'].get('runs'):
        base_runs = m['base']['runs']
        exp_runs = m['exported']['runs']
        cases.append((m.get('index'), (m.get('base_text') or '')[:40], len(base_runs), len(exp_runs)))

print('total runs mismatch', len(cases))
print('first 10:')
for c in cases[:10]:
    print(' ', c)

# inspect one with equal run count but different content
for m in pf[:40]:
    br = m['base'].get('runs')
    er = m['exported'].get('runs')
    if br != er and len(br) == len(er) and len(br) > 0:
        print('---diff run example idx=', m.get('index'))
        print('  base run0=', br[0])
        print('  exp run0=', er[0])
        break
