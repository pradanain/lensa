import {LoadingSkeleton} from './ui/skeleton'
import {useAreaFilters} from './filter-panel'
import {useEffect,useRef,type ReactNode} from 'react'
import {AlertCircle,ArrowUpRight,LockKeyhole,Info} from 'lucide-react'
import {useQuery} from '@tanstack/react-query'
import {init,use as registerCharts,type ECharts} from 'echarts/core'
import {BarChart as EBarChart} from 'echarts/charts'
import {GridComponent,TooltipComponent} from 'echarts/components'
import {SVGRenderer} from 'echarts/renderers'
import {api,type Summary,type Metric} from '@/lib/api'
import {number} from '@/lib/utils'
import {Card} from './ui/card'
import {Button} from './ui/button'

registerCharts([EBarChart,GridComponent,TooltipComponent,SVGRenderer])

export function PageHead({eyebrow,title,description,children}:{eyebrow:string;title:string;description:string;children?:ReactNode}){
  return <div className="page-head"><div>{eyebrow&&<div className="eyebrow">{eyebrow}</div>}<h1>{title}</h1>{description&&<p>{description}</p>}</div>{children}</div>
}
export function Loading({label='Memuat data...',variant='card'}:{label?:string;variant?:'card'|'table'|'chart'|'form'|'filters'|'dashboard'}){return <LoadingSkeleton label={label} variant={variant}/>}
export function ErrorBox({error,retry}:{error:Error|null;retry?:()=>void}){return <div className="notice notice-warning" role="alert"><AlertCircle size={19}/><div><strong>Data belum dapat dimuat</strong><p>{error?.message||'Periksa koneksi ke layanan lokal.'}</p>{retry&&<Button variant="outline" size="sm" onClick={retry}>Coba lagi</Button>}</div></div>}
export function Notice({children,tone='neutral'}:{children:ReactNode;tone?:string}){return <div className={'notice notice-'+tone}><Info size={18}/><div>{children}</div></div>}
export function Restricted(){return <Card className="restricted"><LockKeyhole size={30}/><h3>Direktori memerlukan akses detail</h3><p>Akun pembaca agregat dapat menelusuri ringkasan dan referensi. Hubungi administrator untuk akses direktori dan kuesioner.</p></Card>}
export function TabBar({tabs,value,onChange}:{tabs:{id:string;label:string}[];value:string;onChange:(id:string)=>void}){
  return <div className="tabs" role="tablist" aria-label="Bagian halaman">{tabs.map((tab,i)=><button type="button" role="tab" aria-selected={value===tab.id} tabIndex={value===tab.id?0:-1} key={tab.id} className={value===tab.id?'active':''} onClick={()=>onChange(tab.id)} onKeyDown={event=>{if(['ArrowRight','ArrowLeft'].includes(event.key)){event.preventDefault();const next=(i+(event.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;onChange(tabs[next].id);const siblings=event.currentTarget.parentElement?.querySelectorAll<HTMLButtonElement>('[role="tab"]');siblings?.[next]?.focus()}}}>{tab.label}</button>)}</div>
}
export function StatCard({label,value,note,icon,onClick,accent=false}:{label:string;value:string|number|null|undefined;note:string;icon:ReactNode;onClick?:()=>void;accent?:boolean}){
  return <Card className={'stat-card '+(accent?'stat-accent':'')}><div className="stat-top"><span className="stat-icon">{icon}</span>{onClick&&<button className="icon-link" aria-label={'Lihat '+label} onClick={onClick}><ArrowUpRight size={18}/></button>}</div><div className="stat-value">{number(value)}</div><h3>{label}</h3><p>{note}</p></Card>
}
export function useSummary(filters:Record<string,string>={}){const params=new URLSearchParams(filters);return useQuery({queryKey:['analytics-summary',filters],queryFn:()=>api<Summary>('/analytics/summary?'+params),staleTime:60000})}
export function useBusinessSummary(filters:Record<string,string>,enabled:boolean){const params=new URLSearchParams(filters);return useQuery({queryKey:['business-summary',filters],queryFn:({signal})=>api<Pick<Summary,'counts'>>('/analytics/business-summary?'+params,undefined,undefined,{signal}),enabled,staleTime:300000})}
const metricLabels:Record<string,string>={
  kbli_coverage:'Kode KBLI terisi',kegiatan_usaha_coverage:'Rincian kegiatan usaha',complete_module_coverage:'Modul UB terhubung',
  workers_total_valid:'Jumlah pekerja',workers_mean_valid:'Rata-rata pekerja per usaha',workers_male_valid:'Pekerja laki-laki',workers_female_valid:'Pekerja perempuan',
  internet_yes_rate:'Menggunakan internet',legalitas_usaha_coverage:'Rincian legalitas',digital_usaha_coverage:'Rincian digitalisasi',jaringan_usaha_coverage:'Rincian jaringan usaha',
  anggota_presence:'Keluarga dengan anggota',usaha_presence:'Keluarga dengan usaha',meteran_presence:'Keluarga dengan meteran',ownership_coverage:'Jawaban kepemilikan rumah',perumahan_coverage:'Rincian perumahan',
  sosial_p0_coverage:'Data sosial P0',p1_pekerjaan_coverage:'Data pekerjaan P1',aset_keluarga_coverage:'Rincian aset keluarga',ekonomi_tahunan_coverage:'Rincian ekonomi tahunan',ekonomi_bulanan_coverage:'Rincian ekonomi bulanan',count:'Jumlah kantor / unit',
}
const metricFullLabels:Record<string,string>={
  'usaha.enumerated_residential_count':'Usaha pada bangunan induk tempat tinggal',
  'usaha.enumerated_mixed_count':'Usaha pada bangunan induk campuran',
  'usaha.enumerated_bku_count':'Usaha pada bangunan khusus usaha',
}
function metricLabel(id:string){if(metricFullLabels[id])return metricFullLabels[id];const [source,field]=id.split('.');return (source==='ub'?'UB - ':source==='usaha'?'UMKM - ':'')+(metricLabels[field]||field.replaceAll('_',' '))}
function displayProvenance(value:string){return value.replace(/\b(?:TGR|DTD)\b/g,'UMKM').replace(/\bTCZ\b/g,'UB')}
function displayMetric(value:string|number|null|undefined){return value==null?'\u2014':new Intl.NumberFormat('id-ID',{maximumFractionDigits:2}).format(Number(value))}
export function MetricPanel({ids,title,description}:{ids:string[];title:string;description:string}){
  const filters=useAreaFilters()
  const result=useQuery({queryKey:['metric-panel',ids,filters],queryFn:()=>Promise.all(ids.map(metric_id=>api<Metric>('/analytics/query',{metric_id,filters})))})
  if(result.isPending)return <Loading/>
  if(result.error)return <ErrorBox error={result.error}/>
  const workerMetrics=result.data?.filter(metric=>/workers_(male|female)_valid/.test(metric.metric_id))||[]
  return <Card className="visual-metric-panel"><div className="card-heading"><div><h2>{title}</h2><p>{description}</p></div></div>
    <div className="visual-metrics">{result.data?.filter(metric=>!workerMetrics.includes(metric)).map(metric=>{const row=metric.rows[0];const value=row?.value;return <div className="visual-metric" key={metric.metric_id}><div><span>{metricLabel(metric.metric_id)}</span><strong>{displayMetric(value)}{value!=null&&metric.unit==='persen'?'%':''}</strong></div>{metric.unit==='persen'&&<div className="progress-track"><span style={{width:value==null?'0%':Math.max(0,Math.min(100,Number(value)))+'%'}}/></div>}{value==null&&<small>{row?.suppressed?'Nilai ditahan.':'Tidak tersedia.'}</small>}</div>})}</div>
    {workerMetrics.length>0&&<BarChart data={workerMetrics.map(metric=>({name:metricLabel(metric.metric_id),value:metric.rows[0]?.value==null?null:Number(metric.rows[0].value)}))} label={title+' menurut jenis kelamin'}/>}
    <details className="chart-notes"><summary>Basis perhitungan dan catatan</summary>{result.data?.map(metric=>{const row=metric.rows[0];return <div key={metric.metric_id}><strong>{metricLabel(metric.metric_id)}</strong><p>Basis: {number(row?.denominator)} respons. {row?.suppressed?'Nilai ditahan untuk melindungi data.':''}</p><p>{displayProvenance(metric.interpretation_limits)}</p><p>{metric.period} | {number(row?.excluded_rows)} record di luar basis. Satuan: {metric.unit}.</p></div>})}</details>
  </Card>
}

export function RegionChart({metricId,title,scopeNote='Semua status sumber tetap tercakup.',showFootnote=true,combinedTitle=false}:{metricId:string;title:string;scopeNote?:string;showFootnote?:boolean;combinedTitle?:boolean}){
  const filters=useAreaFilters()
  const level=filters.sls?'subsls':filters.desa?'sls':filters.kecamatan?'desa':'kecamatan'
  const result=useQuery({queryKey:['region-chart',metricId,filters,level],queryFn:()=>api<Metric>('/analytics/query',{metric_id:metricId,filters,group_by:[level]})})
  if(result.isPending)return <Loading variant="chart"/>
  if(result.error)return <ErrorBox error={result.error}/>
  const rows=result.data?.rows||[]
  const heading=combinedTitle?'Distribusi '+title.replace(/^Sebaran /,'')+' Menurut '+(level==='desa'?'Desa / Kelurahan':level==='subsls'?'SUB-SLS':level==='sls'?'SLS':'Kecamatan'):title
  const data=rows.map(row=>{const geo=row.dimensions[level] as {display_label?:string;geo_status?:string};return {name:geo?.display_label||'Wilayah tidak tersedia',value:row.value==null?null:Number(row.value)}}).sort((a,b)=>(b.value??-1)-(a.value??-1)).slice(0,10)
  return <Card className="region-chart"><div className="card-heading"><div><h2>{heading}</h2>{!combinedTitle&&<p>Menurut {level==='desa'?'desa / kelurahan':level==='subsls'?'SUB-SLS':level==='sls'?'SLS':'kecamatan'} | wilayah assignment</p>}</div></div>{data.length?<BarChart data={data} label={title}/>:<p className="muted small">Tidak ada data pada wilayah ini.</p>}{showFootnote&&<p className="muted small">{rows.length>10?'Menampilkan 10 wilayah dengan jumlah terbesar. ':''}Nilai yang ditahan tidak ditampilkan sebagai nol. {scopeNote}</p>}</Card>
}

export type ChartDatum={name:string;value:number|null;code?:string}
export function BarChart({data,onClick,label='Distribusi unit'}:{data:ChartDatum[];onClick?:(item:ChartDatum)=>void;label?:string}){
  const container=useRef<HTMLDivElement>(null)
  useEffect(()=>{
    if(!container.current)return
    const chart:ECharts=init(container.current,undefined,{renderer:'svg'})
    chart.setOption({animation:false,grid:{left:8,right:24,bottom:5,top:15,containLabel:true},tooltip:{trigger:'axis',axisPointer:{type:'shadow'},valueFormatter:(value:unknown)=>value==null?'Ditahan':displayMetric(Number(value))},xAxis:{type:'value',axisLabel:{color:'#667583',fontSize:11},splitLine:{lineStyle:{color:'#edf0f3'}},axisLine:{show:false}},yAxis:{type:'category',inverse:true,data:data.map(r=>r.name),axisTick:{show:false},axisLine:{show:false},axisLabel:{color:'#344f63',fontSize:12,width:125,overflow:'truncate'}},series:[{type:'bar',data:data.map(r=>r.value),barMaxWidth:21,itemStyle:{color:'#b74712',borderRadius:[0,4,4,0]},emphasis:{itemStyle:{color:'#94360c'}},label:{show:true,position:'right',color:'#344f63',fontSize:11,formatter:(params:{value:number})=>displayMetric(params.value)}}]})
    chart.on('click',params=>{const item=data[params.dataIndex];if(item&&onClick)onClick(item)})
    const resize=new ResizeObserver(()=>chart.resize());resize.observe(container.current)
    return()=>{resize.disconnect();chart.dispose()}
  },[data,onClick])
  return <div className="chart" ref={container} role="img" aria-label={label} aria-description={data.map(row=>row.name+': '+(row.value==null?'Tidak tersedia / ditahan':displayMetric(row.value))).join('; ')} style={{height:Math.max(135,data.length*28+30)}}/>
}
