import {useNavigate,useSearch} from '@tanstack/react-router'
import {useQuery} from '@tanstack/react-query'
import {api,type Metric,type SearchState} from '@/lib/api'
import {number} from '@/lib/utils'
import {turnoverAmount,turnoverBases,turnoverGroups,turnoverRanges,type Turnover} from '@/lib/turnover'
import {useAuth} from '@/auth'
import {useBusinessFilters} from './filter-panel'
import {BarChart,ErrorBox,Loading} from './shared'
import {SearchSelect} from './ui/search-select'
import {Card} from './ui/card'
import {Button} from './ui/button'

export function TurnoverFilters({search,onChange}:{search:SearchState;onChange:(values:Partial<SearchState>)=>void}){
  return <div className="turnover-filters">
    <label>Kelompok omzet tahunan<SearchSelect aria-label="Kelompok omzet tahunan" value={search.turnover_group||''} onValueChange={value=>onChange({turnover_group:value||undefined,page:1})}><option value="">Semua kelompok</option>{Object.entries(turnoverGroups).map(([code,label])=><option key={code} value={code}>{label}{turnoverRanges[code]?' · '+turnoverRanges[code]:''}</option>)}</SearchSelect></label>
    <label>Dasar omzet<SearchSelect aria-label="Dasar omzet" value={search.turnover_basis||''} onValueChange={value=>onChange({turnover_basis:value||undefined,page:1})}><option value="">Semua dasar omzet</option>{Object.entries(turnoverBases).map(([code,label])=><option key={code} value={code}>{label}</option>)}</SearchSelect></label>
    <small className="turnover-filter-note">Usaha mulai 2026: omzet bulanan × 12 sebagai estimasi setahun.</small>
  </div>
}

export function TurnoverValue({value,detail=false}:{value?:Turnover;detail?:boolean}){
  if(!value)return <span className="muted">Belum tersedia</span>
  return <div className={'turnover-value'+(detail?' turnover-detail':'')}>
    <strong>{turnoverAmount(value)}</strong>
    <span>{turnoverGroups[value.group]||'Belum tersedia'}{turnoverRanges[value.group]?' · '+turnoverRanges[value.group]:''}</span>
    <small className={value.basis==='ESTIMATE_MONTHLY_X12'?'turnover-estimate':'muted'}>{turnoverBases[value.basis]||'Belum tersedia'}</small>
    {detail&&value.amount_status!=='RESTRICTED'&&value.monthly!=null&&value.annual!=null&&<p>Rp{number(value.monthly)}/bulan × 12 = estimasi Rp{number(value.annual)}/tahun.</p>}
    {detail&&value.basis==='ESTIMATE_MONTHLY_X12'&&<p className="muted">Perkiraan setahun pada laju bulan yang dilaporkan, bukan realisasi sepanjang 2026.</p>}
    {detail&&value.group==='REVIEW'&&<p className="muted">Nominal, periode, atau hubungan sumber perlu diperiksa.</p>}
  </div>
}

