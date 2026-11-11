import {useQuery} from '@tanstack/react-query'
import {useSearch} from '@tanstack/react-router'
import {api,type Metric,type SearchState} from '@/lib/api'
import {number} from '@/lib/utils'
import {useAreaFilters} from './filter-panel'
import {Card} from './ui/card'
import {ErrorBox,Loading,Notice} from './shared'
import {BandPlot,Composition,RateCard,compactNumber,type InsightDatum} from './business-insight-charts'

export function useBusinessSource(){const search=useSearch({strict:false}) as SearchState;return search.source==='ub'?'ub':'usaha'}
function useMetrics(ids:string[]){
  const filters=useAreaFilters()
  return useQuery({queryKey:['business-insights',ids,filters],queryFn:()=>Promise.all(ids.map(metric_id=>api<Metric>('/analytics/query',{metric_id,filters})))})
}

export function BusinessSectors({onSelect}:{onSelect?:(code:string)=>void}){
  const source=useBusinessSource();const filters=useAreaFilters()
  const result=useQuery({queryKey:['business-sectors',source,filters],queryFn:()=>api<Metric>('/analytics/query',{metric_id:source==='usaha'?'usaha.enumerated_count':'ub.enumerated_count',group_by:['kategori'],filters})})
  const reference=useQuery({queryKey:['reference-summary'],queryFn:()=>api<{category_labels:Record<string,string>}>('/references/summary'),staleTime:3600000})
  if(result.isPending)return <Loading variant="chart"/>
  if(result.error)return <ErrorBox error={result.error}/>
  const data:InsightDatum[]=(result.data?.rows||[]).map(row=>{
    const code=String(row.dimensions.kategori??'__MISSING__')
    return {code,name:code==='__MISSING__'?'Kategori belum tersedia':code.startsWith('__')?'Kategori belum dikenali':code+' · '+(reference.data?.category_labels[code]||'Kategori '+code),value:row.value==null?null:Number(row.value)}
  }).sort((a,b)=>(b.value??-1)-(a.value??-1))
  return <Card className="insight-sector-card"><div className="card-heading"><div><h2>Komposisi sektor usaha</h2><p>{source==='usaha'?'UMKM':'UB'}</p></div></div><Composition key={JSON.stringify([source,filters])} data={data} label="Komposisi sektor usaha" onSelect={onSelect} showPercentages sectorLayout/></Card>
}

const bands:Record<string,string>={ZERO:'0 pekerja',ONE_FOUR:'1–4 pekerja',FIVE_NINETEEN:'5–19 pekerja',TWENTY_NINETYNINE:'20–99 pekerja',HUNDRED_PLUS:'100+ pekerja',UNAVAILABLE:'Belum valid / tersedia'}
export function BusinessWorkers(){
  const source=useBusinessSource()
  const ids=['total','male','female','mean'].map(s=>source+'.completed_workers_'+s).concat(source+'.completed_worker_bands')
  const result=useMetrics(ids)
  if(result.isPending)return <Loading variant="chart"/>
  if(result.error)return <ErrorBox error={result.error}/>
  const [total,male,female,mean,distribution]=result.data!
  const gender=[{name:'Laki-laki',value:male.rows[0]?.value==null?null:Number(male.rows[0].value)},{name:'Perempuan',value:female.rows[0]?.value==null?null:Number(female.rows[0].value)}]
  const data=Object.entries(bands).map(([code,name])=>{const row=distribution.rows.find(r=>r.dimensions.worker_band===code);return {name,value:row?.value==null?row?null:0:Number(row.value)}})
  return <div className="insight-topic"><div className="insight-section-heading"><h2>Tenaga kerja {source==='usaha'?'UMKM':'UB'}</h2><p>Rincian usaha yang selesai atau disetujui.</p></div>
    <div className="insight-summary-grid"><Card><span>Pekerja dilaporkan</span><strong>{number(total.rows[0]?.value)}</strong><small>Bukan orang unik lintas usaha</small></Card><Card><span>Rata-rata per usaha</span><strong>{compactNumber(mean.rows[0]?.value)}</strong><small>Dari jawaban pekerja yang valid</small></Card><Card><span>Usaha dengan jawaban valid</span><strong>{number(total.rows[0]?.denominator)}</strong><small>Komponen dan total pekerja konsisten</small></Card></div>
    <div className="insight-grid"><Card><div className="card-heading"><h2>Komposisi pekerja</h2></div><Composition data={gender} label="Komposisi pekerja menurut jenis kelamin"/></Card><Card><div className="card-heading"><div><h2>Usaha menurut jumlah pekerja</h2><p>Jumlah unit usaha pada setiap rentang</p></div></div><BandPlot data={data} label="Distribusi usaha menurut jumlah pekerja"/><p className="insight-foot">Rentang deskriptif, bukan klasifikasi resmi skala usaha. Jawaban tidak valid tetap ditampilkan terpisah.</p></Card></div>
  </div>
}

