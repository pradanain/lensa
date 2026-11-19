import {Pagination} from '@/components/pagination'
import {useDebouncedValue} from '@/lib/use-debounced-value'
import {SearchSelect} from '@/components/ui/search-select'
import { useState, type FormEvent } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { BookOpen, Eye, EyeOff, Plus, Search, Power } from 'lucide-react';
import { api } from '@/lib/api';
import { roleNames } from '@/lib/utils';
import { useAuth } from '@/auth';
import { PageHead, TabBar, Loading, ErrorBox, Notice, Restricted } from '@/components/shared';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Kbli } from './kbli';
import {Modal} from '@/components/ui/modal';
import './admin.css';
export function References(){
  const [tab,setTab]=useState('kbli');const [draft,setDraft]=useState('');const term=useDebouncedValue(draft)
  const [page,setPage]=useState(1);const [pageSize,setPageSize]=useState(10)
  const query=useQuery({queryKey:['reference-search',tab,term,page,pageSize],queryFn:({signal})=>api<{rows:{code:string;title:string}[];total:number}>('/references/'+tab+'?'+new URLSearchParams({q:term,page:String(page),page_size:String(pageSize)}),undefined,undefined,{signal}),enabled:tab!=='kbli'&&term===draft,placeholderData:(previous,previousQuery)=>previousQuery?.queryKey[1]===tab?previous:undefined})
  return <><PageHead eyebrow="REFERENSI LOKAL" title="Referensi data" description="Label dan alias membantu pencarian, tanpa mengubah klasifikasi jawaban sumber."><BookOpen size={25}/></PageHead><TabBar tabs={[{id:'kbli',label:'KBLI 2025'},{id:'professions',label:'Profesi'},{id:'countries',label:'Negara'}]} value={tab} onChange={id=>{setTab(id);setDraft('');setPage(1)}}/>{tab==='kbli'?<Kbli/>:<><Card className="filter-card"><form className="search-row" onSubmit={event=>event.preventDefault()}><Input aria-label="Cari referensi" value={draft} maxLength={100} onChange={event=>{setDraft(event.target.value);setPage(1)}} placeholder={tab==='professions'?'Cari nama profesi, kode atau alias...':'Cari negara atau kode...'}/><Button type="submit">Cari referensi</Button></form><p className="live-search-status" role="status">{query.isFetching||draft!==term?'Memperbarui hasil...':'Hasil diperbarui otomatis saat mengetik.'}</p></Card><Notice>{tab==='professions'?'Alias adalah bantuan pencarian. Kode profesi disimpan sebagai teks tiga digit.':'Label negara mengikuti master lokal. Seluruh baris dipertahankan, termasuk kode dengan label alternatif.'}</Notice>{query.isPending?<Loading variant="table"/>:query.error?<ErrorBox error={query.error}/>:<Card className="table-card reference-results"><div className={'table-scroll '+(query.isPlaceholderData?'is-updating':'')} aria-busy={query.isFetching}><table><thead><tr><th>Kode</th><th>Referensi</th></tr></thead><tbody>{query.data?.rows.map((row,index)=><tr key={row.code+'-'+index}><td><code>{row.code}</code></td><td>{row.title}</td></tr>)}</tbody></table>{!query.data?.rows.length&&<div className="empty"><h3>Tidak ada hasil yang sesuai</h3></div>}</div><Pagination page={page} pageSize={pageSize} total={query.data?.total||0} busy={query.isPlaceholderData} onPage={setPage} onPageSize={value=>{setPageSize(value);setPage(1)}}/></Card>}</>}</>
}

