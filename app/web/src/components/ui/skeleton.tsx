import type {CSSProperties} from 'react'

type Variant='card'|'table'|'chart'|'form'|'filters'|'dashboard'
function Block({width='100%',height=12}:{width?:string;height?:number}){
  return <span className="skeleton-block" style={{width,height} as CSSProperties}/>
}
export function LoadingSkeleton({variant='card',label='Memuat data...'}:{variant?:Variant;label?:string}){
  return <div className={'loading-skeleton skeleton-'+variant} role="status" aria-label={label} aria-busy="true">
    <span className="sr-only">{label}</span>
    <div aria-hidden="true">
      {variant==='table'?<><div className="skeleton-table-head">{[40,22,18,10].map(width=><Block key={width} width={width+'%'}/>)}</div>{Array.from({length:6},(_,i)=><div className="skeleton-table-row" key={i}><div><Block width={i%2?'76%':'90%'} height={13}/><Block width="48%" height={9}/></div><div><Block width="84%"/><Block width="64%" height={9}/></div><div><Block width="65%" height={24}/></div><Block width="65%" height={30}/></div>)}<div className="skeleton-table-foot"><Block width="25%" height={10}/><Block width="145px" height={32}/></div></>:
      variant==='filters'?<>{[0,1,2].map(i=><div className="skeleton-field" key={i}><Block width="45%" height={9}/><Block height={38}/></div>)}</>:
      variant==='form'?<><Block width="40%" height={24}/><div className="skeleton-form-grid">{Array.from({length:6},(_,i)=><div className="skeleton-field" key={i}><Block width={i%2?'65%':'45%'}/><Block height={40}/></div>)}</div></>:
      variant==='dashboard'?<><div className="skeleton-stat-grid">{[0,1,2,3].map(i=><div key={i}><Block width="35%" height={25}/><Block width="70%"/></div>)}</div><div className="skeleton-dashboard-chart"><Block width="42%" height={18}/><Bars/></div></>:
      variant==='chart'?<><Block width="50%" height={18}/><Bars/></>:
      <><Block width="52%" height={17}/><div className="skeleton-card-values">{[0,1].map(i=><div key={i}><Block width="72%"/><Block width="40%" height={25}/><Block height={7}/></div>)}</div></>}
    </div>
  </div>
}
function Bars(){return <div className="skeleton-chart-bars">{[74,52,90,38,62].map((width,i)=><div key={i}><Block width="23%" height={10}/><Block width={width+'%'} height={18}/></div>)}</div>}
