import {describe,it,expect} from 'vitest'
import {number,answerStates} from '../../src/lib/utils'
import {validateSearch} from '../../src/lib/api'

describe('safe display and route state',()=>{
  it('formats large decimal strings without a float conversion',()=>{
    expect(number('12345678901234567890.10')).toBe('12.345.678.901.234.567.890,1')
    expect(number('0')).toBe('0');expect(number(null)).toBe('—')
  })
  it('keeps respondent search text out of URL state',()=>{
    expect(validateSearch({q:'SYNTHETIC_PRIVATE_NAME',nik:'SYNTHETIC_NIK',password:'SYNTHETIC_PASSWORD',kbli_prefix:'01111',page:'2'})).toEqual({kbli_prefix:'01111',page:2})
  })
  it('distinguishes all required answer states',()=>{
    for(const key of ['ANSWERED','BLANK_OR_MISSING','SKIPPED_NOT_APPLICABLE','NOT_EXPORTED','UNMATCHED_VERSION','UNVERIFIED_MAPPING'])expect(answerStates[key].label).toBeTruthy()
    expect(answerStates.RESTRICTED.label).toBe('Akses terbatas')
  })
})
