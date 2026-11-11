import {ExportXlsx} from '@/components/export-xlsx'
import {FilterPanel} from '@/components/filter-panel'
import {Pagination} from '@/components/pagination'
import {useDebouncedValue} from '@/lib/use-debounced-value'
import {SearchSelect} from '@/components/ui/search-select'

import { useNavigate, useSearch } from '@tanstack/react-router';
import { useQuery,keepPreviousData } from '@tanstack/react-query';
import { ArrowUpRight, ChevronRight, RotateCcw, Search } from 'lucide-react';
import { api, type SearchState } from '@/lib/api';
import { number } from '@/lib/utils';
import { useAuth } from '@/auth';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { ErrorBox, Loading } from '@/components/shared';
type CatalogNode = {
    code: string;
    category: string;
    title: string;
    level: number;
    level_name: string;
    parent_code: string | null;
};
type Node = CatalogNode & {
    prefix: string;
    description: string;
    description_status: string;
    is_official: boolean;
    category_label: string;
    reference_codes: number;
    outside_se_codes: number;
    dtd_units: number | null;
    ub_units: number | null;
};
type Tree = {
    rows: Node[];
    selection: Node[];
    total: number;
    page: number;
    pages: number;
    unknown_buckets: Record<string, {
        code: string;
        units: number | null;
    }[]>;
};
type ReferenceSummary = {
    kbli_codes: number;
    categories: number;
    outside_se_codes: number;
    category_codes: string[];
    category_labels: Record<string, string>;
};
export function Kbli() {
    const search = useSearch({ strict: false }) as SearchState;
    const navigate = useNavigate();
    const { session } = useAuth();
    const level = Math.min(5, Math.max(2, search.level || 2));
    const prefix = search.prefix || '';
    const category = search.category || '';
    const page = search.page || 1;
    const draft=search.kbli_q||'';
    const term=useDebouncedValue(draft);
    const pageSize=search.page_size||10;
    const qualified=search.qualified==='true';
    const enumerated=!qualified&&search.enumerated!=='false';
    const master = useQuery({ queryKey: ['reference-summary'], queryFn: () => api<ReferenceSummary>('/references/summary') });
    const catalog = useQuery({ queryKey: ['kbli-catalog'], queryFn: () => api<{
            rows: CatalogNode[];
        }>('/kbli/catalog'), staleTime: Infinity });
    const params = new URLSearchParams({ level: String(level), prefix, category, q: term, page: String(page),page_size:String(pageSize),qualified_only:String(qualified),enumerated_only:String(enumerated) });
    const tree = useQuery({ queryKey: ['kbli', params.toString()], queryFn: ({signal}) => api<Tree>('/kbli/tree?' + params,undefined,undefined,{signal}),placeholderData:keepPreviousData });
    function change(values: Partial<SearchState>) { void navigate({ to: '.', search: { ...search, page: 1, ...values }, replace:true, resetScroll:false }); }
    function choose(code: string, digits: number) {
        const node = catalog.data?.rows.find(row => row.code === code);
        change({ prefix: code || prefix.slice(0, digits === 2 ? 0 : digits - 1), category: category || node?.category || undefined, level: code ? Math.min(5, digits + 1) : Math.max(2, digits), kbli_q: undefined });
    }
    function options(digits: number) { return catalog.data?.rows.filter(row => row.level === digits && (!category || row.category === category) && row.code.startsWith(prefix.slice(0, digits === 2 ? 0 : digits - 1))).sort((a,b)=>a.code.localeCompare(b.code)) || []; }

    const selection = (tree.data?.selection || []).filter(node=>node.is_official);
    const selected = selection[selection.length - 1];
    function directory(node: Node, source: 'dtd' | 'ub') { void navigate({ to: '/usaha', search: { tab: 'direktori', source, qualified:qualified?'true':undefined, enumerated:enumerated?'true':undefined, kbli_category: category || node.category || undefined, kbli_prefix: node.prefix } }); }
    return <div className="analysis-layout kbli-layout">
    <FilterPanel title="Filter klasifikasi">

    <Card className="filter-card">
      <div className="kbli-hierarchy-filters">
        <label>Kategori<SearchSelect aria-label="Kategori KBLI" value={category} onValueChange={(selectedValue) => change({ category: selectedValue, prefix: '', level: 2, kbli_q: undefined })}><option value="">Semua kategori</option>{master.data?.category_codes.map(code => <option key={code} value={code}>{code} - {master.data.category_labels[code]}</option>)}</SearchSelect></label>

        {[2, 3, 4, 5].map(digits => <label key={digits}>KBLI {digits} Digit<SearchSelect aria-label={'KBLI '+digits+' Digit'} value={prefix.length >= digits ? prefix.slice(0, digits) : ''} disabled={digits > 2 && prefix.length < digits - 1} onValueChange={(selectedValue) => choose(selectedValue, digits)}><option value="">Semua kode {digits} digit</option>{options(digits).map(row => <option key={row.code} value={row.code}>{row.code} - {row.title}</option>)}</SearchSelect></label>)}
      </div>


      <Button className="kbli-reset-filter" onClick={() => change({ category: undefined, prefix: undefined, level: 2, kbli_q: undefined })}><RotateCcw size={15}/>Reset filter</Button>
    </Card>
    </FilterPanel><div className="analysis-content kbli-stack">

    {(master.error || catalog.error) && <ErrorBox error={master.error || catalog.error}/>}
    {selection.length>0&&<nav className="kbli-breadcrumb" aria-label="Jalur klasifikasi">{selection.map(node => <button key={node.code} disabled={tree.isPlaceholderData} onClick={() => node.is_official && node.level === 1 ? change({ category: node.code, prefix: '', level: 2, kbli_q: undefined }) : choose(node.code, node.level)}>{node.code}<span>{node.title}</span><ChevronRight size={13}/></button>)}</nav>}

    {tree.isPending ? <Loading variant="table" /> : tree.error ? <ErrorBox error={tree.error}/> : <Card className="table-card kbli-results"><form className="search-row kbli-search" onSubmit={event => { event.preventDefault(); }}><div className="search-input"><Search size={17}/><Input aria-label="Cari kode atau definisi KBLI" placeholder="Cari kode KBLI atau lainnya..." maxLength={120} value={draft} onChange={event => change({kbli_q:event.target.value,level:5})}/></div><Button type="submit">Cari</Button><ExportXlsx path="/kbli/export" payload={{level,prefix,category,q:draft,qualified_only:qualified,enumerated_only:enumerated}} filename="lensa-kbli-2025.xlsx"/></form>
      {selected&&(<div className="kbli-selection" aria-busy={tree.isFetching}><div className="card-heading"><div><h2>{selected.code+' - '+selected.title}</h2></div></div><details key={selected.code} className="kbli-selected-definition"><summary>Definisi dan cakupan kode</summary><p>{selected.description}</p></details></div>)}
      <div className={'table-scroll '+(tree.isPlaceholderData?'is-updating':'')} aria-busy={tree.isFetching}>
        <table className="kbli-table"><thead><tr><th>Judul dan Definisi</th><th className="kbli-numeric-column">Rincian Kode</th><th className="kbli-unit-column">UMKM</th><th className="kbli-unit-column">Usaha Besar (UB)</th></tr></thead>
        <tbody>{tree.data?.rows.map(node=><tr key={node.code}>
          <td><div className="kbli-cell-main"><div className="kbli-node"><code>{node.code}</code><div className="kbli-node-content"><strong>{node.title}</strong>
            {node.outside_se_codes>0&&<small>{node.outside_se_codes} kode di luar cakupan SE</small>}
            <details className="kbli-definition"><summary>Definisi dan cakupan</summary><p>{node.description}</p></details>
          </div></div>
              {level<5&&<Button variant="ghost" size="sm" className="kbli-subcode" disabled={tree.isPlaceholderData} aria-label={'Subkode '+node.code} onClick={()=>choose(node.code,level)}>Subkode<ChevronRight size={14}/></Button>}
          </div></td>
          <td className="kbli-numeric-column">{number(node.reference_codes)}</td>
          <td className="kbli-unit-column">{session?.user?.can_detail?<Button variant="outline" size="sm" className="kbli-count-link" disabled={tree.isPlaceholderData} aria-label={'Lihat '+'UMKM'+' '+node.prefix} title="Lihat direktori usaha" onClick={()=>directory(node,'dtd')}><span>{number(node.dtd_units)}</span><ArrowUpRight size={14}/></Button>:number(node.dtd_units)}</td>
          <td className="kbli-unit-column">{session?.user?.can_detail?<Button variant="outline" size="sm" className="kbli-count-link" disabled={tree.isPlaceholderData} aria-label={'Lihat UB '+node.prefix} title="Lihat direktori Usaha Besar (UB)" onClick={()=>directory(node,'ub')}><span>{number(node.ub_units)}</span><ArrowUpRight size={14}/></Button>:number(node.ub_units)}</td>
        </tr>)}</tbody></table>
        {tree.data?.rows.length===0&&<div className="empty"><h3>Tidak ada kode yang sesuai</h3><p>Ubah filter atau kata pencarian.</p></div>}
      </div>
      <Pagination page={page} pageSize={pageSize} total={tree.data?.total||0} busy={tree.isPlaceholderData} onPage={value=>change({page:value})} onPageSize={value=>change({page_size:value})}/></Card>}

  </div></div>;
}