type Account={id:number;username:string;role:string;active:number;must_change_password?:number};
export function Settings(){
  const {session}=useAuth()
  if(!session?.auth_enabled)return <Notice>Pengaturan akun belum digunakan.</Notice>
  if(session.user?.role!=='admin')return <Restricted/>
  return <Accounts/>
}
function Accounts(){
  const {session}=useAuth();const client=useQueryClient()
  const users=useQuery({queryKey:['users'],queryFn:()=>api<{rows:Account[]}>('/auth/users')})
  const [open,setOpen]=useState(false);const [username,setUsername]=useState('');const [password,setPassword]=useState('')
  const [showPassword,setShowPassword]=useState(false);const [role,setRole]=useState('viewer')
  const [draft,setDraft]=useState('');const term=useDebouncedValue(draft)
  const [page,setPage]=useState(1);const [pageSize,setPageSize]=useState(10)
  const [error,setError]=useState('');const [saved,setSaved]=useState(false);const [pending,setPending]=useState(false)
  const [updating,setUpdating]=useState<number|null>(null)
  const accounts=(users.data?.rows||[]).filter(user=>user.username.toLowerCase().includes(term.trim().toLowerCase()))
  const currentPage=Math.min(page,Math.max(1,Math.ceil(accounts.length/pageSize)))
  const visible=accounts.slice((currentPage-1)*pageSize,currentPage*pageSize)
  const busy=pending||updating!==null
  function changeOpen(value:boolean){
    if(pending)return
    setOpen(value);setUsername('');setPassword('');setRole('viewer');setShowPassword(false);setError('')
    if(value)setSaved(false)
  }
  async function add(event:FormEvent){
    event.preventDefault();if(busy)return
    setError('');setSaved(false);setPending(true)
    try{
      await api('/auth/users',{username,password,role})
      setUsername('');setPassword('');setRole('viewer');setShowPassword(false)
      await client.invalidateQueries({queryKey:['users']})
      setSaved(true);setOpen(false)
    }catch(error){setError(error instanceof Error?error.message:'Pengguna belum dapat dibuat.')}
    finally{setPending(false)}
  }
  async function update(account:Account,newRole:string,active:boolean){
    if(busy)return
    setError('');setSaved(false);setUpdating(account.id)
    try{await api('/auth/users/'+account.id,{role:newRole,active},'PATCH');await client.invalidateQueries({queryKey:['users']})}
    catch(error){setError(error instanceof Error?error.message:'Perubahan belum disimpan.')}
    finally{setUpdating(null)}
  }
  return <div className="admin-page accounts-page">
    <div className="admin-page-heading"><PageHead eyebrow="" title="Kelola pengguna" description=""/><span className="admin-page-count">{users.data?users.data.rows.length+' akun':'Memuat...'}</span></div>
    {error&&!open&&<p className="form-error" role="alert">{error}</p>}
    {saved&&<p className="success-text" role="status">Pengguna dibuat. Berikan sandi sementara secara pribadi.</p>}
    <Card className="accounts-card">
      <div className="accounts-toolbar"><div className="account-search search-input"><Search size={16}/><Input aria-label="Cari pengguna" placeholder="Cari nama pengguna..." value={draft} onChange={event=>{setDraft(event.target.value);setPage(1)}}/></div><Button size="icon" aria-label="Tambah pengguna" title="Tambah pengguna" disabled={busy} onClick={()=>changeOpen(true)}><Plus size={19}/></Button></div>
      {users.isPending?<Loading/>:users.error?<ErrorBox error={users.error} retry={()=>void users.refetch()}/>:<>
        <div className="account-list" aria-busy={updating!==null}><table className="account-table"><thead><tr><th>Pengguna</th><th>Peran</th><th>Status</th><th>Aksi</th></tr></thead><tbody>{visible.map(user=><tr className="account-row" key={user.id}>
          <td data-label="Pengguna" className="account-identity"><strong>{user.username}</strong>{user.id===session?.user?.id&&<small>Akun Anda</small>}</td>
          <td data-label="Peran">{user.id===session?.user?.id?<Badge>Administrator</Badge>:<SearchSelect aria-label={'Peran '+user.username} value={user.role} disabled={busy} onValueChange={value=>void update(user,value,!!user.active)}>{Object.entries(roleNames).map(([key,label])=><option value={key} key={key}>{label}</option>)}</SearchSelect>}</td>
          <td data-label="Status"><span className={'account-status '+(!user.active?'inactive':user.must_change_password?'onboarding':'active')}>{updating===user.id?'Menyimpan...':!user.active?'Nonaktif':user.must_change_password?'Wajib ganti kata sandi':'Aktif'}</span></td>
          <td data-label="Aksi" className="account-actions">{user.id===session?.user?.id?<span className="muted">—</span>:<Button variant="ghost" size="icon" disabled={busy} title={user.active?'Nonaktifkan':'Aktifkan'} aria-label={(user.active?'Nonaktifkan ':'Aktifkan ')+user.username} onClick={()=>void update(user,user.role,!user.active)}><Power size={16}/></Button>}</td>
        </tr>)}</tbody></table></div>
        {!accounts.length&&<div className="admin-empty"><strong>Tidak ada pengguna yang sesuai.</strong><p>Coba nama pengguna lain.</p></div>}
        {accounts.length>10&&<Pagination page={currentPage} pageSize={pageSize} total={accounts.length} busy={busy} onPage={setPage} onPageSize={value=>{setPageSize(value);setPage(1)}}/>}
      </>}
    </Card>
    <p className="account-footnote">Perubahan peran atau status mengakhiri sesi akun tersebut.</p>
    <details className="account-access-note"><summary>Tentang hak akses</summary><p>Matcher hanya dapat melihat, mencari dan memfilter Direktori Usaha dengan informasi setara Viewer, tanpa form dan unduhan. Viewer dapat melihat ringkasan, direktori dan kuesioner serta mengunduh Excel. Data sensitif tetap dibatasi sesuai hak akses. Administrator tidak dapat mengubah perannya sendiri.</p></details>
    <Modal open={open} onOpenChange={changeOpen} busy={pending} title="Tambah pengguna" description="Pengguna mengganti sandi sementara saat login pertama.">
      <form className="account-form" onSubmit={event=>void add(event)}>
        <label>Nama pengguna<Input value={username} onChange={event=>setUsername(event.target.value)} required minLength={3} pattern="[A-Za-z0-9_.@+\-]+" maxLength={128} autoComplete="off" disabled={pending}/></label>
        <label>Kata sandi sementara<span className="account-password"><Input aria-label="Kata sandi sementara" type={showPassword?'text':'password'} value={password} onChange={event=>setPassword(event.target.value)} required minLength={1} maxLength={256} autoComplete="new-password" disabled={pending} aria-describedby="temporary-password-hint"/><Button type="button" variant="ghost" size="icon" aria-label={showPassword?'Sembunyikan kata sandi':'Tampilkan kata sandi'} aria-pressed={showPassword} onClick={()=>setShowPassword(!showPassword)}>{showPassword?<EyeOff size={17}/>:<Eye size={17}/>}</Button></span><small id="temporary-password-hint">Bebas, minimal 1 karakter.</small></label>
        <label>Peran<SearchSelect aria-label="Peran pengguna baru" value={role} disabled={pending} onValueChange={setRole}>{Object.entries(roleNames).map(([key,label])=><option key={key} value={key}>{label}</option>)}</SearchSelect></label>
        <p className="account-role-hint">{role==='matcher'?'Matcher dapat dipakai bersama untuk melihat, mencari dan memfilter Direktori Usaha. Form, unduhan dan halaman lain ditutup. Ganti sandi saat login pertama sebelum membagikan akun.':role==='viewer'?'Viewer dapat melihat data dan mengunduh Excel.':'Administrator juga dapat mengelola akun dan monitoring aktivitas.'}</p>
        {error&&<p className="form-error" role="alert">{error}</p>}
        <div className="admin-modal-actions"><Button type="button" variant="outline" disabled={pending} onClick={()=>changeOpen(false)}>Batal</Button><Button disabled={busy} type="submit">{pending?'Menyimpan...':'Tambah pengguna'}</Button></div>
      </form>
    </Modal>
  </div>
}
