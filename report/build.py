"""Typeset the editable Markdown and the verified coverage figure, offline."""
import csv
from xml.sax.saxutils import escape
import pypdfium2 as pdfium
from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Drawing, Line, Circle, String
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph, Table, TableStyle
from analysis import HERE, compute

INK=colors.HexColor('#172D38'); TEAL=colors.HexColor('#00675E'); MUTED=colors.HexColor('#475F67'); GRID=colors.HexColor('#D3DFDF'); W=504

def figure(rows):
    d=Drawing(W,155)
    def label(x,y,text,anchor='start',size=8,col=MUTED,font='Helvetica'):
        d.add(String(x,y,text,fontName=font,fontSize=size,textAnchor=anchor,fillColor=col))
    for idx,(domain,name) in enumerate([('gsm8k','GSM8K'),('medqa','US MedQA')]):
        ss=[r for r in rows if r['domain']==domain and r['condition']=='C1']; left=30+252*idx
        x=lambda v:left+(v-.4)*207/.55
        y=lambda v:31+v*89/.35
        label(left,138,name,size=11,col=INK,font='Helvetica-Bold'); label(left,123,'Retained error (%)')
        for tick in (0,10,20,30):
            yy=y(tick/100);d.add(Line(left,yy,left+207,yy,strokeColor=GRID,strokeWidth=.5));label(left-5,yy-2,str(tick),'end')
        for tick in (40,50,60,70,80,90):label(x(tick/100),19,str(tick),'middle')
        label(left+104,5,'Actual coverage (%)','middle')
        yy=y(ss[0]['random_risk']);d.add(Line(left,yy,left+207,yy,strokeColor=MUTED,strokeWidth=1,strokeDashArray=[4,3]));label(left+205,yy+4,'Random','end',8)
        prev=None
        for r in ss:
            xx,yy=x(r['actual_coverage']),y(r['confidence_risk'])
            if prev:d.add(Line(*prev,xx,yy,strokeColor=TEAL,strokeWidth=1.6))
            d.add(Circle(xx,yy,3,strokeColor=TEAL,fillColor=TEAL));label(xx,yy-11,f"{r['target']:.0%}",'middle',8,INK);prev=(xx,yy)
    return d

styles={name:ParagraphStyle(name,fontName=font,fontSize=size,leading=leading,textColor=color) for name,font,size,leading,color in [('title','Times-Bold',26,28,INK),('h','Helvetica-Bold',14,17,TEAL),('body','Times-Roman',11.6,14.4,INK),('meta','Helvetica',9.5,12,MUTED),('caption','Helvetica',8.9,11.5,MUTED),('ref','Helvetica',10,15,INK)]}

def table(lines):
    rows=[[v.strip() for v in s.strip('|').split('|')] for s in lines if not s.startswith('| ---')];n=len(rows[0]); widths=[119,152,233] if n==3 else ([70,101,119,101,113] if rows[0][0]=='Target' else [108,91,110,85,110]); vals=[]
    for i,row in enumerate(rows):
        cells=[]
        for j,s in enumerate(row):
            st=ParagraphStyle('cell',fontName='Helvetica-Bold' if i==0 else 'Helvetica',fontSize=8.7,leading=11,textColor=colors.white if i==0 else INK,alignment=0 if j==0 or n==3 else 2);cells.append(Paragraph(escape(s),st))
        vals.append(cells)
    t=Table(vals,colWidths=widths);t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),INK),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#EFF5F4'),colors.white]),('LINEBELOW',(0,-1),(-1,-1),.7,GRID),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]));return t

def blocks(lines,chart,page):
    items=[];i=0
    while i<len(lines):
        s=lines[i].strip();i+=1
        if not s:continue
        if s.startswith('|'):
            group=[s]
            while i<len(lines) and lines[i].startswith('|'):group.append(lines[i]);i+=1
            items.append((table(group),8));continue
        if s.startswith('!['):items.append((chart,8));continue
        if s.startswith('# '):key='title';s=s[2:]
        elif s.startswith('## '):key='h';s=s[3:]
        elif s.startswith(('Figure 1.','Table 1.','Table 2.')):key='caption'
        elif s.startswith(('DSC 261','Haoxiang Qiu')):key='meta'
        elif page==4:key='ref'
        else:key='body'
        items.append((Paragraph(escape(s),styles[key]),{'title':8,'h':8,'body':10,'meta':5,'caption':8,'ref':15}[key]))
    return items

def main():
    rows=compute()
    with (HERE/'coverage-results.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=rows[0],lineterminator='\n');w.writeheader();w.writerows(rows)
    chart=figure(rows);cv=Canvas(str(HERE/'risk-coverage.pdf'),pagesize=(W+12,163),invariant=1);renderPDF.draw(chart,cv,6,4);cv.save()
    with pdfium.PdfDocument(HERE/'risk-coverage.pdf') as pdf:pdf[0].render(scale=2.2).to_pil().save(HERE/'risk-coverage.png')
    pages=(HERE/'midpoint-update.md').read_text(encoding='utf-8').split('\n---\n');assert len(pages)==4
    c=Canvas(str(HERE/'midpoint-update.pdf'),pagesize=(612,792),invariant=1);c.setTitle('Can a language-model judge identify its own grading errors?');c.setAuthor('Qiu, Du, Gu, Si and Kang')
    sections=['Study design','Confidence and review workload','Interpretation and next steps','References']
    for num,source in enumerate(pages,1):
        c.setFont('Helvetica-Bold',9);c.setFillColor(TEAL);c.drawString(54,753,'DSC 261   /   MIDTERM UPDATE');c.setFont('Helvetica',9);c.setFillColor(MUTED);c.drawRightString(558,753,sections[num-1]);c.setStrokeColor(GRID);c.line(54,744,558,744)
        y=720;items=blocks(source.splitlines(),chart,num);dims=[item.wrapOn(c,W,800)[1] for item,gap in items];total=sum(dims);gaps=sum(g for _,g in items);factor=min(1.8,(y-59-total)/gaps) if num<4 else 1
        if factor<.6:raise ValueError(f'Page {num} needs shorter copy: text={total}, gaps={gaps}, factor={factor}')
        for (item,gap),h in zip(items,dims):
            if isinstance(item,Drawing):renderPDF.draw(item,c,54,y-h)
            else:item.drawOn(c,54,y-h)
            y-=h+gap*factor
        print(f'Page {num}: final block ends at {y+items[-1][1]*factor:.0f} pt')
        c.line(54,45,558,45);c.setFont('Helvetica',8.5);c.setFillColor(MUTED);c.drawString(54,29,'Uncertainty and abstention in LLM judging');c.drawRightString(558,29,f'{num} / 4');c.showPage()
    c.save()

if __name__=='__main__':main()
