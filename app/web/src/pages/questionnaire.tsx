import {useLayoutEffect, useRef, useState} from 'react'
import {useNavigate, useParams, useSearch} from '@tanstack/react-router'
import {useQuery} from '@tanstack/react-query'
import {ArrowLeft, BookOpen, ChevronLeft, ChevronRight, Maximize, Minimize} from 'lucide-react'
import {api, detailNavigation, type FormResult, type Question, type SearchState} from '@/lib/api'
import {useAuth} from '@/auth'
import {SearchSelect} from '@/components/ui/search-select'
import {Button} from '@/components/ui/button'
import {ErrorBox, Loading, Notice, Restricted} from '@/components/shared'

export function Questionnaire() {
  const {session} = useAuth()
  return session?.user?.can_detail ? <QuestionnaireContent/> : <Restricted/>
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

function QuestionnaireContent() {
  const {system, assignmentId} = useParams({strict: false}) as {system: string; assignmentId: string}
  const search = useSearch({strict: false}) as SearchState
  const navigate = useNavigate()
  const [expanded, setExpanded] = useState(false)
  const stage = useRef<HTMLDivElement>(null)
  const scrollPositions = useRef(new Map<string, number>())
  const block = search.block || (system === 'ub' ? 'ub_i_1' : 'b5')
  const params = new URLSearchParams()
  if (search.version) params.set('version', search.version)
  if (search.business || (block === 'blokl' && search.index1)) params.set('business', search.business || search.index1 || '')
  if (search.member || (['b_ak', 'b_ak_lanjutan'].includes(block) && search.index1)) params.set('member', search.member || search.index1 || '')
  if (search.meter) params.set('meter', search.meter)
  if (search.office) params.set('office', search.office)
  const query = useQuery({
    queryKey: ['questionnaire', system, assignmentId, params.toString()],
    queryFn: () => api<FormResult>('/questionnaires/' + encodeURIComponent(system) + '/' + encodeURIComponent(assignmentId) + '?' + params),
    gcTime: 0,
  })
  const form = query.data
  const sections = form?.sections.filter(item => item.applicability !== 'NOT_APPLICABLE' && !['anomali_section', 'anomali_keluarga'].includes(item.section_id)) || []
  const section = sections.find(item => item.section_id === block) || sections.find(item => item.section_id === 'blokl') || sections[0]
  const activeBlock = section?.section_id || block
  const sectionIndex = sections.findIndex(item => item.section_id === activeBlock)
  const scrollKey = JSON.stringify([system, assignmentId, activeBlock, form?.version, form?.selections])
  useLayoutEffect(() => {
    if (stage.current) stage.current.scrollTop = scrollPositions.current.get(scrollKey) || 0
  }, [scrollKey, form])

  function select(values: Partial<SearchState>) {
    void navigate({to: '.', search: {
      ...search, index1: undefined,
      business: form?.selections.businesses || undefined,
      member: form?.selections.members || undefined,
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
  if (query.error) return <><Button variant="ghost" onClick={back}><ArrowLeft size={16}/>Kembali ke daftar</Button><ErrorBox error={query.error} retry={() => void query.refetch()}/></>
  if (!form || !section) return null

  const recordKind = activeBlock === 'blokl' ? 'businesses' : ['b_ak', 'b_ak_lanjutan'].includes(activeBlock) ? 'members' : activeBlock === 'b_perumahan' && form.rosters.meters?.length ? 'meters' : undefined
  const records = recordKind ? form.rosters[recordKind] || [] : []
  const selectedRecord = recordKind ? records.find(item => item.index === form.selections[recordKind]) : undefined
  const recordLabel = recordKind === 'businesses' ? 'usaha' : recordKind === 'members' ? 'anggota' : 'meteran'
  const chooseRecord = (value: string) => select({[recordKind === 'businesses' ? 'business' : recordKind === 'members' ? 'member' : 'meter']: value})
  // Only proven family fields precede the member card; unmapped member questions stay in source order.
  const rootFields = section.questions.filter(field => activeBlock === 'b_ak_lanjutan' ? field.source_object === 'mart_keluarga' : recordKind === 'meters' ? field.roster !== 'meters' : false)
  const recordFields = section.questions.filter(field => !rootFields.includes(field))
  const description = activeBlock === 'b5' && form.assignment_context?.kind === 'BKU'
    ? {badge: 'P', description: 'Keterangan bangunan dan usaha'} : blockDescriptions[activeBlock]
  const offices = activeBlock === 'blokl' ? form.rosters.offices || [] : []

  return <div className={'questionnaire-page form-reader ' + (expanded ? 'is-expanded' : '')} onKeyDown={event => {
    if (event.key === 'Escape' && !event.defaultPrevented) setExpanded(false)
  }}>
    <h1 className="sr-only">Kuesioner {system === 'ub' ? 'Usaha Besar' : 'SE2026'}</h1>
    <aside className="form-reader-sidebar" aria-label="Blok kuesioner">
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
      <div className="form-viewer-toolbar"><label>Lompat ke bagian<SearchSelect aria-label="Lompat ke bagian" value={activeBlock} onValueChange={value => select({block: value})}>
        {sections.map(item => <option value={item.section_id} key={item.section_id}>{item.title}</option>)}
      </SearchSelect></label><span className="viewer-position" role="status">{sectionIndex + 1} / {sections.length} bagian</span>
        <Button variant="outline" className="reader-focus-toggle" aria-pressed={expanded} aria-label={expanded ? 'Kembalikan ukuran area baca' : 'Perbesar area baca'} onClick={() => setExpanded(!expanded)}>{expanded ? <Minimize size={16}/> : <Maximize size={16}/>}<span>{expanded ? 'Kembalikan' : 'Perbesar'}</span></Button>
      </div>
      <progress className="form-viewer-progress" max={sections.length} value={sectionIndex + 1} aria-label="Posisi bagian"/>
      <div className="card form-stage" ref={stage} tabIndex={0} aria-label={section.title} onScroll={event => scrollPositions.current.set(scrollKey, event.currentTarget.scrollTop)}>
        <div className="question-section-head"><span className="block-symbol">{description?.badge || <BookOpen size={18}/>}</span><div><h2>{section.title}</h2>{description && <p>{description.description}{records.length ? ' · ' + records.length + ' ' + (recordKind === 'members' ? 'ART' : recordLabel) : ''}</p>}</div></div>
        <div className="form-block-body">
          {section.availability_note && <p className="form-availability-note">{section.availability_note}</p>}
          {form.truncated_rosters.length > 0 && <Notice tone="warning">Pilihan dibatasi 1.000 item per modul.</Notice>}
          {rootFields.length > 0 && <QuestionFields fields={rootFields}/>}
          {recordKind && records.length > 0 ? <div className="form-roster-workspace">
            <div className="form-roster-picker" role="group" aria-label={'Daftar ' + recordLabel}>
              {records.map(item => <button className={'form-roster-choice ' + (selectedRecord?.index === item.index ? 'selected' : '')} key={item.index} aria-pressed={selectedRecord?.index === item.index} onClick={() => chooseRecord(item.index)}>{item.index} · {item.label}</button>)}
            </div>
            <label className="form-roster-mobile">Pilih {recordLabel}<SearchSelect aria-label={'Roster ' + recordLabel} value={selectedRecord?.index || ''} onValueChange={chooseRecord}>{records.map(item => <option key={item.index} value={item.index}>{item.index} · {item.label}</option>)}</SearchSelect></label>
            <div className="form-roster-card"><div className="form-roster-heading"><span className="roster-number">{selectedRecord?.index}</span><h3 className="form-record-name">{selectedRecord?.label}</h3></div>
              {offices.length > 0 && <label className="form-office-picker">Pilih kantor/unit<SearchSelect aria-label="Roster kantor" value={form.selections.offices || ''} onValueChange={office => select({office})}>{offices.map(item => <option key={item.index} value={item.index}>{item.index} · {item.label}</option>)}</SearchSelect></label>}
              <QuestionFields fields={recordFields}/>
            </div>
          </div> : <QuestionFields fields={recordFields} collapseNotExported={section.collapse_not_exported}/>}
        </div>
      </div>
      <nav className="section-navigation" aria-label="Pindah bagian"><Button variant="outline" disabled={sectionIndex <= 0} onClick={() => select({block: sections[sectionIndex - 1].section_id})}><ChevronLeft size={16}/>Sebelumnya</Button><span>Pilih blok atau gulir untuk membaca</span><Button disabled={sectionIndex >= sections.length - 1} onClick={() => select({block: sections[sectionIndex + 1].section_id})}>Berikutnya<ChevronRight size={16}/></Button></nav>
    </section>
  </div>
}

const periodLabels: Record<string, string> = {ANNUAL_2025: 'Tahun 2025', LAST_MONTH_NEW_2026_CALENDAR_MONTH_UNAVAILABLE: 'Bulanan; bulan belum diketahui', UB_FORM_2025_EXPORT_PERIOD_UNVERIFIED: 'Periode sumber belum terverifikasi'}
const missingAnswers: Record<string, string> = {BLANK_OR_MISSING: 'Belum terisi', SKIPPED_NOT_APPLICABLE: 'Tidak berlaku', NOT_EXPORTED: 'Tidak ada dalam data', UNMATCHED_VERSION: 'Ada di versi lain', UNVERIFIED_MAPPING: 'Jawaban belum dapat ditampilkan', RESTRICTED: 'Akses terbatas'}
const presentationOnlyQuestions = new Set(['blokl.pilih_umkm_sls', 'blokl.alamat_usaha_view'])

function QuestionFields({fields, collapseNotExported = false}: {fields: Question[]; collapseNotExported?: boolean}) {
  const questions = fields.filter(field => field.applicability !== 'NOT_APPLICABLE' && (!presentationOnlyQuestions.has(field.question_id) || field.status !== 'UNVERIFIED_MAPPING'))
  if (!questions.length) return null
  const unavailable = questions.filter(field => field.status === 'NOT_EXPORTED')
  if (collapseNotExported && unavailable.length) return <>
    <QuestionFields fields={questions.filter(field => field.status !== 'NOT_EXPORTED')}/>
    <details className="form-unavailable-fields"><summary>Isian yang tidak disertakan ({unavailable.length})</summary><QuestionFields fields={unavailable}/></details>
  </>
  return <div className="question-list">{questions.map(field => {
    const context = [periodLabels[field.period || ''], field.unit === 'SOURCE_UNIT_UNVERIFIED' ? 'Satuan belum terverifikasi' : field.unit === 'SOURCE_COUNT' ? 'Jumlah' : field.unit].filter(Boolean).join(' / ')
    const labelHasCode = field.value && field.label && (field.label === field.value || field.label.startsWith(field.value + '.') || field.label.startsWith(field.value + ' '))
    const referenceName = field.question_id === 'b1_p.nama_sls' ? field.reference_label : undefined
    return <div className="question-row" key={field.question_id}>
      <div className="question-label"><h3>{field.question_text}</h3></div>
      <div className="answer">{field.status === 'ANSWERED' ? <>
        <p className={field.converter === 'decimal' ? 'numeric-answer' : ''}>{referenceName || (field.label && field.value && !labelHasCode ? field.value + ' · ' + field.label : field.label || field.value || '—')}</p>
        {field.reference_label && !referenceName && <p className="reference-answer">{field.reference_label}</p>}
        {field.parse_status && field.parse_status !== 'VALID' && <p className="parse-warning">Format angka perlu diperiksa.</p>}
        {context && <small className="answer-context">{context}</small>}
      </> : <p className="unavailable-answer answer-state">{field.source_conflict ? 'Jawaban berbeda antar sumber' : missingAnswers[field.status] || missingAnswers.UNVERIFIED_MAPPING}</p>}</div>
    </div>
  })}</div>
}
