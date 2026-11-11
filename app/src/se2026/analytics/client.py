"""Bound-value aggregate queries and whitelist dimensions. No row-level API."""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

from ..common import q
from .geography import FIELDS,LEVELS,LENGTHS,bucket,geography_catalog
from .numeric import ExactSum,ratio,worker_valid,worker_band,read_field
from .registry import AnalyticsError,Registry
from .business_audit import register_population


def kbli_valid(value):
    return int(value is not None and re.fullmatch(r'[0-9]{5}',str(value).strip()) is not None)


def read_authorizer(action,arg1,arg2,database,trigger):
    allowed={sqlite3.SQLITE_SELECT,sqlite3.SQLITE_READ,sqlite3.SQLITE_FUNCTION,sqlite3.SQLITE_TRANSACTION,
             sqlite3.SQLITE_RECURSIVE}
    return sqlite3.SQLITE_OK if action in allowed else sqlite3.SQLITE_DENY


def complementary_kbli_geo(rows, suppressed):
    """A published KBLI total must not reveal its sole withheld geographic cell."""
    hidden=set(suppressed);groups={}
    for i,row in enumerate(rows):
        dimensions=row.get('dimensions',{})
        if 'kbli' in dimensions and any(level in dimensions for level in LEVELS):
            groups.setdefault(dimensions['kbli'],[]).append(i)
    for indices in groups.values():
        if sum(i in hidden for i in indices)==1:
            candidates=[i for i in indices if i not in hidden and rows[i].get('eligible_rows')]
            if candidates:hidden.add(min(candidates,key=lambda i:rows[i]['eligible_rows']))
    return sorted(hidden)


