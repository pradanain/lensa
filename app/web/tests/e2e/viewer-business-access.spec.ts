import {test,expect} from '@playwright/test'

test('Viewer sees turnover, Maps and family address while identity numbers stay masked',async({page})=>{
  await page.goto('/usaha?tab=direktori')
  await page.getByLabel('Nama pengguna',{exact:true}).fill('viewer')
  await page.getByLabel('Kata sandi',{exact:true}).fill('Synthetic-only-password-2026!')
  await page.getByRole('button',{name:'Masuk ke portal'}).click()
  await page.getByRole('button',{name:'Saya memahami dan berkomitmen',exact:true}).click()
  await page.route('**/api/v1/directories/businesses/search',async route=>{
    const response=await route.fetch()
    const data=await response.json()
    data.rows=data.rows.slice(0,1).map((row:Record<string,unknown>)=>({...row,
      map_coordinates:{latitude:'2.125',longitude:'117.25'},map_status:'AVAILABLE',
      turnover:{group:'KECIL',basis:'ESTIMATE_MONTHLY_X12',period:'ESTIMATE_12_MONTHS_FROM_2026',reason:'AVAILABLE',amount_status:'AVAILABLE',annual:'2400000000',monthly:'200000000'},
    }))
    await route.fulfill({response,json:data})
  })
  await page.goto('/usaha?tab=direktori')
  await expect(page.locator('td[data-column="turnover"]').first()).toContainText('Rp2.400.000.000')
  await expect(page.locator('td[data-column="turnover"]').first()).toContainText('Estimasi bulanan × 12')
  await expect(page.locator('.directory-map').first()).toHaveAttribute('href','https://www.google.com/maps/search/?api=1&query=2.125%2C117.25')
  await expect(page.locator('.directory-map').first()).toHaveAttribute('rel','noopener noreferrer')
  await page.getByRole('button',{name:'Unduh Excel sesuai pencarian dan filter',exact:true}).click()
  const downloaded=page.waitForEvent('download')
  await page.getByRole('button',{name:'Ya, unduh',exact:true}).click()
  expect((await downloaded).suggestedFilename()).toBe('lensa-umkm.xlsx')
  await page.route('**/api/v1/directories/families/search',async route=>{
    const response=await route.fetch()
    const data=await response.json()
    data.rows=data.rows.slice(0,1).map((row:Record<string,unknown>)=>({...row,
      family_address:'Jalan SINTETIS 10',map_coordinates:{latitude:'2.125',longitude:'117.25'},map_status:'AVAILABLE',
    }))
    await route.fulfill({response,json:data})
  })
  await page.goto('/keluarga?tab=direktori')
  await expect(page.locator('td[data-column="family_address"]').first()).toHaveText('Jalan SINTETIS 10')
  await expect(page.locator('.family-kk').first()).toContainText('••••••••')
  await expect(page.locator('.directory-map').first()).toBeVisible()
})
