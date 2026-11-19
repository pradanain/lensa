import {lazy,Suspense} from 'react'
import type {BusinessAnalysis} from '@/components/business-overview'
const BusinessOverview=lazy(()=>import('@/components/business-overview').then(module=>({default:module.BusinessOverview})))
import {FamilyOverview} from '@/components/family-overview'
import {AnalysisLayout,useBusinessFilters} from '@/components/filter-panel'
import {useNavigate,useParams,useSearch} from '@tanstack/react-router'
import {useQuery} from '@tanstack/react-query'
import {Building2,House,Layers3} from 'lucide-react'
import {api,type SearchState} from '@/lib/api'
import {Directory} from '@/components/directory'
import {PageHead,TabBar,StatCard,useBusinessSummary,ErrorBox,Loading} from '@/components/shared'
import {Kbli} from './kbli'

const businessTabs=[{id:'ringkasan',label:'Ringkasan'},{id:'direktori',label:'Direktori'},{id:'kbli',label:'KBLI 2025'}]
const familyTabs=[{id:'ringkasan',label:'Ringkasan'},{id:'direktori',label:'Direktori'},{id:'anggota',label:'Anggota'}]

export function Business(){
  const navigate=useNavigate();const search=useSearch({strict:false}) as SearchState;const tab=businessTabs.some(item=>item.id===search.tab)?(search.tab||'ringkasan'):'ringkasan';const filters=useBusinessFilters();const summary=useBusinessSummary(filters,tab==='ringkasan')
  const section:BusinessAnalysis=['komposisi','sebaran-kbli','sebaran-usaha','omzet'].includes(search.section||'')?search.section as BusinessAnalysis:'komposisi'
  return <><div className="domain-navigation"><PageHead eyebrow="" title="Direktori Usaha Kabupaten Bulungan" description=""/><TabBar tabs={businessTabs} value={tab} onChange={id=>void navigate({to:'/usaha',search:{...search,tab:id,page:1}})}/></div>
    {tab==='ringkasan'&&<AnalysisLayout businessSource><div className="business-summary"><div className="stats-grid three"><StatCard label="Usaha Keluarga" value={summary.data?.counts['usaha.enumerated_family_count']?.[0]?.value} note="UMKM dalam bangunan tempat tinggal atau bangunan campuran." icon={<House size={20}/>}/><StatCard label="Bangunan Usaha" value={summary.data?.counts['usaha.enumerated_bku_count']?.[0]?.value} note="UMKM dalam bangunan khusus usaha (BKU)." icon={<Building2 size={20}/>}/><StatCard label="Usaha Besar" value={summary.data?.counts['ub.enumerated_count']?.[0]?.value} note="Usaha Besar (UB)" icon={<Layers3 size={20}/>} accent/></div>
    {summary.error&&<ErrorBox error={summary.error}/>}
    <div className="summary-topic-switch" role="group" aria-label="Topik ringkasan usaha">{[{id:'omzet',label:'Distribusi Omzet'},{id:'komposisi',label:'Komposisi Sektor'},{id:'sebaran-kbli',label:'Distribusi KBLI'},{id:'sebaran-usaha',label:search.source==='ub'?'Distribusi UB':'Distribusi UMKM'}].map(item=><button key={item.id} aria-pressed={section===item.id} onClick={()=>void navigate({to:'/usaha',search:{...search,tab:'ringkasan',section:item.id},replace:true,resetScroll:false})}>{item.label}</button>)}</div>
    <Suspense fallback={<Loading variant="chart"/>}><BusinessOverview section={section}/></Suspense>
    </div></AnalysisLayout>}
    {tab==='kbli'&&<Kbli/>}{tab==='direktori'&&<Directory scope="businesses"/>}
  </>
}

export function Families(){
  const navigate=useNavigate();const search=useSearch({strict:false}) as SearchState
  const legacy=['perumahan','pendidikan','aset'].includes(search.tab||'')?search.tab:undefined
  const tab=familyTabs.some(item=>item.id===search.tab)?search.tab||'ringkasan':'ringkasan'
  const section=legacy?'rincian':['sebaran-keluarga','sebaran-anggota','rincian'].includes(search.section||'')?search.section!:'sebaran-keluarga'
  return <><div className="domain-navigation"><PageHead eyebrow="" title="Direktori Keluarga Kabupaten Bulungan" description=""/><TabBar tabs={familyTabs} value={tab} onChange={id=>void navigate({to:'/keluarga',search:{...search,tab:id,status:undefined,page:1},resetScroll:false})}/></div>
    {tab==='ringkasan'&&<AnalysisLayout><FamilyOverview section={section} legacyTab={legacy}/></AnalysisLayout>}
    {tab==='direktori'&&<Directory scope="families" source="dtd"/>}{tab==='anggota'&&<Directory scope="members" source="dtd"/>}

  </>
}

export function DataSE(){
  const {system}=useParams({strict:false}) as {system:string};const navigate=useNavigate()
  const source=system==='ub'?'ub':'dtd'
  return <><div className="domain-navigation"><PageHead eyebrow="" title="Raw Data Kabupaten Bulungan" description=""/><TabBar tabs={[{id:'dtd',label:'UMKM'},{id:'ub',label:'Usaha Besar (UB)'}]} value={source} onChange={id=>void navigate({to:'/data/$system',params:{system:id},resetScroll:false})}/></div><Directory scope="assignments" source={source}/></>
}

type NumericProfile={field_id:string;unit:string;period:string;status_counts:Record<string,number|null>}
export type QualityResult={minimum_contributors:number;numeric_profiles:NumericProfile[];recorded_validation:Record<string,string|number|boolean>;ub_geography:{ub_assignments:number;different_nonempty_desa_codes:number};geographic_caveats:{metric_id:string;level:string;counts_by_code_status:Record<string,number|null>}[];schema:Record<string,{sections:number;questions:number;verified:number}>;p1_classification:Record<string,string|number|null>[];directory_counts:{scope:string;source:string;records:number|null}[];provenance:string}
export function useQuality(){return useQuery({queryKey:['quality'],queryFn:()=>api<QualityResult>('/data-quality/summary'),staleTime:60000})}
