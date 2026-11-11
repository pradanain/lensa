"""Trusted structured metric definitions; users cannot supply SQL expressions."""
import json
from pathlib import Path

from ..common import q


class AnalyticsError(ValueError):
    """Safe code-only errors, never containing input values or respondent data."""


def nonempty(expression):
    return 'NULLIF(TRIM(CAST('+expression+" AS TEXT)),'') IS NOT NULL"


class Registry:
    def __init__(self,root):
        self.root=Path(root)
        self.sources=json.loads((self.root/'app/config/analytics/sources.json').read_text(encoding='utf-8'))
        self.metrics={}
        for path in sorted((self.root/'app/config/analytics/metrics').glob('*.json')):
            for item in json.loads(path.read_text(encoding='utf-8')):
                if item['metric_id'] in self.metrics:
                    raise AnalyticsError('DUPLICATE_METRIC_ID')
                if item['source'] not in self.sources:
                    raise AnalyticsError('SOURCE_NOT_ALLOWED')
                self.metrics[item['metric_id']]=item
        self._needed={sid:set([*s['grain_key'],s['assignment_column'],*s['dimensions'].values()]) for sid,s in self.sources.items()}
        def references(node):
            if not node:return set()
            if node['op'] in ('and','or'):
                return set().union(*(references(child) for child in node['args']))
            return set(node.get('columns',[])) | ({node['column']} if 'column' in node else set())
        for metric in self.metrics.values():
            columns=self._needed[metric['source']]
            for field in ('eligibility','valid','positive'):columns.update(references(metric.get(field)))
            if 'value_column' in metric:columns.add(metric['value_column'])

    def get(self,metric_id):
        if metric_id not in self.metrics:
            raise AnalyticsError('METRIC_NOT_ALLOWED')
        return self.metrics[metric_id]

    def relation(self,source):
        definition=self.sources[source]
        if definition.get('query') in ('family_rosters','social_presence','enumerated_usaha','enumerated_ub','enumerated_business_bku','enumerated_family','enumerated_bku','enumerated_unclassified','enumerated_residential','enumerated_mixed','qualified_usaha','qualified_ub','qualified_family','qualified_bku','review_usaha',
            'dashboard_umkm_workers','dashboard_ub_workers','dashboard_umkm_digital','dashboard_ub_digital','dashboard_umkm_legal','dashboard_umkm_annual','dashboard_umkm_monthly'):
            sql=(self.root/'app/sql/analytics'/(definition['query']+'.sql')).read_text(encoding='utf-8').strip().rstrip(';')
            return '(SELECT * FROM ('+sql+') LIMIT -1 OFFSET 0)'
        view=definition['view']
        if not view.startswith('mart_') or not view.replace('_','').isalnum():
            raise AnalyticsError('SOURCE_IDENTIFIER_NOT_ALLOWED')
        # LIMIT/OFFSET is a read-only query-flattening fence. In particular it
        # prevents GROUP BY of coalesced social keys from turning five indexed
        # LEFT JOINs into nested full scans. Project only metric/dimension fields.
        columns=[col for col in definition['columns'] if col in self._needed[source]]
        return '(SELECT '+','.join(map(q,columns))+' FROM '+q(view)+' LIMIT -1 OFFSET 0)'

    def condition(self,node,source,parameters):
        if not node:
            return '1=1'
        operation=node['op']
        if operation in ('and','or'):
            return '('+(' AND ' if operation=='and' else ' OR ').join(self.condition(child,source,parameters) for child in node['args'])+')'
        allowed=self.sources[source]['columns']
        if operation=='worker_valid':
            cols=node['columns']
            if len(cols)!=3 or any(col not in allowed for col in cols):
                raise AnalyticsError('METRIC_COLUMN_NOT_ALLOWED')
            return 'WORKER_VALID('+','.join('e.'+q(col) for col in cols)+')=1'
        col=node['column']
        if col not in allowed:
            raise AnalyticsError('METRIC_COLUMN_NOT_ALLOWED')
        expression='e.'+q(col)
        if operation=='nonempty':return nonempty(expression)
        if operation=='kbli_valid':return 'KBLI_VALID('+expression+')=1'
        if operation=='in':
            values=node['values']
            if not values:raise AnalyticsError('EMPTY_PREDICATE_VALUES')
            parameters.extend(values)
            return expression+' IN ('+','.join('?' for _ in values)+')'
        if operation=='eq':
            parameters.append(node['value'])
            return expression+'=?'
        if operation=='gt':
            parameters.append(node['value'])
            return expression+'>?'
        raise AnalyticsError('PREDICATE_NOT_ALLOWED')

    def compile(self,metric_id):
        metric=self.get(metric_id)
        parameters=[]
        eligible=self.condition(metric.get('eligibility'),metric['source'],parameters)
        # SELECT placeholders precede WHERE placeholders in SQLite binding order.
        select_parameters=[]
        valid=self.condition(metric.get('valid'),metric['source'],select_parameters)
        positive=self.condition(metric.get('positive'),metric['source'],select_parameters)
        denominator='COALESCE(SUM(CASE WHEN '+valid+' THEN 1 ELSE 0 END),0)'
        if metric['kind'] in ('decimal_sum','decimal_mean'):
            col=metric['value_column']
            if col not in self.sources[metric['source']]['columns']:
                raise AnalyticsError('METRIC_COLUMN_NOT_ALLOWED')
            numerator='DEC_SUM(CASE WHEN '+valid+' THEN e.'+q(col)+' END)'
            # valid predicate appears twice, so compile its parameters again.
            first=[];self.condition(metric.get('valid'),metric['source'],first)
            bindings=first+first+parameters
        else:
            numerator='COALESCE(SUM(CASE WHEN '+valid+' AND '+positive+' THEN 1 ELSE 0 END),0)'
            first=[];self.condition(metric.get('valid'),metric['source'],first)
            last=[];self.condition(metric.get('positive'),metric['source'],last)
            bindings=first+last+first+parameters
        dimension=metric.get('distribution_dimension')
        expression='e.'+q(self.sources[metric['source']]['dimensions'][dimension]) if dimension else None
        sql=('SELECT '+(expression+',' if expression else '')+'COUNT(*) AS eligible_rows,'+numerator+' AS numerator,'+denominator+' AS denominator '
             'FROM '+self.relation(metric['source'])+' e WHERE '+eligible)
        if expression:sql+=' GROUP BY '+expression
        return sql,bindings
