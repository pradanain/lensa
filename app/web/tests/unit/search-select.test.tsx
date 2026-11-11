// @vitest-environment jsdom
import {useState} from 'react'
import {afterEach,describe,expect,it} from 'vitest'
import {cleanup,fireEvent,render,screen} from '@testing-library/react'
import {SearchSelect} from '../../src/components/ui/search-select'

afterEach(cleanup)
function Example(){const [value,setValue]=useState('');return <SearchSelect aria-label="Kode contoh" value={value} onValueChange={setValue}><option value="">Semua kode</option><option value="01111">01111 - Pertanian Jagung</option><option value="01112">01112 - Pertanian Serealia</option></SearchSelect>}
describe('searchable choice behavior',()=>{
  it('filters locally, keeps leading zeros and returns focus after keyboard selection',()=>{
    render(<Example/>)
    const trigger=screen.getByRole('combobox',{name:'Kode contoh'})
    fireEvent.click(trigger)
    const input=screen.getByLabelText('Cari pilihan Kode contoh')
    fireEvent.change(input,{target:{value:'jagung'}})
    expect(screen.getAllByRole('option')).toHaveLength(1)
    fireEvent.keyDown(input,{key:'Enter'})
    expect(trigger.getAttribute('data-value')).toBe('01111')
    expect(trigger.getAttribute('aria-expanded')).toBe('false')
    expect(document.activeElement).toBe(trigger)
  })
  it('supports empty results and Escape without changing the selected value',()=>{
    render(<Example/>)
    const trigger=screen.getByRole('combobox',{name:'Kode contoh'})
    fireEvent.click(trigger)
    const input=screen.getByLabelText('Cari pilihan Kode contoh')
    fireEvent.change(input,{target:{value:'no-match'}})
    expect(screen.getByRole('status').textContent).toContain('Tidak ada pilihan')
    fireEvent.keyDown(input,{key:'Escape'})
    expect(trigger.getAttribute('data-value')).toBe('')
    expect(document.activeElement).toBe(trigger)
  })
})
