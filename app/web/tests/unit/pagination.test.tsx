// @vitest-environment jsdom
import {render,screen,fireEvent,cleanup} from '@testing-library/react'
import {afterEach,it,expect,vi} from 'vitest'
import {Pagination} from '../../src/components/pagination'

afterEach(cleanup)
it('shows surrounding pages and the final page and allows direct jumps',()=>{
  const change=vi.fn()
  render(<Pagination page={50} pageSize={10} total={990} onPage={change} onPageSize={()=>{}}/>)
  expect(screen.getByRole('button',{name:'Halaman 50'}).getAttribute('aria-current')).toBe('page')
  for(const value of [1,49,50,51,99])expect(screen.getByRole('button',{name:'Halaman '+value})).toBeDefined()
  expect(screen.getAllByText('…')).toHaveLength(2)
  fireEvent.click(screen.getByRole('button',{name:'Halaman 99'}))
  expect(change).toHaveBeenCalledWith(99)
})
it('has one active page and disables both arrows for empty results',()=>{
  render(<Pagination page={1} pageSize={10} total={0} onPage={()=>{}} onPageSize={()=>{}}/>)
  expect(screen.getByRole('button',{name:'Halaman sebelumnya'}).hasAttribute('disabled')).toBe(true)
  expect(screen.getByRole('button',{name:'Halaman berikutnya'}).hasAttribute('disabled')).toBe(true)
  expect(screen.getByRole('button',{name:'Halaman 1'}).getAttribute('aria-current')).toBe('page')
})
