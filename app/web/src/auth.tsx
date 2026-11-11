import {createContext,useContext,useEffect,type ReactNode} from 'react'
import {useQuery,useQueryClient} from '@tanstack/react-query'
import {api,clearPrivateState,setCsrf,type Session} from '@/lib/api'

const Auth=createContext<{session:Session|undefined;loading:boolean;error:Error|null;refresh:()=>Promise<void>;logout:()=>Promise<void>}>({session:undefined,loading:true,error:null,refresh:async()=>{},logout:async()=>{}})
export function AuthProvider({children}:{children:ReactNode}){
  const client=useQueryClient()
  const query=useQuery({queryKey:['session'],queryFn:async()=>{const result=await api<Session>('/auth/session');setCsrf(result.csrf_token);return result},refetchInterval:30000,refetchOnWindowFocus:true})
  useEffect(()=>{const clear=()=>{clearPrivateState();client.removeQueries({predicate:query=>query.queryKey[0]!=='session'});client.setQueryData<Session>(['session'],current=>current?{...current,user:null}:undefined);void client.invalidateQueries({queryKey:['session']})};window.addEventListener('portal-session-expired',clear);return()=>window.removeEventListener('portal-session-expired',clear)},[client])
  async function refresh(){clearPrivateState();client.removeQueries({predicate:query=>query.queryKey[0]!=='session'});const result=await api<Session>('/auth/session');setCsrf(result.csrf_token);client.setQueryData(['session'],result)}
  async function logout(){await api('/auth/logout',{});await refresh()}
  return <Auth.Provider value={{session:query.data,loading:query.isPending,error:query.error,refresh,logout}}>{children}</Auth.Provider>
}
export function useAuth(){return useContext(Auth)}
