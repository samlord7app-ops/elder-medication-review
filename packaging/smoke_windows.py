"""Smoke-test frozen application before publishing its already-built ZIP."""
import io, json, subprocess, time, urllib.request, urllib.error
from openpyxl import Workbook
from pathlib import Path

root=Path(__file__).resolve().parents[1]
exe=root/'release-build/ElderMedicationReview/ElderMedicationReview.exe'
process=subprocess.Popen([str(exe),'--no-browser'],cwd=exe.parent)
try:
    deadline=time.monotonic()+180
    while True:
        if process.poll() is not None:raise RuntimeError('Packaged service exited early')
        try:
            with urllib.request.urlopen('http://127.0.0.1:18743/api/catalog',timeout=2) as r:
                catalog=json.load(r)
            break
        except (OSError,urllib.error.URLError):
            if time.monotonic()>deadline:raise RuntimeError('Packaged service did not become ready')
            time.sleep(1)
    assert catalog['productCount']>200000, 'Public catalog failed to initialize'
    with urllib.request.urlopen('http://127.0.0.1:18743/',timeout=5) as r:
        assert r.status==200 and b'intake.js' in r.read()
        assert "frame-ancestors" in r.headers['Content-Security-Policy']
    with urllib.request.urlopen('http://127.0.0.1:18743/api/session',timeout=5) as r:
        token=json.load(r)['token']
    for script in ['records-core.js','records-ui.js','cloud-drugs-ui.js']:
        with urllib.request.urlopen('http://127.0.0.1:18743/'+script,timeout=5) as r:
            assert r.status==200
    request=urllib.request.Request('http://127.0.0.1:18743/api/cloud/drugs',
        data=json.dumps({'medications':['Diazepam'],'consent':False}).encode(),
        headers={'Origin':'http://127.0.0.1:18743','X-Local-Token':token,'Content-Type':'application/json'})
    try:
        urllib.request.urlopen(request,timeout=5)
        raise AssertionError('Cloud lookup accepted without consent')
    except urllib.error.HTTPError as e:assert e.code==400
    request=urllib.request.Request('http://127.0.0.1:18743/api/evaluate',
        data=json.dumps({'age':78,'medications':['Diazepam'],'labs':[],'diagnoses':[]}).encode(),
        headers={'Origin':'http://127.0.0.1:18743','X-Local-Token':token,'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=10) as r:
        analysis=json.load(r)['results'][0]['analysis']
        assert analysis and 'Beers 2023' in analysis[0]['criterion']
        assert analysis[0]['status']=='source_unverified', 'Unverified references must not activate rules'
    request=urllib.request.Request('http://127.0.0.1:18743/api/evaluate',
        data=json.dumps({'medications':['Diazepam'],'labs':[],'diagnoses':[]}).encode(),
        headers={'Origin':'http://127.0.0.1:18743','X-Local-Token':token,'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=10) as r:
        result=json.load(r)
        assert result['context']['age'] is None and not result['context']['ageProvided']
    request=urllib.request.Request('http://127.0.0.1:18743/api/evaluate',
        data=json.dumps({'age':None,'medications':['Lipitor 10 mg'],'labs':[],'diagnoses':[]}).encode(),
        headers={'Origin':'http://127.0.0.1:18743','X-Local-Token':token,'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=10) as r:
        result=json.load(r)['results'][0]
        assert result['strengthMatch']['status']=='matched'
        assert result['ingredient']=='atorvastatin' and result['clinicalInput']['dailyDoseMg'] is None
    workbook=Workbook();workbook.active.append(['Diazepam']);buffer=io.BytesIO();workbook.save(buffer);workbook.close()
    request=urllib.request.Request('http://127.0.0.1:18743/api/extract/excel',data=buffer.getvalue(),
        headers={'Origin':'http://127.0.0.1:18743','X-Local-Token':token})
    with urllib.request.urlopen(request,timeout=10) as r:
        assert json.load(r)['sheets'][0]['rows']==[['Diazepam']]
    request=urllib.request.Request('http://127.0.0.1:18743/api/evaluate',data=b'{}',
        headers={'Origin':'https://untrusted.example','X-Local-Token':token})
    try:
        urllib.request.urlopen(request,timeout=5)
        raise AssertionError('Cross-origin request was accepted')
    except urllib.error.HTTPError as e:assert e.code==403
    # Do not ship the test-generated catalog database: ZIP was assembled beforehand.
    print('Frozen Windows package: startup, catalog, Excel, integrated UI, analysis API, source guard and origin isolation passed.')
finally:
    process.terminate()
    process.wait(timeout=15)
