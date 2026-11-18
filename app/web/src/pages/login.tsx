import {useState,type FormEvent} from 'react'
import {ArrowRight,Coffee,Eye,EyeOff,Heart,LoaderCircle} from 'lucide-react'
import censusLogo from '@/assets/logo-se2026.jpg'
import loginCover from '@/assets/login-cover.webp'
import loginCoverLarge from '@/assets/login-cover@2x.webp'
import {api,setCsrf,type Session} from '@/lib/api'
import {useAuth} from '@/auth'
import {Button} from '@/components/ui/button'
import {Input} from '@/components/ui/input'
import './login.css'

export function Login(){
  const {refresh}=useAuth()
  const [username,setUsername]=useState('');const [password,setPassword]=useState('');const [error,setError]=useState('');const [pending,setPending]=useState(false)
  const [showPassword,setShowPassword]=useState(false)
  async function submit(event:FormEvent){event.preventDefault();if(pending)return;setError('');setPending(true);try{const result=await api<Session>('/auth/login',{username,password});setCsrf(result.csrf_token);setPassword('');await refresh()}catch(error){setError(error instanceof Error?error.message:'Layanan belum dapat dihubungi.')}finally{setPending(false)}}
  return <div className="access-page login-access-page"><header className="access-header"><img src={censusLogo} alt="Sensus Ekonomi 2026"/><div><strong>LENSA SE2026</strong><small>Eksplorasi dan Analisis SE2026</small></div></header>
    <main className="access-layout"><section className="access-story"><h1>Sensus Ekonomi 2026</h1><p><strong>Sensus Ekonomi 2026 (SE2026)</strong> adalah <strong>kegiatan pendataan lengkap seluruh aktivitas usaha dan ekonomi di Indonesia yang diselenggarakan setiap 10 tahun sekali oleh Badan Pusat Statistik (BPS)</strong>.</p><figure className="access-cover"><img src={loginCover} srcSet={`${loginCover} 1200w, ${loginCoverLarge} 2400w`} sizes="(max-width: 760px) calc(100vw - 32px), 650px" width={2400} height={1000} alt="Kolase foto petugas dan kegiatan Sensus Ekonomi 2026" fetchPriority="high"/></figure></section>
      <form className="access-form" onSubmit={event=>void submit(event)} aria-busy={pending}><div className="access-form-heading"><h2>Selamat datang kembali</h2></div>
        <label>Nama pengguna<Input value={username} onChange={event=>setUsername(event.target.value)} autoComplete="username" pattern="[A-Za-z0-9_.@+\-]+" minLength={3} maxLength={128} required disabled={pending} placeholder="Nama pengguna atau email"/></label>
        <div className="login-password-field">
          <label htmlFor="login-password">Kata sandi</label>
          <div className="login-password-input">
            <Input id="login-password" type={showPassword?'text':'password'} value={password} onChange={event=>setPassword(event.target.value)} autoComplete="current-password" minLength={1} maxLength={256} required disabled={pending} placeholder="Masukkan kata sandi" aria-describedby={error?'login-error':undefined}/>
            <button type="button" className="login-password-toggle" aria-label={showPassword?'Sembunyikan kata sandi':'Tampilkan kata sandi'} aria-controls="login-password" aria-pressed={showPassword} disabled={pending} onClick={()=>setShowPassword(!showPassword)}>{showPassword?<EyeOff size={18}/>:<Eye size={18}/>}</button>
          </div>
        </div>
        {error&&<div id="login-error" className="form-error" role="alert">{error}</div>}
        <Button type="submit" className="access-submit" disabled={pending}>{pending?<><LoaderCircle className="login-spinner" size={17}/>Memproses...</>:<>Masuk ke portal<ArrowRight size={17}/></>}</Button>
      </form></main>
    <footer className="login-footer"><p>© {new Date().getFullYear()} BPS Kabupaten Bulungan</p><p className="login-credit">Made with <Heart size={12} aria-label="love" className="footer-heart"/> and <Coffee size={12} aria-label="coffee"/> by <span>Novanni Indi Pradana</span></p></footer>
  </div>
}
