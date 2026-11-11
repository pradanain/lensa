import {useState,type ReactNode} from 'react'
import {SlidersHorizontal,ChevronDown,RotateCcw} from 'lucide-react'
import {useNavigate,useSearch} from '@tanstack/react-router'
import {useQuery} from '@tanstack/react-query'
import {api,type Geo,type SearchState} from '@/lib/api'
import {SearchSelect} from './ui/search-select'
import {Button} from './ui/button'

export function FilterPanel({children,title='Filter data',footer}:{children:ReactNode;title?:string;footer?:ReactNode}){
  const [open,setOpen]=useState(()=>window.matchMedia('(min-width: 901px)').matches)
  return <aside className={'filter-sidebar '+(open?'filters-open':'')} aria-label={title}>
    <button className="filter-sidebar-toggle" aria-label={title} title={open?'Tutup filter':'Buka filter'} aria-expanded={open} onClick={()=>setOpen(!open)}><SlidersHorizontal size={17}/><span className="filter-sidebar-title">{title}</span><ChevronDown size={16}/></button>
    <div className="filter-sidebar-body">{children}</div>{footer&&<div className="filter-sidebar-footer">{footer}</div>}
  </aside>
}

export function useAreaFilters(){
  const search=useSearch({strict:false}) as SearchState
  return Object.fromEntries(['kecamatan','desa','sls','subsls'].filter(key=>search[key as keyof SearchState]).map(key=>[key,String(search[key as keyof SearchState])]))
}

export function AnalysisLayout({children,businessSource=false}:{children:ReactNode;businessSource?:boolean}){
  const search=useSearch({strict:false}) as SearchState;const navigate=useNavigate()
  const source=businessSource&&search.source==='ub'?'ub':'dtd'
  const kec=useQuery({queryKey:['geo',source,'kecamatan'],queryFn:()=>api<{rows:Geo[]}>('/geography?source='+source+'&level=kecamatan')})
  const desa=useQuery({queryKey:['geo',source,'desa',search.kecamatan],queryFn:()=>api<{rows:Geo[]}>('/geography?source='+source+'&level=desa&parent='+encodeURIComponent(search.kecamatan||'')),enabled:!!search.kecamatan})
  const sls=useQuery({queryKey:['geo',source,'sls',search.desa],queryFn:()=>api<{rows:Geo[]}>('/geography?source='+source+'&level=sls&parent='+encodeURIComponent(search.desa||'')),enabled:!!search.desa})
  const subsls=useQuery({queryKey:['geo',source,'subsls',search.sls],queryFn:()=>api<{rows:Geo[]}>('/geography?source='+source+'&level=subsls&parent='+encodeURIComponent(search.sls||'')),enabled:!!search.sls})
  function change(values:Partial<SearchState>){void navigate({to:'.',search:{...search,...values},replace:true,resetScroll:false})}
  return <div className="analysis-layout"><FilterPanel title={businessSource?'Filter data':'Filter wilayah'} footer={<Button className="directory-reset" onClick={()=>change({kecamatan:undefined,desa:undefined,sls:undefined,subsls:undefined})}><RotateCcw size={15}/>Reset filter</Button>}><div className="filter-grid">
    {businessSource&&<label>Sumber<SearchSelect aria-label="Sumber" value={source} onValueChange={value=>change({source:value,page:1})}><option value="dtd">UMKM</option><option value="ub">UB</option></SearchSelect></label>}
    <label>Kecamatan<SearchSelect aria-label="Kecamatan" value={search.kecamatan||''} onValueChange={value=>change({kecamatan:value,desa:undefined,sls:undefined,subsls:undefined})}><option value="">Semua kecamatan</option>{kec.data?.rows.map(row=><option key={row.code||'empty'} value={row.code||''}>{row.label||row.code||'Kode kosong'}</option>)}</SearchSelect></label>
    <label>Desa / kelurahan<SearchSelect aria-label="Desa / kelurahan" value={search.desa||''} disabled={!search.kecamatan} onValueChange={value=>change({desa:value,sls:undefined,subsls:undefined})}><option value="">Semua desa</option>{desa.data?.rows.map(row=><option key={row.code||'empty'} value={row.code||''}>{row.label||row.code||'Kode kosong'}</option>)}</SearchSelect></label>
    <label>SLS<SearchSelect aria-label="SLS" value={search.sls||''} disabled={!search.desa} onValueChange={value=>change({sls:value,subsls:undefined})}><option value="">Semua SLS</option>{sls.data?.rows.map(row=><option key={row.code||'empty'} value={row.code||''}>{row.label||row.code||'Kode kosong'}</option>)}</SearchSelect></label>
    <label>SUB-SLS<SearchSelect aria-label="SUB-SLS" value={search.subsls||''} disabled={!search.sls} onValueChange={value=>change({subsls:value})}><option value="">Semua SUB-SLS</option>{subsls.data?.rows.map(row=><option key={row.code||'empty'} value={row.code||''}>{row.label||row.code}</option>)}</SearchSelect></label>
  </div></FilterPanel><div className="analysis-content">{children}</div></div>
}
