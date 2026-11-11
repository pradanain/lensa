import {Children,Fragment,isValidElement,useEffect,useId,useLayoutEffect,useMemo,useRef,useState,type KeyboardEvent,type ReactNode} from 'react'
import {createPortal} from 'react-dom'
import {Check,ChevronDown,Search} from 'lucide-react'

type Choice={value:string;label:string;disabled:boolean}
type OptionProps={children?:ReactNode;value?:string|number;disabled?:boolean}
type Props={searchable?:boolean;value?:string|number;onValueChange:(value:string)=>void;children:ReactNode;disabled?:boolean;className?:string;id?:string;name?:string;'aria-label':string}

function text(node:ReactNode):string {
  return Children.toArray(node).map(child=>isValidElement<OptionProps>(child)?text(child.props.children):String(child)).join('')
}
function choices(children:ReactNode):Choice[] {
  return Children.toArray(children).flatMap(child=>{
    if(!isValidElement<OptionProps>(child))return []
    if(child.type===Fragment)return choices(child.props.children)
    return [{value:String(child.props.value??text(child.props.children)),label:text(child.props.children),disabled:!!child.props.disabled}]
  })
}

export function SearchSelect({value='',onValueChange,children,disabled=false,searchable=true,className='',id,name,'aria-label':label}:Props){
  const options=useMemo(()=>choices(children),[children])
  const selected=options.find(option=>option.value===String(value))
  const [open,setOpen]=useState(false)
  const [query,setQuery]=useState('')
  const [active,setActive]=useState(0)
  const [position,setPosition]=useState({left:0,top:0,width:240,maxHeight:320})
  const uid=useId();const listId=uid+'-list'
  const trigger=useRef<HTMLButtonElement>(null)
  const popup=useRef<HTMLDivElement>(null)
  const search=useRef<HTMLInputElement>(null)
  const list=useRef<HTMLDivElement>(null)
  const filtered=options.filter(option=>query.toLocaleLowerCase().trim().split(/\s+/).every(term=>option.label.toLocaleLowerCase().includes(term)||option.value.toLocaleLowerCase().includes(term)))
  const enabled=filtered.map((option,index)=>option.disabled?-1:index).filter(index=>index>=0)

  function close(restoreFocus=false){setOpen(false);if(restoreFocus)trigger.current?.focus({preventScroll:true})}
  function choose(option:Choice){if(option.disabled)return;onValueChange(option.value);close(true)}
  function show(){
    if(disabled)return
    setQuery('');setActive(Math.max(0,options.findIndex(option=>option.value===String(value))));setOpen(true)
  }
  useLayoutEffect(()=>{
    if(!open)return
    const measure=()=>{
      const rect=trigger.current?.getBoundingClientRect();if(!rect)return
      const viewport=window.visualViewport
      const viewportTop=viewport?.offsetTop||0;const viewportLeft=viewport?.offsetLeft||0
      const viewportHeight=viewport?.height||window.innerHeight;const viewportWidth=viewport?.width||window.innerWidth
      const below=viewportTop+viewportHeight-rect.bottom-12;const above=rect.top-viewportTop-12
      const upwards=below<220&&above>below
      const maxHeight=Math.min(320,Math.max(70,upwards?above:below))
      const height=Math.min(maxHeight,popup.current?.getBoundingClientRect().height||maxHeight)
      const width=Math.min(Math.max(rect.width,searchable?240:76),viewportWidth-20)
      const next={left:Math.max(viewportLeft+10,Math.min(rect.left,viewportLeft+viewportWidth-width-10)),top:upwards?Math.max(viewportTop+10,rect.top-height-6):rect.bottom+6,width,maxHeight}
      setPosition(previous=>Math.abs(previous.left-next.left)<.5&&Math.abs(previous.top-next.top)<.5&&Math.abs(previous.width-next.width)<.5&&Math.abs(previous.maxHeight-next.maxHeight)<.5?previous:next)
    }
    measure();(searchable?search.current:list.current)?.focus({preventScroll:true})
    window.addEventListener('resize',measure);window.addEventListener('scroll',measure,true)
    window.visualViewport?.addEventListener('resize',measure);window.visualViewport?.addEventListener('scroll',measure)
    const resize=typeof ResizeObserver==='undefined'?null:new ResizeObserver(measure)
    if(popup.current)resize?.observe(popup.current)
    return()=>{window.removeEventListener('resize',measure);window.removeEventListener('scroll',measure,true);window.visualViewport?.removeEventListener('resize',measure);window.visualViewport?.removeEventListener('scroll',measure);resize?.disconnect()}
  },[open,searchable])
  useEffect(()=>{
    if(!open)return
    const outside=(event:PointerEvent)=>{if(!trigger.current?.contains(event.target as Node)&&!popup.current?.contains(event.target as Node))close()}
    document.addEventListener('pointerdown',outside,true)
    return()=>document.removeEventListener('pointerdown',outside,true)
  },[open])
  useLayoutEffect(()=>{
    const container=list.current;const option=container?.children[active] as HTMLElement|undefined
    if(!container||!option)return
    if(option.offsetTop<container.scrollTop)container.scrollTop=option.offsetTop
    else if(option.offsetTop+option.offsetHeight>container.scrollTop+container.clientHeight)container.scrollTop=option.offsetTop+option.offsetHeight-container.clientHeight
  },[active,query,open])
  function keyboard(event:KeyboardEvent){
    if(event.key==='Escape'){event.preventDefault();event.stopPropagation();close(true)}
    else if(event.key==='Tab')close()
    else if(event.key==='ArrowDown'||event.key==='ArrowUp'){
      event.preventDefault();const current=enabled.indexOf(active);const step=event.key==='ArrowDown'?1:-1
      setActive(enabled[(current+step+enabled.length)%enabled.length]??0)
    }else if(event.key==='Home'||event.key==='End'){event.preventDefault();setActive(event.key==='Home'?enabled[0]??0:enabled[enabled.length-1]??0)}
    else if(event.key==='Enter'){event.preventDefault();if(filtered[active])choose(filtered[active])}
  }
  return <span className={'search-select '+className}>
    {name&&<input type="hidden" name={name} value={value}/>}
    <button id={id} type="button" ref={trigger} role="combobox" aria-label={label} aria-expanded={open} aria-controls={listId} aria-haspopup="listbox" data-value={String(value)} className="search-select-trigger" disabled={disabled} title={selected?.label} onClick={()=>open?close():show()} onKeyDown={event=>{if(!open&&['ArrowDown','ArrowUp'].includes(event.key)){event.preventDefault();show()}}}><span>{selected?.label||String(value)||'Pilih...'}</span><ChevronDown size={16}/></button>
    {open&&createPortal(<div ref={popup} className="search-select-popup" style={{left:position.left,top:position.top,width:position.width,maxHeight:position.maxHeight}} onKeyDown={keyboard}>
      {searchable&&<div className="search-select-search"><Search size={16}/><input ref={search} aria-label={'Cari pilihan '+label} aria-controls={listId} aria-activedescendant={filtered[active]?uid+'-option-'+active:undefined} autoComplete="off" spellCheck={false} placeholder={'Cari '+label.toLocaleLowerCase('id-ID')} value={query} onChange={event=>{setQuery(event.target.value);setActive(0)}}/></div>}
      <div ref={list} id={listId} role="listbox" tabIndex={searchable?undefined:-1} aria-activedescendant={!searchable&&filtered[active]?uid+'-option-'+active:undefined} aria-label={'Pilihan '+label} className="search-select-options">{filtered.map((option,index)=><button type="button" tabIndex={-1} role="option" id={uid+'-option-'+index} key={option.value} data-value={option.value} aria-selected={option.value===String(value)} aria-disabled={option.disabled} className={index===active?'is-active':''} onPointerMove={()=>setActive(index)} onClick={()=>choose(option)}><span>{option.label}</span>{option.value===String(value)&&<Check size={15}/>}</button>)}{filtered.length===0&&<div className="search-select-empty" role="status">Tidak ada pilihan yang sesuai.</div>}</div>
      {searchable&&<div className="search-select-count">{filtered.length} pilihan</div>}
    </div>,document.body)}
  </span>
}
