import {BusinessOverview,type BusinessAnalysis} from '@/components/business-overview'
import {AnalysisLayout,useAreaFilters} from '@/components/filter-panel'
import {useNavigate,useParams,useSearch} from '@tanstack/react-router'
import {useQuery} from '@tanstack/react-query'
import {Building2,House,Users,Layers3} from 'lucide-react'
import {api,type SearchState} from '@/lib/api'
import {Directory} from '@/components/directory'
import {PageHead,TabBar,StatCard,MetricPanel,Notice,useSummary,useBusinessSummary,RegionChart,ErrorBox} from '@/components/shared'
import {Badge} from '@/components/ui/badge'
import {Kbli} from './kbli'

const businessTabs=[{id:'ringkasan',label:'Ringkasan'},{id:'direktori',label:'Direktori'},{id:'kbli',label:'KBLI 2025'}]
const familyTabs=[{id:'ringkasan',label:'Ringkasan'},{id:'direktori',label:'Direktori'},{id:'anggota',label:'Anggota'},{id:'perumahan',label:'Perumahan'},{id:'pendidikan',label:'Pendidikan/Pekerjaan'},{id:'aset',label:'Ekonomi & Aset'}]

export function Business(){
  const navigate=useNavigate();const search=useSearch({strict:false}) as SearchState;const tab=businessTabs.some(item=>item.id===search.tab)?(search.tab||'ringkasan'):'ringkasan';const filters=useAreaFilters();const summary=useBusinessSummary(filters,tab==='ringkasan')
  const section:BusinessAnalysis=['komposisi','sebaran-kbli','sebaran-usaha'].includes(search.section||'')?search.section as BusinessAnalysis:'komposisi'
  return <><div className="domain-navigation"><PageHead eyebrow="" title="Direktori Usaha Kabupaten Bulungan" description=""/><TabBar tabs={businessTabs} value={tab} onChange={id=>void navigate({to:'/usaha',search:{...search,tab:id,page:1}})}/></div>
    {tab==='ringkasan'&&<AnalysisLayout businessSource><div className="business-summary"><div className="stats-grid three"><StatCard label="Usaha Keluarga" value={summary.data?.counts['usaha.enumerated_family_count']?.[0]?.value} note="UMKM dalam bangunan tempat tinggal atau bangunan campuran." icon={<House size={20}/>}/><StatCard label="Bangunan Usaha" value={summary.data?.counts['usaha.enumerated_bku_count']?.[0]?.value} note="UMKM dalam bangunan khusus usaha (BKU)." icon={<Building2 size={20}/>}/><StatCard label="Usaha Besar" value={summary.data?.counts['ub.enumerated_count']?.[0]?.value} note="Usaha Besar (UB)" icon={<Layers3 size={20}/>} accent/></div>
    {summary.error&&<ErrorBox error={summary.error}/>}
    <div className="summary-topic-switch" role="group" aria-label="Topik ringkasan usaha">{[{id:'komposisi',label:'Komposisi Sektor'},{id:'sebaran-kbli',label:'Sebaran KBLI'},{id:'sebaran-usaha',label:search.source==='ub'?'Sebaran UB':'Sebaran UMKM'}].map(item=><button key={item.id} aria-pressed={section===item.id} onClick={()=>void navigate({to:'/usaha',search:{...search,tab:'ringkasan',section:item.id},replace:true,resetScroll:false})}>{item.label}</button>)}</div>
    <BusinessOverview section={section}/>
    </div></AnalysisLayout>}
    {tab==='kbli'&&<Kbli/>}{tab==='direktori'&&<Directory scope="businesses"/>}
  </>
}

