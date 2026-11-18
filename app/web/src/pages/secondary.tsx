import {Pagination} from '@/components/pagination'
import {useDebouncedValue} from '@/lib/use-debounced-value'
import {SearchSelect} from '@/components/ui/search-select'
import { useState, type FormEvent } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { BookOpen, Eye, EyeOff, Plus, Search, Users } from 'lucide-react';
import { api } from '@/lib/api';
import { roleNames } from '@/lib/utils';
import { useAuth } from '@/auth';
import { PageHead, TabBar, Loading, ErrorBox, Notice, Restricted } from '@/components/shared';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Kbli } from './kbli';
export function References(){
  const [tab,setTab]=useState('kbli');const [draft,setDraft]=useState('');const term=useDebouncedValue(draft)
  const [page,setPage]=useState(1);const [pageSize,setPageSize]=useState(10)
  const query=useQuery({queryKey:['reference-search',tab,term,page,pageSize],queryFn:({signal})=>api<{rows:{code:string;title:string}[];total:number}>('/references/'+tab+'?'+new URLSearchParams({q:term,page:String(page),page_size:String(pageSize)}),undefined,undefined,{signal}),enabled:tab!=='kbli'&&term===draft,placeholderData:(previous,previousQuery)=>previousQuery?.queryKey[1]===tab?previous:undefined})
  return <><PageHead eyebrow="REFERENSI LOKAL" title="Referensi data" description="Label dan alias membantu pencarian, tanpa mengubah klasifikasi jawaban sumber."><BookOpen size={25}/></PageHead><TabBar tabs={[{id:'kbli',label:'KBLI 2025'},{id:'professions',label:'Profesi'},{id:'countries',label:'Negara'}]} value={tab} onChange={id=>{setTab(id);setDraft('');setPage(1)}}/>{tab==='kbli'?<Kbli/>:<><Card className="filter-card"><form className="search-row" onSubmit={event=>event.preventDefault()}><Input aria-label="Cari referensi" value={draft} maxLength={100} onChange={event=>{setDraft(event.target.value);setPage(1)}} placeholder={tab==='professions'?'Cari nama profesi, kode atau alias...':'Cari negara atau kode...'}/><Button type="submit">Cari referensi</Button></form><p className="live-search-status" role="status">{query.isFetching||draft!==term?'Memperbarui hasil...':'Hasil diperbarui otomatis saat mengetik.'}</p></Card><Notice>{tab==='professions'?'Alias adalah bantuan pencarian. Kode profesi disimpan sebagai teks tiga digit.':'Label negara mengikuti master lokal. Seluruh baris dipertahankan, termasuk kode dengan label alternatif.'}</Notice>{query.isPending?<Loading variant="table"/>:query.error?<ErrorBox error={query.error}/>:<Card className="table-card reference-results"><div className={'table-scroll '+(query.isPlaceholderData?'is-updating':'')} aria-busy={query.isFetching}><table><thead><tr><th>Kode</th><th>Referensi</th></tr></thead><tbody>{query.data?.rows.map((row,index)=><tr key={row.code+'-'+index}><td><code>{row.code}</code></td><td>{row.title}</td></tr>)}</tbody></table>{!query.data?.rows.length&&<div className="empty"><h3>Tidak ada hasil yang sesuai</h3></div>}</div><Pagination page={page} pageSize={pageSize} total={query.data?.total||0} busy={query.isPlaceholderData} onPage={setPage} onPageSize={value=>{setPageSize(value);setPage(1)}}/></Card>}</>}</>
}

type Account = {
    id: number;
    username: string;
    role: string;
    active: number;
    must_change_password?: number;
};
export function Settings() { const { session } = useAuth(); if (!session?.auth_enabled)
    return <Notice>Pengaturan akun belum digunakan.</Notice>; if (session?.user?.role !== 'admin')
    return <Restricted />; return <Accounts />; }
