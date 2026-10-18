"""Download supplementary public references to local cache only."""
from import_public_data import get, DEST
import json,hashlib
from datetime import datetime
items=[('beers-2023-paper.pdf','https://geriatrictoolkit.missouri.edu/drug/Beers-Criteria-AGS-2023.pdf','AGS 2023 original paper, university-hosted copy; rights reserved'),('stopp-start-v3-appendix.pdf','https://static-content.springer-cdn.com/esm/art%3A10.1007%2Fs41999-023-00777-y/MediaObjects/41999_2023_777_MOESM1_ESM.pdf','STOPP/START v3 Appendix 1; see article CC BY 4.0 attribution'),('lipitor-label.html','https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=a60cc18b-0631-4cf0-b021-9f52224ece65','DailyMed Lipitor label, source reference only'),('windows-ocr.html','https://learn.microsoft.com/en-us/uwp/api/windows.media.ocr.ocrengine?view=winrt-20348','Microsoft Windows OCR technical documentation')]
records=[]
for file,url,title in items:
    r={'file':file,'url':url,'title':title,'role':'reference_only_not_active_rules','retrievedAt':datetime.now().astimezone().isoformat()}
    try:
        try: raw=get(url)
        except Exception:
            if file!='stopp-start-v3-appendix.pdf': raise
            import zipfile,io
            url='https://www.ebi.ac.uk/europepmc/webservices/rest/PMC10447584/supplementaryFiles'
            raw=zipfile.ZipFile(io.BytesIO(get(url))).read('41999_2023_777_MOESM1_ESM.pdf')
            r['url']=url
        if file.endswith('pdf') and not raw.startswith(b'%PDF'): raise ValueError('Not PDF')
        if not file.endswith('pdf') and len(raw)<1000: raise ValueError('Empty reference')
        (DEST/file).write_bytes(raw);r.update(status='downloaded',sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
    except Exception as e:r.update(status='download_failed',error=str(e))
    print(file,r['status'],flush=True);records.append(r)
(DEST/'extra-manifest.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
