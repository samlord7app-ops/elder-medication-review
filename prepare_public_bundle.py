"""Package only explicitly allowlisted government catalogs, no patient files."""
import zipfile, json,hashlib, xml.etree.ElementTree as ET
from import_public_data import DEST
from datetime import datetime
for file in ['pim-taiwan-2018','stopp-start-v3']:
    root=ET.parse(DEST/(file+'.xml')).getroot()
    (DEST/(file+'.txt')).write_text('\n'.join(' '.join(e.itertext()) for e in root.findall('.//article-title')+root.findall('.//abstract')+root.findall('.//body')+root.findall('.//permissions')),encoding='utf-8')
path=DEST/'extra-manifest.json';records=json.loads(path.read_text(encoding='utf-8'))
for r in records:
    p=DEST/r['file']
    if p.exists() and p.read_bytes().startswith(b'%PDF'):
        r.update(status='downloaded',sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
        if 'stopp' in p.name:r['url']='https://www.ebi.ac.uk/europepmc/webservices/rest/PMC10447584/supplementaryFiles'
path.write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
with zipfile.ZipFile(DEST/'public-catalog.zip','w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for file in ['tfda.csv','nhi.csv','catalog-manifest.json']:z.write(DEST/file,file)
print('Public bundle bytes:',(DEST/'public-catalog.zip').stat().st_size)
