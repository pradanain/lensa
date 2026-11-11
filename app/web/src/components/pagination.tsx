import {ChevronLeft,ChevronRight} from 'lucide-react'
import {number} from '@/lib/utils'
import {Button} from './ui/button'
import {SearchSelect} from './ui/search-select'

export function Pagination({page,pageSize,total,onPage,onPageSize,busy=false,label='Baris per halaman'}:{page:number;pageSize:number;total:number;onPage:(page:number)=>void;onPageSize:(size:number)=>void;busy?:boolean;label?:string}){
  const pages=Math.max(1,Math.ceil(total/pageSize))
  const visible=Array.from(new Set([1,pages,...Array.from({length:3},(_,index)=>page+index-1),...(page<=2?[2,3]:[]),...(page>=pages-1?[pages-2,pages-1]:[])])).filter(value=>value>=1&&value<=pages).sort((a,b)=>a-b)
  return <div className="pagination"><span>{total?number((page-1)*pageSize+1)+'-'+number(Math.min(page*pageSize,total)):'0'} dari {number(total)}<small> | Halaman {page} / {number(pages)}</small></span><div><SearchSelect searchable={false} aria-label={label} value={pageSize} onValueChange={value=>onPageSize(Number(value))}>{[10,25,50,100].map(size=><option key={size} value={size}>{size}</option>)}</SearchSelect><nav className="pagination-pages" aria-label="Navigasi halaman"><Button variant="outline" size="icon" aria-label="Halaman sebelumnya" disabled={busy||page<=1} onClick={()=>onPage(page-1)}><ChevronLeft size={17}/></Button>{visible.map((value,index)=><span className="pagination-page-item" key={value}>{index>0&&value-visible[index-1]>1&&<span className="pagination-ellipsis" aria-hidden="true">&hellip;</span>}<Button variant={value===page?'default':'outline'} className="pagination-number" aria-label={'Halaman '+value} aria-current={value===page?'page':undefined} disabled={busy} onClick={()=>onPage(value)}>{number(value)}</Button></span>)}<Button variant="outline" size="icon" aria-label="Halaman berikutnya" disabled={busy||page>=pages} onClick={()=>onPage(page+1)}><ChevronRight size={17}/></Button></nav></div></div>
}
