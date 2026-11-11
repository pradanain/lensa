let csrf=''
export function setCsrf(value:string) {csrf=value}

const messages:Record<string,string>={
  LOGIN_REQUIRED:'Silakan masuk untuk melanjutkan.',SESSION_EXPIRED:'Sesi berakhir. Silakan masuk kembali.',
  LOGIN_FAILED:'Nama pengguna atau kata sandi belum sesuai.',LOGIN_RATE_LIMIT:'Terlalu banyak percobaan. Coba kembali dalam lima menit.',
  PASSWORD_MINIMUM_12_CHARACTERS:'Gunakan kata sandi minimal 12 karakter.',CSRF_REQUIRED:'Sesi keamanan perlu dimuat ulang.',
  DETAIL_ACCESS_REQUIRED:'Akun ini hanya memiliki akses agregat.',ADMIN_REQUIRED:'Fitur ini khusus administrator.',
  USERNAME_ALREADY_EXISTS:'Nama pengguna sudah digunakan.',INVALID_REQUEST:'Periksa kembali format isian.',
  ROSTER_KEY_NOT_AVAILABLE:'Roster ini tidak tersedia pada versi yang dipilih.',QUESTIONNAIRE_VERSION_NOT_AVAILABLE:'Versi kuesioner tidak tersedia.',
  INTERNAL_ERROR_NO_SOURCE_VALUES_LOGGED:'Data belum dapat dimuat. Coba kembali atau periksa layanan lokal.',
}
export class ApiError extends Error {constructor(public status:number,public code:string){super(messages[code]||'Permintaan belum dapat diproses.')}}

export async function downloadXlsx(path:string,body:unknown,filename:string){
  const response=await fetch('/api/v1'+path,{method:'POST',credentials:'same-origin',cache:'no-store',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify(body)})
  if(!response.ok){const data=await response.json();throw new ApiError(response.status,data.detail||'REQUEST_FAILED')}
  const blob=await response.blob();const url=URL.createObjectURL(blob)
  try{const anchor=document.createElement('a');anchor.href=url;anchor.download=filename;document.body.appendChild(anchor);anchor.click();anchor.remove()}finally{setTimeout(()=>URL.revokeObjectURL(url),1000)}
}

export async function api<T>(path:string,body?:unknown,method?:string,options?:{signal?:AbortSignal}):Promise<T> {
  const response=await fetch('/api/v1'+path,{
    method:method||(body===undefined?'GET':'POST'),credentials:'same-origin',cache:'no-store',signal:options?.signal,
    headers:{'Content-Type':'application/json',...(body!==undefined||method?{'X-CSRF-Token':csrf}:{})},
    ...(body===undefined?{}:{body:JSON.stringify(body)}),
  })
  const data=await response.json()
  if(!response.ok){if(response.status===401 && !path.startsWith('/auth/'))window.dispatchEvent(new Event('portal-session-expired'));throw new ApiError(response.status,data.detail||'REQUEST_FAILED')}
  return data as T
}

export type User={id:number|null;username:string;role:string;can_detail:boolean;can_sensitive:boolean}
export type Session={business_focus_enabled?:boolean;auth_enabled:boolean;user:User|null;csrf_token:string;setup_required:boolean}
export type MetricRow={dimensions:Record<string,unknown>;eligible_rows:number|null;numerator:number|string|null;denominator:number|null;excluded_rows:number|null;value:number|string|null;percentage:string|null;suppressed:boolean}
export type Metric={metric_id:string;grain:string[];unit:string;period:string;interpretation_limits:string;rows:MetricRow[];location_concept:string}
export type Summary={counts:Record<string,MetricRow[]>;indicators:Metric[];region:Metric;baseline:string;suppression_note:string}
export type Geo={code:string;label:string}
export type DirectoryRow={person_in_charge?:string|null;family_head?:string|null;map_coordinates?:{latitude:string;longitude:string}|null;map_status?:string;record_key:string;source:'dtd'|'ub';assignment_id:string;version:string|null;index1:string|null;title:string;status:string;status_label:string;kbli:string|null;kategori:string|null;kecamatan:string;desa:string;kecamatan_label:string;desa_label:string;sls?:string;subsls?:string;sls_label?:string|null;subsls_label?:string|null;rt?:string|null;rw?:string|null;geography_reference_status?:string;kind:string;kbli_state:string}
export type DirectoryResult={rows:DirectoryRow[];total:number;page:number;page_size:number;pages:number;grain:string}
export type Question={question_id:string;question_text:string;mapping_status:string;source_object:string|null;source_field:string|null;roster:string|null;converter:string;value:string|null;label:string|null;status:string;reference_label?:string;parse_status:string|null;unit:string;period:string;note?:string}
export type FormResult={form:'dtd'|'ub';assignment:{assignment_id:string;status_assignment:string;status_kuesioner:string;kecamatan:string;desa_kelurahan:string};version:string|null;available_versions:string[];selections:Record<string,string|null>;rosters:Record<string,{index:string;label:string}[]>;sections:{section_id:string;title:string;questions:Question[]}[];modules:{source:string;present:boolean;status:string}[];read_only:boolean;warning:string;questionnaire_version_status:string;truncated_rosters:string[]}
export type SearchState={qualified?:string;enumerated?:string;kbli_q?:string;section?:string;tab?:string;kind?:string;source?:string;kecamatan?:string;desa?:string;sls?:string;subsls?:string;status?:string;page?:number;page_size?:number;sort?:string;direction?:string;kbli_category?:string;kbli_prefix?:string;kbli_state?:string;level?:number;prefix?:string;category?:string;block?:string;index1?:string;version?:string;business?:string;member?:string;meter?:string;office?:string}
export function validateSearch(input:Record<string,unknown>):SearchState {
  const allowed=['qualified','enumerated','kbli_q','section','tab','kind','source','kecamatan','desa','sls','subsls','status','sort','direction','kbli_category','kbli_prefix','kbli_state','prefix','category','block','index1','version','business','member','meter','office']
  const output:Record<string,string|number>={}
  for(const key of allowed)if(typeof input[key]==='string' && (input[key] as string).length<=120)output[key]=input[key] as string
  for(const key of ['page','page_size','level'])if(input[key]!==undefined && Number.isFinite(Number(input[key])))output[key]=Math.max(1,Math.min(100000,Number(input[key])))
  return output
}

// Search text, including respondent names, is held only in process memory.
export const directoryMemory=new Map<string,{q:string;result?:DirectoryResult;payload?:Record<string,unknown>}>()
export let detailNavigation:{from:string;search:SearchState;scope:string;rows:DirectoryRow[];position:number;pages:number;payload:Record<string,unknown>}|null=null
export function setDetailNavigation(value:typeof detailNavigation){detailNavigation=value}
export function clearPrivateState(){directoryMemory.clear();detailNavigation=null}
