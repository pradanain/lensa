import {describe,it,expect} from 'vitest'
import {missingKbliLabel,statusLabel,neighborhoodLabel} from '../../src/lib/directory-display'

describe('business directory labels',()=>{
  it('only flags a blank DTD KBLI for found and new businesses',()=>{
    for(const status of ['00','0','3','4','9',''])expect(missingKbliLabel({source:'dtd',status,status_label:'',kbli:null})).toBeNull()
    for(const status of ['1','2'])expect(missingKbliLabel({source:'dtd',status,status_label:'',kbli:null})).toBe('Belum terisi')
    expect(missingKbliLabel({source:'dtd',status:'3',status_label:'Tutup',kbli:'01111'})).toBeNull()
    expect(missingKbliLabel({source:'ub',status:'2',status_label:'Bukan cakupan survei',kbli:null})).toBeNull()
  })
  it('shows the source label without its numeric prefix',()=>{
    expect(statusLabel({status:'00',status_label:'0. Tidak Ditemukan'})).toBe('Tidak Ditemukan')
    expect(statusLabel({status:'2',status_label:'2. Baru'})).toBe('Baru')
  })
})


it('formats RT RW and SUB from the verified full regional code',()=>{
  expect(neighborhoodLabel({sls_label:'RT 052 RW 020',sls:'65020500090052',subsls:'6502050009005202'})).toBe('RT 052 RW 020 SUB 02')
  expect(neighborhoodLabel({sls_label:'RT 001 / RW 002',sls:'65020100010001',subsls:'6502010001000101'})).toBe('RT 001 RW 002 SUB 01')
  expect(neighborhoodLabel({sls_label:null,subsls:'6502050009000000'})).toBe('-')
})


it('omits the SUB suffix only for code 00',()=>{
  expect(neighborhoodLabel({sls_label:'RT 048 RW 018',sls:'65020500090048',subsls:'6502050009004800'})).toBe('RT 048 RW 018')
  expect(neighborhoodLabel({sls_label:'RT 048 RW 018',sls:'65020500090048',subsls:'6502050009004802'})).toBe('RT 048 RW 018 SUB 02')
})
