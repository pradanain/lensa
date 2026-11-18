import {useState,type FormEvent} from 'react'
import {Check,KeyRound,LogOut} from 'lucide-react'
import {useAuth} from '@/auth'
import {api,setCsrf} from '@/lib/api'
import {passwordRules} from '@/lib/password-policy'
import {Button} from '@/components/ui/button'
import {Input} from '@/components/ui/input'
import censusLogo from '@/assets/logo-se2026.jpg'

export function PasswordChange(){
  const {refresh,logout}=useAuth()
  const [current,setCurrent]=useState('');const [password,setPassword]=useState('');const [confirm,setConfirm]=useState('')
  const [error,setError]=useState('');const [pending,setPending]=useState(false)
  const rules=passwordRules(password)
  async function submit(event:FormEvent){
    event.preventDefault();setError('')
    if(!rules.every(rule=>rule.valid)){setError('Kata sandi baru belum memenuhi semua ketentuan.');return}
    if(password===current){setError('Kata sandi baru harus berbeda dari kata sandi sementara.');return}
    if(password!==confirm){setError('Konfirmasi kata sandi belum sama.');return}
    setPending(true)
    try{
      const result=await api<{csrf_token:string}>('/auth/change-password',{current_password:current,new_password:password,confirm_password:confirm})
      setCsrf(result.csrf_token);setCurrent('');setPassword('');setConfirm('');await refresh()
    }catch(error){setError(error instanceof Error?error.message:'Kata sandi belum berhasil diganti.')}
    finally{setPending(false)}
  }
  return <div className="access-page"><header className="access-header"><img src={censusLogo} alt="Sensus Ekonomi 2026"/><div><strong>LENSA SE2026</strong><small>Eksplorasi dan Analisis SE2026</small></div></header>
    <main className="password-change-stage"><form className="access-form" onSubmit={event=>void submit(event)}>
      <div className="access-form-heading"><span className="access-icon"><KeyRound size={28}/></span><h2>Ganti kata sandi sementara</h2><p>Buat kata sandi pribadi sebelum melanjutkan ke pakta integritas dan data.</p></div>
      <label>Kata sandi sementara<Input type="password" autoComplete="current-password" required maxLength={256} value={current} onChange={event=>setCurrent(event.target.value)}/></label>
      <label>Kata sandi baru<Input type="password" autoComplete="new-password" required minLength={8} maxLength={256} value={password} onChange={event=>setPassword(event.target.value)} aria-describedby="password-rules"/></label>
      <ul className="password-rules" id="password-rules">{rules.map(rule=><li key={rule.label} className={rule.valid?'valid':''}><Check size={14}/>{rule.label}</li>)}</ul>
      <label>Konfirmasi kata sandi baru<Input type="password" autoComplete="new-password" required minLength={8} maxLength={256} value={confirm} onChange={event=>setConfirm(event.target.value)}/></label>
      {error&&<div className="form-error" role="alert">{error}</div>}
      <Button type="submit" className="access-submit" disabled={pending}>{pending?'Menyimpan...':'Simpan kata sandi baru'}</Button>
      <Button type="button" variant="ghost" className="password-change-exit" disabled={pending} onClick={()=>void logout().catch(()=>setError('Belum berhasil keluar. Silakan coba lagi.'))}><LogOut size={16}/>Keluar</Button>
    </form></main>
  </div>
}
