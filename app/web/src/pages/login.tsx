import {useState,type FormEvent} from 'react'
import {ArrowRight,Coffee,Heart} from 'lucide-react'
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
  return <div className="access-page login-access-page"><header className="access-header"><img src={censusLogo} alt="Sensus Ekonomi 2026"/><div><strong>LENSA SE2026</strong><small>Eksplorasi dan Analisis SE2026</small></div></header>
    <main className="access-layout"><section className="access-story"><h1>Sensus Ekonomi 2026</h1><p><strong>Sensus Ekonomi 2026 (SE2026)</strong> adalah <strong>kegiatan pendataan lengkap seluruh aktivitas usaha dan ekonomi di Indonesia yang diselenggarakan setiap 10 tahun sekali oleh Badan Pusat Statistik (BPS)</strong>.</p><figure className="access-cover"><img src={loginCover} srcSet={`${loginCover} 1200w, ${loginCoverLarge} 2400w`} sizes="(max-width: 760px) calc(100vw - 48px), 590px" width={2400} height={1000} alt="Kolase foto petugas dan kegiatan Sensus Ekonomi 2026" fetchPriority="high"/></figure></section>
      <form className="access-form" onSubmit={event=>void submit(event)}><div className="access-form-heading"><h2>Selamat datang kembali</h2></div>
        <label>Nama pengguna<Input value={username} onChange={event=>setUsername(event.target.value)} autoComplete="username" pattern="[A-Za-z0-9_.@+\-]+" minLength={3} maxLength={128} required placeholder="Nama pengguna atau email"/></label>
        <label>Kata sandi<Input type="password" value={password} onChange={event=>setPassword(event.target.value)} autoComplete="current-password" minLength={1} maxLength={256} required placeholder="Masukkan kata sandi"/></label>
        {error&&<div className="form-error" role="alert">{error}</div>}
        <Button type="submit" className="access-submit" disabled={pending}>{pending?'Memproses...':'Masuk ke portal'}<ArrowRight size={17}/></Button>
      </form></main>
    <footer className="login-footer"><p>© {new Date().getFullYear()} BPS Kabupaten Bulungan</p><p className="login-credit">Made with <Heart size={12} aria-label="love" className="footer-heart"/> and <Coffee size={12} aria-label="coffee"/> by <span>Novanni Indi Pradana</span></p></footer>
  </div>
}
