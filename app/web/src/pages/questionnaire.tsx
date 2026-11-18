import {createContext, useContext, useEffect, useLayoutEffect, useRef, useState, type ReactNode} from 'react'
import {useNavigate, useParams, useSearch} from '@tanstack/react-router'
import {useQuery, useQueryClient} from '@tanstack/react-query'
import {ArrowLeft, ArrowUp, BookOpen, ChevronDown, ChevronLeft, ChevronRight, ChevronUp, MapPin, Maximize, Minimize, PanelLeftClose, PanelLeftOpen} from 'lucide-react'
import {api, detailNavigation, type FormResult, type Question, type QuestionnaireLocation, type SearchState} from '@/lib/api'
import {MASKED_VALUE} from '@/lib/utils'
import {answerText, questionNumber} from '@/lib/questionnaire-display'
import {useAuth} from '@/auth'
import {SearchSelect} from '@/components/ui/search-select'
import {Button} from '@/components/ui/button'
import {ErrorBox, Loading, Notice, Restricted} from '@/components/shared'
import {TurnoverValue} from '@/components/turnover'

export function Questionnaire() {
  const {session} = useAuth()
  const {system,assignmentId}=useParams({strict:false})
  return session?.user?.can_detail ? <QuestionnaireContent key={JSON.stringify([system,assignmentId,session.user.id,session.user.role])}/> : <Restricted/>
}

const blockDescriptions: Record<string, {badge?: string; description: string}> = {
  b0: {description: 'Pengantar pendataan'},
  b1_p: {description: 'Identitas wilayah'},
  b5: {badge: 'P', description: 'Keterangan keluarga dan bangunan'},
  b_ak: {badge: 'I', description: 'Keterangan anggota keluarga'},
  blokl: {badge: 'II', description: 'Keterangan usaha/perusahaan'},
  b_ak_lanjutan: {badge: 'III', description: 'Pendidikan, pekerjaan dan pendapatan anggota keluarga'},
  b_perumahan: {badge: 'IV', description: 'Tempat tinggal, fasilitas dan aset keluarga'},
  ket_jawaban: {description: 'Keterangan pemberi jawaban'},
  cat: {description: 'Catatan pendataan'},
}

const DisclosureContext = createContext<{scope:string;opened:Record<string,boolean>;setOpen:(key:string,open:boolean)=>void}|null>(null)

