import {test,expect,type Page} from '@playwright/test'

async function signIn(page:Page){
  await page.getByLabel('Nama pengguna',{exact:true}).fill('admin')
  await page.getByLabel('Kata sandi',{exact:true}).fill('Synthetic-only-password-2026!')
  await page.getByRole('button',{name:'Masuk ke portal',exact:true}).click()
  await page.getByRole('button',{name:'Saya memahami dan berkomitmen',exact:true}).click()
}

test('protected routes use login and return to the requested page with filters',async({page})=>{
  await page.goto('/usaha?tab=direktori&source=ub')
  await expect(page).toHaveURL(/\/login$/)
  await expect(page.getByRole('navigation',{name:'Menu utama'})).toHaveCount(0)
  await signIn(page)
  await expect(page).toHaveURL(/\/usaha\?tab=direktori&source=ub$/)
  await expect(page.getByRole('navigation',{name:'Menu utama'})).toBeVisible()
})

test('logout revokes access in every tab and Back cannot reopen protected pages',async({page,context})=>{
  await page.goto('/dashboard')
  await signIn(page)
  await page.getByRole('navigation',{name:'Menu utama'}).getByRole('link',{name:'Keluarga',exact:true}).click()
  const other=await context.newPage()
  await other.goto('/usaha')
  await expect(other.getByRole('navigation',{name:'Menu utama'})).toBeVisible()
  await page.locator('.account-trigger').click()
  await page.getByRole('button',{name:'Keluar dari portal',exact:true}).click()
  for(const tab of [page,other]){
    await expect(tab).toHaveURL(/\/login$/)
    await expect(tab.getByLabel('Kata sandi',{exact:true})).toBeVisible()
    await expect(tab.getByRole('navigation',{name:'Menu utama'})).toHaveCount(0)
  }
  await page.goBack()
  await expect(page).toHaveURL(/\/login$/)
  await expect(page.getByRole('navigation',{name:'Menu utama'})).toHaveCount(0)
  expect((await page.request.get('/api/v1/analytics/business-summary')).status()).toBe(401)
  await page.goto('/questionnaire/dtd/DTD-0001')
  await expect(page).toHaveURL(/\/login$/)
})

test('Back from another document revalidates after logout in another tab',async({page,context})=>{
  await page.goto('/dashboard')
  await signIn(page)
  await page.goto('/api/health')
  const other=await context.newPage()
  await other.goto('/usaha')
  await other.locator('.account-trigger').click()
  await other.getByRole('button',{name:'Keluar dari portal',exact:true}).click()
  await expect(other).toHaveURL(/\/login$/)
  await page.goBack()
  await expect(page).toHaveURL(/\/login$/)
  await expect(page.getByLabel('Kata sandi',{exact:true})).toBeVisible()
  await expect(page.getByRole('navigation',{name:'Menu utama'})).toHaveCount(0)
})

test('an open page returns to login at the server expiry time',async({page})=>{
  let authenticatedReplies=0
  await page.route('**/api/v1/auth/session',async route=>{
    const response=await route.fetch()
    const session=await response.json()
    if(session.user){
      authenticatedReplies++
      if(authenticatedReplies===2){session.expires_at=session.server_time+2}
      if(authenticatedReplies>2){session.user=null;session.expires_at=null}
    }
    await route.fulfill({response,json:session})
  })
  await page.goto('/login')
  await signIn(page)
  await expect(page.getByRole('navigation',{name:'Menu utama'})).toBeVisible()
  await expect(page).toHaveURL(/\/login$/,{timeout:10000})
  await expect(page.getByRole('navigation',{name:'Menu utama'})).toHaveCount(0)
})

test('login with local authentication disabled opens the normal application',async({page})=>{
  await page.goto('http://127.0.0.1:8767/login')
  await expect(page).toHaveURL('http://127.0.0.1:8767/usaha')
  await expect(page.getByLabel('Kata sandi',{exact:true})).toHaveCount(0)
})

test('questionnaire links survive reload during the integrity gate',async({page})=>{
  await page.goto('/questionnaire/dtd/DTD-0001')
  await expect(page).toHaveURL(/\/login$/)
  await page.getByLabel('Nama pengguna',{exact:true}).fill('admin')
  await page.getByLabel('Kata sandi',{exact:true}).fill('Synthetic-only-password-2026!')
  await page.getByRole('button',{name:'Masuk ke portal',exact:true}).click()
  await expect(page).toHaveURL(/\/questionnaire\/dtd\/DTD-0001$/)
  await expect(page.getByRole('dialog',{name:'Pakta integritas',exact:true})).toBeVisible()
  await expect(page.locator('.form-reader')).toHaveCount(0)
  await page.reload()
  await page.getByRole('button',{name:'Saya memahami dan berkomitmen',exact:true}).click()
  await expect(page.locator('.form-reader')).toBeVisible()
})

test('login is visible only after logout navigation finishes before opening another page',async({page})=>{
  await page.goto('/dashboard')
  for(let cycle=0;cycle<3;cycle++){
    await signIn(page)
    await page.locator('.account-trigger').click()
    await page.getByRole('button',{name:'Keluar dari portal',exact:true}).click()
    await expect(page.getByLabel('Nama pengguna',{exact:true})).toBeVisible()
    // Starting another navigation as soon as the form is visible must not race
    // a pending document replacement and abort the user's requested page.
    await page.goto('/dashboard')
    await expect(page).toHaveURL(/\/login$/)
    await expect(page.getByLabel('Kata sandi',{exact:true})).toBeVisible()
  }
})

test('password visibility works by keyboard and a pending login cannot submit twice',async({page})=>{
  let attempts=0
  let release=()=>{}
  const released=new Promise<void>(resolve=>{release=resolve})
  await page.route('**/api/v1/auth/login',async route=>{
    attempts++
    await released
    await route.fulfill({status:401,json:{detail:'LOGIN_FAILED'}})
  })
  await page.goto('/login')
  const username=page.getByLabel('Nama pengguna',{exact:true})
  const password=page.getByLabel('Kata sandi',{exact:true})
  await username.fill('admin')
  await password.fill('Synthetic1!')
  await username.focus()
  await page.keyboard.press('Tab')
  await expect(password).toBeFocused()
  await page.keyboard.press('Tab')
  await expect(page.getByRole('button',{name:'Tampilkan kata sandi',exact:true})).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(password).toHaveAttribute('type','text')
  await expect(password).toHaveValue('Synthetic1!')
  expect(attempts).toBe(0)
  await page.keyboard.press('Enter')
  await expect(password).toHaveAttribute('type','password')
  await page.keyboard.press('Tab')
  await expect(page.getByRole('button',{name:'Masuk ke portal',exact:true})).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('button',{name:'Memproses...',exact:true})).toBeDisabled()
  await expect(password).toBeDisabled()
  await expect.poll(()=>attempts).toBe(1)
  await page.keyboard.press('Enter')
  release()
  await expect(page.getByRole('alert')).toContainText('belum sesuai')
  await expect(password).toBeEnabled()
  await expect(password).toHaveValue('Synthetic1!')
  expect(attempts).toBe(1)
})
