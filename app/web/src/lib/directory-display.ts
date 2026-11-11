import type {DirectoryRow} from './api'

export function neighborhoodLabel(row:Pick<DirectoryRow,'sls_label'|'subsls'|'sls'>){
  if(!row.sls_label)return '-'
  const label=row.sls_label.replace(/\s*\/\s*/g,' ').trim()
  const code=row.subsls||''
  return label+(/^\d{16}$/.test(code)&&code.slice(-2)!=='00'&&(!row.sls||code.startsWith(row.sls))?' SUB '+code.slice(-2):'')
}

export function statusLabel(row:Pick<DirectoryRow,'status'|'status_label'>){
  return (row.status_label||row.status||'Tidak tersedia').replace(/^\s*\d+\s*[.)\-:]\s*/,'').trim()
}

export function missingKbliLabel(row:Pick<DirectoryRow,'source'|'status'|'status_label'|'kbli'>){
  if(row.kbli?.trim())return null
  // Codes are scoped to DTD business existence, not assignment workflow or UB codes.
  if(row.source==='dtd'&&['1','2'].includes(row.status))return 'Belum terisi'
  return null
}
