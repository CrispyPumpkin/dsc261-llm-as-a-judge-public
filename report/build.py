"""Typeset the editable Markdown and the verified coverage figure, offline."""
import csv
import pypdfium2 as pdfium
from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Drawing, Line, Circle, String
from reportlab.lib import colors
from reportlab.pdfgen.canvas import Canvas
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

def main():
    rows=compute()
    with (HERE/'coverage-results.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=rows[0],lineterminator='\n');w.writeheader();w.writerows(rows)
    chart=figure(rows);cv=Canvas(str(HERE/'risk-coverage.pdf'),pagesize=(W+12,163),invariant=1);renderPDF.draw(chart,cv,6,4);cv.save()
    with pdfium.PdfDocument(HERE/'risk-coverage.pdf') as pdf:pdf[0].render(scale=2.2).to_pil().save(HERE/'risk-coverage.png')
    from midterm_paper import render
    render(HERE)
    
if __name__=='__main__':main()
