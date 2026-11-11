"""Observed local codes; classification is not an official code certification."""
import json
import re
from dataclasses import dataclass

FIELDS=('kode_kabupaten','kode_kecamatan','kode_desa','kode_sls','kode_subsls')
LEVELS=('kecamatan','desa','sls','subsls')
LENGTHS={'kode_kabupaten':4,'kode_kecamatan':7,'kode_desa':10,'kode_sls':14,'kode_subsls':16}


@dataclass(frozen=True)
class GeoBucket:
    system: str
    concept: str
    level: str
    codes: tuple
    status: str

    @property
    def key(self):
        return json.dumps([self.system,self.concept,self.level,*self.codes],ensure_ascii=False,separators=(',',':'))

    def as_dict(self):
        return dict(geo_key=self.key,system=self.system,concept=self.concept,level=self.level,
                    raw_codes=dict(zip(FIELDS,self.codes)),geo_status=self.status,
                    display_label=self.codes[LEVELS.index(self.level)+1] or self.status)


def bucket(system,concept,level,values,master_present=True):
    if level not in LEVELS or concept not in ('assignment','response'):
        raise ValueError('GEOGRAPHIC_DIMENSION_NOT_ALLOWED')
    if concept=='response' and (system!='TCZ' or level!='desa'):
        raise ValueError('RESPONSE_GEOGRAPHY_ONLY_UB_DESA')
    codes=tuple(None if values.get(field) is None or not str(values[field]).strip() else str(values[field]).strip() for field in FIELDS)
    end=LEVELS.index(level)+2
    # Do not fabricate response parent codes from substrings of the answer.
    selected=[2] if concept=='response' else list(range(end))
    retained=tuple(code if i in selected else None for i,code in enumerate(codes))
    if not master_present and concept=='assignment':
        return GeoBucket(system,concept,level,retained,'UNMATCHED_ASSIGNMENT')
    status='OBSERVED_CODE_UNVERIFIED'
    for i in selected:
        value=codes[i]
        if value is None:
            status='MISSING_CODE';break
        if not re.fullmatch(r'[0-9]+',value):
            status='INVALID_FORMAT';break
        if len(value)!=LENGTHS[FIELDS[i]]:
            status='INVALID_LENGTH';break
        if not value.startswith('6502'):
            status='OUTSIDE_BASELINE_PREFIX';break
        segment_start=(0,4,7,10,14)[i]
        if i>0 and set(value[segment_start:])=={'0'}:
            status='SPECIAL_ZERO_SEGMENT';break
        if concept=='assignment' and i>0 and not value.startswith(codes[i-1]):
            status='HIERARCHY_MISMATCH';break
    return GeoBucket(system,concept,level,retained,status)


def geography_catalog(connection):
    """Unique geographic keys only; no assignment IDs or respondent counts."""
    entries={}
    administrative_labels={}
    for system,view in [('TGR','mart_assignment_tgr'),('TCZ','mart_assignment_ub')]:
        labels=('kecamatan','desa_kelurahan','sls','subsls')
        columns=','.join('"'+f+'"' for f in (*FIELDS,*labels))
        for row in connection.execute('SELECT '+columns+' FROM "'+view+'" GROUP BY '+columns):
            codes=dict(zip(FIELDS,row[:5]))
            for field_index,label_index in ((1,5),(2,6)):
                code,label=row[field_index],row[label_index]
                if code and label and str(label).strip():
                    administrative_labels.setdefault(str(code),set()).add(str(label).strip())
            for level in LEVELS:
                item=bucket(system,'assignment',level,codes).as_dict()
                existing=entries.setdefault(item['geo_key'],dict(item,label_candidates=set()))
                label=row[5+LEVELS.index(level)]
                if label is not None and str(label).strip():existing['label_candidates'].add(str(label).strip())
    for code,label in connection.execute('SELECT kode_desa,desa_kelurahan FROM mart_ub_a GROUP BY kode_desa,desa_kelurahan'):
        item=bucket('TCZ','response','desa',{'kode_desa':code}).as_dict()
        existing=entries.setdefault(item['geo_key'],dict(item,label_candidates=set()))
        if label is not None and str(label).strip():existing['label_candidates'].add(str(label).strip())
    for item in entries.values():
        item['label_candidates']=sorted(item['label_candidates'])
        item['label_conflict']=len(item['label_candidates'])>1
        item['label_provenance']='Local administrative geography field, not an official reference-code verification'
        if item['concept']=='assignment' and item['geo_status'] in ('SPECIAL_ZERO_SEGMENT','INVALID_LENGTH'):
            fallback=administrative_fallback(item['raw_codes'],administrative_labels)
            if fallback:
                item['display_label'],item['display_level']=fallback
                item['label_provenance']='Available administrative level from observed code; original geographic classification retained'
        if len(item['label_candidates'])==1 and item['geo_status']=='OBSERVED_CODE_UNVERIFIED':
            item['display_label']=item['label_candidates'][0]
    return sorted(entries.values(),key=lambda item:item['geo_key'])


def administrative_fallback(raw_codes, labels):
    """Display only the administrative level actually represented by a code.

    The original bucket and geographic status are never changed or merged.
    """
    values=[str(raw_codes.get(field) or '').strip() for field in reversed(FIELDS)]
    for value in values:
        if not re.fullmatch(r'[0-9]+',value) or len(value) not in (4,7,10,14,16) or not value.startswith('6502'):
            continue
        if value=='6502' or set(value[4:])=={'0'}:
            return 'Bulungan','kabupaten'
        if len(value)>=7 and value[4:7]!='000':
            kec=value[:7]
            if len(value)==7 or set(value[7:])=={'0'}:
                names=labels.get(kec,set())
                return (next(iter(names)) if len(names)==1 else 'Kecamatan '+kec),'kecamatan'
            if len(value)>=10 and value[7:10]!='000' and (len(value)==10 or set(value[10:])=={'0'}):
                desa=value[:10];names=labels.get(desa,set())
                return (next(iter(names)) if len(names)==1 else 'Desa '+desa),'desa'
        return None
    return None
