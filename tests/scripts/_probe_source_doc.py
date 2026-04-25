"""Probe the source sample doc: Normal/Heading pPr and field counts."""
from docx import Document
from docx.oxml.ns import qn

doc = Document(r"samples/南海鸢乌贼捕捞量智能反演文献综述.docx")

print("=== Normal style paragraph_format ===")
s = doc.styles['Normal']
pf = s.paragraph_format
print(f"  line_spacing_rule: {pf.line_spacing_rule}")
print(f"  line_spacing: {pf.line_spacing}")
print(f"  first_line_indent: {pf.first_line_indent}")
print(f"  left_indent: {pf.left_indent}")
print(f"  right_indent: {pf.right_indent}")
print(f"  space_before: {pf.space_before}")
print(f"  space_after: {pf.space_after}")

for name in ('Heading 1', 'Heading 2', 'Heading 3'):
    print(f"\n=== {name} paragraph_format ===")
    try:
        pf = doc.styles[name].paragraph_format
        print(f"  line_spacing_rule: {pf.line_spacing_rule}")
        print(f"  line_spacing: {pf.line_spacing}")
        print(f"  first_line_indent: {pf.first_line_indent}")
        print(f"  space_before: {pf.space_before}")
        print(f"  space_after: {pf.space_after}")
    except Exception as exc:
        print("  (missing)", exc)

print("\n=== Fields / bookmarks / hyperlinks count in body ===")
body = doc.element.body
W = qn('w:')[:-1]
counts = {}
for tag in ('fldSimple', 'fldChar', 'instrText', 'bookmarkStart', 'bookmarkEnd', 'hyperlink'):
    counts[tag] = len(body.findall('.//' + qn('w:' + tag)))
print(counts)

print("\n=== first few fldSimple ===")
for fld in body.findall('.//' + qn('w:fldSimple'))[:5]:
    text = ''.join(t.text or '' for t in fld.iter(qn('w:t')))
    print(f"  instr={fld.get(qn('w:instr'))!r}  text={text!r}")

print("\n=== first few hyperlink ===")
for hl in body.findall('.//' + qn('w:hyperlink'))[:5]:
    text = ''.join(t.text or '' for t in hl.iter(qn('w:t')))
    print(f"  anchor={hl.get(qn('w:anchor'))!r}  rId={hl.get(qn('r:id'))!r}  text={text!r}")

print("\n=== first few complex-field runs (fldChar begin/end) ===")
fld_chars = body.findall('.//' + qn('w:fldChar'))[:10]
for fc in fld_chars:
    print(f"  type={fc.get(qn('w:fldCharType'))!r}")
