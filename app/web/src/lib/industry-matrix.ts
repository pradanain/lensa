import type {MetricRow} from './api'

export type IndustryGeo={geo_key:string;display_label:string;raw_codes:Record<string,string|null>}
export type IndustryCell={code:string;geo:IndustryGeo;value:number|null;suppressed:boolean}

export function industryMatrix(rows:MetricRow[],level:string){
  const regions=new Map<string,IndustryGeo>();const cells=new Map<string,IndustryCell>()
  for(const row of rows){
    const code=String(row.dimensions.kbli??'')
    const geo=row.dimensions[level] as IndustryGeo|undefined
    if(!/^[0-9]{5}$/.test(code)||!geo?.geo_key)continue
    // Kabupaten-only buckets are not kecamatan columns. Keep source rows intact.
    const district=geo.raw_codes.kode_kecamatan
    if(level==='kecamatan'&&(district==='6502'||district==='6502000'||(!district&&geo.raw_codes.kode_kabupaten==='6502')))continue
    regions.set(geo.geo_key,geo)
    cells.set(JSON.stringify([code,geo.geo_key]),{code,geo,value:row.value==null?null:Number(row.value),suppressed:row.suppressed||row.value==null})
  }
  return {regions:[...regions.values()].sort((a,b)=>a.geo_key.localeCompare(b.geo_key)),cells}
}

export function cellDescription(cell:IndustryCell|undefined){
  return !cell?'Tidak ada record pada kombinasi ini':cell.value==null?'Nilai ditahan':new Intl.NumberFormat('id-ID').format(cell.value)+' unit usaha'
}
