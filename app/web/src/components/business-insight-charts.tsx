import {useEffect,useRef,useState} from 'react'
import {ArrowUpRight} from 'lucide-react'
import {Pagination} from './pagination'
import {init,use as register,type ECharts} from 'echarts/core'
import {PieChart,TreemapChart} from 'echarts/charts'
import {TooltipComponent} from 'echarts/components'
import {SVGRenderer} from 'echarts/renderers'
import {Card} from './ui/card'
import {number} from '@/lib/utils'
import type {Metric} from '@/lib/api'

register([PieChart,TreemapChart,TooltipComponent,SVGRenderer])
const colors=['#bb4a18','#287d82','#e9a15f','#65578d','#65a4a0','#687d98','#9a88b1','#a48a45','#adc0d1','#74804e','#d4bf82','#b4bf8c']
export type InsightDatum={name:string;value:number|null;code?:string}
export const compactNumber=(value:unknown)=>value==null?'—':new Intl.NumberFormat('id-ID',{maximumFractionDigits:1}).format(Number(value))
function datumColor(d:InsightDatum,index:number){return d.code?.startsWith('__')?'#98a5b0':colors[d.code&&/^[A-V]$/.test(d.code)?(d.code.charCodeAt(0)-65)%colors.length:index%colors.length]}

export function Composition({data,label,type='donut',onSelect,showPercentages=false,sectorLayout=false}:{data:InsightDatum[];label:string;type?:'donut'|'treemap';onSelect?:(code:string)=>void;showPercentages?:boolean;sectorLayout?:boolean}){
  const host=useRef<HTMLDivElement>(null)
  const chartRef=useRef<ECharts|null>(null)
  const [page,setPage]=useState(1);const [pageSize,setPageSize]=useState(10)
  const withheld=data.some(d=>d.value==null)
  const hasValue=data.some(d=>(d.value??0)>0)
  const total=withheld?null:data.reduce((sum,d)=>sum+(d.value??0),0)
  function percentage(value:number|null){return showPercentages&&total!=null&&total>0&&value!=null?compactNumber(value/total*100)+'%':null}
  useEffect(()=>{
    if(!host.current||withheld||!hasValue)return
    const chart:ECharts=init(host.current,undefined,{renderer:'svg'})
    chartRef.current=chart
    const values=data.map((d,i)=>({...d,id:d.code||d.name,share:showPercentages&&total?compactNumber((d.value??0)/total*100)+'%':null,itemStyle:{color:datumColor(d,i)}}))
    chart.setOption({animation:false,tooltip:{trigger:'item',renderMode:'richText',formatter:(p:{name:string;value:number;data:{share?:string}})=>p.name+'\n'+number(p.value)+(p.data.share?' · '+p.data.share:'')},series:type==='donut'?[{
      type:'pie',radius:['57%','81%'],center:['50%','50%'],avoidLabelOverlap:true,label:{show:false},labelLine:{show:false},itemStyle:{borderColor:'#fff',borderWidth:3,borderRadius:5},data:values,
    }]:[{
      type:'treemap',roam:false,nodeClick:false,breadcrumb:{show:false},left:0,right:0,top:0,bottom:0,visibleMin:1,
      itemStyle:{borderColor:'#fff',borderWidth:2,gapWidth:2,borderRadius:5},label:{show:true,color:'#fff',fontSize:13,formatter:(p:{data:{code?:string;share?:string};value:number})=>(p.data.code||'Lainnya')+'\n'+number(p.value)+(p.data.share?'\n'+p.data.share:'')},data:values,
    }]})
    chart.on('click',p=>{const d=p.data as InsightDatum;if(d.code)onSelect?.(d.code)})
    const resize=new ResizeObserver(()=>chart.resize());resize.observe(host.current)
    return()=>{resize.disconnect();chart.dispose();chartRef.current=null}
  },[data,type,onSelect,withheld,hasValue,showPercentages,total])
  function highlight(index?:number){chartRef.current?.dispatchAction({type:'downplay',seriesIndex:0});if(index!=null)chartRef.current?.dispatchAction({type:'highlight',seriesIndex:0,dataIndex:index})}
  const currentPage=Math.min(page,Math.max(1,Math.ceil(data.length/pageSize)))
  const visible=data.slice((currentPage-1)*pageSize,currentPage*pageSize)
  return <div className={'insight-composition insight-composition-'+type+(sectorLayout?' sector-composition':'')}>
    <div className="composition-plot">
    {withheld?<p className="insight-empty" role="status">Sebagian nilai ditahan. Proporsi tidak digambarkan.</p>:!hasValue?<p className="insight-empty">Belum ada data untuk komposisi ini.</p>:<div className="insight-chart" ref={host} role="img" aria-label={label} aria-description={data.map(d=>d.name+': '+number(d.value)+(percentage(d.value)?' · '+percentage(d.value):'')).join('; ')}/>}
    {sectorLayout&&!withheld&&hasValue&&<div className="sector-donut-total"><span>Total usaha</span><strong>{number(total)}</strong><small>{data.filter(d=>(d.value??0)>0&&/^[A-V]$/.test(d.code||'')).length} sektor</small></div>}
    </div>
    {sectorLayout?<div className="sector-breakdown"><div className="sector-list-heading"><span>Sektor lapangan usaha</span><span>Jumlah / Persentase</span></div><div className="sector-list">{visible.map((d,i)=>{
      const index=(currentPage-1)*pageSize+i;const navigable=!!onSelect&&/^[A-V]$/.test(d.code||'');const share=percentage(d.value)
      return <button type="button" className="sector-row" key={d.code||d.name} disabled={!navigable} onMouseEnter={()=>highlight(index)} onMouseLeave={()=>highlight()} onFocus={()=>highlight(index)} onBlur={()=>highlight()} onClick={()=>d.code&&onSelect?.(d.code)} aria-label={d.name+', '+number(d.value)+(share?', '+share:'')}>
        <span className="sector-code" style={{color:datumColor(d,index),borderColor:datumColor(d,index)}}>{d.code?.startsWith('__')?'—':d.code}</span>
        <span className="sector-row-main"><span className="sector-name">{d.name.replace(/^[A-V]\s*[·-]\s*/, '')}</span>{share&&<span className="sector-share-track"><i style={{width:(d.value??0)/total!*100+'%',background:datumColor(d,index)}}/></span>}</span>
        <span className="sector-row-value"><strong>{number(d.value)}</strong>{share&&<small className="insight-share">{share}</small>}</span>{navigable?<ArrowUpRight size={14} className="sector-open"/>:<span/>}
      </button>
    })}</div>{data.length>10&&<Pagination page={currentPage} pageSize={pageSize} total={data.length} label="Sektor per halaman" onPage={setPage} onPageSize={size=>{setPageSize(size);setPage(1)}}/>}</div>:<div className="insight-legend">{data.map((d,i)=><div key={d.code||d.name}><span className="insight-swatch" style={{background:datumColor(d,i)}}/><span title={d.name}>{d.name}</span><strong>{number(d.value)}{percentage(d.value)&&<small className="insight-share">{percentage(d.value)}</small>}</strong></div>)}</div>}
  </div>
}

