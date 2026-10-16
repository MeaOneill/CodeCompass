"""D02 engineering diagrams: identical coordinates drive native SVG and PNG."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]
COLORS={'static':'#245880','teaching':'#9a4a12','model':'#72408f','unknown':'#555b64'}


class Canvas:
    def __init__(self,w,h):
        self.w,self.h=w,h
        self.image=Image.new('RGB',(w,h),'white');self.draw=ImageDraw.Draw(self.image)
        self.svg=ET.Element('svg',xmlns='http://www.w3.org/2000/svg',width=str(w),height=str(h),viewBox=f'0 0 {w} {h}')
        ET.SubElement(self.svg,'rect',x='0',y='0',width=str(w),height=str(h),fill='white')
        self.text_bounds=[]
    def text(self,x,y,text,size=26,color='#172a38'):
        font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',size)
        for i,line in enumerate(text.split('\n')):
            yy=y+i*size*1.38
            self.draw.text((x,yy),line,font=font,fill=color,anchor='lt')
            node=ET.SubElement(self.svg,'text',x=str(x),y=str(yy+size*.83),fill=color,**{'font-family':'Arial, sans-serif','font-size':str(size)});node.text=line
            bounds=self.draw.textbbox((x,yy),line,font=font,anchor='lt')
            assert bounds[0]>=0 and bounds[1]>=0 and bounds[2]<=self.w and bounds[3]<=self.h,(line,bounds)
            self.text_bounds.append(bounds)
    def box(self,x,y,w,h,lines,color='#245880',fill='#f3f7fa',size=26):
        self.draw.rounded_rectangle((x,y,x+w,y+h),radius=15,outline=color,fill=fill,width=3)
        ET.SubElement(self.svg,'rect',x=str(x),y=str(y),width=str(w),height=str(h),rx='15',fill=fill,stroke=color,**{'stroke-width':'3'})
        font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',size)
        assert all(self.draw.textlength(line,font=font)<=w-36 for line in lines.split('\n')),(lines,w)
        assert len(lines.split('\n'))*size*1.38<h-18,lines
        self.text(x+18,y+18,lines,size,color)
    def line(self,points,kind='static',arrow=True):
        color=COLORS[kind];dash={'static':None,'teaching':(14,9),'model':(3,8),'unknown':(8,8)}[kind]
        for (x1,y1),(x2,y2) in zip(points,points[1:]):
            if dash:
                length=math.hypot(x2-x1,y2-y1)
                for t in range(0,int(length),sum(dash)):
                    a,b=t/length,min(t+dash[0],length)/length
                    self.draw.line((x1+(x2-x1)*a,y1+(y2-y1)*a,x1+(x2-x1)*b,y1+(y2-y1)*b),fill=color,width=3)
            else:self.draw.line((x1,y1,x2,y2),fill=color,width=3)
        attrs={'points':' '.join(f'{x},{y}' for x,y in points),'fill':'none','stroke':color,'stroke-width':'3'}
        if dash:attrs['stroke-dasharray']=' '.join(map(str,dash))
        ET.SubElement(self.svg,'polyline',**attrs)
        if arrow:
            (x1,y1),(x2,y2)=points[-2:];angle=math.atan2(y2-y1,x2-x1)
            tri=[(x2,y2),(x2-16*math.cos(angle-.45),y2-16*math.sin(angle-.45)),(x2-16*math.cos(angle+.45),y2-16*math.sin(angle+.45))]
            self.draw.polygon(tri,fill=color);ET.SubElement(self.svg,'polygon',points=' '.join(f'{x},{y}' for x,y in tri),fill=color)
    def save(self,out,name):
        out.mkdir(parents=True,exist_ok=True)
        self.image.save(out/(name+'.png'),dpi=(300,300))
        ET.indent(self.svg);ET.ElementTree(self.svg).write(out/(name+'.svg'),encoding='utf-8',xml_declaration=True)
        return {'figure_id':name,'text_blocks_checked':len(self.text_bounds),'dimensions_px':[self.w,self.h],'dpi':300,'svg_native_vector':True,'visual_review':'pending'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-id',required=True);args=p.parse_args()
    source=ROOT/'experiments/A'/args.run_id
    g=json.loads((source/'task_001_local_graph.json').read_text(encoding='utf-8'))
    fixture=json.loads((source/'controlled_fixture.json').read_text(encoding='utf-8'))
    out=ROOT/'report_materials/A/A-D02';records=[]
    c=Canvas(2200,1390)
    c.text(65,45,'F01  CodeCompass architecture and implementation boundary',44)
    c.text(65,115,'A-D02 | task_001 | structure diagram; no learning-effect results',27)
    # Connectors first, so boxes mask line interiors.
    c.line([(470,295),(650,295)])
    c.line([(260,400),(260,500)])
    c.line([(260,680),(260,770)])
    c.line([(470,850),(550,850),(550,180),(1300,180),(1300,255),(1390,255)],'unknown')
    c.line([(1170,295),(1390,295)],'unknown')
    c.line([(1170,565),(1280,565),(1280,350),(1390,350)],'unknown')
    c.line([(1170,835),(1320,835),(1320,390),(1390,390)],'unknown')
    c.line([(1660,410),(1660,520)],'unknown')
    c.line([(1660,680),(1660,790)],'unknown')
    c.line([(1660,950),(1660,1050)],'unknown')
    c.box(65,220,405,180,'Third-party fixed source\nboltons / BSD-3-Clause\n4 original files available')
    c.box(650,220,520,180,'Support 1: source graph\nAST + source hashes: built\nTeaching candidates: pending')
    c.box(1390,220,680,190,'Main: content + order planner\nAbility / goal / prerequisite / budget\nPLANNED - no algorithm run',color='#555b64',fill='#f8f8f8')
    c.box(65,500,405,180,'B: package + read-only CLI\nBuilt and rechecked\nUI and persistence planned')
    c.box(650,490,520,170,'Support 2: learning cost\nPLANNED / proxy_cost\nReal costs remain null',color='#555b64',fill='#f8f8f8')
    c.box(65,770,405,180,'Task 001 + rubric\nReal upstream TODO\nHuman pilot not run')
    c.box(650,760,520,170,'Support 3: ability + memory\nEvidence schema available\nModel / persistence planned',color='#555b64',fill='#f8f8f8')
    c.box(1390,520,680,160,'Traceable route and feedback\nPLANNED / fixture is not a real plan',color='#555b64',fill='#f8f8f8')
    c.box(1390,790,680,160,'B independent task evaluator\nPLANNED - separate from planner score',color='#555b64',fill='#f8f8f8')
    c.box(1390,1050,680,160,'Support 4: Issue preparation\nPLANNED - no community submission',color='#555b64',fill='#f8f8f8')
    c.text(65,1030,'Team work: source provenance, contracts, task design;\nplanner mechanisms still require implementation and evidence.',27)
    c.text(65,1135,'AI: drafting / coding / self-check. Human review is pending.\nThird-party source is preserved separately and attributed.',27)
    c.text(65,1260,'Solid blue: implemented input flow. Dashed gray: planned interfaces. No API/model service is connected.',25)
    c.text(65,1310,'Source commit: '+g['commit'],24)
    records.append(c.save(out,'F01_architecture'))
    c=Canvas(2200,1460)
    c.text(65,45,'F02  Fixed-source syntax and teaching candidates',44)
    c.text(65,115,'boltons | task_001 | commit '+g['commit'],26)
    c.text(65,165,'Selection: task.source_spans functions, their module, import itertools, and call expressions inside the functions.',25)
    xs=[65,600,1135,1670];names=['chunked','chunked_iter','is_iterable','_validate_positive_int']
    for x in xs:c.line([(1100,335),(1100,395),(x+220,395),(x+220,480)])
    c.line([(750,285),(625,285)])
    c.box(65,235,560,100,'import itertools  |  L47',size=28)
    c.box(750,235,700,100,'iterutils.py :: module  [static AST]',size=28)
    for x,name in zip(xs,names):
        n=next(n for n in g['nodes'] if n['name']==name)
        sp=n['source_span']
        c.box(x,480,455,165,f'{name}\nL{sp["start_line"]}-{sp["end_line"]}\nSource span + hash verified',size=25)
    c.text(65,700,'Call syntax is located, but runtime targets are NOT inferred:',30)
    c.box(65,765,2070,135,'chunked: chunked_iter(...) at L302 | chunked_iter: is_iterable(...) at L330, _validate_positive_int(...) at L332\nThese are call_unknown records with to=null, not resolved runtime edges.',color='#555b64',fill='#f8f8f8',size=27)
    c.line([(520,1060),(720,1060)],'teaching');c.line([(1260,1060),(1460,1060)],'teaching')
    c.box(65,990,455,145,'u_iterable\nSource-backed reading unit',color=COLORS['teaching'],fill='#fff8f1')
    c.box(720,990,540,145,'u_chunked_iter\nPending teaching suggestion',color=COLORS['teaching'],fill='#fff8f1')
    c.box(1460,990,675,145,'u_chunked\nSoft only; no human approval',color=COLORS['teaching'],fill='#fff8f1')
    c.text(65,1190,'Static contains: solid blue | Teaching suggestion: dashed orange | Model candidate: dotted purple (none)',25)
    c.text(65,1240,'Imports are declarations, not runtime execution or teaching prerequisites. Full AST output includes 2 Python files.',25)
    c.text(65,1290,'Teaching edges are stored separately. No unreviewed edge enters hard constraints.',25)
    c.text(65,1360,'Structure only | source: experiments/A/'+args.run_id+' | no result metrics',24)
    records.append(c.save(out,'F02_source_graph'))
    c=Canvas(2200,1270)
    c.text(65,45,'F02 supplement  Controlled graph for task_001',44)
    c.text(65,120,'SYNTHETIC FIXTURE: shared prerequisite, alternative materials, prior mastery, and cycle detection.',27)
    for pts in [[(450,410),(700,300)],[(450,410),(700,560)],[(1150,300),(1410,410)],[(1150,560),(1410,410)]]:c.line(pts,'teaching')
    c.box(65,320,385,180,'shared: iterator\nFixture mastered concept\nNot a human learner',color=COLORS['teaching'],fill='#fff8f1',size=25)
    c.box(700,225,450,150,'material_A\nCovers chunk_behavior',color=COLORS['teaching'],fill='#fff8f1')
    c.box(700,485,450,150,'material_B\nSame concept, alternative',color=COLORS['teaching'],fill='#fff8f1')
    c.box(1410,320,660,180,'goal: compatible_count\nTwo candidate learning materials\nNo planner execution',color=COLORS['teaching'],fill='#fff8f1')
    c.line([(650,885),(1400,885)],'teaching');c.line([(1400,965),(650,965)],'teaching')
    c.box(220,835,430,180,'cycle_X\nFixture pending edge',color=COLORS['teaching'],fill='#fff8f1')
    c.box(1400,835,430,180,'cycle_Y\nFixture pending edge',color=COLORS['teaching'],fill='#fff8f1')
    c.text(65,1070,'Detected SCC: '+', '.join(fixture['cycle_components'][0])+'. Preserve for review; do not delete an edge to force a DAG.',26)
    c.text(65,1120,'All teaching edges here are fixture/soft. Proxy costs are invented only for structural tests, not measured minutes.',25)
    c.text(65,1170,'Source commit: '+g['commit']+' | task_001 | synthetic structure, not an empirical result',24)
    records.append(c.save(out,'F02_controlled_fixture'))
    config={'run_id':args.run_id,'task_id':'task_001','source_commit':g['commit'],'source_graph':(source/'task_001_local_graph.json').relative_to(ROOT).as_posix(),'fixture':(source/'controlled_fixture.json').relative_to(ROOT).as_posix(),'backend':'Python Pillow + native SVG','font':'Arial','seed':None,'evidence_type':'structure_diagram','command':['python','scripts/A/draw_d02.py','--run-id',args.run_id],'figures':records}
    write=lambda path,obj:path.write_bytes((json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode())
    write(out/'render_config.json',config)
    print(json.dumps(records,indent=2))

if __name__=='__main__':main()
