// Read-only local UI timings; no screenshots, respondent values, or response bodies recorded.
import {chromium} from '../../web/node_modules/playwright/index.mjs'
import {writeFile} from 'node:fs/promises'

const browser=await chromium.launch({channel:'chrome',headless:true})
const context=await browser.newContext()
const page=await context.newPage()
const results=[]
try{
  for(const attempt of ['first-visit','repeat-visit']){
    const start=performance.now()
    await page.goto('http://127.0.0.1:8000/usaha')
    await page.getByRole('img',{name:'Komposisi sektor usaha',exact:true}).waitFor()
    const compositionMs=performance.now()-start
    await page.waitForFunction(()=>{
      const cells=[...document.querySelectorAll('.business-summary .stat-value')]
      return cells.length===3&&cells.every(cell=>/\d/.test(cell.textContent))
    })
    results.push({attempt,composition_ms:Math.round(compositionMs),cards_ms:Math.round(performance.now()-start)})
  }
  const start=performance.now()
  await page.getByRole('tab',{name:'Direktori',exact:true}).click()
  await page.getByRole('table').waitFor()
  await page.waitForFunction(()=>document.querySelectorAll('tbody tr').length>0&&!document.querySelector('.is-updating'))
  results.push({attempt:'directory-navigation',ready_ms:Math.round(performance.now()-start)})
  await writeFile(new URL('../../../docs/reports/app/business_ui_timings.json',import.meta.url),JSON.stringify({results,limitations:'One local run; existing OS and app index caches retained. No respondent values recorded.'},null,2)+'\n')
  process.stdout.write(JSON.stringify(results)+'\n')
}finally{await browser.close()}
