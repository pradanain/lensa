"""Build reviewed metric/config artifacts from existing local mart schemas."""
import json
import sqlite3
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'app/src'))
from se2026.common import dump
from se2026.analytics.registry import Registry
from se2026.analytics.geography import FIELDS,LEVELS,LENGTHS


def eq(column,value):return dict(op='eq',column=column,value=value)
def isin(column,values):return dict(op='in',column=column,values=values)
def filled(column):return dict(op='nonempty',column=column)
def conjunction(*nodes):return dict(op='and',args=list(nodes))


def build(root=ROOT):
    con=sqlite3.connect((root/'data/processed/se2026.sqlite').as_uri()+'?mode=ro',uri=True)
    base_keys={
        'assignment_tgr':['assignment_id'],'assignment_ub':['assignment_id'],
        'keluarga':['assignment_id','__version_normalized'],'anggota':['assignment_id','__version_normalized','index1'],
        'bku':['assignment_id','__version_normalized'],'usaha':['assignment_id','__version_normalized','index1'],
        'ub':['assignment_id'],'meteran':['assignment_id','__version_normalized','index_meteran'],
        'kantor_unit':['assignment_id','__version_normalized','index_usaha','index_kantor_unit'],
        'perumahan':['assignment_id','__version_normalized'],'digital_usaha':['assignment_id','__version_normalized','index1'],
        'ub_digital':['assignment_id'],'program_usaha':['assignment_id','__version_normalized','index1'],
        'ub_workers':['assignment_id'],'keluarga_details':['assignment_id','__version_normalized'],
        'usaha_details':['assignment_id','__version_normalized','index1'],
        'sosial_details':['assignment_id','__version_normalized','index1'],
        'family_rosters':['assignment_id','__version_normalized'],
    }
    aliases={'ub':'ub_integrated','ub_digital':'ub_c','ub_workers':'ub_b','keluarga_details':'keluarga_integrated',
             'usaha_details':'usaha_integrated','sosial_details':'sosial_p0_p1'}
    sources={}
    try:
        for sid,key in base_keys.items():
            view='mart_'+aliases.get(sid,sid)
            if sid=='family_rosters':
                cols=['assignment_id','__version_normalized','linked_member_rows','linked_meter_rows','linked_business_rows']
            else:cols=[r[1] for r in con.execute('PRAGMA table_info("'+view+'")')]
            if not cols:raise ValueError('MART_NOT_FOUND')
            dimensions={}
            status={'keluarga':'kode_keberadaan_keluarga','bku':'kode_keberadaan_bku','usaha':'kode_keberadaan_usaha','ub':'status_keberadaan'}.get(sid)
            if status:dimensions['status']=status
            if sid=='usaha':dimensions.update(kbli='kbli',kategori='kategori')
            if sid=='ub':dimensions.update(kbli='kbli_akhir',kategori='kategori_kbli')
            if sid=='perumahan':dimensions['ownership']='status_kepemilikan'
            values={}
            for name,col in dimensions.items():
                if name in ('kbli','kategori'):continue
                observed=con.execute('SELECT "'+col+'" FROM "'+view+'" GROUP BY "'+col+'"').fetchall()
                values[name]=[str(v) for (v,) in observed if v is not None]
            sources[sid]=dict(view=view,columns=cols,grain_key=key,system='TCZ' if sid in ('assignment_ub','ub','ub_digital','ub_workers') else 'TGR',
                              assignment_column='assignment_id',dimensions=dimensions,category_values=values)
            if sid=='family_rosters':sources[sid]['query']='family_rosters'
            if sid=='sosial_details':
                sources[sid]['query']='social_presence'
                sources[sid]['columns']=[*key,'has_sosial_p0','has_p1_pekerjaan','has_p1_disabilitas','has_p1_kronis_a','has_p1_kronis_b']
            if sources[sid]['system']=='TCZ':sources[sid]['response_desa']='kode_desa'
    finally:con.close()
    dump(root/'app/config/analytics/sources.json',sources)
    dump(root/'app/config/analytics/dimensions/geography.json',dict(version=1,fields=FIELDS,levels=LEVELS,observed_code_lengths=LENGTHS,
        scope_prefix='6502',code_type='TEXT',concepts=dict(assignment=list(LEVELS),response=['desa']),
        response_source='mart_ub_a.kode_desa; no inferred parent/SLS codes',
        key='system + concept + level + retained raw composite code path',
        unknown_policy='Preserve missing/special/invalid/outside/hierarchy mismatch/unmatched buckets; never reassign or drop',
        status_not_official_certification=True))
    metrics=[]
    def add(metric_id,name,domain,source,kind='count',unit='record unit-versi',period='snapshot baseline lokal',valid=None,positive=None,
            value_column=None,dimension=None,limit=None,eligibility_rule=None):
        definition=dict(metric_id=metric_id,name=name,description=name+' dalam cakupan sumber lokal yang dinyatakan.',domain=domain,
                        source=source,source_mart=sources[source]['view'] if source!='family_rosters' else 'READ_ONLY_FAMILY_ROSTER_CTE',
                        kind=kind,grain=sources[source]['grain_key'],eligibility=None,valid=valid,positive=positive,
                        numerator_definition='COUNT unit sumber' if kind in ('count','distribution') else 'SUM kontribusi valid '+str(value_column) if kind.startswith('decimal_') else 'COUNT respons/modul positif dan valid',
                        denominator_definition='COUNT record eligible (konteks hitungan; bukan rate)' if kind=='count' else 'COUNT respons valid pada cohort/filter yang sama' if kind!='distribution' else 'Total COUNT respons pada cohort terfilter, sebelum pemisahan kategori',
                        eligibility_rule=eligibility_rule or 'Seluruh record pada mart snapshot aktif, semua status yang terdapat pada mart; filter opsional terikat SQL.',
                        null_skip_rule='NULL/kosong tidak diisi nol; skip/ketiadaan rincian tidak disimpulkan sebagai jawaban tidak. Tidak mengubah sumber.',
                        unit=unit,period=period,dimensions=['kecamatan','desa','sls','subsls',*sources[source]['dimensions']],
                        location_concepts=['assignment']+(['response_desa'] if sources[source].get('response_desa') else []),
                        sensitivity='RESTRICTED_AGGREGATE' if kind.startswith('decimal_') else 'INTERNAL_AGGREGATE',
                        interpretation_limits=limit or 'Deskriptif baseline lokal; bukan estimasi populasi resmi atau bukti cakupan lengkap SQL Lab.',
                        validation_status='DEFINED_PENDING_LOCAL_VALIDATION',sql_formula='pending',sql_bindings=[])
        if value_column:definition['value_column']=value_column
        if dimension:definition['distribution_dimension']=dimension
        if kind=='rate':definition['null_skip_rule']+=' Denominator hanya valid predicate; numerator selalu subset denominator.'
        if source=='family_rosters':
            definition['null_skip_rule']+=' Zero linked_* berarti tidak ada baris anak tertaut pada key-versi ini, bukan isian jawaban responden.'
        metrics.append(definition)
    for sid,name in [('assignment_tgr','Assignment TGR'),('assignment_ub','Assignment UB'),('keluarga','Keluarga'),('anggota','Anggota'),
                     ('bku','BKU'),('usaha','Usaha'),('ub','UB terintegrasi'),('meteran','Meteran'),('kantor_unit','Kantor/unit anak')]:
        add(sid+'.count','Jumlah '+name,'assignment' if sid.startswith('assignment_') else sid,sid,
            unit='assignment' if sid in ('assignment_tgr','assignment_ub','ub') else 'record pada grain sumber')
    for sid in ['assignment_tgr','assignment_ub']:
        add(sid+'.questionnaire_coverage','Proporsi assignment dengan record kuesioner','assignment',sid,'rate','persen',
            valid=isin('status_kuesioner',['ADA_KUESIONER','TANPA_KUESIONER']),positive=eq('status_kuesioner','ADA_KUESIONER'),
            limit='Ada record root menurut sumber lokal; bukan verifikasi final/submitted dan bukan kesamaan versi modul.')
    for sid in ['keluarga','bku','usaha','ub']:
        add(sid+'.existence_distribution','Distribusi status keberadaan '+sid,sid,sid,'distribution',dimension='status',
            limit='Semua status dan kategori kosong/tidak dikenali tetap menjadi bucket; kode 00 usaha tidak diubah menjadi kode geografis/identitas lain.')
    for sid in ['usaha','ub']:
        for dimension in ['kbli','kategori']:
            add(sid+'.'+dimension+'_distribution','Distribusi '+dimension+' '+sid,'klasifikasi_usaha',sid,'distribution',dimension=dimension,
                limit='KBLI lima digit dan kategori huruf diamati secara lokal; missing/invalid bucket tetap dihitung. Tidak memverifikasi ketepatan kegiatan atau mengubah kode.')
    add('usaha.kbli_coverage','Proporsi usaha dengan format KBLI lima digit','klasifikasi_usaha','usaha','rate','persen',
        positive=dict(op='kbli_valid',column='kbli'),limit='Mengukur format/ketersediaan kode, bukan validitas substantif klasifikasi.')
    add('perumahan.ownership_distribution','Distribusi kode status kepemilikan rumah','perumahan','perumahan','distribution',dimension='ownership',
        limit='Kode 1–5 disajikan sebagai kode yang tersedia; tidak menebak label kategori atau menyebut semua keluarga menjawab perumahan.')
    add('perumahan.ownership_coverage','Keterisian kode kepemilikan perumahan','perumahan','perumahan','rate','persen',
        positive=isin('status_kepemilikan',[1,2,3,4,5]),limit='Denominator adalah seluruh modul perumahan, bukan seluruh master keluarga.')
    add('usaha.internet_yes_rate','Proporsi penggunaan internet dari jawaban valid','digitalisasi','digital_usaha','rate','persen',
        valid=isin('kode_menggunakan_internet',['1','2']),positive=eq('kode_menggunakan_internet','1'),
        eligibility_rule='Seluruh record modul digital; SQL historis membatasi usaha ditemukan/baru pada waktu ekstraksi.',
        limit='Kode 1/2 diverifikasi terhadap label Ya/Tidak lokal. NULL atau kode lain dikeluarkan denominator, bukan dianggap Tidak.')
    add('ub.internet_yes_rate','Proporsi UB menggunakan internet dari jawaban valid','digitalisasi','ub_digital','rate','persen',
        valid=isin('menggunakan_internet',['1. Ya','2. Tidak']),positive=eq('menggunakan_internet','1. Ya'),
        limit='Hanya label valid yang diamati di modul UB. Denominator bukan otomatis 226; versi historis hanya provenance non-blocking.')
    for source,domain,modules in [
        ('keluarga_details','cakupan_keluarga',['perumahan','aset_keluarga','screening']),
        ('usaha_details','cakupan_usaha',['legalitas_usaha','kegiatan_usaha','digital_usaha','program_usaha','ekonomi_tahunan','ekonomi_bulanan','jaringan_usaha']),
        ('sosial_details','cakupan_anggota',['sosial_p0','p1_pekerjaan','p1_disabilitas','p1_kronis_a','p1_kronis_b'])]:
        for module in modules:
            add(source+'.'+module+'_coverage','Cakupan tautan modul '+module,domain,source,'rate','persen',positive=eq('has_'+module,1),
                limit='Mengukur kehadiran key modul pada induk/union, bukan jawaban lengkap setiap kolom. Rincian unmatched tetap ada pada mart mandiri; tidak latest-fill lintas versi.')
    add('ub.complete_module_coverage','Kelengkapan master dan A/B/C per assignment','cakupan_ub','ub','rate','persen',
        positive=conjunction(*[eq('has_'+s,1) for s in ['assignment_ub','ub_a','ub_b','ub_c']]),
        limit='JOIN assignment_id saja; kehadiran modul berbeda dari keterisian variabel keuangan.')
    for source,prefix,total,male,female,flag in [
        ('program_usaha','usaha','total_pekerja_jenis_kelamin','pekerja_laki_laki','pekerja_perempuan','status_konsistensi_pekerja'),
        ('ub_workers','ub','jumlah_pekerja','pekerja_laki_laki','pekerja_perempuan',None)]:
        valid=dict(op='worker_valid',columns=[male,female,total])
        if flag:valid=conjunction(eq(flag,'SESUAI'),valid)
        for name,column in [('total',total),('male',male),('female',female)]:
            add(prefix+'.workers_'+name+'_valid','Jumlah pekerja '+name+' pada respons konsisten','tenaga_kerja',source,'decimal_sum','orang dilaporkan',
                'periode pekerja tidak dinyatakan eksplisit pada SQL lokal',valid=valid,value_column=column,
                limit='Kedua komponen dan total harus nonnegatif, integral, finite, dan jumlah komponen=total; usaha juga mensyaratkan flag SESUAI. Denominator record respons valid, bukan FTE atau pekerja unik lintas usaha.')
        add(prefix+'.workers_mean_valid','Rata-rata pekerja per record respons valid','tenaga_kerja',source,'decimal_mean','orang per record valid',
            'periode pekerja tidak dinyatakan eksplisit pada SQL lokal',valid=valid,value_column=total,
            limit='Rasio total pekerja dilaporkan / jumlah record valid; bukan rerata persentase wilayah, bukan FTE dan bukan produktivitas.')
    add('family_rosters.count','Jumlah keluarga setelah pre-aggregation roster','keluarga','family_rosters')
    for field,label in [('linked_member_rows','anggota'),('linked_meter_rows','meteran'),('linked_business_rows','usaha')]:
        add('family_rosters.'+label+'_linked_rows','Jumlah baris '+label+' tertaut ke keluarga-versi','keluarga','family_rosters','decimal_sum','baris roster tertaut',
            valid=None,value_column=field,limit='Anak diagregasikan pada assignment_id+versi sebelum JOIN. Hanya tautan exact-version ke keluarga; unmatched tetap pada mart anak.')
        add('family_rosters.'+label+'_presence','Proporsi keluarga memiliki tautan roster '+label,'keluarga','family_rosters','rate','persen',
            positive=dict(op='gt',column=field,value=0),limit='Ada baris roster yang tertaut, bukan pengisian jawaban jumlah anak/anggota/usaha. Tidak mencakup usaha pada assignment BKU.')
    folder=root/'app/config/analytics/metrics'
    folder.mkdir(parents=True,exist_ok=True)
    # Definitions are partitioned by domain; this is the single registry source.
    groups={}
    for metric in metrics:groups.setdefault(metric['domain'],[]).append(metric)
    for domain,items in groups.items():dump(folder/(domain+'.json'),items)
    registry=Registry(root)
    for metric in metrics:
        metric['sql_formula'],metric['sql_bindings']=registry.compile(metric['metric_id'])
    for domain,items in groups.items():dump(folder/(domain+'.json'),items)
    print('Defined',len(metrics),'metrics across',len(groups),'domains; local schemas only.')


if __name__=='__main__':build()