function QuestionnaireContent() {
  const {session}=useAuth()
  const client=useQueryClient()
  const {system, assignmentId} = useParams({strict: false}) as {system: string; assignmentId: string}
  const search = useSearch({strict: false}) as SearchState
  const navigate = useNavigate()
  const [expanded, setExpanded] = useState(false)
  const [topClosed,setTopClosed]=useState(false)
  const [sideClosed,setSideClosed]=useState(false)
  const [openedGroups, setOpenedGroups] = useState<Record<string,boolean>>({})
  const stage = useRef<HTMLDivElement>(null)
  const scrollPositions = useRef(new Map<string, number>())
  const pendingQuestion=useRef<string|null>(null)
  const lifetime=useRef({generation:0})
  const block = search.block || (system === 'ub' ? 'ub_i_1' : 'b5')
  const params = new URLSearchParams()
  if (search.version) params.set('version', search.version)
  if (search.business || (block === 'blokl' && search.index1)) params.set('business', search.business || search.index1 || '')
  if (search.member || (['b_ak', 'b_ak_lanjutan'].includes(block) && search.index1)) params.set('member', search.member || search.index1 || '')
  if (search.meter) params.set('meter', search.meter)
  if (search.office) params.set('office', search.office)
  const cacheScope=['questionnaire',system,assignmentId,session?.user?.id,session?.user?.role,search.version||'']
  const reusable=client.getQueryCache().findAll({queryKey:cacheScope}).filter(item=>item.state.status==='success'&&item.state.data).find(item=>{
    const data=item.state.data as FormResult
    const previousParams=new URLSearchParams(String(item.queryKey.at(-1)))
    return (['business','member','meter','office'] as const).every(name=>{
      const kind={business:'businesses',member:'members',meter:'meters',office:'offices'}[name]
      return params.has(name)?params.get(name)===data.selections[kind]:!previousParams.has(name)
    })
  })
  const query = useQuery({
    queryKey: [...cacheScope, params.toString()],
    queryFn: ({signal}) => api<FormResult>('/questionnaires/' + encodeURIComponent(system) + '/' + encodeURIComponent(assignmentId) + '?' + params,undefined,undefined,{signal}),
    gcTime: 300000,
    staleTime:300000,
    initialData:reusable?.state.data as FormResult|undefined,
    initialDataUpdatedAt:reusable?.state.dataUpdatedAt,
    placeholderData:(previous,previousQuery)=>cacheScope.every((value,index)=>previousQuery?.queryKey[index]===value)?previous:undefined,
  })
  useEffect(()=>{
    const tracker=lifetime.current
    const generation=++tracker.generation
    return()=>queueMicrotask(()=>{if(tracker.generation===generation)client.removeQueries({queryKey:['questionnaire',system,assignmentId]})})
  },[client,system,assignmentId])
  const fallback=query.error?client.getQueryCache().findAll({queryKey:cacheScope}).filter(item=>item.state.status==='success'&&item.state.data).sort((a,b)=>b.state.dataUpdatedAt-a.state.dataUpdatedAt)[0]?.state.data as FormResult|undefined:undefined
  const form = query.data||fallback
  const changing=query.isPlaceholderData
  const sections = form?.sections.filter(item => item.applicability !== 'NOT_APPLICABLE' && !['anomali_section', 'anomali_keluarga'].includes(item.section_id)) || []
  const section = sections.find(item => item.section_id === block) || sections.find(item => item.section_id === 'blokl') || sections[0]
  const activeBlock = section?.section_id || block
  const sectionIndex = sections.findIndex(item => item.section_id === activeBlock)
  const scrollKey = JSON.stringify([system, assignmentId, activeBlock, form?.version, search.business||form?.selections.businesses,search.member||form?.selections.members,search.meter||form?.selections.meters,search.office||form?.selections.offices])
  useLayoutEffect(() => {
    if(changing||query.error)return
    if (stage.current) stage.current.scrollTop = scrollPositions.current.get(scrollKey) || 0
    if(pendingQuestion.current){
      const id=pendingQuestion.current
      const frame=requestAnimationFrame(()=>{if(revealQuestion(stage.current,id,setOpenedGroups))pendingQuestion.current=null})
      return()=>cancelAnimationFrame(frame)
    }
  }, [scrollKey, form,changing,query.error])

  function select(values: Partial<SearchState>) {
    void navigate({to: '.', search: {
      ...search, index1: undefined,
      business:search.business||(block==='blokl'?search.index1:undefined),
      member:search.member||(['b_ak','b_ak_lanjutan'].includes(block)?search.index1:undefined),
      ...values,
    }, resetScroll: false})
  }
  function back() {
    const context = detailNavigation
    if (!context) {
      void navigate({to: '/usaha', search: {tab: 'direktori', source: system === 'ub' ? 'ub' : 'dtd'}})
    } else if (context.from.startsWith('/data/')) {
      void navigate({to: '/data/$system', params: {system: context.from.endsWith('ub') ? 'ub' : 'dtd'}, search: context.search})
    } else {
      void navigate({to: context.from === '/keluarga' ? '/keluarga' : '/usaha', search: context.search})
    }
  }
  if (query.isPending) return <Loading variant="form" label="Memuat formulir..."/>
  if (query.error&&!form) return <><Button variant="ghost" onClick={back}><ArrowLeft size={16}/>Kembali ke daftar</Button><ErrorBox error={query.error} retry={() => void query.refetch()}/></>
  if (!form || !section) return null

  const recordKind = activeBlock === 'blokl' ? 'businesses' : ['b_ak', 'b_ak_lanjutan'].includes(activeBlock) ? 'members' : activeBlock === 'b_perumahan' && form.rosters.meters?.length ? 'meters' : undefined
  const records = recordKind ? form.rosters[recordKind] || [] : []
  const requestedIndex=recordKind==='businesses'?search.business||search.index1:recordKind==='members'?search.member||search.index1:search.meter
  const selectedRecord = recordKind ? records.find(item => item.index === (requestedIndex||form.selections[recordKind])) : undefined
  const recordLabel = recordKind === 'businesses' ? 'usaha' : recordKind === 'members' ? 'anggota' : 'meteran'
  const chooseRecord = (value: string) => select({[recordKind === 'businesses' ? 'business' : recordKind === 'members' ? 'member' : 'meter']: value,...(recordKind==='businesses'?{office:undefined}:{})})
  // Only proven family fields precede the member card; unmapped member questions stay in source order.
  const rootFields = section.questions.filter(field => activeBlock === 'b_ak_lanjutan' ? field.source_object === 'mart_keluarga' : recordKind === 'meters' ? field.roster !== 'meters' : false)
  const recordFields = section.questions.filter(field => !rootFields.includes(field))
  const description = activeBlock === 'b5' && form.assignment_context?.kind === 'BKU'
    ? {badge: 'P', description: 'Keterangan bangunan dan usaha'} : blockDescriptions[activeBlock]
  const offices = activeBlock === 'blokl' ? form.rosters.offices || [] : []
  const searchableFields=sections.flatMap(item=>{
    const noMembers=!form.rosters.members?.length
    const fields=item.section_id==='blokl'&&!form.rosters.businesses?.length||item.section_id==='b_ak'&&noMembers?[]:item.section_id==='b_ak_lanjutan'&&noMembers?item.questions.filter(field=>field.source_object==='mart_keluarga'):item.questions
    return fields.filter(field=>field.applicability!=='NOT_APPLICABLE'&&field.display_state!=='HIDDEN'&&!presentationOnlyQuestions.has(field.question_id)&&(!field.roster||form.rosters[field.roster]?.length)).map(field=>({section:item.section_id,title:item.title,field}))
  })
  function jump(value:string){
    if(!value.startsWith('q|')){pendingQuestion.current=null;select({block:value});return}
    const [,target,id]=value.split('|')
    if(target===activeBlock)revealQuestion(stage.current,id,setOpenedGroups)
    else{pendingQuestion.current=id;select({block:target})}
  }

  return <div className={'questionnaire-page form-reader ' + (expanded ? 'is-expanded ' : '')+(sideClosed?'sidebar-closed ':'')+(topClosed?'top-closed':'')} onKeyDown={event => {
    if (event.key === 'Escape' && !event.defaultPrevented) setExpanded(false)
  }}>
    <h1 className="sr-only">Kuesioner {system === 'ub' ? 'Usaha Besar' : 'SE2026'}</h1>
    <aside className="form-reader-sidebar" aria-label="Blok kuesioner" hidden={sideClosed}>
      <Button className="reader-back" variant="ghost" onClick={back}><ArrowLeft size={17}/>Kembali ke daftar</Button>
      <div className="block-navigation"><div className="block-navigation-title">Blok pada form SE2026</div>{sections.map(item => <button key={item.section_id} aria-current={item.section_id === activeBlock ? 'location' : undefined} className={item.section_id === activeBlock ? 'active' : ''} onClick={() => select({block: item.section_id})}>
        <span className="block-symbol">{blockDescriptions[item.section_id]?.badge || <BookOpen size={16}/>}</span><span>{item.title}</span>
      </button>)}</div>
      <details className="reader-source-details" key={assignmentId}><summary>Informasi sumber</summary>
        <div className="reader-source-body">
          <p>{[form.assignment.desa_kelurahan, form.assignment.kecamatan].filter(Boolean).join(' / ')}</p>
          <p>Assignment ID <code>{assignmentId}</code></p>
          {form.assignment_context && <p>Jenis assignment: {{KELUARGA:'Keluarga',BKU:'Bangunan khusus usaha (BKU)',KELUARGA_BKU:'Keluarga dan BKU',UNKNOWN:'Belum dapat dipastikan pada versi ini',UB:'Usaha Besar'}[form.assignment_context.kind]}</p>}
          {system === 'dtd' && <label>Versi kuesioner<SearchSelect aria-label="Versi kuesioner" value={form.version || ''} onValueChange={version => select({version, business: undefined, member: undefined, meter: undefined, office: undefined})}>
            {form.available_versions.map(version => <option value={version} key={version}>{version}</option>)}
            {!form.available_versions.length && <option value="">Tidak ada versi rincian</option>}
          </SearchSelect></label>}
          {form.assignment.status_assignment && <p>Status pendataan: {form.assignment.status_assignment}</p>}
          <p>{form.warning}</p>
          {system === 'ub' && <p>Modul terhubung berdasarkan assignment ID. Kesamaan versi historis belum diverifikasi.</p>}
        </div>
      </details>
    </aside>
    <section className="form-reader-main" aria-label="Pertanyaan dan jawaban">
      <div className="form-viewer-toolbar">
        <Button variant="outline" className="reader-panel-toggle" disabled={expanded} title={sideClosed?'Tampilkan sidebar':'Sembunyikan sidebar'} aria-label={sideClosed?'Tampilkan sidebar':'Sembunyikan sidebar'} aria-expanded={!sideClosed} onClick={()=>setSideClosed(!sideClosed)}>{sideClosed?<PanelLeftOpen size={17}/>:<PanelLeftClose size={17}/>}</Button>
        {topClosed?<div className="reader-compact-context"><strong>{section.title}</strong>{selectedRecord&&<span>{selectedRecord.label}</span>}</div>:<label className="reader-unified-search"><span className="sr-only">Cari bagian atau pertanyaan</span><SearchSelect aria-label="Cari bagian atau pertanyaan" searchPlaceholder="Cari bagian, nomor, atau uraian..." value={activeBlock} disabled={changing||!!query.error} onValueChange={jump}>
          {sections.map(item=><option key={item.section_id} value={item.section_id}>{item.title}</option>)}
          {searchableFields.map(item=><option key={item.field.question_id} value={'q|'+item.section+'|'+item.field.question_id}>{item.field.question_text} · {item.title}</option>)}
        </SearchSelect></label>}
        <span className="viewer-position" role="status">{sectionIndex + 1} / {sections.length} bagian</span>
        <Button variant="outline" className="reader-panel-toggle" title={topClosed?'Tampilkan panel atas':'Sembunyikan panel atas'} aria-label={topClosed?'Tampilkan panel atas':'Sembunyikan panel atas'} aria-expanded={!topClosed} onClick={()=>setTopClosed(!topClosed)}>{topClosed?<ChevronDown size={17}/>:<ChevronUp size={17}/>}</Button>
        <Button variant="outline" className="reader-focus-toggle" aria-pressed={expanded} aria-label={expanded ? 'Kembalikan ukuran area baca' : 'Perbesar area baca'} onClick={() => setExpanded(!expanded)}>{expanded ? <Minimize size={16}/> : <Maximize size={16}/>}<span>{expanded ? 'Kembalikan' : 'Perbesar'}</span></Button>
      </div>
      <progress className="form-viewer-progress" max={sections.length} value={sectionIndex + 1} aria-label="Posisi bagian" hidden={topClosed}/>
      <div className="card form-reader-panel">
        <div className="question-section-head" hidden={topClosed}><span className="block-symbol">{description?.badge || <BookOpen size={18}/>}</span><div className="reader-section-title"><h2>{section.title}</h2>{description && <p>{description.description}{records.length ? ' · ' + records.length + ' ' + (recordKind === 'members' ? 'ART' : recordLabel) : ''}</p>}</div>{selectedRecord&&<h3 className="form-record-name">{selectedRecord.label}</h3>}</div>
        {records.length>0&&<div className="form-roster-controls" hidden={topClosed}>
          <div className="form-roster-picker" role="group" aria-label={'Daftar ' + recordLabel}>
            {records.map(item=><button className={'form-roster-choice '+(selectedRecord?.index===item.index?'selected':'')} key={item.index} aria-pressed={selectedRecord?.index===item.index} onClick={()=>chooseRecord(item.index)}>{item.index} · {item.label}</button>)}
          </div>
          <label className="form-roster-mobile">Pilih {recordLabel}<SearchSelect aria-label={'Roster '+recordLabel} value={selectedRecord?.index||''} onValueChange={chooseRecord}>{records.map(item=><option key={item.index} value={item.index}>{item.index} · {item.label}</option>)}</SearchSelect></label>
          {!changing&&offices.length>0&&<label className="form-office-picker">Kantor/unit<SearchSelect aria-label="Roster kantor" value={search.office||form.selections.offices||''} onValueChange={office=>select({office})}>{offices.map(item=><option key={item.index} value={item.index}>{item.index} · {item.label}</option>)}</SearchSelect></label>}
        </div>}
        <div className="form-stage" ref={stage} tabIndex={0} aria-label={section.title} aria-busy={changing} onScroll={event => {if(!changing&&!query.error)scrollPositions.current.set(scrollKey,event.currentTarget.scrollTop)}}>
        {query.error?<ErrorBox error={query.error} retry={()=>void query.refetch()}/>:changing?<p className="reader-answer-loading" role="status">Memuat jawaban pilihan...</p>:<>
        <DisclosureContext.Provider value={{scope:scrollKey,opened:openedGroups,setOpen:(key,open)=>setOpenedGroups(previous=>previous[key]===open?previous:{...previous,[key]:open})}}><div className="form-block-body">
          {section.availability_note && <p className="form-availability-note">{section.availability_note}</p>}
          {['blokl','ub_i_3'].includes(activeBlock)&&form.turnover&&<section className="turnover-form-summary" aria-label="Ringkasan omzet tahunan"><h3>Omzet tahunan</h3><TurnoverValue value={form.turnover} detail/></section>}
          {activeBlock === 'ub_i_1' && <LocationInfo location={form.locations?.root}/>}
          {form.truncated_rosters.length > 0 && <Notice tone="warning">Pilihan dibatasi 1.000 item per modul.</Notice>}
          {rootFields.length > 0 && <QuestionFields fields={rootFields}/>}
          {recordKind && records.length === 0 ? <p className="form-availability-note">Rincian {recordLabel} tidak tersedia pada versi ini.</p> : recordKind && records.length > 0 ? <div className="form-roster-workspace">
            <div className="form-roster-card">
              <QuestionFields fields={recordFields}/>
              {activeBlock==='blokl'&&<LocationInfo location={form.locations?.business}/>}
            </div>
          </div> : <QuestionFields fields={recordFields} collapseNotExported={section.collapse_not_exported}/>}
          {activeBlock === 'b5' && <LocationInfo location={form.locations?.root}/>}
        </div></DisclosureContext.Provider>
        </>}
        </div>
      </div>
      <nav className="section-navigation" aria-label="Pindah bagian"><Button variant="outline" disabled={sectionIndex <= 0} onClick={() => select({block: sections[sectionIndex - 1].section_id})}><ChevronLeft size={16}/>Sebelumnya</Button><Button variant="ghost" className="reader-to-top" aria-label="Kembali ke awal bagian" onClick={()=>stage.current?.scrollTo({top:0})}><ArrowUp size={16}/><span>Awal bagian</span></Button><Button disabled={sectionIndex >= sections.length - 1} onClick={() => select({block: sections[sectionIndex + 1].section_id})}>Berikutnya<ChevronRight size={16}/></Button></nav>
    </section>
  </div>
}

