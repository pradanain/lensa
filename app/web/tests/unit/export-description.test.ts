import {expect,it} from 'vitest'
import {exportDescription} from '../../src/lib/export-description'

it('names the KBLI category and selected geography in the confirmation and filename',()=>{
  const result=exportDescription('/kbli/export',{category:'C'},[{level:'kecamatan',label:'Tanjung Selor'}])
  expect(result.question).toBe('Unduh data KBLI 2025 dengan filter berikut?')
  expect(result.summary).toContainEqual({label:'Kecamatan',value:'Tanjung Selor'})
  expect(result.summary).toContainEqual({label:'Kategori KBLI',value:'C'})
  expect(result.filename).toBe('lensa-kbli-kategori-c-tanjung-selor.xlsx')
})

it('keeps leading zero codes and excludes private search text from filenames',()=>{
  const result=exportDescription('/directories/businesses/export',{source:'ub',kbli_category:'A',kbli_prefix:'01122',q:'Nama privat/sintetis',enumerated_only:true})
  expect(result.filename).toBe('lensa-ub-01122.xlsx')
  expect(result.filename).not.toContain('privat')
  expect(result.summary).toContainEqual({label:'Pencarian',value:'Nama privat/sintetis'})
})


it('summarizes the most specific KBLI and location without repeated SLS labels or SUB 00',()=>{
  const result=exportDescription('/directories/businesses/export',{source:'dtd',kbli_category:'A',kbli_prefix:'01122',status:'1'},[
    {level:'kecamatan',label:'PESO',code:'6502010'},
    {level:'desa',label:'LONG LEJUH',code:'6502010001'},
    {level:'sls',label:'RT 001 \u00b7 65020100010001',code:'65020100010001'},
    {level:'subsls',label:'RT 001 \u00b7 SUB-SLS 00 \u00b7 6502010001000100',code:'6502010001000100'},
  ],{status:'Ditemukan',kbliTitle:'Pertanian Padi Inbrida'})
  expect(result.filename).toBe('lensa-umkm-01122-peso-long-lejuh-rt001.xlsx')
  expect(result.summary).toContainEqual({label:'SLS',value:'RT 001'})
  expect(result.summary).toContainEqual({label:'Status',value:'Ditemukan'})
  expect(result.summary).toContainEqual({label:'KBLI',value:'[A] 01122 \u2014 Pertanian Padi Inbrida'})
  expect(result.summary.some(r=>r.label==='SUB-SLS')).toBe(false)
  expect(result.regionCodes).toContainEqual({label:'SUB-SLS',value:'6502010001000100'})
})

it('retains a nonzero sub-SLS without repeating its parent RT',()=>{
  const result=exportDescription('/directories/businesses/export',{},[{level:'subsls',label:'RT 001 \u00b7 SUB-SLS 02 \u00b7 6502010001000102',code:'6502010001000102'}])
  expect(result.summary).toContainEqual({label:'SUB-SLS',value:'SUB 02'})
  expect(result.filename).toBe('lensa-umkm-sub02.xlsx')
})
