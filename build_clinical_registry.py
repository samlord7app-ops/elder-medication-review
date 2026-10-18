"""Inventory source criteria; this does not turn text into executable rules."""
import json,re,hashlib,xml.etree.ElementTree as ET
from pathlib import Path
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parent/'public_reference'
def build():
    records=[]
    text='\n'.join(p.extract_text() for p in PdfReader(ROOT/'stopp-start-v3-appendix.pdf').pages)
    mode='STOPP';section=None;current=None
    for line in text.splitlines():
        line=line.strip()
        if 'Screening Tool to Alert to Right Treatment' in line:mode='START';section=None;current=None
        match=re.match(r'Section\s+([A-M])[:.]\s*(.*)',line)
        if match:section=match[1];current=None;continue
        match=re.match(r'(\d{1,2})\.\s+(.+)',line)
        if match and section:
            current={'id':f'{mode}-{section}{match[1]}','source':'stopp-start','text':match[2],'automation':'manual_review'};records.append(current)
        elif current and line and not re.fullmatch(r'\d+',line):current['text']+=' '+line
    ids=[r['id'] for r in records]
    from collections import Counter
    assert len(ids)==len(set(ids)), str({k:v for k,v in Counter(ids).items() if v>1})
    counts={m:sum(r['id'].startswith(m+'-') for r in records) for m in ['STOPP','START']}
    assert counts=={'STOPP':133,'START':57},counts
    root=ET.parse(ROOT/'pim-taiwan-2018.xml').getroot();table=root.findall('.//table-wrap')[0]
    subtype=concern=suggestion=category=''
    for i,tr in enumerate(table.findall('.//tbody/tr'),1):
        cells=[' '.join(''.join(td.itertext()).split()) for td in tr.findall('td')]
        assert len(cells)==6,(i,cells)
        cat,sub,drug,atc,why,advice=cells
        if cat:category=cat
        if sub:subtype=sub;concern='';suggestion=''
        if why:concern=why
        if advice:suggestion=advice
        records.append({'id':f'PIM-TW-T1-{i:03}','source':'pim-taiwan','category':category,'subtype':subtype,'drug':drug,'atc':atc,'reason':concern,'advice':suggestion,'automation':'manual_review'})
    assert sum(r['source']=='pim-taiwan' for r in records)==140
    (ROOT/'clinical-criteria-registry.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Source inventory:',counts,'PIM-Taiwan Table 1: 140 rows; Beers and disease tables not counted as fully encoded.')
if __name__=='__main__':build()
