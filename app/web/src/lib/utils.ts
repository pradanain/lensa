import {clsx, type ClassValue} from 'clsx'
import {twMerge} from 'tailwind-merge'

export function cn(...values: ClassValue[]) {return twMerge(clsx(values))}
export function number(value: string | number | null | undefined) {
  if(value == null) return '—'
  if(typeof value === 'number') return new Intl.NumberFormat('id-ID').format(value)
  if(!/^-?\d+(?:\.\d+)?$/.test(value)) return value
  const [whole, fraction]=value.split('.')
  const grouped=whole.replace(/\B(?=(\d{3})+(?!\d))/g,'.')
  return fraction && Number(fraction)!==0 ? grouped+','+fraction.replace(/0+$/,'') : grouped
}
export const roleNames: Record<string,string>={admin:'Administrator',analyst_detail:'Analis detail',aggregate_viewer:'Pembaca agregat'}

export const answerStates: Record<string,{label:string; tone:string}>={
  ANSWERED:{label:'Terisi',tone:'success'},BLANK_OR_MISSING:{label:'Kosong / belum tersedia',tone:'neutral'},
  SKIPPED_NOT_APPLICABLE:{label:'Tidak berlaku · aturan terverifikasi',tone:'neutral'},NOT_EXPORTED:{label:'Tidak tersedia dalam ekspor',tone:'neutral'},
  UNMATCHED_VERSION:{label:'Tersedia pada versi berbeda',tone:'warning'},UNVERIFIED_MAPPING:{label:'Pemetaan belum terverifikasi',tone:'warning'},
  RESTRICTED:{label:'Akses terbatas',tone:'restricted'},
}
