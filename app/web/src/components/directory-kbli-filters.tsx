import {useQuery} from '@tanstack/react-query'
import {api,type SearchState} from '@/lib/api'
import {SearchSelect} from './ui/search-select'
import {ErrorBox,Loading} from './shared'

type Code={code:string;category:string;title:string;level:number}
export function DirectoryKbliFilters({search,onChange}:{search:SearchState;onChange:(values:Partial<SearchState>)=>void}){
  const catalog=useQuery({queryKey:['kbli-catalog'],queryFn:()=>api<{rows:Code[]}>('/kbli/catalog'),staleTime:Infinity})
  const prefix=search.kbli_prefix||'';const category=search.kbli_category||''
  if(catalog.error)return <ErrorBox error={catalog.error}/>
  if(catalog.isPending)return <Loading variant="filters" label="Memuat pilihan KBLI..."/>
  const rows=catalog.data.rows
  function choose(value:string,digits:number){
    const code=rows.find(row=>row.code===value)
    onChange({kbli_prefix:value||prefix.slice(0,digits===2?0:digits-1),kbli_category:category||code?.category||undefined})
  }
  return <>
    <label>Kategori<SearchSelect aria-label="Kategori KBLI" value={category} onValueChange={value=>onChange({kbli_category:value,kbli_prefix:undefined})}><option value="">Semua kategori</option>{rows.filter(row=>row.level===1).sort((a,b)=>a.code.localeCompare(b.code)).map(row=><option key={row.code} value={row.code}>{row.code} - {row.title}</option>)}</SearchSelect></label>
    {[2,3,4,5].map(digits=><label key={digits}>KBLI {digits} Digit<SearchSelect aria-label={'KBLI '+digits+' Digit'} value={prefix.length>=digits?prefix.slice(0,digits):''} disabled={digits>2&&prefix.length<digits-1} onValueChange={value=>choose(value,digits)}><option value="">Semua kode {digits} digit</option>{rows.filter(row=>row.level===digits&&(!category||row.category===category)&&row.code.startsWith(prefix.slice(0,digits===2?0:digits-1))).sort((a,b)=>a.code.localeCompare(b.code)).map(row=><option key={row.code} value={row.code}>{row.code} - {row.title}</option>)}</SearchSelect></label>)}
  </>
}