export function TurnoverDistribution(){
  const search=useSearch({strict:false}) as SearchState;const filters=useBusinessFilters();const navigate=useNavigate();const {session}=useAuth()
  const source=search.source==='ub'?'ub':'dtd';const metric=source==='ub'?'ub.turnover_distribution':'usaha.turnover_distribution'
  const level=filters.sls?'subsls':filters.desa?'sls':filters.kecamatan?'desa':'kecamatan'
  const result=useQuery({queryKey:['turnover-distribution',metric,filters,level],queryFn:()=>Promise.all([
    api<Metric>('/analytics/query',{metric_id:metric,filters}),
    api<Metric>('/analytics/query',{metric_id:metric,filters,group_by:[level]}),
  ])})
  function directory(group:string,geo?:{raw_codes?:Record<string,string|null>}){
    const area:Partial<SearchState>={}
    const levels=['kecamatan','desa','sls','subsls'] as const
    if(geo)for(const key of levels){const code=geo.raw_codes?.['kode_'+key];area[key]=levels.indexOf(key)<=levels.indexOf(level)?code||undefined:undefined}
    void navigate({to:'/usaha',search:{...search,...area,tab:'direktori',source,turnover_group:group,enumerated:'true',page:1},resetScroll:false})
  }
  if(result.isPending)return <Loading variant="chart"/>
  if(result.error)return <ErrorBox error={result.error}/>
  const [groups,regions]=result.data!
  const rows=Object.keys(turnoverGroups).map(code=>({code,row:groups.rows.find(row=>row.dimensions.turnover_group===code)}))
  const chartData=rows.map(({code,row})=>({name:turnoverGroups[code],code,value:row?.suppressed?null:Number(row?.value||0)}))
  const regionRows=regions.rows.slice().sort((a,b)=>String((a.dimensions[level] as {display_label?:string})?.display_label||'').localeCompare(String((b.dimensions[level] as {display_label?:string})?.display_label||'')))
  return <div className="turnover-distribution">
    <Card><div className="card-heading"><div><h2>Distribusi Omzet Tahunan</h2><p>{source==='ub'?'Sumber UB':'Sumber UMKM'} · usaha selesai atau disetujui</p></div></div>
      <p className="turnover-context">Termasuk estimasi omzet bulanan × 12 untuk usaha mulai 2026. Nilai tahunan dilaporkan merujuk 2025.</p>
      {chartData.some(row=>row.value!=null&&row.value>0)?<BarChart label="Jumlah usaha menurut kelompok omzet tahunan" data={chartData} onClick={session?.user?.can_detail?item=>{if(item.code&&item.value!=null&&item.value>0)directory(item.code)}:undefined}/>:<p className="turnover-context">{groups.rows.some(row=>row.suppressed)?'Angka ditahan untuk melindungi kerahasiaan data.':'Belum ada usaha sesuai filter.'}</p>}
      <div className="table-scroll"><table className="data-table"><thead><tr><th>Kelompok omzet</th><th>Batas per tahun</th><th>Jumlah usaha</th></tr></thead><tbody>{rows.map(({code,row})=><tr key={code}><td>{turnoverGroups[code]}</td><td>{turnoverRanges[code]||'—'}</td><td>{row?.suppressed?<span>Ditahan</span>:session?.user?.can_detail&&Number(row?.value)>0?<Button variant="ghost" size="sm" onClick={()=>directory(code)} aria-label={'Buka direktori omzet '+turnoverGroups[code]}>{number(row?.value||0)}</Button>:number(row?.value||0)}</td></tr>)}</tbody></table></div>
    </Card>
    <Card><div className="card-heading"><h2>Distribusi Omzet Menurut {level==='desa'?'Desa / Kelurahan':level==='sls'?'SLS':level==='subsls'?'SUB-SLS':'Kecamatan'}</h2></div><div className="table-scroll turnover-region-table"><table className="data-table"><thead><tr><th>Wilayah</th><th>Kelompok omzet</th><th>Jumlah usaha</th></tr></thead><tbody>{regionRows.map((row,i)=>{const geo=row.dimensions[level] as {display_label?:string;raw_codes?:Record<string,string|null>};const group=String(row.dimensions.turnover_group);return <tr key={i}><td>{geo?.display_label||'Wilayah belum tersedia'}</td><td>{turnoverGroups[group]||'Belum tersedia'}</td><td>{row.suppressed?'Ditahan':session?.user?.can_detail&&Number(row.value)>0&&geo?.raw_codes?.['kode_'+level]?<Button variant="ghost" size="sm" aria-label={'Buka direktori '+turnoverGroups[group]+' '+geo?.display_label} onClick={()=>directory(group,geo)}>{number(row.value)}</Button>:number(row.value)}</td></tr>})}</tbody></table>{!regionRows.length&&<p className="muted">Belum ada hasil sesuai filter.</p>}</div><p className="turnover-context">Nilai ditahan tetap disembunyikan. Kelompok omzet merupakan pendekatan dari pendapatan barang/jasa kuesioner; sumber UMKM dan UB tetap terpisah.</p></Card>
  </div>
}
