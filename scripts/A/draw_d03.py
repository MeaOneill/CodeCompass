"""Readable Chinese paired-route diagrams, driven only by saved D03 results."""
import argparse,hashlib,json,math,textwrap,xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[2]
FONT='C:/Windows/Fonts/msyh.ttc'
LABEL={'u_iterable':'迭代协议检查','u_chunked_iter':'惰性分块与填充','u_chunked':'列表包装器兼容','u_windowed_iter':'滑动窗口与缺省值','u_positive_int':'类型校验对照'}
CONCEPT={'python.iterator_protocol':'迭代协议','python.keyword_presence':'参数缺省语义','boltons.wrapper_compatibility':'包装器兼容','python.type_validation':'类型校验'}


class Canvas:
 def __init__(self,w,h):
  self.w,self.h=w,h;self.im=Image.new('RGB',(w,h),'white');self.d=ImageDraw.Draw(self.im);self.bounds=[]
  self.svg=ET.Element('svg',xmlns='http://www.w3.org/2000/svg',width=str(w),height=str(h),viewBox=f'0 0 {w} {h}');ET.SubElement(self.svg,'rect',width=str(w),height=str(h),fill='white')
 def text(self,x,y,s,size=28,color='#203344'):
  font=ImageFont.truetype(FONT,size)
  for i,line in enumerate(s.split('\n')):
   yy=y+i*size*1.5;b=self.d.textbbox((x,yy),line,font=font,anchor='lt');assert 0<=b[0] and 0<=b[1] and b[2]<self.w and b[3]<self.h,(line,b)
   self.d.text((x,yy),line,font=font,fill=color,anchor='lt');self.bounds.append(b)
   t=ET.SubElement(self.svg,'text',x=str(x),y=str(yy+size*.9),fill=color,**{'font-size':str(size),'font-family':'Microsoft YaHei, sans-serif'});t.text=line
 def box(self,x,y,w,h,lines,color='#245880',fill='#f2f7fb'):
  self.d.rounded_rectangle((x,y,x+w,y+h),radius=14,fill=fill,outline=color,width=3)
  ET.SubElement(self.svg,'rect',x=str(x),y=str(y),width=str(w),height=str(h),rx='14',fill=fill,stroke=color,**{'stroke-width':'3'})
  assert len(lines)*36<h-14
  for i,line in enumerate(lines):
   size=27 if i==0 else 24
   assert self.d.textlength(line,font=ImageFont.truetype(FONT,size))<w-30,line
   self.text(x+15,y+15+i*36,line,size,color)
 def arrow(self,x,y,end):
  self.d.line((x,y,end,y),fill='#4c687d',width=3);tri=[(end,y),(end-15,y-8),(end-15,y+8)];self.d.polygon(tri,fill='#4c687d')
  ET.SubElement(self.svg,'line',x1=str(x),y1=str(y),x2=str(end),y2=str(y),stroke='#4c687d',**{'stroke-width':'3'});ET.SubElement(self.svg,'polygon',points=' '.join(f'{a},{b}' for a,b in tri),fill='#4c687d')
 def save(self,out,name):
  self.im.save(out/(name+'.png'),dpi=(300,300));ET.indent(self.svg);(out/(name+'.svg')).write_bytes(ET.tostring(self.svg,encoding='utf-8',xml_declaration=True))
  return {'figure_id':name,'size_px':[self.w,self.h],'dpi':300,'text_bounds_checked':len(self.bounds),'review':'pending'}


def row(c,record,y):
 p=record['plan'];method='B0 固定文档顺序' if record['method']=='B0' else '初版闭包增量贪心'
 c.text(65,y+15,method,28);c.text(65,y+65,'代理成本 '+str(p['estimated_cost']),29)
 c.text(65,y+115,'结构可行' if p['status']=='FEASIBLE' else '未找到完整可行路线',25,'#245880' if p['status']=='FEASIBLE' else '#a63c28')
 if not p['ordered_units']:
  c.box(440,y,1910,210,['空路线：固定顺序第一项就超出预算','本次选入材料的代理成本为 0；这是固定前缀的截断结果','没有声称任务成功'],color='#a63c28',fill='#fff4f0');return
 for i,uid in enumerate(p['ordered_units']):
  x=440+i*660;s=record['sources'][uid][0]
  reason='固定文档前缀' if record['method']=='B0' else '目标缺口材料'
  c.box(x,y,590,210,[LABEL[uid],uid,f'iterutils.py L{s["start_line"]}-{s["end_line"]}',f'共同代理成本 {s["end_line"]-s["start_line"]+1}',f'选入：{reason}'])
  if i:c.arrow(x-70,y+105,x)


