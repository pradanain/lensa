import {afterEach,describe,expect,it,vi} from 'vitest'
import {api,downloadXlsx} from '../../src/lib/api'

afterEach(()=>vi.unstubAllGlobals())
function respond(body:string,status=200){vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(body,{status})))}
describe('API response failures',()=>{
  it('turns a plain text 404 into a safe error with its HTTP status',async()=>{
    respond('404 page not found',404)
    await expect(api('/auth/session')).rejects.toMatchObject({status:404,code:'ENDPOINT_NOT_FOUND'})
  })
  it('handles an HTML gateway failure during data loading and export',async()=>{
    respond('<html>private synthetic upstream failure</html>',502)
    await expect(api('/analytics/summary')).rejects.toMatchObject({status:502,code:'SERVICE_UNAVAILABLE'})
    await expect(downloadXlsx('/records/export',{},'test.xlsx')).rejects.toMatchObject({status:502,code:'SERVICE_UNAVAILABLE'})
  })
  it('handles malformed JSON even with a successful HTTP status',async()=>{
    respond('404 page not found')
    await expect(api('/auth/session')).rejects.toMatchObject({status:200,code:'INVALID_RESPONSE'})
  })
  it('preserves successful JSON responses',async()=>{
    respond('{"status":"ok"}')
    await expect(api('/auth/session')).resolves.toEqual({status:'ok'})
  })
  it('preserves the password-change event and safe server error code',async()=>{
    const dispatchEvent=vi.fn();vi.stubGlobal('window',{dispatchEvent})
    respond('{"detail":"PASSWORD_CHANGE_REQUIRED"}',403)
    await expect(api('/records')).rejects.toMatchObject({code:'PASSWORD_CHANGE_REQUIRED'})
    expect(dispatchEvent.mock.calls[0][0].type).toBe('portal-password-change-required')
  })
  it('does not replace aborted body reads with a response error',async()=>{
    const error=new DOMException('Aborted','AbortError')
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:()=>Promise.reject(error)}))
    await expect(api('/records')).rejects.toBe(error)
  })
})
