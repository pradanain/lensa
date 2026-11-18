import {MASKED_VALUE,number} from './utils'

export type Turnover={group:string;basis:string;period:string|null;reason:string;amount_status:string;annual?:string|null;monthly?:string|null}
export const turnoverGroups:Record<string,string>={MIKRO:'Mikro',KECIL:'Kecil',MENENGAH:'Menengah',BESAR:'Besar',UNAVAILABLE:'Belum tersedia',REVIEW:'Perlu diperiksa'}
export const turnoverRanges:Record<string,string>={MIKRO:'≤ Rp2 miliar',KECIL:'> Rp2–15 miliar',MENENGAH:'> Rp15–50 miliar',BESAR:'> Rp50 miliar'}
export const turnoverBases:Record<string,string>={REPORTED_ANNUAL:'Tahunan dilaporkan (2025)',ESTIMATE_MONTHLY_X12:'Estimasi bulanan × 12',UNAVAILABLE:'Belum tersedia'}
export function turnoverAmount(item:Turnover){
  if(item.amount_status==='RESTRICTED')return MASKED_VALUE
  if(item.annual==null)return item.group==='REVIEW'?'Perlu diperiksa':'Belum tersedia'
  return (item.basis==='ESTIMATE_MONTHLY_X12'?'≈ ':'')+'Rp'+number(item.annual)
}
