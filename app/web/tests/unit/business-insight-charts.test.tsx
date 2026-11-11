// @vitest-environment jsdom
import {render,screen,cleanup,fireEvent} from '@testing-library/react'
import {afterEach,expect,it,vi} from 'vitest'
import {Composition,RateCard} from '../../src/components/business-insight-charts'
import type {Metric} from '../../src/lib/api'

const {init}=vi.hoisted(()=>({init:vi.fn(()=>({setOption:vi.fn(),on:vi.fn(),resize:vi.fn(),dispose:vi.fn()}))}))
vi.mock('echarts/core',()=>({init,use:vi.fn()}))
afterEach(()=>{cleanup();vi.clearAllMocks();vi.unstubAllGlobals()})

it('uses the complete sector total for percentages including missing categories',()=>{
  vi.stubGlobal('ResizeObserver',class{observe(){} disconnect(){}})
  render(<Composition label="Sektor" showPercentages data={[{name:'Pertanian',value:60},{name:'Perdagangan',value:30},{name:'Kategori kosong',value:10}]}/> )
  expect(screen.getByText('60%')).toBeTruthy()
  expect(screen.getByText('30%')).toBeTruthy()
  expect(screen.getByText('10%')).toBeTruthy()
  expect(screen.getByRole('img').getAttribute('aria-description')).toContain('Kategori kosong: 10')
})

it('does not derive percentages from partial or zero totals',()=>{
  const {container,unmount}=render(<Composition label="Sektor" showPercentages data={[{name:'A',value:20},{name:'B',value:null}]}/> )
  expect(container.querySelectorAll('.insight-share')).toHaveLength(0)
  expect(init).not.toHaveBeenCalled()
  unmount()
  const empty=render(<Composition label="Sektor" showPercentages data={[{name:'A',value:0}]}/> )
  expect(empty.container.querySelectorAll('.insight-share')).toHaveLength(0)
  expect(empty.container.textContent).not.toMatch(/NaN|Infinity/)
})

it('sector presentation keeps withheld totals private and available categories clickable',()=>{
  const select=vi.fn()
  const {container}=render(<Composition sectorLayout showPercentages onSelect={select} label="Sektor" data={[{code:'A',name:'A · Pertanian',value:20},{code:'G',name:'G · Perdagangan',value:null}]}/> )
  expect(container.querySelector('.sector-donut-total')).toBeNull()
  expect(container.querySelector('.sector-share-track')).toBeNull()
  expect(container.querySelector('.insight-share')).toBeNull()
  fireEvent.click(screen.getByRole('button',{name:'A · Pertanian, 20'}))
  expect(select).toHaveBeenCalledWith('A')
  expect(init).not.toHaveBeenCalled()
})

it('sector list pagination retains the full total and sector shares',()=>{
  vi.stubGlobal('ResizeObserver',class{observe(){} disconnect(){}})
  const {container}=render(<Composition sectorLayout showPercentages label="Sektor" data={Array.from({length:11},(_,i)=>({code:String.fromCharCode(65+i),name:'Sektor '+i,value:10}))}/> )
  expect(container.querySelector('.sector-donut-total strong')?.textContent).toBe('110')
  expect(container.querySelectorAll('.sector-row')).toHaveLength(10)
  fireEvent.click(screen.getByRole('button',{name:'Halaman 2'}))
  expect(container.querySelectorAll('.sector-row')).toHaveLength(1)
  expect(container.querySelector('.insight-share')?.textContent).toBe('9,1%')
})

it('does not draw a whole composition from a partially suppressed dataset',()=>{
  render(<Composition label="Sektor" type="treemap" data={[{name:'A',value:20},{name:'B',value:null}]}/>)
  expect(screen.getByRole('status').textContent).toContain('Proporsi tidak digambarkan')
  expect(init).not.toHaveBeenCalled()
  expect(screen.queryByRole('img')).toBeNull()
})

it('keeps an empty composition distinct from an observed zero',()=>{
  render(<Composition label="Pekerja" data={[{name:'Laki-laki',value:0},{name:'Perempuan',value:0}]}/>)
  expect(screen.getByText('Belum ada data untuk komposisi ini.')).toBeTruthy()
  expect(init).not.toHaveBeenCalled()
})

function metric(value:number|null,suppressed=false):Metric{
  return {metric_id:'usaha.completed_nib_rate',grain:['assignment_id'],unit:'persen',period:'snapshot',interpretation_limits:'',location_concept:'assignment',rows:[{dimensions:{},eligible_rows:suppressed?null:12,numerator:suppressed?null:0,denominator:suppressed?null:12,excluded_rows:suppressed?null:0,value,percentage:value==null?null:String(value),suppressed}]}
}

it('shows a real zero percent without changing missing to zero',()=>{
  const {unmount}=render(<RateCard title="NIB" metric={metric(0)}/>)
  expect(screen.getByRole('img').getAttribute('aria-label')).toBe('NIB: 0 persen')
  unmount()
  render(<RateCard title="NIB" metric={metric(null,true)}/>)
  expect(screen.getByRole('img').getAttribute('aria-label')).toBe('NIB: Tidak tersedia / ditahan')
  expect(screen.getByText('Nilai ditahan.')).toBeTruthy()
})
