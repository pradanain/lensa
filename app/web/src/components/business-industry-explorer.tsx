import {useState,type ReactNode} from 'react'
import {useQuery} from '@tanstack/react-query'
import {useNavigate,useSearch} from '@tanstack/react-router'
import {ArrowUpRight,X} from 'lucide-react'
import {api,type Geo,type Metric,type SearchState} from '@/lib/api'
import {number} from '@/lib/utils'
import {industryMatrix,cellDescription,type IndustryGeo} from '@/lib/industry-matrix'
import {useAuth} from '@/auth'
import {useAreaFilters} from './filter-panel'
import {useBusinessSource} from './business-insights'
import {ErrorBox,Loading} from './shared'
import {Pagination} from './pagination'
import {SearchSelect} from './ui/search-select'
import {Card} from './ui/card'
import {Button} from './ui/button'

type CodeLabel={code:string;category:string;title:string;level:number}
type Ranking={code:string;category:string;value:number|null;title:string}
export function BusinessIndustryExplorer({view='ranking'}:{view?:'ranking'|'map'}){
  const source=useBusinessSource();const filters=useAreaFilters();const search=useSearch({strict:false}) as SearchState
  const navigate=useNavigate();const {session}=useAuth()
  const [page,setPage]=useState(1);const [pageSize,setPageSize]=useState(10)
  const category=/^[A-V]$/.test(search.kbli_category||'')?search.kbli_category||'':''
  const selected=/^[0-9]{5}$/.test(search.kbli_prefix||'')?search.kbli_prefix||'':''
  const metric=source==='usaha'?'usaha.enumerated_count':'ub.enumerated_count'
  const queryFilters={...filters,...(category?{kategori:category}:{})}
  const catalog=useQuery({queryKey:['kbli-catalog'],queryFn:()=>api<{rows:CodeLabel[]}>('/kbli/catalog'),staleTime:Infinity})
  const result=useQuery({queryKey:['business-kbli-ranking',source,queryFilters],queryFn:()=>api<Metric>('/analytics/query',{metric_id:metric,filters:queryFilters,group_by:['kbli']})})
  const labels=new Map(catalog.data?.rows.filter(r=>r.level===5).map(r=>[r.code,r.title]))
  const categories=new Map(catalog.data?.rows.filter(r=>r.level===5&&/^[A-V]$/.test(r.category)).map(r=>[r.code,r.category]))
  const rows:Ranking[]=(result.data?.rows||[]).filter(r=>/^[0-9]{5}$/.test(String(r.dimensions.kbli))&&labels.has(String(r.dimensions.kbli))).map(r=>({code:String(r.dimensions.kbli),category:categories.get(String(r.dimensions.kbli))||'\u2014',value:r.value==null?null:Number(r.value),title:labels.get(String(r.dimensions.kbli))!})).sort((a,b)=>(b.value??-1)-(a.value??-1)||a.code.localeCompare(b.code))
  const currentPage=Math.min(page,Math.max(1,Math.ceil(rows.length/pageSize)))
  const visible=rows.slice((currentPage-1)*pageSize,currentPage*pageSize)
  const mapCodes=selected?[selected]:visible.map(r=>r.code)
  function chooseCategory(code:string){if(code&&!/^[A-V]$/.test(code))return;setPage(1);void navigate({to:'/usaha',search:{...search,kbli_category:code||undefined,kbli_prefix:undefined},replace:true,resetScroll:false})}
  function chooseCode(code:string){void navigate({to:'/usaha',search:{...search,tab:'ringkasan',section:'sebaran-usaha',kbli_prefix:view==='ranking'?code:code===selected?undefined:code},replace:true,resetScroll:false})}
  function directory(code?:string,geo?:IndustryGeo){
    const area:Record<string,string>={...filters}
    if(geo)for(const name of ['kecamatan','desa','sls','subsls']){
      const value=geo.raw_codes['kode_'+name]
      if(value)area[name]=value;else delete area[name]
    }
    void navigate({to:'/usaha',search:{...area,tab:'direktori',source:source==='usaha'?'dtd':'ub',enumerated:'true',kbli_category:category||undefined,kbli_prefix:code||undefined},resetScroll:false})
  }
  const mapControls=<label className="industry-category">Kategori lapangan usaha<SearchSelect aria-label="Kategori lapangan usaha" value={category} onValueChange={chooseCategory}><option value="">Semua kategori</option>{catalog.data?.rows.filter(r=>r.level===1).map(r=><option key={r.code} value={r.code}>{r.code} &middot; {r.title}</option>)}</SearchSelect></label>
  return <div className="industry-explorer">
    {view==='ranking'&&<Card className="industry-ranking"><div className="card-heading"><div><h2>Sebaran KBLI</h2><p>{source==='usaha'?'UMKM':'UB'}</p></div><label className="industry-category">Kategori lapangan usaha<SearchSelect aria-label="Kategori lapangan usaha" value={category} onValueChange={chooseCategory}><option value="">Semua kategori</option>{catalog.data?.rows.filter(r=>r.level===1).map(r=><option key={r.code} value={r.code}>{r.code} &middot; {r.title}</option>)}</SearchSelect></label></div><h3 className="industry-ranking-title">KBLI 5 digit terbanyak</h3>
        {result.isPending||catalog.isPending?<Loading variant="table"/>:result.error||catalog.error?<ErrorBox error={result.error||catalog.error}/>:<><div className="industry-ranking-list" role="list" aria-label="Peringkat KBLI 5 digit">{visible.map((row,i)=><div role="listitem" key={row.code} className={selected===row.code?'selected':''}>
          <span className="industry-rank-number">{row.value==null?'—':(currentPage-1)*pageSize+i+1}</span><button className="industry-rank-main" aria-pressed={selected===row.code} aria-label={'Petakan KBLI '+row.code} onClick={()=>chooseCode(row.code)}><span><span className="industry-code-label"><span className="industry-category-code">[{row.category}]</span><code>{row.code}</code></span><strong>{row.title}</strong></span><span className="industry-rank-count">{number(row.value)} <small>usaha</small></span></button>
          {session?.user?.can_detail&&<Button variant="ghost" size="icon" aria-label={'Direktori KBLI '+row.code} title="Buka direktori" onClick={()=>directory(row.code)}><ArrowUpRight size={15}/></Button>}
        </div>)}</div>{!rows.length&&<p className="insight-empty">Belum ada KBLI 5 digit pada pilihan ini.</p>}<Pagination page={currentPage} pageSize={pageSize} total={rows.length} label="Kode per halaman" onPage={setPage} onPageSize={size=>{setPageSize(size);setPage(1)}}/>
          </>}
      </Card>}
    {catalog.error&&<ErrorBox error={catalog.error}/>}
    {view==='map'&&(result.isPending||catalog.isPending?<Loading variant="chart"/>:mapCodes.length>0?<IndustryHeatmap key={JSON.stringify([mapCodes,queryFilters])} metric={metric} filters={queryFilters} codes={mapCodes} labels={labels} categories={categories} controls={mapControls} selected={selected} onClear={()=>chooseCode(selected)} onDirectory={session?.user?.can_detail?directory:undefined}/>:<Card className="industry-map-card"><div className="card-heading"><h2>Distribusi KBLI Menurut {filters.sls?'SUB-SLS':filters.desa?'SLS':filters.kecamatan?'Desa / Kelurahan':'Kecamatan'}</h2>{mapControls}</div><p className="insight-empty">Pemetaan muncul ketika tersedia kode KBLI pada pilihan ini.</p></Card>)}
  </div>
}

