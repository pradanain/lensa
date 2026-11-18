import {describe,it,expect} from 'vitest'
import {turnoverAmount,type Turnover} from '../../src/lib/turnover'
import {exportDescription} from '../../src/lib/export-description'

const item:Turnover={group:'KECIL',basis:'ESTIMATE_MONTHLY_X12',period:'ESTIMATE_12_MONTHS_FROM_2026',reason:'AVAILABLE',amount_status:'AVAILABLE',annual:'12345678901234567890.10'}
describe('turnover presentation',()=>{
  it('formats large amounts without converting to floating point and marks estimates',()=>{
    expect(turnoverAmount(item)).toBe('≈ Rp12.345.678.901.234.567.890,1')
    expect(turnoverAmount({...item,basis:'REPORTED_ANNUAL',annual:'0'})).toBe('Rp0')
  })
  it('does not turn restricted or unavailable amounts into zero',()=>{
    expect(turnoverAmount({...item,amount_status:'RESTRICTED',annual:undefined})).toBe('Nominal dibatasi')
    expect(turnoverAmount({...item,group:'UNAVAILABLE',annual:null})).toBe('Belum tersedia')
  })
  it('includes both frozen filters in export confirmation',()=>{
    expect(exportDescription('/directories/businesses/export',{turnover_group:'KECIL',turnover_basis:'ESTIMATE_MONTHLY_X12'}).summary).toEqual([
      {label:'Kelompok omzet',value:'Kecil'},{label:'Dasar omzet',value:'Estimasi bulanan × 12'},
    ])
  })
})
