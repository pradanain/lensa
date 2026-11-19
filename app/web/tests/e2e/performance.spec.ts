import {test,expect} from '@playwright/test'

const base='http://127.0.0.1:8767'

test('directory loads no charts and requests KBLI catalog only when opened',async({page})=>{
  const urls:string[]=[]
  page.on('request',request=>urls.push(request.url()))
  await page.goto(base+'/usaha?tab=direktori')
  await expect(page.getByRole('button',{name:'Buka kuesioner USAHA SINTETIS 1',exact:true})).toBeVisible()
  expect(urls.some(url=>url.includes('/assets/charts-'))).toBe(false)
  expect(urls.some(url=>url.includes('/kbli/catalog'))).toBe(false)
  await page.locator('.directory-classification > summary').click()
  await expect(page.getByRole('combobox',{name:'Kategori KBLI',exact:true})).toBeVisible()
  expect(urls.some(url=>url.includes('/kbli/catalog'))).toBe(true)
  expect(urls.some(url=>url.includes('/assets/charts-'))).toBe(false)
})

test('Dashboard family and distribution load while business counts wait; notes load on demand',async({page})=>{
  let release!:()=>void
  const ready=new Promise<void>(resolve=>{release=resolve})
  const urls:string[]=[]
  page.on('request',request=>urls.push(request.url()))
  await page.route('**/api/v1/analytics/business-summary?*',async route=>{await ready;await route.continue()})
  try{
    await page.goto(base+'/dashboard',{waitUntil:'domcontentloaded'})
    await expect(page.getByRole('region',{name:'Keluarga dan anggota',exact:true}).locator('.stat-value')).toHaveCount(2)
    await expect(page.getByRole('img',{name:'Assignment UMKM menurut kecamatan',exact:true})).toBeVisible()
    await expect(page.getByRole('region',{name:'Usaha selesai didata',exact:true}).locator('.stat-value')).toHaveCount(0)
    expect(urls.some(url=>url.includes('/analytics/summary'))).toBe(false)
    expect(urls.some(url=>url.includes('part=notes'))).toBe(false)
    await page.locator('.dashboard-notes > summary').click()
    await expect(page.locator('.dashboard-notes dd')).toHaveCount(4)
    expect(urls.some(url=>url.includes('part=notes'))).toBe(true)
  }finally{release()}
  await expect(page.getByRole('region',{name:'Usaha selesai didata',exact:true}).locator('.stat-value')).toHaveCount(3)
})

test('returning from a form reuses the same private in-memory directory page',async({page})=>{
  let searches=0
  page.on('request',request=>{if(request.url().includes('/directories/businesses/search'))searches++})
  await page.goto(base+'/usaha?tab=direktori')
  await page.getByLabel('Cari direktori',{exact:true}).fill('USAHA SINTETIS KEDUA')
  await page.getByRole('button',{name:'Cari',exact:true}).click()
  const open=page.getByRole('button',{name:'Buka kuesioner USAHA SINTETIS KEDUA',exact:true})
  await expect(open).toBeVisible()
  const before=searches
  await open.click()
  await expect(page.getByRole('heading',{name:'Kuesioner SE2026',exact:true})).toBeVisible()
  await page.getByRole('button',{name:'Kembali ke daftar',exact:true}).click()
  await expect(open).toBeVisible()
  await expect(page.getByLabel('Cari direktori',{exact:true})).toHaveValue('USAHA SINTETIS KEDUA')
  expect(searches).toBe(before)
})

test('turnover totals remain available while geographic distribution waits',async({page})=>{
  let release!:()=>void
  const ready=new Promise<void>(resolve=>{release=resolve})
  await page.route('**/api/v1/analytics/query',async route=>{
    const body=route.request().postDataJSON()
    if(body.metric_id==='usaha.turnover_distribution'&&body.group_by?.length)await ready
    await route.continue()
  })
  try{
    await page.goto(base+'/usaha?section=omzet',{waitUntil:'domcontentloaded'})
    await expect(page.locator('.turnover-distribution table')).toHaveCount(1)
    await expect(page.locator('.turnover-distribution table')).toContainText('Mikro')
  }finally{release()}
  await expect(page.locator('.turnover-distribution table')).toHaveCount(2)
})
