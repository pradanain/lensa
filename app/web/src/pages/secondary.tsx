import {Pagination} from '@/components/pagination'
import {useDebouncedValue} from '@/lib/use-debounced-value'
import {SearchSelect} from '@/components/ui/search-select'
import { useState, type FormEvent } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { BookOpen, Plus, Users } from 'lucide-react';
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
};
export function Settings() { const { session } = useAuth(); if (!session?.auth_enabled)
    return <Notice>Pengaturan akun belum digunakan.</Notice>; if (session?.user?.role !== 'admin')
    return <Restricted />; return <Accounts />; }
function Accounts() {
    const { session } = useAuth();
    const client = useQueryClient();
    const users = useQuery({ queryKey: ['users'], queryFn: () => api<{
            rows: Account[];
        }>('/auth/users') });
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [role, setRole] = useState('aggregate_viewer');
    const [error, setError] = useState('');
    const [saved, setSaved] = useState(false);
    const [pending, setPending] = useState(false);
    async function add(event: FormEvent) { event.preventDefault(); setError(''); setSaved(false); setPending(true); try {
        await api('/auth/users', { username, password, role });
        setUsername('');
        setPassword('');
        setSaved(true);
        await client.invalidateQueries({ queryKey: ['users'] });
    }
    catch (error) {
        setError(error instanceof Error ? error.message : 'Pengguna belum dapat dibuat.');
    }
    finally {
        setPending(false);
    } }
    async function update(account: Account, newRole: string, active: boolean) { setError(''); try {
        await api('/auth/users/' + account.id, { role: newRole, active }, 'PATCH');
        await client.invalidateQueries({ queryKey: ['users'] });
    }
    catch (error) {
        setError(error instanceof Error ? error.message : 'Perubahan belum disimpan.');
    } }
    return <><PageHead eyebrow="PENGATURAN LOKAL" title="Akses yang terkelola" description="Kelola akun portal. Perubahan peran mengakhiri sesi pengguna tersebut."><Users size={24}/></PageHead><div className="settings-layout"><Card><div className="card-heading"><div><h2>Akun pengguna</h2><p>Administrator tidak mengubah perannya sendiri.</p></div></div>{users.isPending ? <Loading /> : users.error ? <ErrorBox error={users.error}/> : <div className="account-list">{users.data?.rows.map(user => <div className="account-row" key={user.id}><div className="avatar">{user.username.slice(0, 1).toUpperCase()}</div><div><strong>{user.username}</strong><small>{user.id === session?.user?.id ? 'Akun Anda' : user.active ? 'Aktif' : 'Nonaktif'}</small></div>{user.id === session?.user?.id ? <Badge>Administrator</Badge> : <><SearchSelect aria-label={'Peran ' + user.username} value={user.role} onValueChange={(selectedValue) => void update(user, selectedValue, !!user.active)}>{Object.entries(roleNames).map(([key, label]) => <option value={key} key={key}>{label}</option>)}</SearchSelect><Button variant="ghost" size="sm" onClick={() => void update(user, user.role, !user.active)}>{user.active ? 'Nonaktifkan' : 'Aktifkan'}</Button></>}</div>)}</div>}</Card><Card><div className="card-heading"><div><h2>Tambah pengguna</h2><p>Kata sandi disimpan sebagai hash, bukan teks asli.</p></div></div><form className="account-form" onSubmit={event => void add(event)}><label>Nama pengguna<Input value={username} onChange={event => setUsername(event.target.value)} required minLength={3} pattern="[A-Za-z0-9_.-]+" autoComplete="off"/></label><label>Kata sandi<Input type="password" value={password} onChange={event => setPassword(event.target.value)} required minLength={12} autoComplete="new-password" placeholder="Minimal 12 karakter"/></label><label>Peran<SearchSelect aria-label="Peran pengguna baru" value={role} onValueChange={(selectedValue) => setRole(selectedValue)}>{Object.entries(roleNames).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</SearchSelect></label>{error && <div className="form-error" role="alert">{error}</div>}{saved && <p className="success-text" role="status">Pengguna berhasil dibuat.</p>}<Button disabled={pending} type="submit"><Plus size={15}/>{pending ? 'Menyimpan…' : 'Tambah pengguna'}</Button></form></Card></div><Notice>Pembaca agregat tidak dapat membuka direktori atau kuesioner. Analis detail tidak melihat NIK/KK, kontak, koordinat, nominal keuangan dan kondisi kesehatan. Nilai sensitif yang dipetakan hanya dapat dilihat administrator.</Notice></>;
}