function revealQuestion(stage:HTMLDivElement|null,id:string,setOpened:(update:(previous:Record<string,boolean>)=>Record<string,boolean>)=>void){
  const row=Array.from(stage?.querySelectorAll<HTMLElement>('[data-question-id]')||[]).find(element=>element.dataset.questionId===id)
  if(!row)return false
  const opened:Record<string,boolean>={}
  let parent=row.parentElement
  while(parent&&parent!==stage){
    if(parent instanceof HTMLDetailsElement){parent.open=true;if(parent.dataset.disclosureKey)opened[parent.dataset.disclosureKey]=true}
    parent=parent.parentElement
  }
  setOpened(previous=>({...previous,...opened}))
  requestAnimationFrame(()=>{row.scrollIntoView({block:'start'});row.querySelector<HTMLElement>('h3')?.focus({preventScroll:true})})
  return true
}

const missingAnswers: Record<string, string> = {BLANK_OR_MISSING: 'Belum terisi', SKIPPED_NOT_APPLICABLE: 'Tidak berlaku', NOT_EXPORTED: 'Tidak ada dalam data', UNMATCHED_VERSION: 'Ada di versi lain', UNVERIFIED_MAPPING: 'Jawaban belum dapat ditampilkan', RESTRICTED: MASKED_VALUE}
const presentationOnlyQuestions = new Set(['blokl.pilih_umkm_sls', 'blokl.alamat_usaha_view'])

