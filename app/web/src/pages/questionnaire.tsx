import {Pagination} from '@/components/pagination'
import type {Question} from '@/lib/api'
import {SearchSelect} from '@/components/ui/search-select'
import { useState } from 'react';
import { useNavigate, useParams, useSearch } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, ChevronLeft, ChevronRight, Check, Copy, PanelLeft } from 'lucide-react';
import { api, detailNavigation, setDetailNavigation, type DirectoryResult, type DirectoryRow, type FormResult, type SearchState } from '@/lib/api';
import { useAuth } from '@/auth';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ErrorBox, Loading, Notice, Restricted } from '@/components/shared';
export function Questionnaire() { const { session } = useAuth(); if (!session?.user?.can_detail)
    return <Restricted />; return <QuestionnaireContent />; }
function QuestionnaireContent() {
    const { system, assignmentId } = useParams({ strict: false }) as {
        system: string;
        assignmentId: string;
    };
    const search = useSearch({ strict: false }) as SearchState;
    const navigate = useNavigate();
    const [showBlocks, setShowBlocks] = useState(false);
    const [copied, setCopied] = useState(false);
    const [moving, setMoving] = useState(false);
    const [questionPageSize,setQuestionPageSize]=useState(10);
    const block = search.block || (system === 'ub' ? 'ub_i_1' : 'b5');
    const params = new URLSearchParams();
    if (search.version)
        params.set('version', search.version);
    if (search.business || (block === 'blokl' && search.index1))
        params.set('business', search.business || search.index1 || '');
    if (search.member || (['b_ak', 'b_ak_lanjutan'].includes(block) && search.index1))
        params.set('member', search.member || search.index1 || '');
    if (search.meter)
        params.set('meter', search.meter);
    if (search.office)
        params.set('office', search.office);
    const query = useQuery({ queryKey: ['questionnaire', system, assignmentId, params.toString()], queryFn: () => api<FormResult>('/questionnaires/' + encodeURIComponent(system) + '/' + encodeURIComponent(assignmentId) + '?' + params), gcTime: 0 });
    const form = query.data;
    const sections = form?.sections.filter(item => !['anomali_section','anomali_keluarga'].includes(item.section_id)) || [];
    const section = sections.find(item => item.section_id === block) || sections[0];
    const activeBlock = section?.section_id || block;
    const sectionIndex = sections.findIndex(item => item.section_id === activeBlock);
    const recordKind = activeBlock==='blokl'?'businesses':['b_ak','b_ak_lanjutan'].includes(activeBlock)?'members':undefined;
    const recordName = recordKind?form?.rosters[recordKind]?.find(item => item.index===form.selections[recordKind])?.label:undefined;
    function select(values: Partial<SearchState>) { void navigate({ to: '.', search: { ...search, index1: undefined, business: form?.selections.businesses || undefined, member: form?.selections.members || undefined, ...values },resetScroll:false }); setShowBlocks(false); }
    function back() { const context = detailNavigation; if (!context) {
        void navigate({ to: '/usaha', search: {tab:'direktori',source:system==='ub'?'ub':'dtd'} });
        return;
    } if (context.from.startsWith('/data/'))
        void navigate({ to: '/data/$system', params: { system: context.from.endsWith('ub') ? 'ub' : 'dtd' }, search: context.search });
    else
        void navigate({ to: context.from === '/keluarga' ? '/keluarga' : '/usaha', search: context.search }); }
    function open(row: DirectoryRow) { const context = detailNavigation; const member = context?.scope === 'members'; const business = context?.scope === 'businesses'; void navigate({ to: '/questionnaire/$system/$assignmentId', params: { system: row.source, assignmentId: row.assignment_id }, search: { block: row.source === 'ub' ? 'ub_i_1' : business ? 'blokl' : member ? 'b_ak' : 'b5', version: row.version || undefined, index1: row.index1 || undefined } }); }
    async function adjacent(direction: number) { const context = detailNavigation; if (!context)
        return; const position = context.position + direction; if (position >= 0 && position < context.rows.length) {
        setDetailNavigation({ ...context, position });
        open(context.rows[position]);
        return;
    } const payload = { ...context.payload, page: Number(context.payload.page || 1) + direction }; if (Number(payload.page) < 1)
        return; setMoving(true); try {
        const result = await api<DirectoryResult>('/directories/' + context.scope + '/search', payload);
        if (!result.rows.length)
            return;
        const selected = direction > 0 ? 0 : result.rows.length - 1;
        setDetailNavigation({ ...context, payload, pages: result.pages, rows: result.rows, position: selected, search: { ...context.search, page: result.page } });
        open(result.rows[selected]);
    }
    finally {
        setMoving(false);
    } }
    if (query.isPending)
        return <Loading variant="form" label="Memuat formulir..."/>;
    if (query.error)
        return <><Button variant="ghost" onClick={back}><ArrowLeft size={16}/>Kembali ke daftar</Button><ErrorBox error={query.error} retry={() => void query.refetch()}/></>;
    if (!form)
        return null;
    return <div className="questionnaire-page"><div className="form-navigation"><Button variant="ghost" onClick={back}><ArrowLeft size={17}/>Kembali ke daftar</Button><div><Button variant="outline" size="sm" onClick={() => void adjacent(-1)} disabled={!detailNavigation || moving || (detailNavigation.position === 0 && Number(detailNavigation.payload.page || 1) <= 1)}><ChevronLeft size={16}/>Sebelumnya</Button><Button variant="outline" size="sm" onClick={() => void adjacent(1)} disabled={!detailNavigation || moving || (detailNavigation.position >= detailNavigation.rows.length - 1 && Number(detailNavigation.payload.page || 1) >= detailNavigation.pages)}>Berikutnya<ChevronRight size={16}/></Button></div></div>
    <Card className="form-header compact-form-header">
      <div className="form-title-row"><div><h1>Kuesioner {system === 'ub' ? 'Usaha Besar' : 'SE2026'}</h1>{recordName&&<p className="form-record-name">{recordName}</p>}</div></div>
      {(form.assignment.desa_kelurahan||form.assignment.kecamatan)&&<p className="form-context">{[form.assignment.desa_kelurahan,form.assignment.kecamatan].filter(Boolean).join(' / ')}</p>}
      <details className="form-data-details" key={assignmentId}><summary>Detail data</summary>
        <div className="assignment-meta"><div><span>Assignment ID</span><button className="copy-id" aria-label="Salin ID assignment" onClick={() => { void navigator.clipboard.writeText(assignmentId).then(() => { setCopied(true); setTimeout(() => setCopied(false), 2000); }); }}><code>{assignmentId}</code>{copied ? <Check size={14}/> : <Copy size={14}/>}</button></div>
        {system==='dtd'&&<label>Versi kuesioner<SearchSelect aria-label="Versi kuesioner" value={form.version||''} onValueChange={selectedValue=>select({version:selectedValue,business:undefined,member:undefined,meter:undefined,office:undefined})}>{form.available_versions.map(version=><option value={version} key={version}>{version}</option>)}{!form.available_versions.length&&<option value="">Tidak ada versi rincian</option>}</SearchSelect></label>}</div>
        {form.assignment.status_assignment&&<p className="form-provenance">Status pendataan: {form.assignment.status_assignment}</p>}
        <p className="form-provenance">{form.warning}</p>
        {system==='ub'&&<p className="form-provenance">Modul terhubung berdasarkan assignment ID. Kesamaan versi historis belum diverifikasi.</p>}
      </details>
    </Card>
    {form.truncated_rosters.length > 0 && <Notice tone="warning">Pilihan dibatasi 1.000 item per modul.</Notice>}
    <Button className="mobile-block-toggle" variant="outline" onClick={() => setShowBlocks(!showBlocks)}><PanelLeft size={16}/>Navigasi blok</Button>
    <div className="form-layout"><aside className={'block-navigation ' + (showBlocks ? 'show' : '')} aria-label="Blok kuesioner"><div className="block-navigation-title">Blok formulir</div>{sections.map((item, index) => <button key={item.section_id} className={item.section_id === section?.section_id ? 'active' : ''} onClick={() => select({ block: item.section_id })}><span className="block-number">{String(index + 1).padStart(2, '0')}</span><span>{item.title}</span>{item.section_id === section?.section_id && <ChevronRight size={14}/>}</button>)}</aside>
      <section className="question-content" aria-label="Pertanyaan dan jawaban"><Card><div className="question-section-head"><h2>{section?.title}</h2></div>
      <div className="roster-bar">{Object.entries(form.rosters).filter(([key, items]) => items.length > 0 && (key === 'businesses' ? activeBlock === 'blokl' : key === 'members' ? ['b_ak', 'b_ak_lanjutan'].includes(activeBlock) : key === 'meters' ? activeBlock === 'b_perumahan' : activeBlock === 'blokl')).map(([key, items]) => <label key={key}>{key === 'businesses' ? 'Pilih usaha' : key === 'members' ? 'Pilih anggota' : key === 'meters' ? 'Pilih meteran' : 'Pilih kantor/unit'}<SearchSelect aria-label={key === 'businesses' ? 'Roster usaha' : key === 'members' ? 'Roster anggota' : key === 'meters' ? 'Roster meteran' : 'Roster kantor'} value={form.selections[key] || ''} onValueChange={(selectedValue) => select({ [key === 'businesses' ? 'business' : key === 'members' ? 'member' : key === 'meters' ? 'meter' : 'office']: selectedValue })}>{items.map(item => <option value={item.index} key={item.index}>#{item.index} · {item.label}</option>)}</SearchSelect></label>)}</div>
      <QuestionFields key={system+':'+assignmentId+':'+block+':'+params.toString()} fields={section?.questions||[]} pageSize={questionPageSize} onPageSize={setQuestionPageSize}/></Card>
      <nav className="section-navigation" aria-label="Pindah bagian"><Button variant="outline" disabled={sectionIndex<=0} onClick={()=>select({block:sections[sectionIndex-1].section_id})}><ChevronLeft size={16}/>Bagian sebelumnya</Button><span>{sectionIndex+1} / {sections.length} bagian</span><Button disabled={sectionIndex>=sections.length-1} onClick={()=>select({block:sections[sectionIndex+1].section_id})}>Bagian berikutnya<ChevronRight size={16}/></Button></nav></section>
    </div>
  </div>;
}

const periodLabels:Record<string,string>={ANNUAL_2025:'Tahun 2025',LAST_MONTH_NEW_2026_CALENDAR_MONTH_UNAVAILABLE:'Bulanan; bulan belum diketahui',UB_FORM_2025_EXPORT_PERIOD_UNVERIFIED:'Periode sumber belum terverifikasi'};
const missingAnswers:Record<string,string>={BLANK_OR_MISSING:'Belum terisi',SKIPPED_NOT_APPLICABLE:'Tidak berlaku',NOT_EXPORTED:'Tidak ada dalam data',UNMATCHED_VERSION:'Ada di versi lain',UNVERIFIED_MAPPING:'Jawaban belum dapat ditampilkan',RESTRICTED:'Akses terbatas'};
// These two source widgets are a picker and an address preview, not extra answers.
const presentationOnlyQuestions=new Set(['blokl.pilih_umkm_sls','blokl.alamat_usaha_view']);
function QuestionFields({fields,pageSize,onPageSize}:{fields:Question[];pageSize:number;onPageSize:(size:number)=>void}){
 const questions=fields.filter(field=>!presentationOnlyQuestions.has(field.question_id)||field.status!=='UNVERIFIED_MAPPING');
 const [page,setPage]=useState(1);const visible=questions.slice((page-1)*pageSize,page*pageSize)
 return <><div className="question-list">{visible.map(field => {
   const context=[periodLabels[field.period||''],field.unit==='SOURCE_UNIT_UNVERIFIED'?'Satuan belum terverifikasi':field.unit==='SOURCE_COUNT'?'Jumlah':field.unit].filter(Boolean).join(' / ');
   const labelHasCode=field.value&&field.label&&(field.label===field.value||field.label.startsWith(field.value+'.')||field.label.startsWith(field.value+' ')||field.label.startsWith(field.value+' -'));
   return <div className="question-row" key={field.question_id}>
     <div className="question-label"><h3>{field.question_text}</h3></div>
     <div className="answer">{field.status==='ANSWERED'?<>
       <p className={field.converter==='decimal'?'numeric-answer':''}>{field.label&&field.value&&!labelHasCode?field.value+' \u00b7 '+field.label:field.label||field.value||'\u2014'}</p>
       {field.reference_label&&<p className="reference-answer">{field.reference_label}</p>}
       {field.parse_status&&field.parse_status!=='VALID'&&<p className="parse-warning">Format angka perlu diperiksa.</p>}
       {context&&<small className="answer-context">{context}</small>}
     </>:<p className="unavailable-answer answer-state">{missingAnswers[field.status]||missingAnswers.UNVERIFIED_MAPPING}</p>}
     </div>
   </div>
 })}</div><Pagination label="Pertanyaan per halaman" page={page} pageSize={pageSize} total={questions.length} onPage={setPage} onPageSize={value=>{onPageSize(value);setPage(1)}}/></>
}
