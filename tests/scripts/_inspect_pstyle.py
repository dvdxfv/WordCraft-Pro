from zipfile import ZipFile
import re

for label, p in [
    ('base', r'G:/开发项目/wordcraft-pro/samples/南海鸢乌贼捕捞量智能反演文献综述.docx'),
    ('exp', r'E:/浏览器下载/2025年部门预算公开/9.2/新建文件夹/南海鸢乌贼捕捞量智能反演文献综述_导出 (3).docx'),
]:
    with ZipFile(p) as z:
        doc = z.read('word/document.xml').decode('utf-8')
    pstyles = re.findall(r'<w:pStyle\s+w:val="([^"]+)"', doc)
    from collections import Counter
    print(label, 'pStyle counter', Counter(pstyles))
