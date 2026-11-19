import {useRef,type ReactNode} from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import {X} from 'lucide-react'
import {Button} from './button'

export function Modal({open,onOpenChange,title,description,children,busy=false}:{open:boolean;onOpenChange:(open:boolean)=>void;title:string;description:string;children:ReactNode;busy?:boolean}){
  const previousFocus=useRef<HTMLElement|null>(null)
  return <Dialog.Root open={open} onOpenChange={value=>{if(!busy)onOpenChange(value)}}><Dialog.Portal>
    <Dialog.Overlay className="admin-modal-overlay"/>
    <Dialog.Content className="admin-modal" onOpenAutoFocus={()=>{previousFocus.current=document.activeElement as HTMLElement}} onCloseAutoFocus={event=>{if(previousFocus.current?.isConnected){event.preventDefault();previousFocus.current.focus()}}} onEscapeKeyDown={event=>{if(busy||document.querySelector('.admin-modal .search-select-popup'))event.preventDefault()}}>
      <div className="admin-modal-heading"><Dialog.Title>{title}</Dialog.Title><Dialog.Description>{description}</Dialog.Description></div>
      {children}
      <Dialog.Close asChild><Button type="button" variant="ghost" size="icon" className="admin-modal-close" aria-label="Tutup dialog" disabled={busy}><X size={18}/></Button></Dialog.Close>
    </Dialog.Content>
  </Dialog.Portal></Dialog.Root>
}
