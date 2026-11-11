import {defineConfig,devices} from '@playwright/test'
import {fileURLToPath,URL} from 'node:url'
import {resolve} from 'node:path'

const root=fileURLToPath(new URL('../../',import.meta.url))
const python=resolve(root,process.env.SE2026_TEST_PYTHON || (process.platform==='win32'?'.cache/venv/Scripts/python.exe':'.cache/venv/bin/python'))
export default defineConfig({
  testDir:'tests/e2e',fullyParallel:false,workers:1,retries:0,timeout:30000,
  reporter:[['list'],['json',{outputFile:'../../docs/reports/app/browser_tests.json'}]],
  use:{baseURL:'http://127.0.0.1:8765',...devices['Desktop Chrome'],channel:process.env.SE2026_BROWSER_CHANNEL||'chrome',trace:'retain-on-failure',screenshot:'only-on-failure'},
  webServer:[
    {command:'"'+python+'" -B app/tests/web/serve.py --port 8765',cwd:root,url:'http://127.0.0.1:8765/api/health',reuseExistingServer:false,timeout:60000},
    {command:'"'+python+'" -B app/tests/web/serve.py --port 8766 --empty-users',cwd:root,url:'http://127.0.0.1:8766/api/health',reuseExistingServer:false,timeout:60000},
    {command:'"'+python+'" -B app/tests/web/serve.py --port 8767 --no-login',cwd:root,url:'http://127.0.0.1:8767/api/health',reuseExistingServer:false,timeout:60000},
    {command:'"'+python+'" -B app/tests/web/serve.py --port 8768 --no-login --business-focus',cwd:root,url:'http://127.0.0.1:8768/api/health',reuseExistingServer:false,timeout:60000},
  ],
})