class Analytics:
    def __init__(self,database=None,root=None):
        self.root=Path(root or Path(__file__).resolve().parents[4])
        path=Path(database or self.root/'data/processed/se2026.sqlite').resolve()
        self.registry=Registry(self.root)
        policy=json.loads((self.root/'app/config/analytics/dimensions/geography.json').read_text(encoding='utf-8'))
        if (policy['fields']!=list(FIELDS) or policy['levels']!=list(LEVELS) or policy['code_type']!='TEXT'
            or policy['observed_code_lengths']!=LENGTHS or policy['scope_prefix']!='6502'):
            raise AnalyticsError('DIMENSION_POLICY_MISMATCH')
        self._connection=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)
        self._connection.execute('PRAGMA query_only=ON')
        self._connection.create_aggregate('DEC_SUM',1,ExactSum)
        self._connection.create_function('WORKER_VALID',3,worker_valid,deterministic=True)
        self._connection.create_function('WORKER_BAND',4,worker_band,deterministic=True)
        self._connection.create_function('KBLI_VALID',1,kbli_valid,deterministic=True)
        register_population(self._connection, path, self.root)
        self._connection.execute('BEGIN')
        self._schemas={}
        self._checked=set()
        self._masters=set()
        self._master_total={}
        self._geography_cache=None
        self._provenance=[]
        if self._connection.execute("SELECT COUNT(*) FROM sqlite_master WHERE name='imported_files'").fetchone()[0]:
            self._provenance=[dict(source_id=sid,source_sha256=checksum,batch_id=batch) for sid,checksum,batch in
                self._connection.execute('SELECT f.source_id,f.sha256,f.batch_id FROM imported_files f JOIN active_imports a ON a.import_id=f.import_id ORDER BY f.source_id')]

    def __enter__(self):return self

    def __exit__(self,*args):self.close()

    def close(self):
        self._connection.close()

    def _schema(self,source):
        if source not in self._schemas:
            relation=self.registry.relation(source)
            self._schemas[source]={entry[0] for entry in self._connection.execute('SELECT * FROM '+relation+' LIMIT 0').description}
        return self._schemas[source]

    def _check_source(self,source):
        if source in self._checked:return
        definition=self.registry.sources[source]
        schema=self._schema(source)
        if not set([*definition['grain_key'],definition['assignment_column']]).issubset(schema):
            raise AnalyticsError('SOURCE_SCHEMA_MISMATCH')
        key=definition['grain_key']
        relation=self.registry.relation(source)
        columns=','.join(map(q,key))
        invalid=' OR '.join('NULLIF(TRIM(CAST('+q(col)+" AS TEXT)),'') IS NULL" for col in key)
        if self._connection.execute('SELECT COUNT(*) FROM '+relation+' WHERE '+invalid).fetchone()[0]:
            raise AnalyticsError('SOURCE_GRAIN_KEY_INVALID')
        duplicate=self._connection.execute('SELECT COUNT(*) FROM (SELECT '+columns+' FROM '+relation+' GROUP BY '+columns+' HAVING COUNT(*)>1)').fetchone()[0]
        if duplicate:raise AnalyticsError('SOURCE_GRAIN_NOT_UNIQUE')
        self._checked.add(source)

    def _check_master(self,system):
        if system in self._masters:return
        source='assignment_tgr' if system=='TGR' else 'assignment_ub'
        self._check_source(source)
        self._master_total[system]=self._connection.execute('SELECT COUNT(*) FROM '+self.registry.relation(source)).fetchone()[0]
        self._masters.add(system)

    def validate_definitions(self,progress=None):
        required=['metric_id','name','description','domain','source','grain','numerator_definition',
                  'denominator_definition','eligibility_rule','null_skip_rule','unit','period','dimensions',
                  'sensitivity','interpretation_limits','validation_status','sql_formula']
        for metric in self.registry.metrics.values():
            if progress is not None and metric['source'] not in self._checked:progress(metric['source'])
            if any(field not in metric for field in required):
                raise AnalyticsError('METRIC_METADATA_INCOMPLETE')
            self._check_source(metric['source'])
            sql,parameters=self.registry.compile(metric['metric_id'])
            if sql!=metric['sql_formula']:
                raise AnalyticsError('REGISTRY_SQL_FORMULA_DRIFT')
            # EXPLAIN checks every reference and binding without executing aggregation.
            self._connection.execute('EXPLAIN '+sql,parameters).fetchall()
        return len(self.registry.metrics)

    def _dimension(self,name,source,concept):
        definition=self.registry.sources[source]
        if name in LEVELS:
            if concept=='response' and (definition['system']!='TCZ' or name!='desa' or not definition.get('response_desa')):
                raise AnalyticsError('RESPONSE_GEOGRAPHY_NOT_AVAILABLE')
            return ('geo',name)
        if name not in definition['dimensions']:
            raise AnalyticsError('DIMENSION_NOT_ALLOWED')
        if definition['dimensions'][name] not in self._schema(source):
            raise AnalyticsError('DIMENSION_NOT_AVAILABLE')
        return ('column',definition['dimensions'][name])

    def _query(self,metric_id,filters=None,group_by=None,location='assignment'):
        metric=self.registry.get(metric_id)
        source=metric['source'];definition=self.registry.sources[source]
        self._check_source(source)
        if location not in ('assignment','response'):
            raise AnalyticsError('GEOGRAPHIC_CONCEPT_NOT_ALLOWED')
        if filters is not None and (not isinstance(filters,dict) or not all(isinstance(k,str) for k in filters)):
            raise AnalyticsError('FILTERS_NOT_ALLOWED')
        filters=filters or {}
        if group_by is not None and not isinstance(group_by,(str,list,tuple)):
            raise AnalyticsError('GROUPING_NOT_ALLOWED')
        groups=[group_by] if isinstance(group_by,str) else list(group_by or [])
        if not all(isinstance(g,str) for g in groups):raise AnalyticsError('GROUPING_NOT_ALLOWED')
        default=metric.get('distribution_dimension')
        if default and default not in groups:groups.append(default)
        if len(groups)!=len(set(groups)) or len(groups)>3 or sum(g in LEVELS for g in groups)>1:
            raise AnalyticsError('GROUPING_NOT_ALLOWED')
        for name in [*groups,*filters]:self._dimension(name,source,location)
        geo=any(name in LEVELS for name in [*groups,*filters])
        parameters=[]
        select_parameters=[]
        valid=self.registry.condition(metric.get('valid'),source,select_parameters)
        positive=self.registry.condition(metric.get('positive'),source,select_parameters)
        first=[];self.registry.condition(metric.get('valid'),source,first)
        last=[];self.registry.condition(metric.get('positive'),source,last)
        denominator='COALESCE(SUM(CASE WHEN '+valid+' THEN 1 ELSE 0 END),0)'
        if metric['kind'] in ('decimal_sum','decimal_mean'):
            numerator='DEC_SUM(CASE WHEN '+valid+' THEN e.'+q(metric['value_column'])+' END)'
            parameters+=first+first
        else:
            numerator='COALESCE(SUM(CASE WHEN '+valid+' AND '+positive+' THEN 1 ELSE 0 END),0)'
            parameters+=first+last+first
        expressions=[];group_expressions=[];readers=[]
        join=''
        if geo and location=='assignment':
            self._check_master(definition['system'])
            master='assignment_tgr' if definition['system']=='TGR' else 'assignment_ub'
            join=(' LEFT JOIN '+q('clean_'+master)+' g INDEXED BY '+q('ix_join_'+master)+
                  " ON g.__import_id=(SELECT import_id FROM active_imports WHERE source_id='"+master+"') AND e."+q(definition['assignment_column'])+'=g.assignment_id')
        elif geo:
            self._check_source('ub')
            duplicates=self._connection.execute('SELECT COUNT(*) FROM (SELECT assignment_id FROM mart_ub_a GROUP BY assignment_id HAVING COUNT(*)>1)').fetchone()[0]
            if duplicates:raise AnalyticsError('RESPONSE_GEOGRAPHY_GRAIN_NOT_UNIQUE')
            join=(" LEFT JOIN clean_ub_a r INDEXED BY ix_join_ub_a ON r.__import_id=(SELECT import_id FROM active_imports WHERE source_id='ub_a') AND e."+q(definition['assignment_column'])+'=r.id_penghubung')
        for name in groups:
            kind,column=self._dimension(name,source,location)
            if kind=='geo':
                if location=='response':
                    cols=['NULL','NULL','r.'+q(definition['response_desa']),'NULL','NULL','r.id_penghubung IS NOT NULL']
                else:
                    cols=['g.'+q(field) for field in FIELDS]+['g.assignment_id IS NOT NULL']
                expressions+=cols;group_expressions+=cols
                readers.append((name,'geo',len(cols)))
            else:
                expressions.append('e.'+q(column));group_expressions.append('e.'+q(column))
                readers.append((name,'column',1))
        where=self.registry.condition(metric.get('eligibility'),source,parameters)
        for name,value in filters.items():
            if isinstance(value,(str,int)) and not isinstance(value,bool):values=[str(value)]
            elif isinstance(value,(list,tuple)) and value and len(value)<=100 and all(isinstance(v,(str,int)) and not isinstance(v,bool) for v in value):values=[str(v) for v in value]
            else:raise AnalyticsError('FILTER_VALUE_NOT_ALLOWED')
            if any(len(v)>200 for v in values):raise AnalyticsError('FILTER_VALUE_TOO_LONG')
            kind,column=self._dimension(name,source,location)
            if kind=='geo':
                expr='r.'+q(definition['response_desa']) if location=='response' else 'g.'+q('kode_'+name)
            else:expr='e.'+q(column)
            # Normalize only surrounding whitespace in approved categorical fields.
            where+=' AND TRIM(CAST('+expr+' AS TEXT)) IN ('+','.join('?' for _ in values)+')'
            parameters+=values
        select=expressions+['COUNT(*)',numerator,denominator]
        sql='SELECT '+','.join(select)+' FROM '+self.registry.relation(source)+' e'+join+' WHERE '+where
        if group_expressions:sql+=' GROUP BY '+','.join(group_expressions)
        self._connection.set_authorizer(read_authorizer)
        try:
            rows=self._connection.execute(sql,parameters).fetchall()
        except sqlite3.Error:
            raise AnalyticsError('AGGREGATE_QUERY_FAILED') from None
        finally:
            self._connection.set_authorizer(None)
        result=[]
        for row in rows:
            offset=0;dimensions={}
            for name,kind,width in readers:
                if kind=='geo':
                    codes=dict(zip(FIELDS,row[offset:offset+5]))
                    item=bucket(definition['system'],location,name,codes,bool(row[offset+5])).as_dict()
                    if self._geography_cache is None:
                        self._geography_cache={g['geo_key']:g for g in self.geography()}
                    dimensions[name]=self._geography_cache.get(item['geo_key'],item)
                else:
                    raw=row[offset]
                    dimensions[name]=self._safe_category(name,raw,definition)
                offset+=width
            eligible,num,den=row[offset:offset+3]
            result.append(dict(dimensions=dimensions,eligible_rows=eligible,numerator=num,denominator=den,
                               excluded_rows=eligible-den,suppressed=False))
        # Multiple raw labels can normalize to one safe category. Reaggregate counts,
        # never percentages, after normalization (no respondent labels are returned).
        combined={}
        for row in result:
            key=json.dumps(row['dimensions'],sort_keys=True,ensure_ascii=False)
            if key not in combined:combined[key]=row;continue
            target=combined[key]
            for field in ['eligible_rows','denominator','excluded_rows']:target[field]+=row[field]
            if metric['kind'] in ('decimal_sum','decimal_mean'):
                acc=ExactSum();acc.add(target['numerator']);acc.add(row['numerator']);target['numerator']=acc.result()
            else:target['numerator']+=row['numerator']
        result=list(combined.values())
        distribution_den=sum(row['denominator'] for row in result)
        for row in result:
            if metric['kind']=='rate':row['percentage']=ratio(row['numerator'],row['denominator'],100)
            elif metric['kind']=='distribution':row['percentage']=ratio(row['numerator'],distribution_den,100)
            else:row['percentage']=None
            if metric['kind']=='decimal_mean':row['value']=ratio(row['numerator'],row['denominator'])
            elif metric['kind']=='rate':row['value']=row['percentage']
            else:row['value']=row['numerator']
        return metric,result

    @staticmethod
    def _safe_category(name,value,definition):
        if value is None or not str(value).strip():return '__MISSING__'
        text=str(value).strip()
        if name=='kbli':return text if kbli_valid(text) else '__INVALID_CODE__'
        if name=='kategori':
            match=re.fullmatch(r'([A-Z])(?:[.\s-].*)?',text)
            return match[1] if match else '__INVALID_CODE__'
        allowed=definition.get('category_values',{}).get(name,[])
        return text if text in allowed else '__OTHER_UNRECOGNIZED__'

    def query(self,metric_id,filters=None,group_by=None,location='assignment'):
        metric,rows=self._query(metric_id,filters,group_by,location)
        grouped=bool(group_by or metric.get('distribution_dimension'))
        # No health metrics or individual dimensions are registered. A minimum
        # contributor rule still protects narrow operational/worker aggregates.
        suppressed=[]
        for i,row in enumerate(rows):
            n=row['eligible_rows']
            small=0<n<5
            if metric['kind'] in ('decimal_sum','decimal_mean'):
                small|=0<row['denominator']<5
            if metric['kind']=='rate':
                small|=0<row['numerator']<5 or 0<row['denominator']-row['numerator']<5
            if small:suppressed.append(i)
        if grouped and len(suppressed)==1:
            candidates=[i for i in range(len(rows)) if i not in suppressed]
            if candidates:suppressed.append(min(candidates,key=lambda i:rows[i]['eligible_rows']))
        suppressed=complementary_kbli_geo(rows,suppressed)
        for i in suppressed:
            for field in ['eligible_rows','numerator','denominator','excluded_rows','percentage','value']:rows[i][field]=None
            rows[i]['suppressed']=True
        if suppressed and metric['kind']=='distribution':
            for row in rows:row['percentage']=None
        return dict(metric_id=metric_id,kind=metric['kind'],grain=metric['grain'],unit=metric['unit'],period=metric['period'],
                    location_concept=location,rows=rows,suppression=dict(minimum_contributors=5,suppressed_rows=len(suppressed),grand_totals_omitted=True),
                    provenance=self._provenance,interpretation_limits=metric['interpretation_limits'],
                    validation_status=metric['validation_status'])

    def geography(self):
        self._check_master('TGR');self._check_master('TCZ')
        return geography_catalog(self._connection)

    def ub_geography_comparison(self):
        self._check_source('ub');self._check_master('TCZ')
        row=self._connection.execute('''SELECT COUNT(*),COALESCE(SUM(a.kode_desa<>m.kode_desa
            AND NULLIF(TRIM(a.kode_desa),'') IS NOT NULL AND NULLIF(TRIM(m.kode_desa),'') IS NOT NULL),0)
            FROM mart_ub_a a LEFT JOIN mart_assignment_ub m ON a.assignment_id=m.assignment_id''').fetchone()
        return dict(ub_assignments=row[0],different_nonempty_desa_codes=row[1],policy='PRESERVE_BOTH_CONCEPTS_NO_REASSIGNMENT')

    def numeric_profile(self,field_id):
        from collections import Counter
        fields=json.loads((self.root/'app/config/analytics/numeric_fields.json').read_text(encoding='utf-8'))
        if field_id not in fields:raise AnalyticsError('NUMERIC_FIELD_NOT_ALLOWED')
        definition=fields[field_id]
        schema={r[1] for r in self._connection.execute('PRAGMA table_info('+q(definition['view'])+')')}
        if definition['column'] not in schema:raise AnalyticsError('NUMERIC_FIELD_SCHEMA_MISMATCH')
        statuses=Counter()
        for (value,) in self._connection.execute('SELECT '+q(definition['column'])+' FROM '+q(definition['view'])):
            statuses[read_field(value,definition).status]+=1
        return dict(field_id=field_id,unit=definition['unit'],period=definition['period'],unit_verified=False,
                    format_policy=definition['default_format'],status_counts=dict(statuses),values_exposed=False)
