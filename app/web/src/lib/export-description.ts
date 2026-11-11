export type ExportFilters=Record<string,unknown>
export type ExportArea={level:string;label:string;code?:string}
export type ExportLabels={status?:string;kbliTitle?:string;categoryTitle?:string;kind?:string}
const text=(value:unknown)=>typeof value==='string'?value:''
export const exportSlug=(value:string)=>value.normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'')
const readable=(label:string)=>label===label.toUpperCase()?label.toLowerCase().replace(/(^|[\s/-])\p{L}/gu,c=>c.toUpperCase()):label

export function exportDescription(path:string,filters:ExportFilters,areas:ExportArea[]=[],labels:ExportLabels={}){
  const kbli=path==='/kbli/export'
  const category=text(filters.category)||text(filters.kbli_category)
  const prefix=text(filters.prefix)||text(filters.kbli_prefix)
  const source=filters.source==='ub'?'UB':'UMKM'
  const subject=kbli?'data KBLI 2025':path.includes('/businesses/')?'direktori UMKM':path.includes('/families/')?'direktori keluarga':path.includes('/members/')?'data anggota keluarga':'data assignment '+source
  const selectedSubject=path.includes('/businesses/')&&source==='UB'?'direktori UB':subject
  const summary:{label:string;value:string}[]=[]
  const regionCodes:{label:string;value:string}[]=[]
  const areaNames:string[]=[]
  for(const area of areas){
    const label=area.level==='kecamatan'?'Kecamatan':area.level==='desa'?'Desa':area.level==='sls'?'SLS':'SUB-SLS'
    if(area.code)regionCodes.push({label,value:area.code})
    if(area.level==='subsls'&&/^[0-9]{16}$/.test(area.code||'')&&area.code!.endsWith('00'))continue
    let value=area.label
    if(area.level==='sls')value=value.split(/\s*[\u00b7|]\s*/)[0].replace(/\s*\/\s*/g,' ').trim()
    else if(area.level==='subsls'){
      const match=value.match(/SUB[-\s]?SLS\s+(\d+)/i)
      value=match?'SUB '+match[1]:value.split(/\s*[\u00b7|]\s*/)[0].trim()
    }else value=readable(value)
    summary.push({label,value})
    areaNames.push(exportSlug(value).replace(/\b(rt|rw|sub)-(\d+)/g,'$1$2'))
  }
  if(filters.status)summary.push({label:'Status',value:labels.status||'Label belum tersedia'})
  if(prefix)summary.push({label:'KBLI',value:(category?'['+category+'] ':'')+prefix+(labels.kbliTitle?' \u2014 '+labels.kbliTitle:'')})
  else if(category)summary.push({label:'Kategori KBLI',value:category+(labels.categoryTitle?' \u2014 '+labels.categoryTitle:'')})
  if(filters.kind)summary.push({label:'Jenis',value:labels.kind||text(filters.kind)})
  if(filters.kbli_state)summary.push({label:'Kode KBLI',value:({MISSING:'Belum terisi',INVALID_FORMAT:'Format tidak valid',UNKNOWN_REFERENCE:'Belum dikenali',VALID:'Valid'} as Record<string,string>)[text(filters.kbli_state)]||text(filters.kbli_state)})
  if(filters.enumerated_only)summary.push({label:'Pendataan',value:'Selesai atau disetujui'})
  if(filters.qualified_only)summary.push({label:'Cakupan',value:'Sesuai pemeriksaan lokal'})
  if(text(filters.q))summary.push({label:'Pencarian',value:text(filters.q)})
  const nameBase=kbli?'kbli':path.includes('/businesses/')?source.toLowerCase():path.includes('/families/')?'keluarga':path.includes('/members/')?'anggota':'assignment-'+source.toLowerCase()
  const name=['lensa',nameBase,...(prefix?[prefix]:category?['kategori',category]:[]),...areaNames].map(exportSlug).filter(Boolean).join('-')+'.xlsx'
  return {question:'Unduh '+selectedSubject+' dengan filter berikut?',filename:name,summary,regionCodes}
}