function Accounts() {
    const { session } = useAuth();
    const client = useQueryClient();
    const users = useQuery({ queryKey: ['users'], queryFn: () => api<{ rows: Account[] }>('/auth/users') });
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [role, setRole] = useState('viewer');
    const [draft, setDraft] = useState('');
    const term = useDebouncedValue(draft);
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(10);
    const [error, setError] = useState('');
    const [saved, setSaved] = useState(false);
    const [pending, setPending] = useState(false);
    const [updating, setUpdating] = useState<number|null>(null);
    const accounts = (users.data?.rows || []).filter(user => user.username.toLowerCase().includes(term.trim().toLowerCase()));
    const currentPage = Math.min(page, Math.max(1, Math.ceil(accounts.length / pageSize)));
    const visible = accounts.slice((currentPage - 1) * pageSize, currentPage * pageSize);
    const busy = pending || updating !== null;
    async function add(event: FormEvent) {
        event.preventDefault(); if (busy) return;
        setError(''); setSaved(false); setPending(true);
        try {
            await api('/auth/users', { username, password, role });
            setUsername(''); setPassword(''); setShowPassword(false); setSaved(true);
            await client.invalidateQueries({ queryKey: ['users'] });
        } catch (error) { setError(error instanceof Error ? error.message : 'Pengguna belum dapat dibuat.'); }
        finally { setPending(false); }
    }
    async function update(account: Account, newRole: string, active: boolean) {
        if (busy) return;
        setError(''); setSaved(false); setUpdating(account.id);
        try {
            await api('/auth/users/' + account.id, { role: newRole, active }, 'PATCH');
            await client.invalidateQueries({ queryKey: ['users'] });
        } catch (error) { setError(error instanceof Error ? error.message : 'Perubahan belum disimpan.'); }
        finally { setUpdating(null); }
    }
    return <div className="accounts-page">
      <PageHead eyebrow="" title="Kelola pengguna" description="Atur peran dan akses akun LENSA."><Users size={24}/></PageHead>
      {error && <div className="form-error" role="alert">{error}</div>}
      <div className="settings-layout">
        <Card className="accounts-card">
          <div className="account-section-heading"><h2>Akun pengguna</h2><span>{users.data ? users.data.rows.length+' akun' : 'Memuat...'}</span></div>
          <div className="account-search search-input"><Search size={16}/><Input aria-label="Cari pengguna" placeholder="Cari nama pengguna..." value={draft} onChange={event=>{setDraft(event.target.value);setPage(1)}}/></div>
          {users.isPending ? <Loading /> : users.error ? <ErrorBox error={users.error} retry={()=>void users.refetch()}/> : <>
            <div className="account-list" aria-busy={updating!==null}>{visible.map(user =>
              <div className="account-row" key={user.id}>
                <div className="avatar" aria-hidden="true">{user.username.slice(0,1).toUpperCase()}</div>
                <div className="account-identity"><strong>{user.username}</strong><small>{updating===user.id?'Menyimpan...':user.id===session?.user?.id?'Akun Anda':!user.active?'Nonaktif':user.must_change_password?'Wajib ganti kata sandi':'Aktif'}</small></div>
                <div className="account-actions">{user.id===session?.user?.id?<Badge>Administrator</Badge>:<>
                  <SearchSelect aria-label={'Peran '+user.username} value={user.role} disabled={busy} onValueChange={value=>void update(user,value,!!user.active)}>{Object.entries(roleNames).map(([key,label])=><option value={key} key={key}>{label}</option>)}</SearchSelect>
                  <Button variant="ghost" size="sm" disabled={busy} aria-label={(user.active?'Nonaktifkan ':'Aktifkan ')+user.username} onClick={()=>void update(user,user.role,!user.active)}>{user.active?'Nonaktifkan':'Aktifkan'}</Button>
                </>}</div>
              </div>)}
            </div>
            {!accounts.length&&<p className="account-empty">Tidak ada pengguna yang sesuai.</p>}
            {accounts.length>10&&<Pagination page={currentPage} pageSize={pageSize} total={accounts.length} busy={busy} onPage={setPage} onPageSize={value=>{setPageSize(value);setPage(1)}}/>}
          </>}
          <p className="account-footnote">Perubahan peran atau status mengakhiri sesi akun tersebut.</p>
        </Card>
        <Card className="add-account-card">
          <div className="account-section-heading"><h2>Tambah pengguna</h2></div>
          <p className="account-form-intro">Pengguna mengganti sandi sementara saat login pertama.</p>
          <form className="account-form" onSubmit={event=>void add(event)}>
            <label>Nama pengguna<Input value={username} onChange={event=>setUsername(event.target.value)} required minLength={3} pattern="[A-Za-z0-9_.@+\-]+" maxLength={128} autoComplete="off" disabled={pending}/></label>
            <label>Kata sandi sementara<span className="account-password"><Input aria-label="Kata sandi sementara" type={showPassword?'text':'password'} value={password} onChange={event=>setPassword(event.target.value)} required minLength={1} maxLength={256} autoComplete="new-password" disabled={pending} aria-describedby="temporary-password-hint"/><Button type="button" variant="ghost" size="icon" aria-label={showPassword?'Sembunyikan kata sandi':'Tampilkan kata sandi'} aria-pressed={showPassword} onClick={()=>setShowPassword(!showPassword)}>{showPassword?<EyeOff size={17}/>:<Eye size={17}/>}</Button></span><small id="temporary-password-hint">Bebas, minimal 1 karakter.</small></label>
            <label>Peran<SearchSelect aria-label="Peran pengguna baru" value={role} disabled={pending} onValueChange={setRole}>{Object.entries(roleNames).map(([key,label])=><option key={key} value={key}>{label}</option>)}</SearchSelect></label>
            <p className="account-role-hint">{role==='viewer'?'Viewer dapat melihat data dan mengunduh Excel.':'Administrator juga dapat mengelola akun dan monitoring aktivitas.'}</p>
            {saved&&<p className="success-text" role="status">Pengguna dibuat. Berikan sandi sementara secara pribadi.</p>}
            <Button disabled={busy} type="submit"><Plus size={16}/>{pending?'Menyimpan...':'Tambah pengguna'}</Button>
          </form>
        </Card>
      </div>
      <details className="account-access-note"><summary>Tentang hak akses</summary><p>Viewer dapat melihat ringkasan, direktori dan kuesioner serta mengunduh Excel. NIK/KK, kontak, koordinat, nominal keuangan dan kondisi kesehatan tetap khusus Administrator. Administrator tidak dapat mengubah perannya sendiri.</p></details>
    </div>;
}
