import {SearchSelect} from '@/components/ui/search-select'
import { useMemo } from 'react';
import { useNavigate, useSearch } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { api, type Geo, type SearchState } from '@/lib/api';
import { ArrowRight, Building2, ClipboardList, House, Layers3, Users, BriefcaseBusiness } from 'lucide-react';
import { useAuth } from '@/auth';
import { number } from '@/lib/utils';
import { PageHead, StatCard, BarChart, useSummary, ErrorBox, Loading, Notice } from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
export function Dashboard() {
    const { session } = useAuth();
    const navigate = useNavigate();
    const search = useSearch({ strict: false }) as SearchState;
    const filters = Object.fromEntries(['kecamatan', 'desa', 'sls'].filter(key => search[key as keyof SearchState]).map(key => [key, String(search[key as keyof SearchState])]));
    const result = useSummary(filters);
    const kec = useQuery({ queryKey: ['geo', 'dtd', 'kecamatan'], queryFn: () => api<{
            rows: Geo[];
        }>('/geography?source=dtd&level=kecamatan') });
    const desa = useQuery({ queryKey: ['geo', 'dtd', 'desa', search.kecamatan], queryFn: () => api<{
            rows: Geo[];
        }>('/geography?source=dtd&level=desa&parent=' + encodeURIComponent(search.kecamatan || '')), enabled: !!search.kecamatan });
    const sls = useQuery({ queryKey: ['geo', 'dtd', 'sls', search.desa], queryFn: () => api<{
            rows: Geo[];
        }>('/geography?source=dtd&level=sls&parent=' + encodeURIComponent(search.desa || '')), enabled: !!search.desa });
    function filter(values: Partial<SearchState>) { void navigate({ to: '/dashboard', search: { ...search, ...values },replace:true,resetScroll:false }); }
    const regions = useMemo(() => result.data?.region.rows.map(row => { const geo = row.dimensions.kecamatan as {
        display_label: string;
        raw_codes: Record<string, string>;
        geo_status: string;
    }; return { name: geo.display_label, value: typeof row.value === 'number' ? row.value : null, code: geo.raw_codes.kode_kecamatan }; }) || [], [result.data]);
    if (result.isPending)
        return <><PageHead eyebrow="IKHTISAR WILAYAH" title="Ringkasan Data SE2026" description="Ringkasan keluarga dan usaha dari baseline lokal yang tersedia."/><Loading variant="dashboard" label="Memuat ringkasan…"/></>;
    if (result.error)
        return <ErrorBox error={result.error} retry={() => void result.refetch()}/>;
    const data = result.data;
    const value = (id: string) => data.counts[id]?.[0]?.value;
    const canDetail = !!session?.user?.can_detail;
    function regionClick(item: {
        code?: string;
    }) { if (canDetail && item.code)
        void navigate({ to: '/data/$system', params: { system: 'dtd' }, search: { ...filters, kecamatan: item.code } }); }
    const digital = data.indicators.filter(metric => metric.metric_id.includes('internet_yes_rate'));
    return <><PageHead eyebrow="IKHTISAR WILAYAH" title="Ringkasan Data SE2026" description="Jumlah assignment, keluarga, anggota dan usaha pada data SE2026 Bulungan."><Badge variant="success"><span className="live-dot"/>Data lokal</Badge></PageHead>
    <div className="section-label"><h2>Cakupan data</h2><span>Jumlah pada masing-masing unit data</span></div><div className="stats-grid">
      <StatCard label="Assignment UMKM" value={value('assignment_tgr.count')} note="Master assignment UMKM" icon={<ClipboardList size={20}/>} accent onClick={canDetail ? () => void navigate({ to: '/data/$system', params: { system: 'dtd' }, search: filters }) : undefined}/>
      <StatCard label="Keluarga" value={value('keluarga.count')} note="Data keluarga per versi" icon={<House size={20}/>} onClick={canDetail ? () => void navigate({ to: '/keluarga', search: { ...filters, tab: 'direktori' } }) : undefined}/>
      <StatCard label="Anggota keluarga" value={value('anggota.count')} note="Data anggota per versi" icon={<Users size={20}/>} onClick={canDetail ? () => void navigate({ to: '/keluarga', search: { ...filters, tab: 'anggota' } }) : undefined}/>
      <StatCard label="Bangunan usaha" value={value('bku.count')} note="BKU · berbeda dari unit usaha" icon={<Building2 size={20}/>}/>
      <StatCard label="UMKM" value={value('usaha.count')} note="Usaha pada daftar UMKM" icon={<BriefcaseBusiness size={20}/>} onClick={canDetail ? () => void navigate({ to: '/usaha', search: { ...filters, tab: 'direktori', source: 'dtd' } }) : undefined}/>
      <StatCard label="Usaha besar" value={value('ub.count')} note="Usaha Besar (UB)" icon={<Layers3 size={20}/>} onClick={canDetail ? () => void navigate({ to: '/data/$system', params: { system: 'ub' }, search: filters }) : undefined}/>
    </div>
    <Card className="filter-card dashboard-filters"><div className="filter-heading"><span>Wilayah assignment</span><Button variant="ghost" size="sm" onClick={() => void navigate({ to: '/dashboard', search: {} })}>Reset wilayah</Button></div><div className="filter-grid"><label>Kecamatan<SearchSelect aria-label="Kecamatan" value={search.kecamatan || ''} onValueChange={(selectedValue) => filter({ kecamatan: selectedValue, desa: undefined, sls: undefined, subsls: undefined })}><option value="">Semua kecamatan</option>{kec.data?.rows.map(row => <option key={row.code || 'empty'} value={row.code || ''}>{row.label || row.code || 'Kode kosong'}</option>)}</SearchSelect></label><label>Desa / kelurahan<SearchSelect aria-label="Desa / kelurahan" disabled={!search.kecamatan} value={search.desa || ''} onValueChange={(selectedValue) => filter({ desa: selectedValue, sls: undefined, subsls: undefined })}><option value="">Semua desa</option>{desa.data?.rows.map(row => <option key={row.code || 'empty'} value={row.code || ''}>{row.label || row.code}</option>)}</SearchSelect></label><label>SLS<SearchSelect aria-label="SLS" disabled={!search.desa} value={search.sls || ''} onValueChange={(selectedValue) => filter({ sls: selectedValue })}><option value="">Semua SLS</option>{sls.data?.rows.map(row => <option key={row.code || 'empty'} value={row.code || ''}>{row.label || row.code}</option>)}</SearchSelect></label></div><p className="muted small">Kartu dan grafik mengikuti wilayah assignment yang dipilih. UB memakai kode assignment sendiri, sehingga hasilnya dapat kosong.</p></Card>
    <div className="dashboard-columns"><Card><div className="card-heading"><div><div className="eyebrow">SEBARAN WILAYAH</div><h2>Assignment menurut kecamatan</h2><p>Wilayah assignment UMKM, termasuk kode khusus</p></div><Badge>UMKM</Badge></div><BarChart data={regions} onClick={canDetail ? regionClick : undefined} label="Assignment UMKM menurut kecamatan"/><div className="card-foot">Unit: assignment · {canDetail ? 'Klik batang untuk membuka daftar tersaring.' : 'Akses pembaca agregat.'}</div></Card><div className="dashboard-side"><Card className="digital-card"><div className="eyebrow">DIGITALISASI USAHA</div><h2>Terhubung ke internet</h2><p>Proporsi dari jawaban yang valid</p>{digital.map(metric => { const row = metric.rows[0]; return <div className="digital-stat" key={metric.metric_id}><div><span>{metric.metric_id.startsWith('ub') ? 'Usaha besar · UB' : 'UMKM'}</span><strong>{number(row?.percentage)}{row?.percentage != null && <small>%</small>}</strong></div><div className="progress-track"><span style={{ width: (row?.percentage || '0') + '%' }}/></div><p>{number(row?.numerator)} dari {number(row?.denominator)} respons valid</p></div>; })}<Button variant="ghost" onClick={() => void navigate({ to: '/usaha', search: { tab: 'ringkasan', section: 'komposisi' } })}>Lihat ringkasan usaha<ArrowRight size={16}/></Button></Card></div></div>
    <Notice>Ringkasan bersifat deskriptif atas data yang tersedia. Jumlah keluarga, anggota, BKU, UMKM, dan UB tidak dijumlahkan menjadi satu populasi unik.</Notice>
  </>;
}