function IndustryHeatmap({metric,filters,codes,labels,categories,controls,selected,onClear,onDirectory}:{metric:string;filters:Record<string,string>;codes:string[];labels:Map<string,string>;categories:Map<string,string>;controls:ReactNode;selected:string;onClear:()=>void;onDirectory?:(code:string,geo?:IndustryGeo)=>void}){
  const [page,setPage]=useState(1);const [pageSize,setPageSize]=useState(10)
  const level=filters.sls?'subsls':filters.desa?'sls':filters.kecamatan?'desa':'kecamatan'
  const name=level==='desa'?'desa / kelurahan':level==='subsls'?'SUB-SLS':level==='sls'?'SLS':'kecamatan'
  const heading='Distribusi KBLI Menurut '+(level==='desa'?'Desa / Kelurahan':level==='subsls'?'SUB-SLS':level==='sls'?'SLS':'Kecamatan')
  const source=metric.startsWith('usaha')?'dtd':'ub'
  const parent=level==='subsls'?filters.sls:level==='sls'?filters.desa:''
  const geographicLabels=useQuery({queryKey:['geo',source,level,parent],queryFn:()=>api<{rows:Geo[]}>('/geography?source='+source+'&level='+level+'&parent='+encodeURIComponent(parent||'')),enabled:level==='sls'||level==='subsls'})
  const result=useQuery({queryKey:['industry-map',metric,filters,codes,level],queryFn:()=>api<Metric>('/analytics/query',{metric_id:metric,filters:{...filters,kbli:codes},group_by:['kbli',level]})})
  const data=industryMatrix(result.data?.rows||[],level)
  const current=Math.min(page,Math.max(1,Math.ceil(data.regions.length/pageSize)))
  const referenceLabels=new Map(geographicLabels.data?.rows.map(g=>[g.code,g.label]))
  const regions=data.regions.slice((current-1)*pageSize,current*pageSize).map(geo=>({...geo,display_label:referenceLabels.get(geo.raw_codes['kode_'+level]||'')||geo.display_label}))
  const max=Math.max(1,...[...data.cells.values()].map(c=>c.value??0))
  return <Card className="industry-map-card"><div className="card-heading"><div><h2>{heading}</h2></div><div className="industry-map-controls">{controls}{selected&&<Button variant="outline" size="sm" onClick={onClear}><X size={14}/>Lepas pilihan {selected}</Button>}</div></div>
    {result.isPending?<Loading variant="chart"/>:result.error?<ErrorBox error={result.error}/>:!regions.length?<p className="insight-empty">Tidak ada record KBLI pada wilayah yang dipilih.</p>:<>
      <div className="industry-matrix-scroll" role="region" aria-label={'Pemetaan KBLI menurut '+name} tabIndex={0}><div className="industry-matrix" style={{gridTemplateColumns:`160px repeat(${regions.length},minmax(86px,1fr))`}}>
        <div className="industry-matrix-corner">KBLI / {name}</div>{regions.map(geo=><div className="industry-matrix-column" key={geo.geo_key} title={geo.display_label}>{geo.display_label}</div>)}
        {codes.map(code=><div className="industry-matrix-row" key={code}><div className="industry-matrix-label"><span className="industry-code-label"><span className="industry-category-code">[{categories.get(code)||'\u2014'}]</span><code>{code}</code></span><span title={labels.get(code)}>{labels.get(code)||'Judul belum tersedia'}</span></div>{regions.map(geo=>{
          const cell=data.cells.get(JSON.stringify([code,geo.geo_key]));const value=cell?.value
          const fill=value==null?undefined:`rgba(183,71,18,${0.12+0.78*Math.sqrt(value/max)})`
          const title=code+' · '+geo.display_label+': '+cellDescription(cell)
          const geoCode=geo.raw_codes['kode_'+level]
          return <button key={geo.geo_key} className={'industry-matrix-cell '+(!cell?'empty':value==null?'withheld':'')} title={title} aria-label={title} disabled={!onDirectory||value==null||value===0||!geoCode||geoCode.length>40} onClick={()=>onDirectory?.(code,geo)} style={fill?{backgroundColor:fill,color:value!=null&&value/max>.5?'white':undefined}:undefined}>{!cell?'·':value==null?'—':number(value)}</button>
        })}</div>)}
      </div></div>
      <Pagination page={current} pageSize={pageSize} total={data.regions.length} label="Wilayah per halaman" onPage={setPage} onPageSize={size=>{setPageSize(size);setPage(1)}}/>
    </>}
  </Card>
}
