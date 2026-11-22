"""Render the editable Markdown as a compact, two-column course paper."""
from pathlib import Path
from xml.sax.saxutils import escape
import re
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (BaseDocTemplate,Frame,PageTemplate,Paragraph,NextPageTemplate,PageBreak,Table,TableStyle,KeepTogether,Spacer)
from reportlab.pdfgen.canvas import Canvas
from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Drawing
import sys
D=Path(__file__).resolve().parent
sys.path.insert(0,str(D.parent))

W,H=612,792; M=45; G=18; CW=(W-2*M-G)/2
INK=colors.HexColor('#18232b'); MUTED=colors.HexColor('#44535a'); LINE=colors.HexColor('#a9b3b7')
def st(name,face,size,lead,**kw): return ParagraphStyle(name,fontName=face,fontSize=size,leading=lead,textColor=INK,**kw)
body=st('body','Times-Roman',9.75,11.45,alignment=TA_JUSTIFY,spaceAfter=3.7,allowWidows=0,allowOrphans=0)
h2=st('section','Helvetica-Bold',10.2,12,spaceBefore=7,spaceAfter=4,keepWithNext=True)
h3=st('subsection','Times-BoldItalic',10.2,12.2,spaceBefore=5,spaceAfter=3,keepWithNext=True)
cap=st('cap','Times-Italic',8.75,10.3,spaceBefore=3,spaceAfter=5)
cell=st('cell','Times-Roman',8.45,9.8); head=st('head','Times-Bold',8.35,9.65)
ref=st('ref','Times-Roman',9.5,12,spaceAfter=8,leftIndent=15,firstLineIndent=-15)
def fmt(s):
    s=re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',escape(s.strip()))
    return re.sub(r'(https?://[^\s]+)',r'<link href="\1" color="#274e60">\1</link>',s)
def para(s,style=body):return Paragraph(fmt(s),style)
def frames(prefix,top):return [Frame(x,42,CW,top-42,id=prefix+str(i),leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0) for i,x in enumerate((M,M+CW+G))]
def furniture(c,d):
    c.saveState();c.setFillColor(MUTED);c.setFont('Helvetica',8)
    if d.page>1:
        c.drawString(M,762,'DSC 261  /  Responsible Data Science');c.drawRightString(W-M,762,'Can a language-model judge identify its own grading errors?');c.setStrokeColor(LINE);c.line(M,755,W-M,755)
    c.setFont('Times-Roman',9);c.drawCentredString(W/2,25,str(d.page));c.restoreState()
def front(c,d):
    furniture(c,d);c.saveState();c.setFillColor(INK);c.setFont('Helvetica',8.5);c.drawCentredString(W/2,755,'DSC 261   /   RESPONSIBLE DATA SCIENCE   /   FINAL REPORT');c.setFont('Times-Bold',18.5);c.drawCentredString(W/2,727,'Can a Language-Model Judge Identify Its Own Grading Errors?');c.setFont('Times-Roman',11);c.drawCentredString(W/2,706,'Haoxiang Qiu, Yuguo Du, Edith Gu, Lucia Si, Wenkai Kang');c.setFont('Times-Italic',9.5);c.drawCentredString(W/2,691,'University of California San Diego');c.setStrokeColor(LINE);c.line(M,679,W-M,679);c.restoreState()
