import {useState} from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import {Check,ShieldCheck,X} from 'lucide-react'
import {useAuth} from '@/auth'
import {api} from '@/lib/api'
import {Button} from '@/components/ui/button'
import censusLogo from '@/assets/logo-se2026.jpg'

export function Commitment(){
  const {session,refresh,logout}=useAuth()
  const [pending,setPending]=useState(false);const [error,setError]=useState('')
  async function decide(accept:boolean){
    if(pending)return
    setPending(true);setError('')
    try{
      if(accept){await api('/auth/commitment',{version:session?.commitment_version,accepted:true});await refresh()}
      else await logout()
    }catch(error){setError(error instanceof Error?error.message:'Permintaan belum berhasil. Silakan coba kembali.');await refresh().catch(()=>{})}
    finally{setPending(false)}
  }
  return <div className="access-page"><header className="access-header"><img src={censusLogo} alt="Sensus Ekonomi 2026"/><div><strong>LENSA SE2026</strong><small>Eksplorasi dan Analisis SE2026</small></div></header>
    <Dialog.Root open><Dialog.Portal><Dialog.Overlay className="commitment-overlay"/><Dialog.Content className="commitment-dialog" onEscapeKeyDown={event=>{event.preventDefault();void decide(false)}} onPointerDownOutside={event=>event.preventDefault()} onInteractOutside={event=>event.preventDefault()}>
      <Button variant="ghost" size="icon" className="commitment-close" aria-label="Tutup dan keluar dari portal" disabled={pending} onClick={()=>void decide(false)}><X size={22}/></Button>
      <div className="commitment-heading"><span className="commitment-emblem" aria-hidden="true"><ShieldCheck size={24}/></span><Dialog.Title>Pakta integritas</Dialog.Title></div>
      <Dialog.Description className="commitment-intro">Kepercayaan responden ada dalam setiap data yang kita akses.</Dialog.Description>
      <ul className="commitment-points">
        <li>Saya menggunakan data <strong>hanya untuk tugas dan analisis yang berwenang</strong>.</li>
        <li>Saya <strong>menjaga kerahasiaan responden</strong> dan tidak membagikan data, tangkapan layar, hasil unduhan, atau akses akun kepada pihak yang tidak berwenang.</li>
        <li>Saya <strong>bertanggung jawab penuh atas data yang saya akses, gunakan, simpan, dan unduh</strong> melalui LENSA SE2026.</li>
      </ul>
      {error&&<p className="form-error" role="alert">{error}</p>}
      <div className="commitment-actions"><Button variant="outline" disabled={pending} onClick={()=>void decide(false)}>Keluar</Button><Button disabled={pending} onClick={()=>void decide(true)}>{pending?'Memproses...':'Saya memahami dan berkomitmen'}<Check size={18}/></Button></div>
      <p className="commitment-hint">Menutup dialog akan mengeluarkan Anda dari portal.</p>
    </Dialog.Content></Dialog.Portal></Dialog.Root>
  </div>
}
