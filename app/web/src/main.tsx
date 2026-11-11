import React,{Suspense,lazy} from 'react'
import ReactDOM from 'react-dom/client'
import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import {createRootRoute,createRoute,createRouter,RouterProvider,redirect} from '@tanstack/react-router'
import {AuthProvider} from './auth'
import {Root} from './app'
import {validateSearch} from './lib/api'
const Dashboard=lazy(()=>import('./pages/dashboard').then(m=>({default:m.Dashboard})))
import {Business,DataSE,Families} from './pages/domains'
const Questionnaire=lazy(()=>import('./pages/questionnaire').then(m=>({default:m.Questionnaire})))
import {Quality} from './pages/quality'
import {References,Settings} from './pages/secondary'
import './styles.css'

const rootRoute=createRootRoute({component:Root,validateSearch})
const index=createRoute({getParentRoute:()=>rootRoute,path:'/',beforeLoad:()=>{throw redirect({to:'/usaha'})}})
const routes=[index,
  createRoute({getParentRoute:()=>rootRoute,path:'/dashboard',component:Dashboard}),
  createRoute({getParentRoute:()=>rootRoute,path:'/usaha',component:Business}),
  createRoute({getParentRoute:()=>rootRoute,path:'/keluarga',component:Families}),
  createRoute({getParentRoute:()=>rootRoute,path:'/data/$system',component:DataSE}),
  createRoute({getParentRoute:()=>rootRoute,path:'/questionnaire/$system/$assignmentId',component:Questionnaire}),
  createRoute({getParentRoute:()=>rootRoute,path:'/kualitas',component:Quality}),
  createRoute({getParentRoute:()=>rootRoute,path:'/referensi',component:References}),
  createRoute({getParentRoute:()=>rootRoute,path:'/pengaturan',component:Settings}),
]
export const router=createRouter({routeTree:rootRoute.addChildren(routes),defaultPreload:false,scrollRestoration:true})
declare module '@tanstack/react-router'{interface Register{router:typeof router}}
const queryClient=new QueryClient({defaultOptions:{queries:{retry:false,refetchOnWindowFocus:false,staleTime:300000,gcTime:600000}}})
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><QueryClientProvider client={queryClient}><AuthProvider><Suspense fallback={<div className="route-loading" role="status">Memuat halaman...</div>}><RouterProvider router={router}/></Suspense></AuthProvider></QueryClientProvider></React.StrictMode>)
