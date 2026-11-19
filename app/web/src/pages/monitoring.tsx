import {useState} from 'react'
import {useQuery} from '@tanstack/react-query'
import {Download,RefreshCw,ShieldCheck,SlidersHorizontal,MoreHorizontal} from 'lucide-react'
import {useAuth} from '@/auth'
import {api,downloadXlsx} from '@/lib/api'
import {PageHead,ErrorBox,Loading,Notice,TabBar} from '@/components/shared'
import {Pagination} from '@/components/pagination'
import {SearchSelect} from '@/components/ui/search-select'
import {Button} from '@/components/ui/button'
import {Input} from '@/components/ui/input'
import {Card} from '@/components/ui/card'
import {Modal} from '@/components/ui/modal'
import './admin.css'
import './monitoring.css'

type Activity={id:number;occurred_at:number;user_id:number|null;username:string|null;role:string;session_ref:string;request_id:string;action:string;evidence:string;endpoint:string;method:string;status:number;duration_ms:number;response_bytes:number;ip:string;agent:string;context:Record<string,unknown>;event_hash:string}
type Result={rows:Activity[];total:number;summary:Record<string,number|null>;actions:string[];legacy_events:number}
type SessionRow={user_id:number|null;username:string;session_ref:string;first_seen:number;last_seen:number;events:number;exports:number;active:boolean}
const labels:Record<string,string>={LOGIN:'Login',LOGOUT:'Keluar',PASSWORD_CHANGE:'Ganti kata sandi',COMMITMENT:'Pakta integritas',USER_CREATE:'Tambah akun',USER_UPDATE:'Ubah akun',DIRECTORY_SEARCH:'Pencarian direktori',DETAIL_VIEW:'Akses kuesioner',EXPORT:'Unduh data',API_ACCESS:'Akses API',PAGE_VIEW:'Buka halaman / bagian',CONTROL_CLICK:'Klik kontrol',MONITOR_VIEW:'Buka monitoring',MONITOR_EXPORT:'Unduh jejak aktivitas',INTEGRITY_CHECK:'Periksa integritas'}
function when(value:number){return new Date(value).toLocaleString('id-ID',{dateStyle:'medium',timeStyle:'medium'})}
function localDate(value:string,end=false){return value?new Date(value+(end?'T23:59:59.999':'T00:00:00')).getTime():undefined}
export function Monitoring(){const {session}=useAuth();if(session?.user?.role!=='admin'||!session.auth_enabled)return <Notice>Monitoring aktivitas hanya tersedia untuk administrator.</Notice>;return <ActivityMonitor/>}
function ActivityMonitor(){
  const [user,setUser]=useState('non_admin')
  const [action,setAction]=useState('');const [outcome,setOutcome]=useState('');const [since,setSince]=useState('');const [until,setUntil]=useState('')
  const [sessionRef,setSessionRef]=useState('');const [resourceRef,setResourceRef]=useState('');const [tab,setTab]=useState('events')
  const [page,setPage]=useState(1);const [pageSize,setPageSize]=useState(10);const [error,setError]=useState('');const [busy,setBusy]=useState(false)
  const [datesOpen,setDatesOpen]=useState(false);const [detail,setDetail]=useState<Activity|null>(null)
  const specificUser=/^\d+$/.test(user)
  const accountFilter={account_scope:specificUser?'all':user,user_id:specificUser?Number(user):undefined}
  const filter={...accountFilter,action,outcome,since:localDate(since),until:localDate(until,true),session_ref:sessionRef,resource_ref:resourceRef}
  const params=new URLSearchParams({page:String(page),page_size:String(pageSize)})
  Object.entries(filter).forEach(([key,value])=>{if(value!==undefined&&value!=='')params.set(key,String(value))})
  const sessionParams=new URLSearchParams({account_scope:accountFilter.account_scope,...(specificUser?{user_id:user}:{})})
  const query=useQuery({queryKey:['activity',params.toString()],queryFn:({signal})=>api<Result>('/activity?'+params,undefined,undefined,{signal}),staleTime:0})
  const users=useQuery({queryKey:['users'],queryFn:()=>api<{rows:{id:number;username:string;role:string}[]}>('/auth/users')})
  const sessions=useQuery({queryKey:['activity-sessions',sessionParams.toString()],queryFn:({signal})=>api<{rows:SessionRow[]}>('/activity/sessions?'+sessionParams,undefined,undefined,{signal}),enabled:tab==='sessions',staleTime:0})
  const [integrity,setIntegrity]=useState<{valid:boolean;checked:number;last_id:number;head:string}|null>(null)
  async function verify(){setBusy(true);setError('');try{setIntegrity(await api('/activity/integrity'))}catch(e){setError(e instanceof Error?e.message:'Pemeriksaan gagal.')}finally{setBusy(false)}}
  async function download(){setBusy(true);setError('');try{await downloadXlsx('/activity/export',filter,'lensa-aktivitas-utc.xlsx')}catch(e){setError(e instanceof Error?e.message:'Unduhan gagal.')}finally{setBusy(false)}}
  function reset(){setUser('non_admin');setAction('');setOutcome('');setSince('');setUntil('');setSessionRef('');setResourceRef('');setDatesOpen(false);setPage(1)}
  function changeAccount(value:string){setUser(value);setSessionRef('');setResourceRef('');setPage(1)}
  function traceSession(ref:string,userId?:number|null){
    setAction('');setOutcome('');setSince('');setUntil('');setResourceRef('');setPage(1)
    if(userId)setUser(String(userId))
    setSessionRef(ref);setTab('events');setDetail(null)
  }
  return <div className="admin-page activity-monitor">
    <div className="admin-page-heading"><PageHead eyebrow="" title="Monitoring aktivitas" description=""/>
      <div className="admin-page-actions"><Button variant="outline" size="icon" aria-label="Perbarui" title="Perbarui" onClick={()=>{void query.refetch();if(tab==='sessions')void sessions.refetch()}}><RefreshCw size={17}/></Button><Button variant="outline" size="icon" aria-label="Periksa integritas" title="Periksa integritas" disabled={busy} onClick={()=>void verify()}><ShieldCheck size={17}/></Button><Button disabled={busy||tab!=='events'} onClick={()=>void download()}><Download size={16}/>Unduh Excel</Button></div>
    </div>
    <div className="activity-summary" aria-label="Ringkasan aktivitas sesuai filter">{[['Aktivitas','total'],['Akun','accounts'],['Login','logins'],['Unduhan','exports'],['Gagal / ditolak','failures']].map(([title,key])=><div key={key}><span>{title}</span><strong>{query.data?(query.data.summary[key]||0).toLocaleString('id-ID'):'\u2014'}</strong></div>)}</div>
    <Card className="activity-results">
      <div className="activity-toolbar"><TabBar tabs={[{id:'events',label:'Aktivitas'},{id:'sessions',label:'Sesi terbaru'}]} value={tab} onChange={setTab}/><span className="activity-time-note">Waktu lokal perangkat</span></div>
      <div className="activity-filters">
        <label>Akun<SearchSelect aria-label="Filter akun" value={user} onValueChange={changeAccount}><option value="non_admin">Selain administrator</option><option value="all">Semua akun</option><option value="admin">Administrator saja</option>{users.data?.rows.map(row=><option key={row.id} value={row.id}>{row.username}{row.role==='admin'?' (Admin)':''}</option>)}</SearchSelect></label>
        {tab==='events'&&<><label>Aktivitas<SearchSelect aria-label="Filter aktivitas" value={action} onValueChange={v=>{setAction(v);setPage(1)}}><option value="">Semua aktivitas</option>{query.data?.actions.map(value=><option key={value} value={value}>{labels[value]||value}</option>)}</SearchSelect></label><label>Hasil<SearchSelect aria-label="Filter hasil" value={outcome} onValueChange={v=>{setOutcome(v);setPage(1)}}><option value="">Semua hasil</option><option value="success">Berhasil</option><option value="failure">Gagal / ditolak</option></SearchSelect></label><Button variant="outline" aria-expanded={datesOpen} aria-controls="activity-dates" onClick={()=>setDatesOpen(!datesOpen)}><SlidersHorizontal size={15}/>Tanggal{since||until?' •':''}</Button></>}
        <Button variant="ghost" onClick={reset}>Reset filter</Button>
      </div>
      {tab==='events'&&datesOpen&&<div className="activity-dates" id="activity-dates"><label>Dari tanggal<Input type="date" aria-label="Dari tanggal" value={since} onChange={e=>{setSince(e.target.value);setPage(1)}}/></label><label>Sampai tanggal<Input type="date" aria-label="Sampai tanggal" value={until} onChange={e=>{setUntil(e.target.value);setPage(1)}}/></label></div>}
      {sessionRef&&<Notice>Sedang menelusuri sesi <code>{sessionRef}</code>. <Button variant="ghost" size="sm" onClick={()=>{setSessionRef('');setPage(1)}}>Semua sesi</Button></Notice>}
      {resourceRef&&<Notice>Sedang menelusuri referensi data yang sama. <Button variant="ghost" size="sm" onClick={()=>{setResourceRef('');setPage(1)}}>Semua data</Button></Notice>}
      {tab==='events'?(query.isPending?<Loading variant="table"/>:query.error?<ErrorBox error={query.error} retry={()=>void query.refetch()}/>:<>
        <div className="activity-table-wrap"><table className="activity-table"><thead><tr><th>Waktu / akun</th><th>Aktivitas</th><th>Halaman</th><th>Hasil</th></tr></thead><tbody>{query.data?.rows.map(row=><tr key={row.id}>
          <td data-label="Waktu / akun"><strong>{row.username||'Tanpa akun'}</strong><small>{when(row.occurred_at)}</small></td>
          <td data-label="Aktivitas">{labels[row.action]||row.action}</td>
          <td data-label="Halaman">{[row.context.screen,row.context.tab,row.context.block,row.context.scope,row.context.system].filter(Boolean).map(String).join(' · ')||'—'}</td>
          <td data-label="Hasil"><div className="activity-row-actions"><span className={'activity-status '+(row.status<400?'success':'failure')}>{row.status<400?'Berhasil':'Gagal / ditolak'}</span><Button variant="ghost" size="icon" aria-label={'Rincian aktivitas '+row.id} title="Lihat rincian" onClick={()=>setDetail(row)}><MoreHorizontal size={17}/></Button></div></td>
        </tr>)}</tbody></table>{!query.data?.total&&<div className="admin-empty"><ShieldCheck size={24}/><strong>Belum ada aktivitas yang sesuai</strong><p>Ubah filter akun untuk melihat aktivitas lain.</p></div>}</div>
        <Pagination page={page} pageSize={pageSize} total={query.data?.total||0} onPage={setPage} onPageSize={v=>{setPageSize(v);setPage(1)}}/>
      </>):sessions.isPending?<Loading/>:sessions.error?<ErrorBox error={sessions.error} retry={()=>void sessions.refetch()}/>:<div className="activity-sessions">{!sessions.data?.rows.length&&<div className="admin-empty"><strong>Belum ada sesi yang sesuai</strong><p>Ubah filter akun untuk melihat sesi lain.</p></div>}{sessions.data?.rows.map(row=><Card key={row.session_ref}><div className="activity-session-heading"><strong>{row.username||'Tanpa akun'}</strong><span className={'activity-status '+(row.active?'success':'')}>{row.active?'Sesi masih berlaku':'Sesi telah berakhir'}</span></div><p>{when(row.first_seen)} — {when(row.last_seen)}</p><div className="activity-session-heading"><small>{row.events.toLocaleString('id-ID')} aktivitas · {row.exports} unduhan</small><Button variant="outline" size="sm" onClick={()=>traceSession(row.session_ref,row.user_id)}>Telusuri sesi</Button></div></Card>)}</div>}
    </Card>
    {error&&<p className="form-error" role="alert">{error}</p>}
    {integrity&&<Notice tone={integrity.valid?'neutral':'warning'}>{integrity.valid?'Rantai catatan sesuai':'Perubahan catatan terdeteksi'} · {integrity.checked.toLocaleString('id-ID')} catatan diperiksa hingga ID {integrity.last_id}.<details><summary>Sidik pemeriksaan</summary><code>{integrity.head}</code></details></Notice>}
    <details className="activity-about"><summary>Tentang catatan aktivitas</summary><p>Aktivitas administrator tetap dicatat. Pilih akun atau Administrator saja untuk menampilkannya. Jejak rinci dimulai sejak fitur diaktifkan; {query.data?.legacy_events||0} catatan ringkas tersimpan terpisah. Klik browser dapat tidak terkirim atau dimanipulasi; akses dan unduhan API dicatat server. IP dapat dipakai bersama. Catatan membantu penelusuran, bukan bukti tunggal pelaku kebocoran. Tidak merekam isi pencarian, jawaban, kata sandi, atau tangkapan layar.</p></details>
    <Modal open={detail!==null} onOpenChange={open=>{if(!open)setDetail(null)}} title="Rincian aktivitas" description={detail?`${detail.username||'Tanpa akun'} · ${when(detail.occurred_at)}`:''}>
      {detail&&<div className="activity-detail"><dl>
        <dt>Aktivitas</dt><dd>{labels[detail.action]||detail.action} · #{detail.id}</dd>
        <dt>Peran tercatat</dt><dd>{detail.role==='admin'?'Administrator':['viewer','analyst_detail','aggregate_viewer'].includes(detail.role)?'Viewer':'Tanpa akun'}</dd>
        <dt>Bukti</dt><dd>{detail.evidence==='browser'?'Dilaporkan browser':'Dicatat server'}</dd>
        <dt>Endpoint</dt><dd><code>{detail.endpoint}</code></dd>
        <dt>Status / durasi</dt><dd>{detail.status} · {detail.duration_ms} ms</dd>
        <dt>Alamat IP</dt><dd>{detail.ip}</dd><dt>Browser / perangkat</dt><dd>{detail.agent||'Tidak tersedia'}</dd>
        <dt>Respons</dt><dd>{detail.method} · {detail.response_bytes.toLocaleString('id-ID')} byte disiapkan</dd>
        <dt>Referensi sesi</dt><dd>{detail.session_ref?<button className="activity-text-link" onClick={()=>traceSession(detail.session_ref,detail.user_id)}>{detail.session_ref}</button>:'Tidak ada'}</dd>
        <dt>Referensi request</dt><dd><code>{detail.request_id}</code></dd>
        <dt>Referensi akses data</dt><dd>{typeof detail.context.resource_ref==='string'?<button className="activity-text-link" onClick={()=>{setSessionRef('');setResourceRef(String(detail.context.resource_ref));setPage(1);setDetail(null)}}>Telusuri akses data yang sama</button>:'Tidak ada'}</dd>
        <dt>Konteks</dt><dd><pre>{JSON.stringify(detail.context,null,2)}</pre></dd>
      </dl></div>}
    </Modal>
  </div>
}
