import {useState,type FormEvent} from 'react'
import {ArrowRight,ChartNoAxesCombined,ShieldCheck} from 'lucide-react'
import censusLogo from '@/assets/logo-se2026.jpg'
import {api,setCsrf,type Session} from '@/lib/api'
import {useAuth} from '@/auth'
import {Button} from '@/components/ui/button'
import {Input} from '@/components/ui/input'

export function Login(){
  const {session,refresh}=useAuth();const setup=!!session?.setup_required
  const [username,setUsername]=useState('');const [password,setPassword]=useState('');const [confirm,setConfirm]=useState('');const [error,setError]=useState('');const [pending,setPending]=useState(false)
  async function submit(event:FormEvent){event.preventDefault();setError('');if(setup&&password!==confirm){setError('Konfirmasi kata sandi belum sama.');return}setPending(true);try{if(setup)await api('/auth/setup',{username,password});const result=await api<Session>('/auth/login',{username,password});setCsrf(result.csrf_token);setPassword('');setConfirm('');await refresh()}catch(error){setError(error instanceof Error?error.message:'Layanan belum dapat dihubungi.')}finally{setPending(false)}}
  return <div className="access-page"><header className="access-header"><img src={censusLogo} alt="Sensus Ekonomi 2026"/><div><strong>LENSA SE2026</strong><small>Eksplorasi dan Analisis SE2026</small></div></header>
    <main className="access-layout"><section className="access-story"><span className="access-icon"><ChartNoAxesCombined size={32}/></span><h1>LENSA SE2026</h1><p>Eksplorasi dan Analisis SE2026</p><p>Telusuri usaha, keluarga, dan gambaran ekonomi Kabupaten Bulungan dalam satu portal.</p><div className="access-reminder"><ShieldCheck size={22}/><div><strong>Jaga kepercayaan responden</strong><p>Gunakan akun Anda sendiri. Setelah masuk, baca dan setujui pakta integritas sebelum membuka data.</p></div></div></section>
      <form className="access-form" onSubmit={event=>void submit(event)}><div className="access-form-heading"><h2>{setup?'Siapkan akses pertama':'Selamat datang kembali'}</h2><p>{setup?'Buat akun administrator untuk portal ini.':'Masuk dengan akun yang diberikan administrator.'}</p></div>
        <label>Nama pengguna<Input value={username} onChange={event=>setUsername(event.target.value)} autoComplete="username" pattern="[A-Za-z0-9_.@+\-]+" minLength={3} maxLength={128} required placeholder="Nama pengguna atau email"/></label>
        <label>Kata sandi<Input type="password" value={password} onChange={event=>setPassword(event.target.value)} autoComplete={setup?'new-password':'current-password'} minLength={setup?12:1} maxLength={256} required placeholder={setup?'Minimal 12 karakter':'Masukkan kata sandi'}/></label>
        {setup&&<label>Konfirmasi kata sandi<Input type="password" value={confirm} onChange={event=>setConfirm(event.target.value)} autoComplete="new-password" required minLength={12} maxLength={256}/></label>}
        {error&&<div className="form-error" role="alert">{error}</div>}
        <Button type="submit" className="access-submit" disabled={pending}>{pending?'Memproses...':setup?'Buat akun dan masuk':'Masuk ke portal'}<ArrowRight size={17}/></Button><p className="access-form-note">Akses mengikuti hak akun Anda.</p>
      </form></main>
  </div>
}
