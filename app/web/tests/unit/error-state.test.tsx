// @vitest-environment jsdom
import {cleanup,fireEvent,render,screen} from '@testing-library/react'
import {afterEach,expect,it,vi} from 'vitest'
import {ErrorState} from '../../src/components/error-state'
import {ApiError} from '../../src/lib/api'

afterEach(cleanup)
it('offers retry without exposing parser errors or private response values',()=>{
  const retry=vi.fn()
  render(<ErrorState error={new SyntaxError('SYNTHETIC_PRIVATE_VALUE')} retry={retry}/>)
  expect(screen.queryByText(/SYNTHETIC_PRIVATE_VALUE/)).toBeNull()
  fireEvent.click(screen.getByRole('button',{name:'Coba lagi'}))
  expect(retry).toHaveBeenCalledOnce()
  expect(screen.getByRole('link',{name:'Kembali ke Dashboard'}).getAttribute('href')).toBe('/dashboard')
})
it('shows a dedicated 404 state and recovery link',()=>{
  render(<ErrorState notFound page/>)
  expect(screen.getByRole('heading',{level:1}).textContent).toBe('Halaman atau data tidak ditemukan')
  expect(screen.getByText('LENSA / 404')).toBeTruthy()
  expect(screen.queryByRole('button',{name:'Coba lagi'})).toBeNull()
})
it('distinguishes access restrictions from unavailable services',()=>{
  render(<ErrorState error={new ApiError(403,'ADMIN_REQUIRED')}/>)
  expect(screen.getByRole('heading').textContent).toBe('Akses belum tersedia')
})
