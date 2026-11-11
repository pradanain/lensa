import {useRef,useState} from 'react'
import {FileSpreadsheet,LoaderCircle} from 'lucide-react'
import * as Dialog from '@radix-ui/react-dialog'
import {api,downloadXlsx,type Geo} from '@/lib/api'
import {exportDescription,type ExportFilters,type ExportLabels} from '@/lib/export-description'
import {Button} from './ui/button'

export function ExportXlsx({path,payload,filename}:{path:string;payload:unknown;filename:string}){
  const [busy,setBusy]=useState(false);const [error,setError]=useState('')
  const generation=useRef(0)
  const [confirmation,setConfirmation]=useState<{payload:ExportFilters;description:ReturnType<typeof exportDescription>;loading:boolean}|null>(null)
  async function prepare(){
    const selected=structuredClone(payload) as ExportFilters;const token=++generation.current
    setConfirmation({payload:selected,description:exportDescription(path,selected),loading:true})
    const source=selected.source==='ub'?'ub':'dtd'
    const definitions=[['kecamatan',''],['desa',selected.kecamatan],['sls',selected.desa],['subsls',selected.sls]]
    const areas=await Promise.all(definitions.filter(([level])=>selected[level as string]).map(async([level,parent])=>{
      const code=String(selected[level as string]);let label=code
      try{const data=await api<{rows:Geo[]}>('/geography?source='+source+'&level='+level+'&parent='+encodeURIComponent(String(parent||'')));label=data.rows.find(row=>row.code===code)?.label||code}catch{/* Original code remains explicit when a label is unavailable. */}
      return {level:level as string,label,code}
    }))
    const labels:ExportLabels={}
    const scope=path.split('/')[2]
    const tasks:Promise<void>[]=[]
    if(selected.status)tasks.push(api<{options:{code:string;label:string}[]}>('/directory-statuses?source='+source+'&scope='+scope).then(data=>{labels.status=data.options.find(r=>r.code===selected.status)?.label}))
    const code=String(selected.prefix||selected.kbli_prefix||'')
    const category=String(selected.category||selected.kbli_category||'')
    if(code||category)tasks.push(api<{rows:{code:string;title:string}[]}>('/kbli/catalog').then(data=>{labels.kbliTitle=data.rows.find(r=>r.code===code)?.title;labels.categoryTitle=data.rows.find(r=>r.code===category)?.title}))
    await Promise.allSettled(tasks)
    if(generation.current===token)setConfirmation({payload:selected,description:exportDescription(path,selected,areas,labels),loading:false})
  }
  async function download(){if(!confirmation||confirmation.loading||busy)return;const selected=confirmation.payload;const selectedFilename=confirmation.description.filename;setConfirmation(null);setBusy(true);setError('');try{await downloadXlsx(path,selected,selectedFilename||filename)}catch{setError('Unduhan gagal. Silakan coba kembali.')}finally{setBusy(false)}}
  return <><Dialog.Root open={confirmation!==null} onOpenChange={open=>{if(!open){generation.current++;setConfirmation(null)}}}><Dialog.Trigger asChild><Button type="button" variant="outline" className="export-xlsx" title="Unduh Excel (.xlsx)" aria-label="Unduh Excel sesuai pencarian dan filter" disabled={busy} aria-busy={busy} onClick={()=>void prepare()}>{busy?<LoaderCircle size={21} className="spin"/>:<FileSpreadsheet size={21}/>}</Button></Dialog.Trigger><Dialog.Portal><Dialog.Overlay className="export-dialog-overlay"/><Dialog.Content className="export-dialog"><div className="export-dialog-body"><div className="export-dialog-heading"><FileSpreadsheet size={22}/><Dialog.Title>Unduh Excel?</Dialog.Title></div><Dialog.Description>{confirmation?.loading?'Menyiapkan rincian unduhan…':confirmation?.description.question}</Dialog.Description>{!confirmation?.loading&&<><dl className="export-filter-summary">{confirmation?.description.summary.map(item=><div key={item.label}><dt>{item.label}</dt><dd>{item.value}</dd></div>)}</dl><p className="export-filename">{confirmation?.description.filename}</p></>}</div><div className="export-dialog-actions"><Dialog.Close asChild><Button type="button" variant="outline">Batal</Button></Dialog.Close><Button type="button" disabled={confirmation?.loading} onClick={()=>void download()}>Ya, unduh</Button></div></Dialog.Content></Dialog.Portal></Dialog.Root>{error&&<span className="export-error" role="alert">{error}</span>}</>
}
