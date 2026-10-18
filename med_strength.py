"""Conservative label-strength parsing. Never infers daily dose or concentration."""
from decimal import Decimal
import re, unicodedata

NUMBER=r'(?:\d+(?:\.\d+)?|\.\d+)'
UNIT=r'(?:微克|毫克|公克|mcg|mg|ug|g)'
RATIO=re.compile(rf'({NUMBER})\s*({UNIT})(?:\s*/\s*({NUMBER})?\s*(ml|毫升))?',re.I)
SHARED=re.compile(rf'({NUMBER})\s*/\s*({NUMBER})\s*({UNIT})(?![a-z])',re.I)
FORMS={
 'extended':r'\b(?:er|xr|sr|cr|xl|extended[ -]release|sustained[ -]release|controlled[ -]release)\b|緩釋|持續釋放|控釋',
 'immediate':r'\b(?:ir|immediate[ -]release)\b|速放|即放',
 'tablet':r'\b(?:tablets?|tabs?)\b|膜衣錠|糖衣錠|錠劑|錠',
 'capsule':r'\b(?:capsules?|caps?)\b|膠囊',
 'injection':r'\b(?:injections?|injectables?|inj)\b|注射',
 'topical':r'\b(?:cream|ointment|gel)\b|乳膏|軟膏|凝膠'
}
def clean(s):
    return unicodedata.normalize('NFKC',s).casefold().replace('μg','mcg').replace('µg','mcg')
def number(s):return format(Decimal(s).normalize(),'f')
def quantity(value,unit,denominator=None):
    factor={'mcg':1,'ug':1,'微克':1,'mg':1000,'毫克':1000,'g':1000000,'公克':1000000}[unit]
    mass=Decimal(value)*factor
    return ('mass_per_ml',number(mass/Decimal(denominator or '1'))) if denominator is not None else ('mass',number(mass))
def parse(value):
    text=clean(value);parts=[];spans=[];display=[]
    if re.search(rf'(?:^|\s)-\s*{NUMBER}\s*{UNIT}',text):return None
    for m in SHARED.finditer(text):
        parts.extend([quantity(m[1],m[3]),quantity(m[2],m[3])]);spans.append(m.span());display.append(f'{m[1]} {m[3]} + {m[2]} {m[3]}')
    for m in RATIO.finditer(text):
        if any(a<=m.start()<b for a,b in spans):continue
        if m.end()<len(text) and text[m.end()].isalpha():continue
        parts.append(quantity(m[1],m[2],m[3] or '1' if m[4] else None));spans.append(m.span());display.append(m[0])
    if not parts or any(Decimal(p[1])<=0 for p in parts):return None
    # A dangling slash, alternate mass unit, or unmatched number is ambiguous.
    base=text
    for a,b in sorted(spans,reverse=True):base=base[:a]+' '+base[b:]
    if ('/' in base and len(parts)<2) or re.search(r'\d',base):return None
    forms={k for k,p in FORMS.items() if re.search(p,text,re.I)}
    for pattern in FORMS.values():base=re.sub(pattern,' ',base,flags=re.I)
    base=re.sub(r'\b(?:film[ -]?coated|coated|oral)\b',' ',base)
    base_text=' '.join(re.sub(r'[()\[\]「」“”"+]', ' ',base).split())
    base=re.sub(r'[\s\W_]+','',base,flags=re.UNICODE)
    return {'base':base,'baseText':base_text,'signature':parts,'forms':forms,'display':' + '.join(display)}
def compatible(request,labels,form=''):
    matches=[parse(label) for label in labels]
    if not any(m and m['signature']==request['signature'] for m in matches):return False
    evidence=clean(' '.join(labels)+' '+form)
    return all(re.search(FORMS[f],evidence,re.I) for f in request['forms'])
