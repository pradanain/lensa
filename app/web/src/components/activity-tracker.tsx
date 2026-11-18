import {useEffect,useRef,useState} from 'react'
import {useLocation} from '@tanstack/react-router'
import {useAuth} from '@/auth'
import {api} from '@/lib/api'
import './activity-tracker.css'

const screens=new Set(['dashboard','usaha','keluarga','data','questionnaire','pengaturan','monitoring','referensi','kualitas'])
const tabs=new Set(['ringkasan','direktori','anggota','kbli','rincian','komposisi'])
const blocks=new Set(['b0','b1_p','b5','b_ak','blokl','b_ak_lanjutan','b_perumahan','ket_jawaban','cat','ub_i_1','ub_i_2','ub_i_3','ub_ii','ub_iii'])
export function ActivityTracker(){
  const {session}=useAuth()
  const location=useLocation()
  const latest=useRef<Record<string,string>>({screen:'dashboard',tab:'',block:''})
  const previous=useRef('')
  const [failed,setFailed]=useState(false)
  const enabled=!!session?.auth_enabled&&!!session.user
  const screen=session?.password_change_required?'password':session?.commitment_required?'commitment':screens.has(location.pathname.split('/')[1])?location.pathname.split('/')[1]:'dashboard'
  const search=location.search as Record<string,unknown>
  const tab=tabs.has(String(search.tab))?String(search.tab):''
  const block=blocks.has(String(search.block))?String(search.block):''
  useEffect(()=>{
    const parts=location.pathname.split('/')
    const resource:Record<string,string>={}
    if(screen==='questionnaire'&&['dtd','ub'].includes(parts[2])){
      resource.assignment=parts[3]?.slice(0,128)||'';resource.system=parts[2]
      for(const key of ['version','business','member','meter','office'])resource[key]=String(search[key]||'').slice(0,key==='version'?100:80)
    }
    latest.current={screen,tab,block,...resource}
    const key=JSON.stringify([session?.user?.id,location.pathname,location.search,screen])
    if(!enabled||previous.current===key)return
    previous.current=key
    void api('/activity/events',{event:'PAGE_VIEW',...latest.current}).then(()=>setFailed(false)).catch(()=>setFailed(true))
  },[enabled,screen,tab,block,location.pathname,location.search,search,session?.user?.id])
  useEffect(()=>{
    if(!enabled)return
    const click=(event:MouseEvent)=>{
      const target=event.target instanceof Element?event.target.closest('button,a,[role="tab"],[role="combobox"],[role="option"],summary'):null
      if(!target)return
      // Classify controls structurally. Never send textContent, labels, href or input values.
      const role=target.getAttribute('role')
      const control=target.closest('.export-xlsx,.export-dialog')?'export':target.closest('.pagination')?'pagination':role==='tab'?'tab':role==='combobox'||role==='option'?'select':target.closest('.search-row')?'search':target.tagName==='A'?(target.getAttribute('href')?.startsWith('https://')?'map':'navigation'):'button'
      void api('/activity/events',{event:'CONTROL_CLICK',...latest.current,control}).then(()=>setFailed(false)).catch(()=>setFailed(true))
    }
    document.addEventListener('click',click,true)
    return()=>document.removeEventListener('click',click,true)
  },[enabled])
  return enabled&&failed?<div className="activity-alert" role="alert">Pencatatan aktivitas belum tersambung. Periksa koneksi sebelum melanjutkan.</div>:null
}
