import {Pagination} from '@/components/pagination'
import type {Question} from '@/lib/api'
import {SearchSelect} from '@/components/ui/search-select'
import { useState } from 'react';
import { useNavigate, useParams, useSearch } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, ChevronLeft, ChevronRight, Check, Copy, LockKeyhole, PanelLeft, FileText } from 'lucide-react';
import { api, detailNavigation, setDetailNavigation, type DirectoryResult, type DirectoryRow, type FormResult, type SearchState } from '@/lib/api';
import { answerStates } from '@/lib/utils';
import { useAuth } from '@/auth';
import { Badge } from '@/components/ui/badge';
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
    const section = form?.sections.find(item => item.section_id === block) || form?.sections[0];
    function select(values: Partial<SearchState>) { void navigate({ to: '.', search: { ...search, index1: undefined, business: form?.selections.businesses || undefined, member: form?.selections.members || undefined, ...values },resetScroll:false }); setShowBlocks(false); }
    function back() { const context = detailNavigation; if (!context) {
        void navigate({ to: '/data/$system', params: { system } });
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
        return <Loading variant="form" label="Memuat kuesioner baca saja…"/>;
    if (query.error)
        return <><Button variant="ghost" onClick={back}><ArrowLeft size={16}/>Kembali ke daftar</Button><ErrorBox error={query.error} retry={() => void query.refetch()}/></>;
    if (!form)
        return null;
    return <div className="questionnaire-page"><div className="form-navigation"><Button variant="ghost" onClick={back}><ArrowLeft size={17}/>Kembali ke daftar</Button><div><Button variant="outline" size="sm" onClick={() => void adjacent(-1)} disabled={!detailNavigation || moving || (detailNavigation.position === 0 && Number(detailNavigation.payload.page || 1) <= 1)}><ChevronLeft size={16}/>Sebelumnya</Button><Button variant="outline" size="sm" onClick={() => void adjacent(1)} disabled={!detailNavigation || moving || (detailNavigation.position >= detailNavigation.rows.length - 1 && Number(detailNavigation.payload.page || 1) >= detailNavigation.pages)}>Berikutnya<ChevronRight size={16}/></Button></div></div>
    <Card className="form-header"><div className="form-title-row"><div><div className="eyebrow">DATA SE / {system.toUpperCase()}</div><h1>Kuesioner {system === 'ub' ? 'Usaha Besar' : 'DTD'}</h1></div><Badge variant="success"><LockKeyhole size={12}/>Baca saja</Badge></div><div className="assignment-meta"><div><span>Assignment ID</span><button className="copy-id" onClick={() => { void navigator.clipboard.writeText(assignmentId).then(() => { setCopied(true); setTimeout(() => setCopied(false), 2000); }); }}><code>{assignmentId}</code>{copied ? <Check size={14}/> : <Copy size={14}/>}</button></div><div><span>Wilayah assignment</span><strong>{form.assignment.kecamatan || 'Kode wilayah khusus'} · {form.assignment.desa_kelurahan || '—'}</strong></div><div><span>Status operasional</span><strong>{form.assignment.status_assignment || 'Tidak tersedia'}</strong></div></div><div className="version-line"><span><FileText size={14}/>{system === 'ub' ? 'Modul dihubungkan dengan assignment ID' : 'Versi kuesioner'}</span>{system === 'dtd' && <SearchSelect aria-label="Versi kuesioner" value={form.version || ''} onValueChange={(selectedValue) => select({ version: selectedValue, business: undefined, member: undefined, meter: undefined, office: undefined })}>{form.available_versions.map(version => <option value={version} key={version}>{version}</option>)}{!form.available_versions.length && <option value="">Tidak ada versi rincian</option>}</SearchSelect>}{system === 'ub' && <span className="muted">Kesamaan versi historis belum diverifikasi</span>}</div></Card>
    <Notice>{form.warning}</Notice>
    {form.truncated_rosters.length > 0 && <Notice tone="warning">Pilihan roster dibatasi 1.000 baris per modul. Gunakan sumber lokal untuk pemeriksaan unit yang sangat besar.</Notice>}
    <Button className="mobile-block-toggle" variant="outline" onClick={() => setShowBlocks(!showBlocks)}><PanelLeft size={16}/>Navigasi blok</Button>
    <div className="form-layout"><aside className={'block-navigation ' + (showBlocks ? 'show' : '')} aria-label="Blok kuesioner"><div className="eyebrow">BAGIAN KUESIONER</div>{form.sections.map((item, index) => <button key={item.section_id} className={item.section_id === section?.section_id ? 'active' : ''} onClick={() => select({ block: item.section_id })}><span className="block-number">{String(index + 1).padStart(2, '0')}</span><span>{item.title}</span>{item.section_id === section?.section_id && <ChevronRight size={14}/>}</button>)}<div className="module-summary"><strong>Cakupan modul</strong><p>{form.modules.filter(module => module.present).length} / {form.modules.length} modul tersedia pada konteks ini</p><details><summary>Lihat status modul</summary>{form.modules.map(module => <div key={module.source}><span>{module.source.replaceAll('_', ' ')}</span><Badge variant={module.present ? 'success' : module.status === 'UNMATCHED_VERSION' ? 'warning' : 'neutral'}>{module.present ? 'Ada' : module.status === 'UNMATCHED_VERSION' ? 'Versi lain' : 'Tidak tersedia'}</Badge></div>)}</details></div></aside>
      <section className="question-content" aria-label="Pertanyaan dan jawaban"><Card><div className="question-section-head"><div className="eyebrow">KUESIONER {system.toUpperCase()}</div><h2>{section?.title}</h2><p>Jawaban dari data lokal. Kolom kosong tetap dibedakan dari bagian yang tidak diekspor.</p></div>
      <div className="roster-bar">{Object.entries(form.rosters).filter(([key, items]) => items.length > 0 && (key === 'businesses' ? block === 'blokl' : key === 'members' ? ['b_ak', 'b_ak_lanjutan'].includes(block) : key === 'meters' ? block === 'b_perumahan' : block === 'blokl')).map(([key, items]) => <label key={key}>{key === 'businesses' ? 'Pilih usaha' : key === 'members' ? 'Pilih anggota' : key === 'meters' ? 'Pilih meteran' : 'Pilih kantor/unit'}<SearchSelect aria-label={key === 'businesses' ? 'Roster usaha' : key === 'members' ? 'Roster anggota' : key === 'meters' ? 'Roster meteran' : 'Roster kantor'} value={form.selections[key] || ''} onValueChange={(selectedValue) => select({ [key === 'businesses' ? 'business' : key === 'members' ? 'member' : key === 'meters' ? 'meter' : 'office']: selectedValue })}>{items.map(item => <option value={item.index} key={item.index}>#{item.index} · {item.label}</option>)}</SearchSelect></label>)}</div>
      <QuestionFields key={system+':'+assignmentId+':'+block+':'+params.toString()} fields={section?.questions||[]} pageSize={questionPageSize} onPageSize={setQuestionPageSize}/></Card></section>
    </div>
  </div>;
}

function QuestionFields({fields,pageSize,onPageSize}:{fields:Question[];pageSize:number;onPageSize:(size:number)=>void}){
 const [page,setPage]=useState(1);const visible=fields.slice((page-1)*pageSize,page*pageSize)
 return <><div className="question-list">{visible.map(field => { const status = answerStates[field.status] || answerStates.UNVERIFIED_MAPPING; return <div className="question-row" key={field.question_id}><div className="question-label"><h3>{field.question_text}</h3><Badge variant={status.tone}>{status.label}</Badge></div><div className="answer">{field.status === 'ANSWERED' ? <><p className={field.converter === 'decimal' ? 'numeric-answer' : ''}>{field.label && field.value ? field.value + ' · ' + field.label : field.label || field.value || '—'}</p>{field.reference_label && <p className="reference-answer">{field.reference_label}</p>}{field.parse_status && field.parse_status !== 'VALID' && <p className="parse-warning">Format angka: {field.parse_status}. Tidak diperlakukan sebagai nol.</p>}</> : <p className="unavailable-answer">{field.status === 'NOT_EXPORTED' ? 'Jawaban tidak termasuk dalam dataset yang tersedia.' : field.status === 'UNMATCHED_VERSION' ? 'Modul ditemukan pada versi lain. Jawaban tidak dipindahkan ke versi ini.' : field.status === 'RESTRICTED' ? 'Nilai disembunyikan sesuai hak akses akun.' : field.status === 'SKIPPED_NOT_APPLICABLE' ? 'Tidak ditanyakan menurut aturan yang dapat diverifikasi.' : field.status === 'UNVERIFIED_MAPPING' ? 'Hubungan pertanyaan dengan kolom ekspor belum dapat dibuktikan.' : 'Tidak ada jawaban terisi pada konteks ini.'}</p>}</div>{field.mapping_status === 'VERIFIED' && <details className="source-detail"><summary>Sumber jawaban</summary><code>{field.source_object}.{field.source_field}</code><p>Periode: {field.period} {field.unit ? ' · Satuan: ' + field.unit : ''}</p>{field.note && <p>{field.note}</p>}</details>}</div>; })}</div><Pagination label="Pertanyaan per halaman" page={page} pageSize={pageSize} total={fields.length} onPage={setPage} onPageSize={value=>{onPageSize(value);setPage(1)}}/></>
}
