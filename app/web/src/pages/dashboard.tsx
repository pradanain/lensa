import {useNavigate,useSearch} from '@tanstack/react-router'
import {useQuery} from '@tanstack/react-query'
import {ArrowRight,Building2,House,Layers3,Users,BriefcaseBusiness} from 'lucide-react'
import {api,type Metric,type SearchState} from '@/lib/api'
import {useAuth} from '@/auth'
import {number} from '@/lib/utils'
import {AnalysisLayout,useAreaFilters} from '@/components/filter-panel'
import {PageHead,StatCard,BarChart,useSummary,ErrorBox,Loading} from '@/components/shared'
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
  const result=useSummary(filters)
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
  if(result.isPending)return <Loading variant="dashboard" label="Memuat ringkasan..."/>
  if(result.error)return <ErrorBox error={result.error} retry={()=>void result.refetch()}/>
  const data=result.data;const value=(id:string)=>data.counts[id]?.[0]?.value
  const digital=data.indicators.filter(metric=>metric.metric_id.includes('internet_yes_rate'))
  const place=level==='desa'?'desa / kelurahan':level==='subsls'?'SUB-SLS':level==='sls'?'SLS':'kecamatan'
  return <div className="dashboard-overview">
    <section aria-labelledby="dashboard-business-heading"><div className="dashboard-section-heading"><h2 id="dashboard-business-heading">Usaha selesai didata</h2><span>Ditemukan / Baru, selesai atau disetujui</span></div>
      <div className="stats-grid three">
        <StatCard label="Usaha Keluarga" value={value('usaha.enumerated_family_count')} note="Usaha dalam bangunan tempat tinggal atau campuran." icon={<House size={20}/>} accent/>
        <StatCard label="Usaha di BKU" value={value('usaha.enumerated_bku_count')} note="Unit usaha dalam bangunan khusus usaha." icon={<Building2 size={20}/>}/>
        <StatCard label="Usaha Besar" value={value('ub.enumerated_count')} note="UB aktif dengan pendataan selesai atau disetujui." icon={<Layers3 size={20}/>} onClick={canDetail?()=>directory('ub'):undefined}/>
      </div>
    </section>
    <section aria-labelledby="dashboard-family-heading"><div className="dashboard-section-heading"><h2 id="dashboard-family-heading">Keluarga dan anggota</h2><span>Seluruh status pada versi kuesioner sumber</span></div>
      <div className="stats-grid two">
        <StatCard label="Keluarga" value={value('keluarga.count')} note="Data keluarga per versi kuesioner." icon={<House size={20}/>} onClick={canDetail?()=>directory('keluarga'):undefined}/>
        <StatCard label="Anggota keluarga" value={value('anggota.count')} note="Data anggota per versi kuesioner." icon={<Users size={20}/>} onClick={canDetail?()=>directory('anggota'):undefined}/>
      </div>
    </section>
    <div className="dashboard-visuals">
      <Card className="dashboard-distribution"><div className="dashboard-section-heading"><h2>Distribusi wilayah</h2></div>
        <label className="dashboard-chart-choice">Tampilkan<SearchSelect aria-label="Data distribusi" value={selection.id} onValueChange={section=>void navigate({to:'/dashboard',search:{...search,section},replace:true,resetScroll:false})}>{distributions.map(item=><option key={item.id} value={item.id}>{item.label}</option>)}</SearchSelect></label>
        {region.isPending?<Loading variant="chart"/>:region.error?<ErrorBox error={region.error} retry={()=>void region.refetch()}/>:regions.length?<BarChart data={regions} label={selection.label+' menurut '+place} onClick={canDetail?item=>{if(item.code)directory(selection.id,{...filters,[level]:item.code})}:undefined}/>:<p className="muted dashboard-empty">Tidak ada data pada wilayah ini.</p>}
        <p className="muted small">{rows.length>10?'10 wilayah dengan jumlah terbesar. ':''}Nilai yang ditahan tetap ditandai dan tidak dianggap nol.</p>
        {canDetail&&<Button variant="ghost" onClick={()=>directory(selection.id)}>Lihat daftar sesuai grafik<ArrowRight size={16}/></Button>}
      </Card>
      <Card className="dashboard-digital"><div className="dashboard-section-heading"><h2>Penggunaan internet</h2></div><p className="muted small">Seluruh respons valid pada masing-masing sumber.</p>
        {digital.map(metric=>{const row=metric.rows[0];const percentage=row?.percentage==null?null:Number(row.percentage);return <div className="digital-stat" key={metric.metric_id}><div><span>{metric.metric_id.startsWith('ub')?'Usaha Besar':'UMKM'}</span><strong>{percentage==null?'\u2014':new Intl.NumberFormat('id-ID',{maximumFractionDigits:2}).format(percentage)+'%'}</strong></div>{percentage!=null&&<div className="progress-track"><span style={{width:Math.max(0,Math.min(100,percentage))+'%'}}/></div>}<p>{percentage==null?(row?.suppressed?'Nilai ditahan.':'Belum tersedia.'):(number(row?.numerator)+' dari '+number(row?.denominator)+' respons valid')}</p></div>})}
        <Button variant="ghost" onClick={()=>void navigate({to:'/usaha',search:{...filters,tab:'ringkasan',section:'komposisi'}})}>Lihat ringkasan usaha<ArrowRight size={16}/></Button>
      </Card>
    </div>
    <details className="compact-notes dashboard-notes"><summary>Cakupan dan dasar perhitungan</summary><p>Unit usaha, keluarga, anggota dan assignment dihitung terpisah. Angkanya tidak dijumlahkan menjadi satu populasi unik.</p><p>Angka usaha memakai cohort selesai didata yang sama dengan halaman Usaha. UB aktif memakai aturan sumber UB. Penggunaan internet memakai seluruh respons valid, sehingga basisnya berbeda dari angka utama.</p><dl><div><dt>Assignment UMKM</dt><dd>{number(value('assignment_tgr.count'))}</dd></div><div><dt>Assignment UB</dt><dd>{number(value('assignment_ub.count'))}</dd></div><div><dt>Bangunan khusus usaha</dt><dd>{number(value('bku.count'))}</dd></div><div><dt>UMKM selesai didata</dt><dd>{number(value('usaha.enumerated_count'))}</dd></div></dl>{canDetail&&<Button variant="outline" onClick={()=>directory('usaha')}><BriefcaseBusiness size={16}/>Lihat UMKM selesai didata</Button>}</details>
  </div>
}
