import {useState,type FormEvent} from 'react'
import {ArrowRight,ShieldCheck} from 'lucide-react'
import censusLogo from '@/assets/logo-se2026.jpg'
import loginCover from '@/assets/login-cover.webp'
import loginCoverLarge from '@/assets/login-cover@2x.webp'
import {api,setCsrf,type Session} from '@/lib/api'
import {useAuth} from '@/auth'
import {Button} from '@/components/ui/button'
import {Input} from '@/components/ui/input'

export function Login(){
  const {refresh}=useAuth()
  const [username,setUsername]=useState('');const [password,setPassword]=useState('');const [error,setError]=useState('');const [pending,setPending]=useState(false)
  async function submit(event:FormEvent){event.preventDefault();setError('');setPending(true);try{const result=await api<Session>('/auth/login',{username,password});setCsrf(result.csrf_token);setPassword('');await refresh()}catch(error){setError(error instanceof Error?error.message:'Layanan belum dapat dihubungi.')}finally{setPending(false)}}
  return <div className="access-page"><header className="access-header"><img src={censusLogo} alt="Sensus Ekonomi 2026"/><div><strong>LENSA SE2026</strong><small>Eksplorasi dan Analisis SE2026</small></div></header>
    <main className="access-layout"><section className="access-story"><h1>LENSA SE2026</h1><p>Telusuri usaha, keluarga, dan gambaran ekonomi Kabupaten Bulungan dalam satu portal.</p><figure className="access-cover"><img src={loginCover} srcSet={`${loginCover} 1200w, ${loginCoverLarge} 2400w`} sizes="(max-width: 760px) calc(100vw - 48px), 590px" width={2400} height={1000} alt="Terima kasih, pejuang data Sensus Ekonomi 2026 — kolase foto petugas dan kegiatan pendataan" fetchPriority="high"/><figcaption>Pejuang Data Sensus Ekonomi 2026 · Kabupaten Bulungan</figcaption></figure><div className="access-reminder"><ShieldCheck size={22}/><div><strong>Jaga kepercayaan responden</strong><p>Gunakan akun Anda sendiri. Setelah masuk, baca dan setujui pakta integritas sebelum membuka data.</p></div></div></section>
      <form className="access-form" onSubmit={event=>void submit(event)}><div className="access-form-heading"><h2>Selamat datang kembali</h2><p>Masuk dengan akun yang diberikan administrator.</p></div>
        <label>Nama pengguna<Input value={username} onChange={event=>setUsername(event.target.value)} autoComplete="username" pattern="[A-Za-z0-9_.@+\-]+" minLength={3} maxLength={128} required placeholder="Nama pengguna atau email"/></label>
        <label>Kata sandi<Input type="password" value={password} onChange={event=>setPassword(event.target.value)} autoComplete="current-password" minLength={1} maxLength={256} required placeholder="Masukkan kata sandi"/></label>
        {error&&<div className="form-error" role="alert">{error}</div>}
        <Button type="submit" className="access-submit" disabled={pending}>{pending?'Memproses...':'Masuk ke portal'}<ArrowRight size={17}/></Button><p className="access-form-note">Akun hanya dibuat oleh administrator.</p>
      </form></main>
  </div>
}
