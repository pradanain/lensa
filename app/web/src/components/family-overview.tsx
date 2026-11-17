import {useState} from 'react'
import {useQuery} from '@tanstack/react-query'
import {useNavigate,useSearch} from '@tanstack/react-router'
import {House,Users} from 'lucide-react'
import {api,type SearchState,type Summary} from '@/lib/api'
import {useAuth} from '@/auth'
import {useAreaFilters} from './filter-panel'
import {ErrorBox,MetricPanel,RegionChart,StatCard} from './shared'

const detailGroups=[
  {id:'roster',title:'Anggota, usaha, dan meteran',ids:['family_rosters.anggota_presence','family_rosters.usaha_presence','family_rosters.meteran_presence'],description:'Keluarga yang memiliki rincian tertaut pada versi yang sama.'},
  {id:'perumahan',title:'Perumahan',ids:['perumahan.ownership_coverage','keluarga_details.perumahan_coverage'],description:'Ketersediaan jawaban kepemilikan rumah dan rincian perumahan.'},
  {id:'pendidikan',title:'Pendidikan dan pekerjaan',ids:['sosial_details.sosial_p0_coverage','sosial_details.p1_pekerjaan_coverage'],description:'Ketersediaan rincian pendidikan dan pekerjaan anggota, sesuai versi sumbernya.'},
  {id:'aset',title:'Ekonomi dan aset',ids:['keluarga_details.aset_keluarga_coverage'],description:'Ketersediaan rincian aset keluarga, bukan jumlah nilai uangnya.'},
]
function FamilyDetail({group,initialOpen}:{group:typeof detailGroups[number];initialOpen:boolean}){
  const [open,setOpen]=useState(initialOpen)
  return <details className="family-detail compact-notes" open={open} onToggle={event=>setOpen(event.currentTarget.open)}><summary>{group.title}</summary>{open&&<MetricPanel ids={group.ids} title={group.title} description={group.description}/>}</details>
}

export function FamilyOverview({section,legacyTab}:{section:string;legacyTab?:string}){
  const filters=useAreaFilters();const search=useSearch({strict:false}) as SearchState;const navigate=useNavigate();const {session}=useAuth()
  const query=new URLSearchParams(filters)
  const summary=useQuery({queryKey:['family-summary',filters],queryFn:({signal})=>api<Pick<Summary,'counts'>>('/analytics/family-summary?'+query,undefined,undefined,{signal}),staleTime:300000})
  function directory(tab:string){void navigate({to:'/keluarga',search:{...filters,tab,page:1,page_size:search.page_size},resetScroll:false})}
  const topics=[{id:'sebaran-keluarga',label:'Distribusi Keluarga'},{id:'sebaran-anggota',label:'Distribusi Anggota'},{id:'rincian',label:'Rincian Keluarga'}]
  return <div className="business-summary family-summary">
    <div className="stats-grid two"><StatCard label="Keluarga" value={summary.data?.counts['keluarga.count']?.[0]?.value} note="Data keluarga per versi kuesioner." icon={<House size={20}/>} accent onClick={session?.user?.can_detail?()=>directory('direktori'):undefined}/><StatCard label="Anggota keluarga" value={summary.data?.counts['anggota.count']?.[0]?.value} note="Data anggota per versi kuesioner." icon={<Users size={20}/>} onClick={session?.user?.can_detail?()=>directory('anggota'):undefined}/></div>
    {summary.error&&<ErrorBox error={summary.error} retry={()=>void summary.refetch()}/>}
    <div className="summary-topic-switch" role="group" aria-label="Topik ringkasan keluarga">{topics.map(item=><button key={item.id} aria-pressed={section===item.id} onClick={()=>void navigate({to:'/keluarga',search:{...search,tab:'ringkasan',section:item.id},replace:true,resetScroll:false})}>{item.label}</button>)}</div>
    <div className="business-overview family-overview">
      {section==='sebaran-keluarga'&&<RegionChart metricId="keluarga.count" title="Distribusi keluarga" combinedTitle/>}
      {section==='sebaran-anggota'&&<RegionChart metricId="anggota.count" title="Distribusi anggota keluarga" combinedTitle/>}
      {section==='rincian'&&<div className="family-details" key={legacyTab}>{detailGroups.map(group=><FamilyDetail key={group.id} group={group} initialOpen={legacyTab===group.id}/>)}</div>}
    </div>
  </div>
}
