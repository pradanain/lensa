import {describe,expect,it} from 'vitest'
import type {Question} from '../../src/lib/api'
import {answerText,questionNumber} from '../../src/lib/questionnaire-display'

const field=(props:Partial<Question>)=>({question_id:'synthetic',value:null,label:null,converter:'text',...props} as Question)

describe('questionnaire presentation',()=>{
  it('groups large decimal strings without losing precision',()=>{
    expect(answerText(field({converter:'decimal',parse_status:'VALID',numeric_value:'12345678901234567890.10'}))).toBe('12.345.678.901.234.567.890,1')
    expect(answerText(field({converter:'decimal',value:'11825263478.50',parse_status:'VALID'}))).toBe('11.825.263.478,5')
    expect(answerText(field({display_format:'number',value:'12345'}))).toBe('12.345')
  })
  it('leaves identifiers years and ambiguous separators intact',()=>{
    for(const value of ['00123','6502010001000101','2007','1234567890123456'])expect(answerText(field({value}))).toBe(value)
    expect(answerText(field({converter:'decimal',value:'1.234',parse_status:'AMBIGUOUS_SEPARATOR'}))).toBe('1.234')
    expect(answerText(field({converter:'decimal',value:'0',parse_status:'VALID'}))).toBe('0')
  })
  it('shows the choice label without repeating a code or a multi selection list',()=>{
    expect(answerText(field({value:'4',label:'4. Tidak tahu tentang NIB'}))).toBe('4. Tidak tahu tentang NIB')
    expect(answerText(field({value:'01a',label:'Perseroan'}))).toBe('01a · Perseroan')
    expect(answerText(field({value:'["1","2"]',label:'1. Ya; 2. Tidak',label_status:'TEMPLATE_MULTI'}))).toBe('1. Ya; 2. Tidak')
  })
  it('recognizes DTD and UB main numbers while keeping subquestions together',()=>{
    const cases: [string,string|null][] = [['30. f. Total pengeluaran','30'],['31. a. Pendapatan','31'],['20a. Pekerja laki-laki','20'],['20b. Pekerja perempuan','20'],['Nama pengusaha',null]]
    for(const [text,n] of cases)expect(questionNumber({question_text:text})).toBe(n)
  })
})
