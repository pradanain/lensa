import {ExportXlsx} from './export-xlsx'
import {missingKbliLabel,statusLabel,neighborhoodLabel} from '@/lib/directory-display'
import {DirectoryKbliFilters} from './directory-kbli-filters'
import {FilterPanel} from './filter-panel'
import {Pagination} from '@/components/pagination'
import {useDebouncedValue} from '@/lib/use-debounced-value'
import {SearchSelect} from '@/components/ui/search-select'
import { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate, useSearch } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { flexRender, getCoreRowModel, useReactTable, type ColumnDef } from '@tanstack/react-table';
import { ArrowUpRight, MapPin, RotateCcw, Search } from 'lucide-react';
import { api, directoryMemory, setDetailNavigation, type DirectoryRow, type DirectoryResult, type Geo, type SearchState } from '@/lib/api';
import { number } from '@/lib/utils';
import { useAuth } from '@/auth';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import { Card } from './ui/card';
import { ErrorBox, Loading, Restricted } from './shared';
export function Directory({ scope, source: fixedSource }: {
    scope: 'assignments' | 'businesses' | 'families' | 'members';
    source?: 'dtd' | 'ub';
}) {
    const { session } = useAuth();
    const routeSearch=useSearch({strict:false}) as SearchState;
    if (!session?.user?.can_detail)
        return <Restricted />;
    return <DirectoryContent key={scope+':'+(fixedSource||routeSearch.source||'dtd')} scope={scope} source={fixedSource}/>;
}
function DirectoryContent({ scope, source: fixedSource }: {
    scope: 'assignments' | 'businesses' | 'families' | 'members';
    source?: 'dtd' | 'ub';
}) {
    const navigate = useNavigate();
    const location = useLocation();
    const search = useSearch({ strict: false }) as SearchState;
    const source = fixedSource || ((scope === 'families' || scope === 'members') ? 'dtd' : search.source === 'ub' ? 'ub' : 'dtd');
    const memoryKey = scope + ':' + source;
    const [draft, setDraft] = useState(() => directoryMemory.get(memoryKey)?.q || '');
    const [term, setTerm] = useState(draft);
    const settled=useDebouncedValue(draft);
    useEffect(()=>{if(settled!==draft||settled===term)return;setTerm(settled);directoryMemory.set(memoryKey,{q:settled});void navigate({to:'.',search:{...search,page:1},replace:true,resetScroll:false})},[settled,draft,term,memoryKey,navigate,search]);
    const page = search.page || 1;
    const pageSize = search.page_size || 10;
    const payload = { source, enumerated_only:search.enumerated==='true', qualified_only:search.qualified==='true', q: term, page, page_size: pageSize, sort: scope==='businesses'?'business_priority':search.sort||'id', direction: search.direction || 'asc', kecamatan: search.kecamatan || '', desa: search.desa || '', sls: search.sls || '', subsls: search.subsls || '', status: search.status || '', kind: search.kind || '', kbli_category: search.kbli_category || '', kbli_prefix: search.kbli_prefix || '', kbli_state: search.kbli_state || '' };
    const result = useQuery({ queryKey: ['directory', scope, payload], queryFn: ({signal}) => api<DirectoryResult>('/directories/' + scope + '/search', payload,undefined,{signal}), placeholderData:(previous,previousQuery)=>previousQuery?.queryKey[1]===scope&&(previousQuery.queryKey[2] as {source?:string})?.source===source?previous:undefined, gcTime: 0 });
    const kec = useQuery({ queryKey: ['geo', source, 'kecamatan'], queryFn: () => api<{
            rows: Geo[];
        }>('/geography?source=' + source + '&level=kecamatan') });
    const desa = useQuery({ queryKey: ['geo', source, 'desa', search.kecamatan], queryFn: () => api<{
            rows: Geo[];
        }>('/geography?source=' + source + '&level=desa&parent=' + encodeURIComponent(search.kecamatan || '')), enabled: !!search.kecamatan });
    const sls = useQuery({ queryKey: ['geo', source, 'sls', search.desa], queryFn: () => api<{
            rows: Geo[];
        }>('/geography?source=' + source + '&level=sls&parent=' + encodeURIComponent(search.desa || '')), enabled: !!search.desa });
    const subsls=useQuery({queryKey:['geo',source,'subsls',search.sls],queryFn:()=>api<{rows:Geo[]}>('/geography?source='+source+'&level=subsls&parent='+encodeURIComponent(search.sls||'')),enabled:!!search.sls});
    const statuses = useQuery({ queryKey: ['statuses', source, scope], queryFn: () => api<{
            rows: string[]; options: {code:string;label:string}[];
        }>('/directory-statuses?source=' + source + '&scope=' + scope) });
    function update(values: Partial<SearchState>) { void navigate({ to: '.', search: { ...search, page: 1, ...values }, replace:true, resetScroll:false }); }
    function reset(){setDraft('');setTerm('');directoryMemory.set(memoryKey,{q:''});void navigate({to:'.',search:{tab:search.tab,source},replace:true,resetScroll:false})}
    function open(row: DirectoryRow) {
        if(result.isPlaceholderData)return;
        directoryMemory.set(memoryKey, { q: term, result: result.data, payload });
        setDetailNavigation({ from: location.pathname, search, scope, pages: result.data?.pages || 1, rows: result.data?.rows || [], position: result.data?.rows.findIndex(item => item.record_key === row.record_key) || 0, payload });
        const block = scope === 'businesses' ? 'blokl' : scope === 'members' ? 'b_ak' : scope === 'families' ? 'b_ak_lanjutan' : undefined;
        void navigate({ to: '/questionnaire/$system/$assignmentId', params: { system: row.source, assignmentId: row.assignment_id }, search: { block: row.source === 'ub' ? 'ub_i_1' : block, version: row.version || undefined, index1: row.index1 || undefined } });
    }
    const kbliCatalog=useQuery({queryKey:['kbli-catalog'],queryFn:()=>api<{rows:{code:string;title:string;category:string;level:number}[]}>('/kbli/catalog'),staleTime:Infinity,enabled:scope==='businesses'});
    const kbliTitles=useMemo(()=>new Map(kbliCatalog.data?.rows.map(row=>[row.code,row.title])||[]),[kbliCatalog.data]);
    const columns = useMemo<ColumnDef<DirectoryRow>[]>(() => [
        { accessorKey: 'title', header: scope === 'members' ? 'Anggota keluarga' : scope === 'families' ? 'Kepala keluarga' : scope === 'businesses' ? 'Nama Usaha' : 'Assignment', cell: ({ row }) => <button className="record-title" disabled={result.isPlaceholderData} onClick={() => open(row.original)}><span>{row.original.title}</span><small>{'ID '+row.original.assignment_id.slice(0, 8)}…{row.original.index1 ? ' · roster ' + row.original.index1 : ''}</small></button> },
        ...(scope==='assignments'?[{accessorKey:'kind',header:'Jenis',cell:({row}:{row:{original:DirectoryRow}})=><Badge>{({KELUARGA_BKU:'Keluarga & BKU',KELUARGA:'Keluarga',BKU:'BKU',USAHA:'Usaha',ASSIGNMENT:'Assignment'} as Record<string,string>)[row.original.kind]||row.original.kind}</Badge>}]:[]),
        { accessorKey:'desa_label',header:scope==='businesses'?'SLS/SUB-SLS':'Desa dan RT/RW',cell:({row})=><div className="table-location">{scope==='businesses'?<><strong>{neighborhoodLabel(row.original)}</strong><span className="directory-village">{row.original.desa_label||row.original.desa||'-'}</span><small className="directory-region-code">{row.original.subsls||'-'}</small></>:<><strong>{row.original.desa_label||row.original.desa||'-'}</strong><span className="directory-neighborhood">{row.original.subsls_label||row.original.sls_label||'RT/RW belum tersedia'}</span><small>{row.original.kecamatan_label||'Kode wilayah khusus'}</small></>}</div>},
        ...(scope==='businesses'?[{id:'responsible',header:'Penanggung Jawab',cell:({row}:{row:{original:DirectoryRow}})=><div className="directory-person"><strong>{row.original.family_head||row.original.person_in_charge||'-'}</strong>{row.original.family_head&&row.original.person_in_charge&&row.original.family_head!==row.original.person_in_charge&&<small>PJ: {row.original.person_in_charge}</small>}{row.original.family_head&&<small className="muted">Kepala keluarga</small>}</div>}]:[]),
        ...(scope === 'businesses' ? [{ accessorKey: 'kbli', header: 'KBLI 2025', cell: ({ row }: {
                    row: {
                        original: DirectoryRow;
                    };
                }) => {const item=row.original;const missing=missingKbliLabel(item);const code=item.kbli?.trim();return code?<div className="directory-kbli"><code>{item.kategori?'['+item.kategori+'] ':''}{code}</code>{kbliTitles.get(code)&&<span className="directory-kbli-title">{kbliTitles.get(code)}</span>}{item.kbli_state!=='VALID'&&<small className="muted block">Kode perlu ditinjau</small>}</div>:<div className="directory-kbli-missing"><span>-</span>{missing&&<small className="muted block">{missing}</small>}</div>} }] : []),
        ...(scope==='businesses'?[{id:'maps',header:'Lokasi',cell:({row}:{row:{original:DirectoryRow}})=>row.original.map_coordinates?<a className="button button-outline button-sm directory-map" href={'https://www.google.com/maps/search/?api=1&query='+encodeURIComponent(row.original.map_coordinates.latitude+','+row.original.map_coordinates.longitude)} target="_blank" rel="noopener noreferrer" referrerPolicy="no-referrer" aria-label={'Maps '+row.original.title} title="Buka titik tagging di Google Maps"><MapPin size={15}/><span>Maps</span></a>:<span className="muted">-</span>}]:[]),
        { accessorKey: 'status_label', header: 'Status', cell: ({ row }) => <Badge variant={scope==='businesses'&&row.original.source==='dtd'&&['1','2'].includes(row.original.status)?'success':'neutral'}>{statusLabel(row.original)}</Badge> },
        { id: 'open', header: 'Aksi', cell: ({ row }) => <Button variant="outline" size="sm" className="directory-open" disabled={result.isPlaceholderData} aria-label={'Buka kuesioner ' + row.original.title} onClick={() => open(row.original)}>Form<ArrowUpRight size={14}/></Button> },
        // Context is intentionally refreshed with each query: neighbors follow the
        // current server-side page/filter and never a previously displayed directory.
        // eslint-disable-next-line react-hooks/exhaustive-deps
    ], [scope, result.data, result.isPlaceholderData, search, term, kbliTitles]);
    const table = useReactTable({ data: result.data?.rows || [], columns, getCoreRowModel: getCoreRowModel(), manualPagination: true, manualSorting: true, rowCount: result.data?.total || 0, state: { pagination: { pageIndex: page - 1, pageSize } } });
    return <div className="analysis-layout directory-layout"><FilterPanel footer={<Button className="directory-reset" onClick={reset}><RotateCcw size={15}/>Reset filter</Button>}><Card className="filter-card">
    <div className="filter-grid">
      {!fixedSource && scope === 'businesses' && <label>Sumber<SearchSelect aria-label="Sumber" value={source} onValueChange={(selectedValue) => update({ source: selectedValue, kecamatan: undefined, desa: undefined, sls: undefined, subsls: undefined, status: undefined })}><option value="dtd">UMKM</option><option value="ub">Usaha Besar (UB)</option></SearchSelect></label>}
      {source === 'dtd' && <><label>Kecamatan<SearchSelect aria-label="Kecamatan" value={search.kecamatan || ''} onValueChange={(selectedValue) => update({ kecamatan: selectedValue, desa: undefined, sls: undefined, subsls: undefined })}><option value="">Semua kecamatan</option>{kec.data?.rows.map(item => <option key={item.code || 'missing'} value={item.code || ''}>{item.label || item.code || 'Kode kosong'}</option>)}</SearchSelect></label><label>Desa / kelurahan<SearchSelect aria-label="Desa / kelurahan" value={search.desa || ''} disabled={!search.kecamatan} onValueChange={(selectedValue) => update({ desa: selectedValue, sls: undefined, subsls: undefined })}><option value="">Semua desa</option>{desa.data?.rows.map(item => <option key={item.code || 'missing'} value={item.code || ''}>{item.label || item.code}</option>)}</SearchSelect></label><label>SLS<SearchSelect aria-label="SLS" value={search.sls || ''} disabled={!search.desa} onValueChange={(selectedValue) => update({ sls: selectedValue, subsls: undefined })}><option value="">Semua SLS</option>{sls.data?.rows.map(item => <option key={item.code || 'missing'} value={item.code || ''}>{item.label || item.code}</option>)}</SearchSelect></label><label>SUB-SLS<SearchSelect aria-label="SUB-SLS" value={search.subsls||''} disabled={!search.sls} onValueChange={value=>update({subsls:value})}><option value="">Semua SUB-SLS</option>{subsls.data?.rows.map(item=><option key={item.code||'missing'} value={item.code||''}>{item.label||item.code}</option>)}</SearchSelect></label></>}
      {scope === 'assignments' && source === 'dtd' && <label>Jenis assignment<SearchSelect aria-label="Jenis assignment" value={search.kind || ''} onValueChange={(selectedValue) => update({ kind: selectedValue })}><option value="">Semua jenis</option><option value="KELUARGA">Keluarga</option><option value="BKU">BKU</option><option value="KELUARGA_BKU">Keluarga dan BKU</option><option value="USAHA">Usaha tanpa induk keluarga/BKU</option><option value="ASSIGNMENT">Belum ada rincian</option></SearchSelect></label>}
      <label>Status<SearchSelect aria-label="Status" value={search.status || ''} onValueChange={(selectedValue) => update({ status: selectedValue })}><option value="">Semua status</option>{statuses.data?.options.map(item => <option key={item.code} value={item.code}>{item.label}</option>)}</SearchSelect></label>
      {scope==='businesses'&&<><details className="directory-classification" open={!!search.kbli_prefix||!!search.kbli_category}><summary>KBLI 2025</summary><div className="directory-classification-fields"><DirectoryKbliFilters search={search} onChange={update}/></div></details></>}
    </div>

  </Card></FilterPanel><div className="analysis-content directory-stack">

  <Card className="table-card">    <form className="search-row data-search" onSubmit={event => { event.preventDefault(); setTerm(draft); directoryMemory.set(memoryKey, { q: draft }); update({ page: 1 }); }}><div className="search-input"><Search size={17}/><Input aria-label="Cari direktori" value={draft} onChange={event => setDraft(event.target.value)} placeholder={scope==='businesses'?'Cari nama usaha, kode KBLI, atau lainnya...':scope==='families'?'Cari nama kepala keluarga atau lainnya...':scope==='members'?'Cari nama anggota keluarga atau lainnya...':'Cari nama atau ID assignment...'}/></div><Button type="submit">Cari</Button><ExportXlsx path={'/directories/'+scope+'/export'} payload={{...payload,q:draft,page:1}} filename={'lensa-'+scope+'.xlsx'}/></form><h2 className="sr-only">{scope==='assignments'?'Daftar assignment':scope==='families'?'Direktori keluarga':scope==='members'?'Anggota keluarga':'Direktori usaha'}</h2><p className="sr-only" role="status">{result.isPending?'Menghitung...':number(result.data?.total)+' record ditemukan'}</p>
    {result.error ? <ErrorBox error={result.error} retry={() => void result.refetch()}/> : result.isPending ? <Loading variant="table" /> : <><div className={'table-scroll '+(result.isPlaceholderData?'is-updating':'')} aria-busy={result.isFetching}><table className="directory-table"><thead>{table.getHeaderGroups().map(group => <tr key={group.id}>{group.headers.map(header => <th key={header.id} data-column={header.column.id} className={['kind','maps','status_label','open'].includes(header.column.id)?'directory-centered':undefined}>{flexRender(header.column.columnDef.header, header.getContext())}</th>)}</tr>)}</thead><tbody>{table.getRowModel().rows.map(row => <tr key={row.id}>{row.getVisibleCells().map(cell => <td key={cell.id} data-column={cell.column.id} className={['kind','maps','status_label','open'].includes(cell.column.id)?'directory-centered':undefined}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>)}</tr>)}</tbody></table>{!result.data?.rows.length && <div className="empty"><Search size={28}/><h3>Belum ada hasil yang sesuai</h3><p>Coba kata pencarian lain atau kurangi filter.</p></div>}</div><Pagination page={page} pageSize={pageSize} total={result.data?.total||0} busy={result.isPlaceholderData} onPage={value=>update({page:value})} onPageSize={value=>update({page_size:value,page:1})}/></>}
  </Card></div></div>;
}
