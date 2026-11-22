"""Small vector study maps shared by the report renderers."""
from pathlib import Path
from reportlab.graphics.shapes import Drawing, Rect, Line, String, Polygon
from reportlab.lib import colors
from reportlab.graphics import renderPDF

def workflow(final=False, width=251):
    steps=[('Construct fixed candidates','200 math + 200 medical questions'),('Collect four sets of verdicts','One model; thinking x rubric'),('Evaluate error selection','Frozen confidence rule vs matched random')]
    if final: steps.append(('Replay selected second judgments','Corrected / new errors + output tokens'))
    height=len(steps)*32-7
    d=Drawing(width,height)
    ink=colors.HexColor('#18232b'); teal=colors.HexColor('#126263')
    for i,(title,detail) in enumerate(steps):
        y=height-(i+1)*32+7
        d.add(Rect(0,y,width,25,fillColor=colors.HexColor('#edf3f3'),strokeColor=colors.HexColor('#bfd0d0'),strokeWidth=.5))
        d.add(String(width/2,y+14,title,fontName='Helvetica-Bold',fontSize=8,textAnchor='middle',fillColor=ink))
        d.add(String(width/2,y+4,detail,fontName='Helvetica',fontSize=7,textAnchor='middle',fillColor=ink))
        if i<len(steps)-1:
            d.add(Line(width/2,y,width/2,y-4,strokeColor=teal,strokeWidth=.6))
            d.add(Polygon([width/2-2,y-3,width/2+2,y-3,width/2,y-6],fillColor=teal,strokeColor=None))
    return d

def export(folder):
    import pypdfium2 as pdfium
    for final,name in [(False,'workflow-midterm'),(True,'workflow-final')]:
        raw=renderPDF.drawToString(workflow(final))
        (folder/(name+'.pdf')).write_bytes(raw)
        with pdfium.PdfDocument(raw) as doc:
            doc[0].render(scale=3).to_pil().save(folder/(name+'.png'))
