"""One-time download of public literature, not invoked by the clinical API."""
from import_public_data import get, DEST
import hashlib, json, xml.etree.ElementTree as ET
from datetime import datetime
SOURCES=[('beers-2023','PMC12478568','AGS Beers 2023','https://pmc.ncbi.nlm.nih.gov/articles/PMC12478568/'),('stopp-start-v3','PMC10447584','STOPP/START version 3','https://pmc.ncbi.nlm.nih.gov/articles/PMC10447584/'),('pim-taiwan-2018','PMC6779000','PIM-Taiwan 2018, published 2019','https://pmc.ncbi.nlm.nih.gov/articles/PMC6779000/')]
if __name__=='__main__':
    DEST.mkdir(exist_ok=True);records=[]
    for slug,pmc,title,url in SOURCES:
        record={'id':slug,'title':title,'url':url,'role':'reference_only_not_active_rules','retrievedAt':datetime.now().astimezone().isoformat()}
        try:
            data=get(f'https://www.ebi.ac.uk/europepmc/webservices/rest/{pmc}/fullTextXML')
            root=ET.fromstring(data)
            if root.tag!='article': raise ValueError('Not article XML')
            path=DEST/(slug+'.xml');path.write_bytes(data)
            (DEST/(slug+'.txt')).write_text('\n'.join(' '.join(e.itertext()) for e in root.findall('.//article-title')+root.findall('.//abstract')+root.findall('.//body')+root.findall('.//permissions')),encoding='utf-8')
            record.update(status='downloaded',sha256=hashlib.sha256(data).hexdigest(),file=path.name,license=' '.join(' '.join(e.itertext()) for e in root.findall('.//permissions')))
            # Keep machine-readable tables as pending-review references, not executable rules.
            tables=[{'id':t.get('id'),'text':' '.join(t.itertext())} for t in root.findall('.//table-wrap')]
            (DEST/(slug+'-tables.json')).write_text(json.dumps(tables,ensure_ascii=False,indent=2),encoding='utf-8')
            record['tableCount']=len(tables)
            record['supplementLinks']=[e.get('{http://www.w3.org/1999/xlink}href') for e in root.findall('.//supplementary-material//media')]
        except Exception as e: record.update(status='download_failed',error=str(e))
        records.append(record);print(slug,record['status'],flush=True)
    (DEST/'literature-manifest.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