export function RateCard({metric,title,detail}:{metric:Metric;title:string;detail?:string}){
  const row=metric.rows[0];const value=row?.value==null?null:Number(row.value)
  return <Card className="insight-rate-card"><div><h3>{title}</h3>{detail&&<p>{detail}</p>}</div><div className="insight-rate-body">
    <div className={'insight-gauge '+(value==null?'insight-gauge-empty':'')} style={value==null?undefined:{background:`conic-gradient(#b74712 ${Math.max(0,Math.min(100,value))*3.6}deg, #edf1f4 0deg)`}} role="img" aria-label={title+': '+(value==null?'Tidak tersedia / ditahan':compactNumber(value)+' persen')}><strong>{compactNumber(value)}{value!=null&&<small>%</small>}</strong></div>
    <div><strong>{number(row?.numerator)} <span>dari {number(row?.denominator)}</span></strong><p>jawaban valid</p>{row?.suppressed&&<small>Nilai ditahan.</small>}</div>
  </div></Card>
}

export function BandPlot({data,label}:{data:InsightDatum[];label:string}){
  const max=Math.max(1,...data.map(d=>d.value??0))
  return <div className="insight-band-plot" role="img" aria-label={label} aria-description={data.map(d=>d.name+': '+number(d.value)).join('; ')}>{data.map(d=><div key={d.name}><span>{d.name}</span><div className="insight-dot-track">{d.value!=null&&<i style={{left:`${Math.max(0,d.value)/max*94}%`}}/>}</div><strong>{number(d.value)}</strong></div>)}</div>
}