def main():
 ap=argparse.ArgumentParser();ap.add_argument('--run-id',required=True);a=ap.parse_args();source=ROOT/'experiments/A'/a.run_id
 summary=json.loads((source/'summary.json').read_text(encoding='utf-8'));out=ROOT/'report_materials/A/A-D03'/a.run_id;out.mkdir(parents=True,exist_ok=True)
 records=[]
 for tid,title in [('task_001','任务1：给惰性分块增加 count 限制'),('task_002','任务2：滑动窗口 size 边界防护')]:
  c=Canvas(2500,1760);c.text(65,40,title,46);c.text(65,120,'开发短测｜真实固定源码任务 + 明确模拟画像｜不是学习效果或真人成功率',30)
  for profile,top,label in [('sim_unknown',210,'模拟画像一：没有独立能力证据'),('sim_evidence',890,'模拟画像二：四类基础知识各有10条模拟独立题通过记录')]:
   c.text(65,top,label,31)
   for method,y in [('B0',top+60),('B2_initial',top+340)]:
    r=next(r for r in summary['cases'] if r['task_id']==tid and r['profile_id']==profile and r['method']==method and 'failure' not in r['case_id']);row(c,r,y)
   note='未知能力不跳过；两方法使用相同材料和预算 100。' if profile=='sim_unknown' else '证据覆盖概念：迭代协议、缺省语义、包装器兼容、类型校验；不表示真人已掌握。'
   c.text(65,top+585,note,27)
  c.text(65,1555,'每个节点都有固定源码行号；完整选择原因与证据ID见本run的逐步复核表。',28)
  c.text(65,1610,'真实教学边仍为 soft；诊断未实现。代理成本 = 固定源码闭区间行数，不能换算为分钟。',27)
  c.text(65,1660,'boltons 4e5faa3d7e4008d89e0d8bf1ea87b6d9a061a16d | '+a.run_id,25)
  records.append(c.save(out,tid+'_paired_routes'))
 c=Canvas(2500,1300);c.text(65,40,'失败案例：任务1只给20代理单位预算',46)
 c.text(65,120,'模拟：无能力证据｜两方法均未找到完整路线｜NO_FEASIBLE_FOUND 不是无解证明',30)
 for method,y in [('B0',270),('B2_initial',550)]:
  r=next(r for r in summary['cases'] if r['case_id']=='task_001-budget_failure' and r['method']==method);row(c,r,y)
 r=next(r for r in summary['cases'] if r['case_id']=='task_001-budget_failure' and r['method']=='B2_initial')
 c.box(65,850,2300,220,['必须保留的未完成项',f'本次只覆盖 {len(r["plan"]["coverage"]["covered_concept_ids"])} / {len(r["plan"]["coverage"]["required_concept_ids"])} 个目标概念；还有目标缺口。','完整目标材料的增量成本超过剩余预算，不把部分建议记为成功。','另保留一个合成反例：贪心未找到路线，但已知另一条路线可行。'],color='#a63c28',fill='#fff4f0')
 c.text(65,1135,'源码版本：4e5faa3d7e4008d89e0d8bf1ea87b6d9a061a16d｜完整失败原因在原始结果。',27)
 c.text(65,1190,'开发短测；无真人学习数据；不要求算法必须胜过基线才能通过工程G1。',27)
 records.append(c.save(out,'failure_budget_route'))
 meta={'run_id':a.run_id,'source_json':(source/'summary.json').relative_to(ROOT).as_posix(),'source_sha256':hashlib.sha256((source/'summary.json').read_bytes()).hexdigest(),
       'script':'scripts/A/draw_d03.py','font':FONT,'font_sha256':hashlib.sha256(Path(FONT).read_bytes()).hexdigest(),'seed':None,'kind':'development_route_cases_not_effect_results',
       'command':['python','scripts/A/draw_d03.py','--run-id',a.run_id],'figures':records}
 (out/'render_config.json').write_bytes((json.dumps(meta,ensure_ascii=False,indent=2)+'\n').encode())
 print(json.dumps(records,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
