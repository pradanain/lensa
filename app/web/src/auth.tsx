import {createContext,useContext,useEffect,useRef,type ReactNode} from 'react'
import {useQuery,useQueryClient} from '@tanstack/react-query'
import {api,clearPrivateState,setCsrf,type Session} from '@/lib/api'

const Auth=createContext<{session:Session|undefined;loading:boolean;error:Error|null;refresh:()=>Promise<void>;logout:()=>Promise<void>}>({session:undefined,loading:true,error:null,refresh:async()=>{},logout:async()=>{}})
export function AuthProvider({children}:{children:ReactNode}){
  const client=useQueryClient()
  const signoutChannel=useRef<BroadcastChannel|null>(null)
  const query=useQuery({queryKey:['session'],queryFn:async({signal})=>{const result=await api<Session>('/auth/session',undefined,undefined,{signal});setCsrf(result.csrf_token);return result},refetchInterval:30000,refetchOnWindowFocus:'always'})
  useEffect(()=>{
    const channel=new BroadcastChannel('lensa-session')
    signoutChannel.current=channel
    channel.onmessage=event=>{if(event.data==='signed-out'){clearPrivateState();client.clear();window.location.replace('/login')}}
    return()=>{channel.close();signoutChannel.current=null}
  },[client])
  useEffect(()=>{
    if(!query.data?.auth_enabled||!query.data.user)return
    // A document restored by Back must revalidate with the server before showing data.
    const hide=()=>{document.documentElement.style.visibility='hidden'}
    const restore=(event:PageTransitionEvent)=>{if(event.persisted)window.location.reload()}
    window.addEventListener('pagehide',hide)
    window.addEventListener('pageshow',restore)
    return()=>{window.removeEventListener('pagehide',hide);window.removeEventListener('pageshow',restore)}
  },[query.data?.auth_enabled,query.data?.user])
  useEffect(()=>{
    if(!query.data?.user||!query.data.expires_at)return
    // Use server time so an incorrect device clock cannot prolong the UI session.
    const remaining=(query.data.expires_at-(query.data.server_time??Date.now()/1000))*1000-(Date.now()-query.dataUpdatedAt)
    const timer=window.setTimeout(()=>{clearPrivateState();client.clear();window.location.replace('/login')},Math.max(0,remaining))
    return()=>window.clearTimeout(timer)
  },[client,query.data?.user,query.data?.expires_at,query.data?.server_time,query.dataUpdatedAt])
  useEffect(()=>{const clear=()=>{clearPrivateState();client.removeQueries({predicate:query=>query.queryKey[0]!=='session'});client.setQueryData<Session>(['session'],current=>current?{...current,user:null}:undefined);void client.invalidateQueries({queryKey:['session']})};window.addEventListener('portal-session-expired',clear);return()=>window.removeEventListener('portal-session-expired',clear)},[client])
  useEffect(()=>{const gate=()=>{clearPrivateState();client.removeQueries({predicate:query=>query.queryKey[0]!=='session'});client.setQueryData<Session>(['session'],current=>current?{...current,commitment_required:true}:undefined);void client.invalidateQueries({queryKey:['session']})};window.addEventListener('portal-commitment-required',gate);return()=>window.removeEventListener('portal-commitment-required',gate)},[client])
  useEffect(()=>{const gate=()=>{clearPrivateState();client.removeQueries({predicate:query=>query.queryKey[0]!=='session'});client.setQueryData<Session>(['session'],current=>current?{...current,password_change_required:true}:undefined);void client.invalidateQueries({queryKey:['session']})};window.addEventListener('portal-password-change-required',gate);return()=>window.removeEventListener('portal-password-change-required',gate)},[client])
  async function refresh(){clearPrivateState();client.removeQueries({predicate:query=>query.queryKey[0]!=='session'});const result=await api<Session>('/auth/session');setCsrf(result.csrf_token);client.setQueryData(['session'],result)}
  async function logout(){await api('/auth/logout',{});signoutChannel.current?.postMessage('signed-out');clearPrivateState();client.clear();window.location.replace('/login')}
  return <Auth.Provider value={{session:query.data,loading:query.isPending,error:query.error,refresh,logout}}>{children}</Auth.Provider>
}
export function useAuth(){return useContext(Auth)}
