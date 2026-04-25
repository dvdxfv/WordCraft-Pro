from zipfile import ZipFile
import re

p = r'E:/浏览器下载/2025年部门预算公开/9.2/新建文件夹/南海鸢乌贼捕捞量智能反演文献综述_导出 (3).docx'
with ZipFile(p) as z:
    x = z.read('word/styles.xml').decode('utf-8')
ids = [m.group(1) for m in re.finditer(r'styleId="([^"]+)"', x)]
print('count', len(ids), 'ids', ids)
print('has Normal', 'Normal' in ids)