export function Families(){
  const navigate=useNavigate();const search=useSearch({strict:false}) as SearchState;const tab=search.tab||'ringkasan';const filters=useAreaFilters();const summary=useSummary(filters)
  return <><div className="domain-navigation"><PageHead eyebrow="" title="Data keluarga" description=""/><TabBar tabs={familyTabs} value={tab} onChange={id=>void navigate({to:'/keluarga',search:{...search,tab:id,page:1},resetScroll:false})}/></div>
    {!['direktori','anggota'].includes(tab)&&<AnalysisLayout>
    {tab==='ringkasan'&&<><div className="stats-grid two"><StatCard label="Keluarga" value={summary.data?.counts['keluarga.count']?.[0]?.value} note="Assignment keluarga pada versi sumber" icon={<House size={20}/>} accent/><StatCard label="Anggota keluarga" value={summary.data?.counts['anggota.count']?.[0]?.value} note="Anggota-roster-versi, bukan gabungan P0/P1" icon={<Users size={20}/>}/></div><div className="overview-grid"><RegionChart metricId="keluarga.count" title="Sebaran keluarga"/><MetricPanel ids={['family_rosters.anggota_presence','family_rosters.usaha_presence','family_rosters.meteran_presence']} title="Keterhubungan roster" description="Proporsi keluarga dengan rincian anggota, usaha, atau meteran."/></div></>}
    {tab==='perumahan'&&<><MetricPanel ids={['perumahan.ownership_coverage','keluarga_details.perumahan_coverage']} title="Cakupan perumahan" description="Denominator kepemilikan dan ketersediaan modul ditampilkan terpisah."/><Notice>Rincian kondisi rumah dapat dibuka melalui Direktori keluarga → kuesioner → Blok IV. Kondisi kosong tidak ditafsirkan sebagai tidak memiliki fasilitas.</Notice></>}
    {tab==='pendidikan'&&<><MetricPanel ids={['sosial_details.sosial_p0_coverage','sosial_details.p1_pekerjaan_coverage']} title="Cakupan pendidikan dan pekerjaan" description="Denominator adalah union key anggota-versi, bukan seluruh populasi anggota keluarga."/><Notice>Jawaban substantif tersedia untuk akun detail di Blok III. P0 dan P1 dengan versi berbeda tetap terpisah. Nilai pendapatan P1 yang berupa teks tidak dijumlahkan sebagai uang.</Notice></>}
    {tab==='aset'&&<><MetricPanel ids={['keluarga_details.aset_keluarga_coverage']} title="Cakupan ekonomi dan aset keluarga" description="Ketersediaan modul berbeda dari validitas setiap nilai uang."/><Notice>Rincian nominal dibatasi untuk administrator dalam kuesioner Blok IV. Ukuran mingguan, bulanan dan tahunan tidak digabungkan secara otomatis.</Notice></>}
    </AnalysisLayout>}
    {tab==='direktori'&&<Directory scope="families" source="dtd"/>}{tab==='anggota'&&<Directory scope="members" source="dtd"/>}

  </>
}

export function DataSE(){
  const {system}=useParams({strict:false}) as {system:string};const navigate=useNavigate()
  const source=system==='ub'?'ub':'dtd'
  return <><div className="domain-navigation"><PageHead eyebrow="" title={source==='ub'?'Assignment Usaha Besar':'Assignment UMKM'} description=""><Badge>Baca saja</Badge></PageHead><TabBar tabs={[{id:'dtd',label:'UMKM'},{id:'ub',label:'UB'}]} value={source} onChange={id=>void navigate({to:'/data/$system',params:{system:id}})}/></div><Directory scope="assignments" source={source}/></>
}

type NumericProfile={field_id:string;unit:string;period:string;status_counts:Record<string,number|null>}
export type QualityResult={minimum_contributors:number;numeric_profiles:NumericProfile[];recorded_validation:Record<string,string|number|boolean>;ub_geography:{ub_assignments:number;different_nonempty_desa_codes:number};geographic_caveats:{metric_id:string;level:string;counts_by_code_status:Record<string,number|null>}[];schema:Record<string,{sections:number;questions:number;verified:number}>;p1_classification:Record<string,string|number|null>[];directory_counts:{scope:string;source:string;records:number|null}[];provenance:string}
export function useQuality(){return useQuery({queryKey:['quality'],queryFn:()=>api<QualityResult>('/data-quality/summary'),staleTime:60000})}