function UnavailableFields({fields,children,run=false}: {fields:Question[];children:ReactNode;run?:boolean}) {
  const context=useContext(DisclosureContext)
  const key=JSON.stringify([context?.scope,fields[0]?.question_id,fields.at(-1)?.question_id])
  return <details data-disclosure-key={key} className={'form-unavailable-fields'+(run?' question-unavailable-run':'')} open={context?.opened[key]||false} onToggle={event=>context?.setOpen(key,event.currentTarget.open)}>{children}</details>
}

function LocationInfo({location}: {location?: QuestionnaireLocation}) {
  if(!location) return null
  const states:Record<string,string> = {UNAVAILABLE:'Tagging belum tersedia',RESTRICTED:MASKED_VALUE,UNMATCHED_VERSION:'Tagging tidak tersedia pada versi ini',SOURCE_CONFLICT:'Tagging perlu diperiksa'}
  return <div className="form-location" aria-label="Tagging lokasi pendataan"><MapPin size={18}/><div><strong>Tagging lokasi</strong>{location.status === 'AVAILABLE' ? <>
    <p>{location.latitude}, {location.longitude}</p>
    {location.provenance === 'QUESTIONNAIRE_ROOT_TAG' && <p className="small muted">Titik pendataan kuesioner</p>}
    <a href={'https://www.google.com/maps/search/?api=1&query='+encodeURIComponent(location.latitude+','+location.longitude)} target="_blank" rel="noopener noreferrer" referrerPolicy="no-referrer">Buka di Maps</a>
  </> : <p>{states[location.status] || states.UNAVAILABLE}</p>}</div></div>
}

