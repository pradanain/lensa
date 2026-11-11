import {useEffect,useState} from 'react'
import {Link,Outlet,useLocation} from '@tanstack/react-router'
import {BarChart3,Coffee,Heart,Building2,ChevronRight,Database,Grid2X2,House,LogOut,Menu,X} from 'lucide-react'
import {useAuth} from '@/auth'
import {roleNames} from '@/lib/utils'
import {Button} from '@/components/ui/button'
import {ErrorBox,Loading} from '@/components/shared'
import {Login} from '@/pages/login'
import censusLogo from '@/assets/logo-se2026.jpg'

export function Root(){
  const {session,loading,error,refresh}=useAuth()
  const location=useLocation()
  const [mobile,setMobile]=useState(false)
  useEffect(()=>{setMobile(false)},[location.pathname])
  useEffect(()=>{
    const escape=(event:KeyboardEvent)=>{if(event.key==='Escape')setMobile(false)}
    window.addEventListener('keydown',escape)
    return()=>window.removeEventListener('keydown',escape)
  },[])
  if(loading)return <div className="boot-skeleton"><div className="boot-skeleton-brand"><BarChart3 size={24}/><strong>LENSA SE2026</strong></div><Loading variant="dashboard" label="Memuat LENSA SE2026..."/></div>
  if(error)return <div className="boot-loading"><ErrorBox error={error} retry={()=>void refresh().catch(()=>{})}/></div>
  if(!session?.user)return <Login/>
  const current=location.pathname.split('/')[1]||'dashboard'
  const titles:Record<string,string>={dashboard:'Dashboard',usaha:'Usaha',keluarga:'Keluarga',data:'Raw Data',kualitas:'Kualitas Data',referensi:'Referensi',pengaturan:'Pengaturan',questionnaire:'Kuesioner'}
  return <div className={'app-layout '+(current==='questionnaire'?'reader-page':'')} key={session.user.id+':'+session.user.role}>
    <a href="#main-content" className="skip-link">Langsung ke konten</a>
    <header className="portal-header"><div className="portal-header-inner">
      <Link className="brand" to="/usaha" aria-label="Beranda LENSA SE2026"><img src={censusLogo} alt="Sensus Ekonomi 2026" width="48" height="60"/><span className="brand-title"><strong title="LENSA SE2026"><span className="brand-name-full">LENSA SE2026</span><span className="brand-name-short">LENSA</span></strong><small>Eksplorasi dan Analisis SE2026</small></span></Link>
      <nav id="primary-navigation" className={'primary-navigation '+(mobile?'is-open':'')} aria-label="Menu utama">
        <Link className="nav-item" to="/dashboard"><Grid2X2 size={17}/><span>Dashboard</span></Link>
        <Link className="nav-item" to="/usaha"><Building2 size={17}/><span>Usaha</span></Link>
        <Link className="nav-item" to="/keluarga"><House size={17}/><span>Keluarga</span></Link>
        <Link className={'nav-item '+(['data','questionnaire'].includes(current)?'current':'')} to="/data/$system" params={{system:'dtd'}}><Database size={17}/><span>Raw Data</span></Link>
      </nav>
      <UserMenu/>
      <Button variant="ghost" size="icon" className="mobile-menu" aria-label={mobile?'Tutup menu':'Buka menu'} aria-expanded={mobile} aria-controls="primary-navigation" onClick={()=>setMobile(!mobile)}>{mobile?<X size={22}/>:<Menu size={22}/>}</Button>
    </div></header>
    {mobile&&<button className="navigation-backdrop" aria-label="Tutup navigasi" onClick={()=>setMobile(false)}/>}
    <main id="main-content" className={'content '+(current==='questionnaire'?'content-wide':['usaha','keluarga','data'].includes(current)?'content-domain':'')}>
      <nav className="page-breadcrumb" aria-label="Jejak navigasi"><Link to="/dashboard">Beranda</Link><ChevronRight size={13}/><span aria-current="page">{titles[current]||'Dashboard'}</span></nav>
      {session.business_focus_enabled&&['dashboard','keluarga','data'].includes(current)?<section className="module-unavailable" role="alert"><span>403</span><h1>Halaman belum tersedia</h1><p>Halaman ini sedang disiapkan.</p><Link to="/usaha" className="button button-default">Buka Usaha</Link></section>:<Outlet/>}
    </main>
    <footer className="app-footer"><p>Made with <Heart size={14} aria-label="love" className="footer-heart"/> and <Coffee size={14} aria-label="coffee"/> by <span>Novanni Indi Pradana</span></p></footer>
  </div>
}

function UserMenu(){
  const {session,logout}=useAuth()
  const [error,setError]=useState(false)
  if(!session?.auth_enabled)return null
  return <div className="user-menu"><div className="user-label"><strong>{session.user?.username}</strong><small>{roleNames[session.user?.role||'']}</small></div><Button variant="ghost" size="icon" aria-label="Keluar dari portal" onClick={()=>void logout().catch(()=>setError(true))}><LogOut size={17}/></Button>{error&&<span role="alert">Belum berhasil keluar.</span>}</div>
}
