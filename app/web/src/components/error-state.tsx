import {FileSearch,House,RefreshCw,ShieldCheck,Unplug} from 'lucide-react'
import {ApiError} from '@/lib/api'
import {Button} from './ui/button'

export function ErrorState({error,retry,notFound=false,page=false}:{error?:unknown;retry?:()=>void;notFound?:boolean;page?:boolean}){
  const status=notFound?404:error instanceof ApiError?error.status:undefined
  const missing=status===404
  const restricted=status===403
  const Icon=missing?FileSearch:restricted?ShieldCheck:Unplug
  const title=missing?'Halaman atau data tidak ditemukan':restricted?'Akses belum tersedia':'Data belum dapat dimuat'
  const description=missing?'Tautan mungkin sudah berubah atau data yang dicari tidak tersedia. Anda bisa melanjutkan dari halaman Dashboard.':restricted?'Bagian ini belum bisa dibuka. Kembali ke Dashboard atau hubungi pengelola layanan.':error instanceof ApiError?error.message:'Koneksi ke layanan terputus atau halaman belum berhasil dimuat. Tunggu sebentar, lalu coba lagi.'
  return <section className={'error-state'+(page?' error-state-page':'')} role="alert">
    <div className="error-state-art" aria-hidden="true"><span className="error-state-orbit"/><div className="error-state-symbol"><Icon size={36} strokeWidth={1.6}/></div><span className="error-state-dot"/></div>
    <div className="error-state-content"><span className="error-state-label">{status&&status>=400?`LENSA / ${status}`:'LENSA SE2026'}</span>
      {page?<h1>{title}</h1>:<h2>{title}</h2>}<p>{description}</p>
      <div className="error-state-actions">{retry&&!missing&&!restricted&&<Button onClick={retry}><RefreshCw size={16}/>Coba lagi</Button>}<Button asChild variant={missing||restricted?'default':'outline'}><a href="/dashboard"><House size={16}/>Kembali ke Dashboard</a></Button></div>
    </div>
  </section>
}