function QuestionFields({fields, collapseNotExported = false, expandUnavailable = false, startNumber = null}: {fields: Question[]; collapseNotExported?: boolean; expandUnavailable?: boolean; startNumber?:string|null}) {
  const questions = fields.filter(field => field.applicability !== 'NOT_APPLICABLE' && field.display_state !== 'HIDDEN' && (!presentationOnlyQuestions.has(field.question_id) || field.status !== 'UNVERIFIED_MAPPING'))
  if (!questions.length) return null
  const unavailable = questions.filter(field => field.status === 'NOT_EXPORTED')
  if (collapseNotExported && unavailable.length && !expandUnavailable) return <>
    <QuestionFields fields={questions.filter(field => field.status !== 'NOT_EXPORTED')}/>
    <UnavailableFields fields={unavailable}><summary>Isian yang tidak disertakan ({unavailable.length})</summary><QuestionFields fields={unavailable} expandUnavailable/></UnavailableFields>
  </>
  const uncertain = (field:Question) => ['NOT_EXPORTED','UNVERIFIED_MAPPING','UNMATCHED_VERSION'].includes(field.status) || (field.display_state === 'UNKNOWN' && ['BLANK_OR_MISSING','SKIPPED_NOT_APPLICABLE'].includes(field.status))
  if (!expandUnavailable && questions.some(uncertain)) {
    const runs: {uncertain:boolean;fields:Question[];before:string|null;group?:string}[] = []
    let preceding = startNumber
    for(const field of questions){
      const last=runs.at(-1);const missing=uncertain(field)
      if(last?.uncertain===missing&&last?.group===field.availability_group)last.fields.push(field)
      else runs.push({uncertain:missing,fields:[field],before:preceding,group:field.availability_group})
      preceding=questionNumber(field)||preceding
    }
    return <div className="question-list question-list-groups">{runs.map((run,index)=>run.uncertain ?
      <UnavailableFields fields={run.fields} run key={index}><summary>{run.group==='annual_capital'?'29. Sumber modal — tidak tersedia dalam data lokal':<>Isian kosong/belum tersedia ({run.fields.length})</>}</summary>{run.fields[0].availability_note&&<p className="form-availability-note">{run.fields[0].availability_note}</p>}<QuestionFields fields={run.fields} expandUnavailable startNumber={run.before}/></UnavailableFields> :
      <QuestionFields key={index} fields={run.fields} expandUnavailable startNumber={run.before}/>)}</div>
  }
  let previousNumber: string|null = startNumber
  return <div className="question-list">{questions.map((field,index) => {
    const currentNumber = questionNumber(field)
    const groupStart = (index > 0 || startNumber !== null) && currentNumber !== null && currentNumber !== previousNumber
    previousNumber = currentNumber || previousNumber
    const referenceName = field.question_id === 'b1_p.nama_sls' ? field.reference_label : undefined
    return <div className={'question-row'+(groupStart ? ' question-group-start' : '')} data-question-id={field.question_id} data-question-number={currentNumber || previousNumber || undefined} key={field.question_id}>
      <div className="question-label"><h3 tabIndex={-1}>{field.question_text}</h3></div>
      <div className="answer">{field.status === 'ANSWERED' ? <>
        <p className={field.converter === 'decimal' || field.display_format === 'number' ? 'numeric-answer' : ''}>{answerText(field)}</p>
        {field.reference_label && !referenceName && <p className="reference-answer">{field.reference_label}</p>}
        {field.parse_status && field.parse_status !== 'VALID' && <p className="parse-warning">Format angka perlu diperiksa.</p>}
        {field.label_status === 'UNRECOGNIZED_CODE' && <small className="answer-context">Label pilihan belum tersedia.</small>}
      </> : <p className="unavailable-answer answer-state" aria-label={field.status==='RESTRICTED'?'Data disamarkan':undefined}>{field.status==='RESTRICTED' ? MASKED_VALUE : field.source_conflict ? 'Jawaban berbeda antar sumber' : missingAnswers[field.status] || missingAnswers.UNVERIFIED_MAPPING}</p>}</div>
    </div>
  })}</div>
}
