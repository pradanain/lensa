import {useEffect,useRef} from 'react'
import {init,use as registerCharts,type ECharts} from 'echarts/core'
import {BarChart as EBarChart} from 'echarts/charts'
import {GridComponent,TooltipComponent} from 'echarts/components'
import {SVGRenderer} from 'echarts/renderers'
import type {BarChartProps} from './shared'

registerCharts([EBarChart,GridComponent,TooltipComponent,SVGRenderer])
const displayMetric=(value:unknown)=>value==null?'\u2014':new Intl.NumberFormat('id-ID',{maximumFractionDigits:2}).format(Number(value))

export function BarChart({data,onClick,label='Distribusi unit'}:BarChartProps){
  const container=useRef<HTMLDivElement>(null)
  useEffect(()=>{
    if(!container.current)return
    const chart:ECharts=init(container.current,undefined,{renderer:'svg'})
    chart.setOption({animation:false,grid:{left:8,right:24,bottom:5,top:15,containLabel:true},tooltip:{trigger:'axis',axisPointer:{type:'shadow'},valueFormatter:(value:unknown)=>value==null?'Ditahan':displayMetric(Number(value))},xAxis:{type:'value',axisLabel:{color:'#667583',fontSize:11},splitLine:{lineStyle:{color:'#edf0f3'}},axisLine:{show:false}},yAxis:{type:'category',inverse:true,data:data.map(r=>r.name),axisTick:{show:false},axisLine:{show:false},axisLabel:{color:'#344f63',fontSize:12,width:125,overflow:'truncate'}},series:[{type:'bar',data:data.map(r=>r.value),barMaxWidth:21,itemStyle:{color:'#b74712',borderRadius:[0,4,4,0]},emphasis:{itemStyle:{color:'#94360c'}},label:{show:true,position:'right',color:'#344f63',fontSize:11,formatter:(params:{value:number})=>displayMetric(params.value)}}]})
    chart.on('click',params=>{const item=data[params.dataIndex];if(item&&onClick)onClick(item)})
    const resize=new ResizeObserver(()=>chart.resize());resize.observe(container.current)
    return()=>{resize.disconnect();chart.dispose()}
  },[data,onClick])
  return <div className="chart" ref={container} role="img" aria-label={label} aria-description={data.map(row=>row.name+': '+(row.value==null?'Tidak tersedia / ditahan':displayMetric(row.value))).join('; ')} style={{height:Math.max(135,data.length*28+30)}}/>
}
