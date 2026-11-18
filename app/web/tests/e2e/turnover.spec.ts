import {test,expect,type Page} from '@playwright/test'

const origin='http://127.0.0.1:8770'
async function select(page:Page,label:string,value:string){
  await page.getByRole('combobox',{name:label,exact:true}).click()
  await page.getByRole('listbox').locator('[role="option"][data-value="'+value+'"]').click()
}

test('turnover filters survive tabs, questionnaire and export context',async({page})=>{
  await page.goto(origin+'/usaha?tab=direktori')
  await select(page,'Kelompok omzet tahunan','KECIL')
  await select(page,'Dasar omzet','ESTIMATE_MONTHLY_X12')
  const row=page.getByRole('row').filter({has:page.getByRole('button',{name:'Buka kuesioner USAHA SINTETIS 8',exact:true})})
  await expect(row).toContainText('≈ Rp2.400.000.000')
  await expect(row).toContainText('Estimasi bulanan × 12')
  await page.getByRole('tab',{name:'KBLI 2025',exact:true}).click()
  await expect(page.getByRole('combobox',{name:'Kelompok omzet tahunan',exact:true})).toContainText('Kecil')
  await expect(page.getByRole('combobox',{name:'Dasar omzet',exact:true})).toContainText('Estimasi')
  await expect(page.locator('.kbli-results')).toBeVisible()
  await page.getByRole('tab',{name:'Direktori',exact:true}).click()
  await page.getByRole('button',{name:'Buka kuesioner USAHA SINTETIS 8',exact:true}).click()
  await expect(page.getByRole('region',{name:'Ringkasan omzet tahunan'})).toContainText('Rp200.000.000/bulan × 12 = estimasi Rp2.400.000.000/tahun')
  await page.getByRole('button',{name:'Kembali ke daftar',exact:true}).click()
  await expect(page.getByRole('combobox',{name:'Dasar omzet',exact:true})).toContainText('Estimasi')
  await page.getByRole('button',{name:'Unduh Excel sesuai pencarian dan filter',exact:true}).click()
  await expect(page.getByRole('dialog')).toContainText('Kelompok omzet')
  await expect(page.getByRole('dialog')).toContainText('Kecil')
  await expect(page.getByRole('dialog')).toContainText('Estimasi bulanan × 12')
})

test('turnover distribution suppresses small cells and drills into the same source',async({page})=>{
  await page.goto(origin+'/usaha?section=omzet')
  await expect(page.getByRole('heading',{name:'Distribusi Omzet Tahunan',exact:true})).toBeVisible()
  await expect(page.locator('.turnover-distribution')).toContainText('Ditahan')
  await expect(page.getByRole('button',{name:'Buka direktori omzet Kecil',exact:true})).toHaveCount(0)
  await select(page,'Sumber','ub')
  await expect(page.getByRole('button',{name:'Buka direktori omzet Kecil',exact:true})).toHaveText('12')
  await page.getByRole('button',{name:'Buka direktori omzet Kecil',exact:true}).click()
  await expect(page).toHaveURL(/turnover_group=KECIL/)
  await expect(page.getByRole('combobox',{name:'Sumber',exact:true})).toContainText('Usaha Besar')
  await expect(page.locator('td[data-column="turnover"]').first()).toContainText('Rp3.000.000.000')
  await expect(page.locator('td[data-column="turnover"]').first()).toContainText('Tahunan dilaporkan')
  await page.getByRole('button',{name:'Reset filter',exact:true}).click()
  await expect(page.getByRole('combobox',{name:'Kelompok omzet tahunan',exact:true})).toContainText('Semua kelompok')
})

test('mobile turnover cards fit the viewport and retain estimate labels',async({page})=>{
  await page.setViewportSize({width:390,height:844})
  await page.goto(origin+'/usaha?tab=direktori&turnover_group=KECIL&turnover_basis=ESTIMATE_MONTHLY_X12')
  await expect(page.locator('td[data-column="turnover"]').first()).toContainText('Estimasi bulanan × 12')
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)).toBeTruthy()
  await page.screenshot({path:'../../docs/reports/app/screenshots/turnover-mobile-synthetic.png',fullPage:false})
  await page.setViewportSize({width:1440,height:1000})
  await page.goto(origin+'/usaha?section=omzet')
  await expect(page.getByRole('heading',{name:'Distribusi Omzet Tahunan',exact:true})).toBeVisible()
  await page.screenshot({path:'../../docs/reports/app/screenshots/turnover-summary-synthetic.png',fullPage:false})
})

test('turnover geography drills to its own level and preserves the selected group',async({page})=>{
  await page.goto(origin+'/usaha?section=omzet&source=ub')
  const cell=page.locator('.turnover-region-table').getByRole('button').first()
  await expect(cell).toHaveText('12')
  await cell.click()
  const search=new URL(page.url()).searchParams
  expect(JSON.parse(search.get('kecamatan')||'null')).toBe('6502010')
  expect(search.has('desa')).toBeFalsy()
  expect(search.has('sls')).toBeFalsy()
  expect(search.get('turnover_group')).toBe('KECIL')
  await expect(page.locator('td[data-column="turnover"]').first()).toContainText('Rp3.000.000.000')
})
