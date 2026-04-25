from zipfile import ZipFile
import re

for label, p in [
    ('base', r'G:/开发项目/wordcraft-pro/samples/南海鸢乌贼捕捞量智能反演文献综述.docx'),
    ('exp', r'E:/浏览器下载/2025年部门预算公开/9.2/新建文件夹/南海鸢乌贼捕捞量智能反演文献综述_导出 (3).docx'),
]:
    with ZipFile(p) as z:
        x = z.read('word/styles.xml').decode('utf-8')
    ids = [m.group(1) for m in re.finditer(r'styleId="([^"]+)"', x)]
    print(label, 'count', len(ids), 'has_Normal', 'Normal' in ids)
    if 'Normal' in ids:
        i = x.find('styleId="Normal"')
        end = x.find('</w:style>', i) + len('</w:style>')
        start = x.rfind('<w:style', 0, i)
        print('  Normal block:', x[start:end])
