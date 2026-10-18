"""Allowlist-only release assembly. Never recursively copy the workspace."""
from pathlib import Path
import hashlib, shutil, subprocess, sys, zipfile
from importlib.metadata import distribution

ROOT = Path(__file__).resolve().parents[1]
APP_FILES = ['intake.html','intake.css','intake.js','intake-core.js',
             'clinical-ui.js','update-controls.js','records-core.js','records-ui.js','cloud-drugs-ui.js','windows_ocr.ps1']
PUBLIC_FILES = ['public-catalog.zip','catalog-manifest.json','literature-manifest.json',
                'extra-manifest.json','reference-approvals.json','clinical-rulepack-manifest.json']

def build():
    if sys.platform != 'win32':
        raise SystemExit('Build on Windows x64 using 64-bit Python.')
    args = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir',
            '--name', 'ElderMedicationReview', '--distpath', str(ROOT/'release-build'),
            '--workpath', str(ROOT/'release-work'), '--specpath', str(ROOT/'release-work'),
            '--hidden-import', 'openpyxl', '--hidden-import', 'pypdf',
            '--copy-metadata', 'openpyxl', '--copy-metadata', 'et_xmlfile',
            '--copy-metadata', 'pypdf',
            '--hidden-import', 'build_clinical_registry']
    for name in APP_FILES:
        args += ['--add-data', f'{ROOT/name};.']
    for name in PUBLIC_FILES:
        source = ROOT/'public_reference'/name
        if not source.is_file():
            raise SystemExit(f'Missing public release input: {name}')
        args += ['--add-data', f'{source};public_reference']
    args += [str(ROOT/'desktop_launcher.py')]
    subprocess.run(args, cwd=ROOT, check=True)
    folder = ROOT/'release-build'/'ElderMedicationReview'
    licenses = folder/'THIRD-PARTY-LICENSES'
    licenses.mkdir(exist_ok=True)
    python_license = Path(sys.base_prefix)/'LICENSE.txt'
    if not python_license.is_file():raise SystemExit('Python runtime license missing')
    shutil.copy2(python_license,licenses/'Python-LICENSE.txt')
    for package in ['pyinstaller','openpyxl','et_xmlfile','pypdf']:
        dist=distribution(package)
        for file in dist.files or []:
            if file.name.lower().startswith(('license','licence','copying')):
                shutil.copy2(dist.locate_file(file),licenses/(package+'-'+file.name))
    for name in ['SHARING.md','CLINICAL_RULES.md','REFERENCES.md']:
        shutil.copy2(ROOT/name, folder/name)
    output = ROOT/'release-build'/'ElderMedicationReview-Windows-x64.zip'
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(folder.rglob('*')):
            if path.is_file(): archive.write(path,path.relative_to(folder.parent))
    checksum = hashlib.sha256(output.read_bytes()).hexdigest()
    (output.parent/'SHA256SUMS.txt').write_text(f'{checksum}  {output.name}\n',encoding='ascii')
    print(f'Packaged {output.name}; SHA256 {checksum}')

if __name__ == '__main__': build()