def tbl(lines):
    parts=[[v.strip() for v in line.strip('|').split('|')] for line in lines if not line.startswith('| ---')];n=len(parts[0]);assert all(len(r)==n for r in parts)
    if n==4: weights=[.34,.20,.23,.23]
    elif parts[0][0]=='Condition': weights=[.46,.27,.27]
    elif n==3: weights=[.23,.36,.41]
    elif parts[0][0]=='Target': weights=[.13,.19,.245,.19,.245]
    elif parts[0][0]=='Prompt': weights=[.21,.17,.225,.17,.225]
    else:weights=[.28,.19,.14,.20,.19]
    data=[[para(v,head if i==0 else cell) for v in row] for i,row in enumerate(parts)]
    table=Table(data,colWidths=[CW*w for w in weights],hAlign='LEFT',repeatRows=1);table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LINEABOVE',(0,0),(-1,0),.8,INK),('LINEBELOW',(0,0),(-1,0),.45,INK),('LINEBELOW',(0,-1),(-1,-1),.8,INK),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f3f5f5')]),('LEFTPADDING',(0,0),(-1,-1),2),('RIGHTPADDING',(0,0),(-1,-1),2),('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),2)]));return table

def workload_plot():
    """Two vertically stacked vector panels with column-sized, 8 pt labels."""
    import csv
    from reportlab.graphics.shapes import Line, String, Circle
    rows=list(csv.DictReader((D.parent/'coverage-results.csv').open(encoding='utf8')))
    graph=Drawing(CW,204);accent=colors.HexColor('#126263')
    def label(x,y,s,size=8,anchor='start',font='Helvetica'):
        graph.add(String(x,y,s,fontName=font,fontSize=size,textAnchor=anchor,fillColor=INK))
    x0,x1=30,CW-13
    def xp(c):return x0+(x1-x0)*(c-.35)/.65
    for domain,y0,title in [('gsm8k',122,'GSM8K'),('medqa',39,'MedQA')]:
        vals=[r for r in rows if r['domain']==domain and r['condition']=='C1'];assert len(vals)==3
        y=lambda v:y0+v*138
        label(x0,y0+53,title,8.5,font='Helvetica-Bold')
        for tick in (0,.15,.30):
            graph.add(Line(x0,y(tick),x1,y(tick),strokeColor=LINE,strokeWidth=.3));label(x0-4,y(tick)-2.5,str(round(tick*100))+'%',7.5,'end')
        yr=y(float(vals[0]['random_risk']));graph.add(Line(x0,yr,x1,yr,strokeColor=MUTED,strokeDashArray=[3,2],strokeWidth=.9))
        pts=[(xp(float(r['actual_coverage'])),y(float(r['confidence_risk']))) for r in vals]
        for (xa,ya),(xb,yb) in zip(pts,pts[1:]):graph.add(Line(xa,ya,xb,yb,strokeColor=accent,strokeWidth=1.25))
        for (x,yv),r in zip(pts,vals):
            graph.add(Circle(x,yv,2.2,fillColor=accent,strokeColor=accent));label(x,yv-11,'%d%%'%round(100*float(r['target'])),7.5,'middle')
    for tick in (.4,.6,.8,1.):label(xp(tick),28,'%d%%'%round(tick*100),7.5,'middle')
    label((x0+x1)/2,16,'Actual share retained',8,'middle');label(x0,190,'Retained error rate',8.5);graph.add(Line(x0,3,x0+13,3,strokeColor=accent));label(x0+16,1,'Confidence',7.5);graph.add(Line(x0+83,3,x0+96,3,strokeColor=MUTED,strokeDashArray=[3,2]));label(x0+100,1,'Matched random',7.5);return graph

def cost_plot():
    """Plot the observed correctness and output-token cost of both prompt pairs."""
    import csv
    from reportlab.graphics.shapes import Circle, Line, Rect, String
    with (D/'paired-results.csv').open(encoding='utf8') as stream:
        rows = list(csv.DictReader(stream))
    graph = Drawing(CW, 205)
    x = lambda ratio: 28 + (CW-42)*ratio
    palette = {'C1': colors.HexColor('#126263'), 'C2': colors.HexColor('#8a492b')}
    for domain, bottom, title in [('gsm8k',123,'GSM8K'), ('medqa',40,'MedQA')]:
        y = lambda count: bottom + (count-95)*1.04
        graph.add(String(28,bottom+54,title,fontName='Helvetica-Bold',fontSize=8.5))
        for count in (100,120,140):
            graph.add(Line(28,y(count),CW-14,y(count),strokeColor=LINE,strokeWidth=.3))
            graph.add(String(23,y(count)-2,str(count),fontName='Helvetica',fontSize=7.5,textAnchor='end'))
        for pair, color in palette.items():
            group = [r for r in rows if r['domain']==domain and r['base']==pair]
            row = group[0]
            cost = int(row['thinking_only_tokens'])
            points = [(int(row['first_tokens'])/cost, int(row['first_correct']))]
            points += sorted((int(r['policy_tokens'])/cost,int(r['final_correct'])) for r in group)
            for a,b in zip(points,points[1:]):
                graph.add(Line(x(a[0]),y(a[1]),x(b[0]),y(b[1]),strokeColor=color,strokeWidth=.8))
            for ratio,count in points:
                px,py=x(ratio),y(count)
                marker = Circle(px,py,2.1) if pair=='C1' else Rect(px-2,py-2,4,4)
                marker.fillColor=color;marker.strokeColor=color;graph.add(marker)
            # Standalone thinking is a separate baseline (no first pass).
            px,py=x(1),y(int(row['thinking_only_correct']))
            marker=Circle(px,py,2.5) if pair=='C1' else Rect(px-2.5,py-2.5,5,5)
            marker.fillColor=None;marker.strokeColor=color;graph.add(marker)
    for tick in (0,.25,.5,.75,1):
        graph.add(String(x(tick),30,f'{tick:.0%}',fontName='Helvetica',fontSize=7.5,textAnchor='middle'))
    graph.add(String(CW/2,15,'Output tokens relative to thinking on every item',fontName='Helvetica',fontSize=8,textAnchor='middle'))
    graph.add(String(28,193,'Correct verdicts out of 140',fontName='Helvetica',fontSize=8))
    return graph

def main():
    from workflow import export
    export(D.parent)
    text=(D/'final-report.md').read_text(encoding='utf8');lines=text[text.index('## Abstract'):].splitlines();out=[];i=0;refs=False
    while i<len(lines):
        line=lines[i].strip();i+=1
        if not line:continue
        if line=='## References':
            refs=True;out.extend([NextPageTemplate('refs'),PageBreak(),para('REFERENCES',h2)]);continue
        if line.startswith('## '):out.append(para(line[3:].upper(),h2));continue
        if line.startswith('### '):out.append(para(line[4:],h3));continue
        if line.startswith('!['):
            is_cost = 'paired-cost.png' in line
            from workflow import workflow
            graph = workflow(True,CW) if 'workflow-final' in line else (cost_plot() if is_cost else workload_plot())
            while i<len(lines) and not lines[i].strip():i+=1
            assert lines[i].startswith('Figure ');out.append(KeepTogether([graph,para(lines[i],cap)]));i+=1;continue
        if line.startswith('Table ') or line.startswith('|'):
            group=[];rows=[]
            if line.startswith('Table '):group.append(para(line,cap))
            else:rows.append(line)
            while i<len(lines) and not lines[i].strip():i+=1
            while i<len(lines) and lines[i].startswith('|'):rows.append(lines[i]);i+=1
            assert rows;group.extend([tbl(rows),Spacer(1,5)]);out.append(KeepTogether(group));continue
        out.append(para(line,ref if refs else body))
    doc=BaseDocTemplate(str(D/'final-report.pdf'),pagesize=(W,H),title='Can a Language-Model Judge Identify Its Own Grading Errors?',author='DSC 261 project team',allowSplitting=1)
    doc.addPageTemplates([PageTemplate('first',frames('first',666),onPage=front,autoNextPageTemplate='paper'),PageTemplate('paper',frames('body',745),onPage=furniture),PageTemplate('refs',[Frame(M,42,W-2*M,703,id='refs',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)],onPage=furniture)])
    import pypdfium2 as pdfium
    image_pdf = pdfium.PdfDocument(renderPDF.drawToString(cost_plot()))
    image_pdf[0].render(scale=3).to_pil().save(D/'paired-cost.png')
    doc.build(out,canvasmaker=lambda *a,**kw: Canvas(*a,**dict(kw,invariant=1)))
if __name__=='__main__':main()
