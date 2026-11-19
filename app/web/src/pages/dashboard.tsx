import {useNavigate,useSearch} from '@tanstack/react-router'
import {useQuery} from '@tanstack/react-query'
import {useState} from 'react'
import {ArrowRight,Building2,House,Layers3,Users,BriefcaseBusiness} from 'lucide-react'
import {api,type Metric,type SearchState,type Summary} from '@/lib/api'
import {useAuth} from '@/auth'
import {number} from '@/lib/utils'
import {AnalysisLayout,useAreaFilters} from '@/components/filter-panel'
import {PageHead,StatCard,BarChart,useBusinessSummary,ErrorBox,Loading} from '@/components/shared'
import {SearchSelect} from '@/components/ui/search-select'
import {Button} from '@/components/ui/button'
import {Card} from '@/components/ui/card'

const distributions=[
  {id:'assignment',label:'Assignment UMKM',metric:'assignment_tgr.count'},
  {id:'usaha',label:'UMKM selesai didata',metric:'usaha.enumerated_count'},
  {id:'ub',label:'Usaha Besar selesai didata',metric:'ub.enumerated_count'},
  {id:'keluarga',label:'Keluarga',metric:'keluarga.count'},
  {id:'anggota',label:'Anggota keluarga',metric:'anggota.count'},
]
export function Dashboard(){
  return <><div className="domain-navigation"><PageHead eyebrow="" title="Ringkasan Data SE2026" description=""/></div><AnalysisLayout><DashboardContent/></AnalysisLayout></>
}
function DashboardContent(){
  const {session}=useAuth();const navigate=useNavigate();const filters=useAreaFilters()
  const search=useSearch({strict:false}) as SearchState
  const [notesOpen,setNotesOpen]=useState(false)
  const params=new URLSearchParams(filters)
  const business=useBusinessSummary(filters,true)
  const family=useQuery({queryKey:['family-summary',filters],queryFn:({signal})=>api<Pick<Summary,'counts'>>('/analytics/family-summary?'+params,undefined,undefined,{signal})})
  const internet=useQuery({queryKey:['dashboard-internet',filters],queryFn:({signal})=>api<Pick<Summary,'indicators'>>('/analytics/dashboard?part=internet&'+params,undefined,undefined,{signal})})
  const notes=useQuery({queryKey:['dashboard-notes',filters],queryFn:({signal})=>api<Pick<Summary,'counts'>>('/analytics/dashboard?part=notes&'+params,undefined,undefined,{signal}),enabled:notesOpen})
  const selection=distributions.find(item=>item.id===search.section)||distributions[0]
  const level=filters.sls?'subsls':filters.desa?'sls':filters.kecamatan?'desa':'kecamatan'
  const region=useQuery({queryKey:['dashboard-region',selection.metric,filters,level],queryFn:({signal})=>api<Metric>('/analytics/query',{metric_id:selection.metric,filters,group_by:[level]},undefined,{signal})})
  const rows=region.data?.rows||[]
  const regions=rows.map(row=>{const geo=row.dimensions[level] as {display_label?:string;raw_codes?:Record<string,string>};return {name:geo?.display_label||'Wilayah tidak tersedia',value:row.value==null?null:Number(row.value),code:geo?.raw_codes?.['kode_'+level]}}).sort((a,b)=>(b.value??-1)-(a.value??-1)).slice(0,10)
  const canDetail=!!session?.user?.can_detail
  function directory(kind:string,area=filters){
    if(kind==='keluarga'||kind==='anggota')void navigate({to:'/keluarga',search:{...area,tab:kind==='anggota'?'anggota':'direktori',page:1}})
    else if(kind==='usaha'||kind==='ub')void navigate({to:'/usaha',search:{...area,source:kind==='ub'?'ub':'dtd',tab:'direktori',enumerated:'true',page:1}})
    else void navigate({to:'/data/$system',params:{system:'dtd'},search:{...area,page:1}})
  }
  const value=(id:string)=>(id==='keluarga.count'||id==='anggota.count'?family.data:business.data)?.counts[id]?.[0]?.value
  const digital=internet.data?.indicators||[]
  const place=level==='desa'?'desa / kelurahan':level==='subsls'?'SUB-SLS':level==='sls'?'SLS':'kecamatan'
  return <div className="dashboard-overview">
    <section aria-labelledby="dashboard-business-heading"><div className="dashboard-section-heading"><h2 id="dashboard-business-heading">Usaha selesai didata</h2><span>Ditemukan / Baru, selesai atau disetujui</span></div>
      {business.isPending?<Loading label="Memuat jumlah usaha..."/>:business.error?<ErrorBox error={business.error} retry={()=>void business.refetch()}/>:<div className="stats-grid three">
        <StatCard label="Usaha Keluarga" value={value('usaha.enumerated_family_count')} note="Usaha dalam bangunan tempat tinggal atau campuran." icon={<House size={20}/>} accent/>
        <StatCard label="Usaha di BKU" value={value('usaha.enumerated_bku_count')} note="Unit usaha dalam bangunan khusus usaha." icon={<Building2 size={20}/>}/>
        <StatCard label="Usaha Besar" value={value('ub.enumerated_count')} note="UB aktif dengan pendataan selesai atau disetujui." icon={<Layers3 size={20}/>} onClick={canDetail?()=>directory('ub'):undefined}/>
      </div>}
    </section>
    <section aria-labelledby="dashboard-family-heading"><div className="dashboard-section-heading"><h2 id="dashboard-family-heading">Keluarga dan anggota</h2><span>Seluruh status pada versi kuesioner sumber</span></div>
      {family.isPending?<Loading label="Memuat jumlah keluarga..."/>:family.error?<ErrorBox error={family.error} retry={()=>void family.refetch()}/>:<div className="stats-grid two">
        <StatCard label="Keluarga" value={value('keluarga.count')} note="Data keluarga per versi kuesioner." icon={<House size={20}/>} onClick={canDetail?()=>directory('keluarga'):undefined}/>
        <StatCard label="Anggota keluarga" value={value('anggota.count')} note="Data anggota per versi kuesioner." icon={<Users size={20}/>} onClick={canDetail?()=>directory('anggota'):undefined}/>
      </div>}
    </section>
    <div className="dashboard-visuals">
      <Card className="dashboard-distribution"><div className="dashboard-section-heading"><h2>Distribusi wilayah</h2></div>
        <label className="dashboard-chart-choice">Tampilkan<SearchSelect aria-label="Data distribusi" value={selection.id} onValueChange={section=>void navigate({to:'/dashboard',search:{...search,section},replace:true,resetScroll:false})}>{distributions.map(item=><option key={item.id} value={item.id}>{item.label}</option>)}</SearchSelect></label>
        {region.isPending?<Loading variant="chart"/>:region.error?<ErrorBox error={region.error} retry={()=>void region.refetch()}/>:regions.length?<BarChart data={regions} label={selection.label+' menurut '+place} onClick={canDetail?item=>{if(item.code)directory(selection.id,{...filters,[level]:item.code})}:undefined}/>:<p className="muted dashboard-empty">Tidak ada data pada wilayah ini.</p>}
        <p className="muted small">{rows.length>10?'10 wilayah dengan jumlah terbesar. ':''}Nilai yang ditahan tetap ditandai dan tidak dianggap nol.</p>
        {canDetail&&<Button variant="ghost" onClick={()=>directory(selection.id)}>Lihat daftar sesuai grafik<ArrowRight size={16}/></Button>}
      </Card>
      <Card className="dashboard-digital"><div className="dashboard-section-heading"><h2>Penggunaan internet</h2></div><p className="muted small">Seluruh respons valid pada masing-masing sumber.</p>
        {internet.isPending?<Loading label="Memuat penggunaan internet..."/>:internet.error?<ErrorBox error={internet.error} retry={()=>void internet.refetch()}/>:digital.map(metric=>{const row=metric.rows[0];const percentage=row?.percentage==null?null:Number(row.percentage);return <div className="digital-stat" key={metric.metric_id}><div><span>{metric.metric_id.startsWith('ub')?'Usaha Besar':'UMKM'}</span><strong>{percentage==null?'\u2014':new Intl.NumberFormat('id-ID',{maximumFractionDigits:2}).format(percentage)+'%'}</strong></div>{percentage!=null&&<div className="progress-track"><span style={{width:Math.max(0,Math.min(100,percentage))+'%'}}/></div>}<p>{percentage==null?(row?.suppressed?'Nilai ditahan.':'Belum tersedia.'):(number(row?.numerator)+' dari '+number(row?.denominator)+' respons valid')}</p></div>})}
        <Button variant="ghost" onClick={()=>void navigate({to:'/usaha',search:{...filters,tab:'ringkasan',section:'komposisi'}})}>Lihat ringkasan usaha<ArrowRight size={16}/></Button>
      </Card>
    </div>
    <details className="compact-notes dashboard-notes" onToggle={event=>setNotesOpen(event.currentTarget.open)}><summary>Cakupan dan dasar perhitungan</summary><p>Unit usaha, keluarga, anggota dan assignment dihitung terpisah. Angkanya tidak dijumlahkan menjadi satu populasi unik.</p><p>Angka usaha memakai cohort selesai didata yang sama dengan halaman Usaha. UB aktif memakai aturan sumber UB. Penggunaan internet memakai seluruh respons valid, sehingga basisnya berbeda dari angka utama.</p>{notesOpen&&(notes.isPending?<Loading label="Memuat cakupan..."/>:notes.error?<ErrorBox error={notes.error} retry={()=>void notes.refetch()}/>:<dl>{[['assignment_tgr.count','Assignment UMKM'],['assignment_ub.count','Assignment UB'],['bku.count','Bangunan khusus usaha'],['usaha.enumerated_count','UMKM selesai didata']].map(([id,label])=><div key={id}><dt>{label}</dt><dd>{number(notes.data?.counts[id]?.[0]?.value)}</dd></div>)}</dl>)}{canDetail&&<Button variant="outline" onClick={()=>directory('usaha')}><BriefcaseBusiness size={16}/>Lihat UMKM selesai didata</Button>}</details>
  </div>
}
