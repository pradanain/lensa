import {test,expect} from '@playwright/test'

const base='http://127.0.0.1:8767'
test('unknown page shows the LENSA 404 design and returns to Dashboard',async({page})=>{
  await page.goto(base+'/synthetic-missing-page')
  await expect(page.getByRole('heading',{name:'Halaman atau data tidak ditemukan'})).toBeVisible()
  await expect(page.getByText('LENSA / 404')).toBeVisible()
  await page.screenshot({path:'../../docs/reports/app/screenshots/error-404-desktop.png',fullPage:true})
  await page.getByRole('link',{name:'Kembali ke Dashboard',exact:true}).click()
  await expect(page).toHaveURL(base+'/dashboard')
  await expect(page.locator('.error-state')).toHaveCount(0)
})
test('session gateway failure has a safe message and retry restores the app',async({page})=>{
  await page.route('**/api/v1/auth/session',route=>route.fulfill({status:502,contentType:'text/html',body:'<h1>SYNTHETIC_PRIVATE_UPSTREAM</h1>'}))
  await page.goto(base+'/usaha')
  await expect(page.getByRole('heading',{name:'Data belum dapat dimuat'})).toBeVisible()
  await expect(page.getByText('LENSA / 502')).toBeVisible()
  await expect(page.getByText(/SYNTHETIC_PRIVATE_UPSTREAM|Unexpected/)).toHaveCount(0)
  await page.screenshot({path:'../../docs/reports/app/screenshots/error-service-desktop.png',fullPage:true})
  await page.unroute('**/api/v1/auth/session')
  await page.getByRole('button',{name:'Coba lagi'}).click()
  await expect(page.locator('.brand-name-full')).toBeVisible()
  await expect(page.locator('.error-state')).toHaveCount(0)
})
test('plain text API 404 works on mobile without horizontal overflow',async({page})=>{
  await page.setViewportSize({width:390,height:844})
  await page.route('**/api/v1/auth/session',route=>route.fulfill({status:404,contentType:'text/plain',body:'404 page not found'}))
  await page.goto(base+'/keluarga')
  await expect(page.getByRole('heading',{name:'Halaman atau data tidak ditemukan'})).toBeVisible()
  await expect(page.getByRole('link',{name:'Kembali ke Dashboard'})).toBeVisible()
  await expect(page.getByText(/Unexpected non-whitespace/)).toHaveCount(0)
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true)
  await page.screenshot({path:'../../docs/reports/app/screenshots/error-404-mobile.png',fullPage:true})
})
