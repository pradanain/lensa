import {describe,it,expect} from 'vitest'
import {industryMatrix,cellDescription} from '../../src/lib/industry-matrix'
import type {MetricRow} from '../../src/lib/api'

function row(code:string,value:number|null):MetricRow{
  return {dimensions:{kbli:code,kecamatan:{geo_key:'kec-1',display_label:'WILAYAH SINTETIS',raw_codes:{kode_kecamatan:'6502010'}}},value,numerator:value,denominator:value,eligible_rows:value,excluded_rows:value==null?null:0,percentage:null,suppressed:value==null}
}
describe('KBLI geographic mapping',()=>{
  it('excludes kabupaten-only columns before district pagination without modifying source rows',()=>{
    const rows=Array.from({length:11},(_,i)=>{
      const item=row('01111',10)
      item.dimensions.kecamatan={geo_key:'district-'+String(i).padStart(2,'0'),display_label:i===0?'Bulungan':i===10?'Bunyu':'Kecamatan sintetis '+i,raw_codes:{kode_kabupaten:'6502',kode_kecamatan:i===0?'6502000':'6502'+String(i).padStart(2,'0')+'0'}}
      return item
    })
    const matrix=industryMatrix(rows,'kecamatan')
    expect(rows).toHaveLength(11)
    expect(matrix.regions).toHaveLength(10)
    expect(matrix.regions.slice(0,10).map(r=>r.display_label)).toContain('Bunyu')
    expect(matrix.regions.map(r=>r.display_label)).not.toContain('Bulungan')
    expect(matrix.cells.size).toBe(10)
  })
  it('retains leading zeroes and never substitutes suppressed counts with zero',()=>{
    const data=industryMatrix([row('01111',12),row('01222',null)],'kecamatan')
    expect(data.regions).toHaveLength(1)
    expect(data.cells.get(JSON.stringify(['01111','kec-1']))?.value).toBe(12)
    expect(data.cells.get(JSON.stringify(['01222','kec-1']))?.value).toBeNull()
    expect(cellDescription(data.cells.get(JSON.stringify(['01222','kec-1'])))).toBe('Nilai ditahan')
  })
  it('distinguishes an unobserved combination from an observed zero',()=>{
    expect(cellDescription(undefined)).toBe('Tidak ada record pada kombinasi ini')
    expect(cellDescription({code:'01111',geo:{geo_key:'1',display_label:'Sintetis',raw_codes:{}},value:0,suppressed:false})).toBe('0 unit usaha')
  })
  it('does not invent valid KBLI identities from malformed groups',()=>{
    expect(industryMatrix([row('__MISSING__',10),row('1111',10)],'kecamatan').cells.size).toBe(0)
  })
})
