import {useNavigate,useSearch} from '@tanstack/react-router'
import {type SearchState} from '@/lib/api'
import {useAreaFilters} from './filter-panel'
import {RegionChart} from './shared'
import {BusinessSectors} from './business-insights'
import {BusinessIndustryExplorer} from './business-industry-explorer'

export type BusinessAnalysis='komposisi'|'sebaran-kbli'|'sebaran-usaha'
export function BusinessOverview({section}:{section:BusinessAnalysis}){
  const search=useSearch({strict:false}) as SearchState
  const source=search.source==='ub'?'ub':'dtd'
  const filters=useAreaFilters();const navigate=useNavigate()
  return <div className="business-overview">
    {section==='komposisi'&&<BusinessSectors onSelect={code=>{if(/^[A-V]$/.test(code))void navigate({to:'/usaha',search:{...search,tab:'ringkasan',section:'sebaran-kbli',kbli_category:code,kbli_prefix:undefined},resetScroll:false})}}/>}
    {section==='sebaran-kbli'&&<BusinessIndustryExplorer key={JSON.stringify([source,filters])}/>}
    {section==='sebaran-usaha'&&<><RegionChart metricId={source==='dtd'?'usaha.enumerated_count':'ub.enumerated_count'} title={source==='dtd'?'Sebaran UMKM':'Sebaran UB'} showFootnote={false} combinedTitle/><BusinessIndustryExplorer view="map" key={JSON.stringify([source,filters])}/></>}
  </div>
}
