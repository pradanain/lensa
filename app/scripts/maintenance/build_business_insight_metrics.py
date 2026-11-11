"""Add completed-business insight metrics to the existing registry; no census writes."""
import copy
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'app/src'))
from se2026.analytics.registry import Registry


def main():
    path=ROOT/'app/config/analytics/sources.json'
    sources=json.loads(path.read_text(encoding='utf-8'))
    source_config={s['id']:s for s in json.loads((ROOT/'app/config/sources.json').read_text(encoding='utf-8'))['sources']}
    registry=Registry(ROOT)
    specs=[('umkm_workers','program_usaha','TGR'),('ub_workers','ub_b','TCZ'),
           ('umkm_digital','digital_usaha','TGR'),('ub_digital','ub_c','TCZ'),
           ('umkm_legal','legalitas_usaha','TGR'),('umkm_annual','ekonomi_tahunan','TGR'),
           ('umkm_monthly','ekonomi_bulanan','TGR')]
    needed={
        'umkm_workers':['pekerja_laki_laki','pekerja_perempuan','total_pekerja_jenis_kelamin','status_konsistensi_pekerja'],
        'ub_workers':['pekerja_laki_laki','pekerja_perempuan','jumlah_pekerja','memiliki_catatan_keuangan','total_pendapatan','total_pengeluaran','total_aset'],
        'umkm_digital':['kode_menggunakan_internet','internet_promosi','internet_menerima_pesanan'],
        'ub_digital':['menggunakan_internet','internet_promosi','internet_pesanan','memiliki_nib'],
        'umkm_legal':['punya_nib','mempunyai_laporan_keuangan'],
        'umkm_annual':['total_pendapatan_2025','total_pengeluaran_2025','total_aset_2025'],
        'umkm_monthly':['total_pendapatan_bln','total_pengeluaran_bln','total_aset_bln'],
    }
    for name,sid,system in specs:
        query='dashboard_'+name
        cols=needed[name]
        if not set(cols).issubset(source_config[sid]['columns']):raise ValueError('INSIGHT_SOURCE_COLUMN_NOT_PROVEN')
        key=['assignment_id'] if system=='TCZ' else ['assignment_id','__version_normalized','index1']
        columns=list(dict.fromkeys([*key,*cols,'__key_valid','__conflict']))
        expressions=['p."'+col+'"' for col in columns]
        dimensions={};category_values={}
        if name.endswith('workers'):
            total='jumlah_pekerja' if system=='TCZ' else 'total_pekerja_jenis_kelamin'
            flag='NULL' if system=='TCZ' else "COALESCE(p.status_konsistensi_pekerja,'UNVERIFIED')"
            expressions.append('WORKER_BAND(p.pekerja_laki_laki,p.pekerja_perempuan,p.'+total+','+flag+') AS worker_band')
            columns.append('worker_band');dimensions['worker_band']='worker_band'
            category_values['worker_band']=['ZERO','ONE_FOUR','FIVE_NINETEEN','TWENTY_NINETYNINE','HUNDRED_PLUS','UNAVAILABLE']
        if system=='TGR':
            cohort="EXISTS (SELECT 1 FROM mart_usaha u WHERE u.assignment_id=p.assignment_id AND u.__version_normalized=p.__version_normalized AND u.index1=p.index1 AND u.kode_keberadaan_usaha IN ('1','2')) AND EXISTS (SELECT 1 FROM mart_assignment_tgr a WHERE a.assignment_id=p.assignment_id AND a.status_assignment IN ('APPROVED BY Pengawas','COMPLETED BY Admin Kabupaten'))"
        else:
            cohort="EXISTS (SELECT 1 FROM mart_ub_a u WHERE u.assignment_id=p.assignment_id AND u.status_keberadaan='1. Ditemukan dan masih aktif') AND EXISTS (SELECT 1 FROM mart_assignment_ub a WHERE a.assignment_id=p.assignment_id AND a.status_assignment IN ('APPROVED BY Pengawas','COMPLETED BY Admin Kabupaten'))"
        sql='SELECT '+','.join(expressions)+' FROM mart_'+sid+' p WHERE p.__key_valid=1 AND p.__conflict=0 AND '+cohort
        (ROOT/'app/sql/analytics'/f'{query}.sql').write_text(sql+'\n',encoding='utf-8')
        sources[query]=dict(view='mart_'+sid,query=query,columns=columns,grain_key=key,assignment_column='assignment_id',system=system,dimensions=dimensions,category_values=category_values)
    path.write_text(json.dumps(sources,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    metrics=[]
    def add(template,mid,source,name,**updates):
        m=copy.deepcopy(registry.get(template));m.update(metric_id=mid,source='dashboard_'+source,name=name,description=name+' pada usaha selesai/disetujui.',source_mart=sources['dashboard_'+source]['view'],
            grain=sources['dashboard_'+source]['grain_key'],eligibility=None,eligibility_rule='Ditemukan/Baru (UB: aktif), master APPROVED BY Pengawas / COMPLETED BY Admin Kabupaten. Rincian UMKM pada versi dan indeks tepat; UB assignment ID saja.',
            dimensions=['kecamatan','desa','sls','subsls'],validation_evidence='docs/reports/app/BUSINESS_INSIGHTS.md',validation_status='LOCAL_COMPLETED_COHORT',
            interpretation_limits='Hanya rincian yang tertaut pada cohort usaha selesai/disetujui. NULL/skip tidak menjadi jawaban Tidak. Denominator per respons valid, bukan semua usaha. Tidak membuktikan keunikan fisik atau keaktifan server sekarang. Pekerja bukan orang unik lintas usaha. Interval pekerja bukan klasifikasi resmi skala usaha.')
        m.update(updates);metrics.append(m);return m
    for system,source,prefix in [('usaha','umkm_workers','usaha'),('ub','ub_workers','ub')]:
        for suffix in ['total','male','female','mean']:
            add(system+'.workers_'+suffix+'_valid',prefix+'.completed_workers_'+suffix,source,'Pekerja '+suffix)
        add('usaha.kategori_distribution',prefix+'.completed_worker_bands',source,'Distribusi jumlah pekerja',valid=None,positive=None,distribution_dimension='worker_band',dimensions=['kecamatan','desa','sls','subsls','worker_band'],unit='unit usaha')
    def rate(mid,source,column,yes,no,title,eligibility=None):
        return add('usaha.internet_yes_rate',mid,source,title,valid={'op':'in','column':column,'values':[yes,no]},positive={'op':'eq','column':column,'value':yes},eligibility=eligibility)
    for prefix,source,yes,no in [('usaha','umkm_digital','1','2'),('ub','ub_digital','1. Ya','2. Tidak')]:
        internet='kode_menggunakan_internet' if prefix=='usaha' else 'menggunakan_internet'
        rate(prefix+'.completed_internet_rate',source,internet,yes,no,'Menggunakan internet')
        for suffix,column,title in [('promotion','internet_promosi','Internet untuk promosi'),('orders','internet_menerima_pesanan' if prefix=='usaha' else 'internet_pesanan','Internet untuk menerima pesanan')]:
            rate(prefix+'.completed_'+suffix+'_rate',source,column,yes,no,title,eligibility={'op':'eq','column':internet,'value':yes})
    rate('usaha.completed_nib_rate','umkm_legal','punya_nib','1','2','Memiliki NIB')
    rate('ub.completed_nib_rate','ub_digital','memiliki_nib','1. Ya','2. Tidak','Memiliki NIB')
    rate('usaha.completed_bookkeeping_rate','umkm_legal','mempunyai_laporan_keuangan','1','2','Memiliki laporan keuangan')
    rate('ub.completed_bookkeeping_rate','ub_workers','memiliki_catatan_keuangan','1. Ya','2. Tidak','Memiliki catatan keuangan')
    for prefix,source,period,fields in [
        ('usaha','umkm_annual','Tahun 2025',{'income':'total_pendapatan_2025','expense':'total_pengeluaran_2025','assets':'total_aset_2025'}),
        ('usaha','umkm_monthly','Bulan terakhir usaha mulai 2026',{'income':'total_pendapatan_bln','expense':'total_pengeluaran_bln','assets':'total_aset_bln'}),
        ('ub','ub_workers','Periode sumber UB belum terverifikasi',{'income':'total_pendapatan','expense':'total_pengeluaran','assets':'total_aset'})]:
        for suffix,column in fields.items():
            m=add('usaha.internet_yes_rate',prefix+'.'+('monthly' if source=='umkm_monthly' else 'annual' if source=='umkm_annual' else 'reported')+'_'+suffix+'_coverage',source,'Isian '+suffix+' tercatat',valid=None,positive={'op':'nonempty','column':column},period=period)
            m['interpretation_limits']='Proporsi isian tercatat pada modul yang tertaut; bukan validitas nominal, nilai uang, laba atau pertumbuhan. Satuan uang belum terverifikasi sehingga nominal tidak dijumlahkan. Periode tahunan/bulanan/UB tidak digabung. Missing modul bukan jawaban nol. Cohort usaha selesai/disetujui; wilayah assignment.'
    # Store first, then compile exactly the registered formulas.
    target=ROOT/'app/config/analytics/metrics/business_insights.json'
    target.write_text(json.dumps(metrics,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    compiled=Registry(ROOT)
    for m in metrics:m['sql_formula'],m['sql_bindings']=compiled.compile(m['metric_id'])
    target.write_text(json.dumps(metrics,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'added_metrics':len(metrics),'total_metrics':len(compiled.metrics)}))


if __name__=='__main__':main()
