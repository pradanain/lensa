import {test,expect,type Page} from '@playwright/test'

async function login(page:Page){
  await page.goto('/dashboard')
  await page.getByLabel('Nama pengguna',{exact:true}).fill('matcher')
  await page.getByLabel('Kata sandi',{exact:true}).fill('Synthetic-only-password-2026!')
  await page.getByRole('button',{name:'Masuk ke portal'}).click()
  await page.getByRole('button',{name:'Saya memahami dan berkomitmen',exact:true}).click()
  await expect(page).toHaveURL(/\/usaha\?tab=direktori/)
  await expect(page.locator('.directory-table tbody tr').first()).toBeVisible()
}

test('Matcher sees only business directory search filters and pagination',async({page})=>{
  const unexpected:string[]=[]
  page.on('request',request=>{
    const path=new URL(request.url()).pathname
    if(path.includes('/api/v1/')&&['/analytics/','/questionnaires/','/export'].some(part=>path.includes(part)))unexpected.push(path)
  })
  await login(page)
  const menu=page.getByRole('navigation',{name:'Menu utama'})
  await expect(menu.getByRole('link')).toHaveCount(1)
  await expect(menu.getByRole('link',{name:'Direktori Usaha'})).toBeVisible()
  await expect(page.getByRole('tab')).toHaveCount(0)
  await expect(page.getByRole('button',{name:/Buka kuesioner|Unduh Excel/})).toHaveCount(0)
  await expect(page.locator('.directory-table th[data-column="open"]')).toHaveCount(0)
  await expect(page.locator('button.record-title')).toHaveCount(0)
  await page.locator('.record-title').first().click()
  await expect(page).toHaveURL(/\/usaha\?tab=direktori/)
  await page.getByLabel('Cari direktori').fill('USAHA SINTETIS 1')
  await page.getByRole('button',{name:'Cari',exact:true}).click()
  await expect(page.locator('.directory-table tbody')).toContainText('USAHA SINTETIS 1')
  expect(page.url()).not.toContain('SINTETIS')
  await page.getByRole('button',{name:'Reset filter',exact:true}).click()
  await page.getByLabel('Sumber',{exact:true}).click()
  await page.getByRole('option',{name:'Usaha Besar (UB)',exact:true}).click()
  await expect(page).toHaveURL(/source=ub/)
  await expect(page.locator('.directory-table tbody tr').first()).toBeVisible()
  expect(unexpected).toEqual([])
})

test('Matcher direct URLs return to directory without requesting forbidden data',async({page})=>{
  await login(page)
  for(const path of ['/questionnaire/dtd/DTD-0001?index1=001','/keluarga','/data/dtd','/dashboard','/pengaturan','/monitoring','/referensi','/kualitas','/usaha?tab=kbli','/usaha?tab=ringkasan']){
    await page.goto(path)
    await expect(page).toHaveURL(/\/usaha\?tab=direktori/)
    await expect(page.locator('.directory-table tbody tr').first()).toBeVisible()
  }
})

test('shared Matcher sessions remain independent across browsers and mobile filters work',async({page,browser})=>{
  await login(page)
  const context=await browser.newContext({baseURL:'http://127.0.0.1:8765',viewport:{width:390,height:844}})
  const mobile=await context.newPage()
  await login(mobile)
  await mobile.getByRole('button',{name:'Filter data',exact:true}).click()
  await expect(mobile.getByLabel('Status',{exact:true})).toBeVisible()
  await mobile.getByLabel('Status',{exact:true}).click()
  await expect(mobile.getByRole('listbox')).toBeVisible()
  await mobile.keyboard.press('Escape')
  await page.locator('.account-trigger').click()
  await page.getByRole('button',{name:'Keluar dari portal',exact:true}).click()
  await expect(page).toHaveURL(/\/login$/)
  await mobile.reload()
  await expect(mobile.locator('.directory-table tbody tr').first()).toBeVisible()
  await expect(mobile.getByRole('button',{name:/Buka kuesioner|Unduh Excel/})).toHaveCount(0)
  await context.close()
})