export function BusinessDigital(){
  const source=useBusinessSource()
  const ids=['internet','nib','promotion','orders'].map(s=>source+'.completed_'+s+'_rate')
  const result=useMetrics(ids)
  if(result.isPending)return <Loading variant="chart"/>
  if(result.error)return <ErrorBox error={result.error}/>
  const titles=['Penggunaan internet','Kepemilikan NIB','Promosi melalui internet','Pesanan melalui internet']
  return <div className="insight-topic"><div className="insight-section-heading"><h2>Digital &amp; legalitas {source==='usaha'?'UMKM':'UB'}</h2><p>Persentase dari jawaban Ya/Tidak yang tersedia pada usaha selesai atau disetujui.</p></div><div className="insight-grid">{result.data?.map((metric,i)=><RateCard key={metric.metric_id} metric={metric} title={titles[i]} detail={i>1?'Di antara pengguna internet yang menjawab pertanyaan ini.':undefined}/>)}</div><p className="insight-foot">Jawaban kosong tidak dianggap Tidak. Kepemilikan NIB mengikuti jawaban responden, bukan verifikasi izin di luar data lokal.</p></div>
}

export function BusinessEconomy(){
  const source=useBusinessSource()
  const ids=[source+'.completed_bookkeeping_rate',...(source==='usaha'?['usaha.annual_income_coverage','usaha.annual_expense_coverage','usaha.annual_assets_coverage','usaha.monthly_income_coverage','usaha.monthly_expense_coverage','usaha.monthly_assets_coverage']:['ub.reported_income_coverage','ub.reported_expense_coverage','ub.reported_assets_coverage'])]
  const result=useMetrics(ids)
  if(result.isPending)return <Loading variant="chart"/>
  if(result.error)return <ErrorBox error={result.error}/>
  const [bookkeeping,...coverage]=result.data!
  const periods=source==='usaha'?[{title:'Tahunan 2025',metrics:coverage.slice(0,3)},{title:'Bulanan · usaha mulai 2026',metrics:coverage.slice(3)}]:[{title:'Keuangan UB',metrics:coverage}]
  return <div className="insight-topic"><div className="insight-section-heading"><h2>Ekonomi {source==='usaha'?'UMKM':'UB'}</h2><p>Pelaporan keuangan dan kesiapan isian menurut periode sumber.</p></div><RateCard metric={bookkeeping} title={source==='usaha'?'Memiliki laporan keuangan':'Memiliki catatan keuangan'}/><div className="insight-grid">{periods.map(period=><Card className="insight-economic-card" key={period.title}><div className="card-heading"><div><h2>{period.title}</h2><p>Proporsi isian tercatat pada modul yang tersedia</p></div></div><div className="insight-economic-fields">{period.metrics.map((metric,i)=>{
    const row=metric.rows[0];const pct=row?.value==null?null:Number(row.value)
    return <div key={metric.metric_id}><div><span>{['Pendapatan','Pengeluaran','Aset'][i]}</span><strong>{compactNumber(pct)}{pct!=null?'%':''}</strong></div><div className="insight-coverage-track">{pct!=null&&<span style={{width:Math.max(0,Math.min(100,pct))+'%'}}/>}</div><small>{number(row?.numerator)} dari {number(row?.denominator)} record modul{row?.suppressed?' · nilai ditahan':''}</small></div>
  })}</div><p className="insight-foot">{period.metrics[0]?.period}. Isian tercatat belum membuktikan nominalnya valid.</p></Card>)}</div><Notice>Nominal uang belum dijumlahkan karena satuan atau periode belum terverifikasi sepenuhnya. Data tahunan, bulanan, dan UB tetap terpisah.</Notice></div>
}

export function BusinessProfile({open=false}:{open?:boolean}){
  const source=useBusinessSource()
  return <details className="compact-notes insight-profile" open={open||undefined}><summary>Profil usaha dan jaringan</summary><p>Hubungan kantor pusat, cabang, dan unit tercatat pada formulir masing-masing usaha. Kantor atau unit anak tidak dijumlahkan sebagai usaha induk baru.</p><p className="insight-foot">{source==='usaha'?'Gunakan direktori untuk menelusuri rincian jaringan per usaha.':'UB terhubung berdasarkan assignment yang sama pada modul identitas, ekonomi, dan karakteristik.'}</p></details>
}
