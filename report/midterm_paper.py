"""Render the midpoint manuscript in the proposal's ACM/PVLDB course format."""
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.sax.saxutils import escape
import os
import re
import shutil
import subprocess


def manuscript(folder):
    lines = (folder / 'midpoint-update.md').read_text(encoding='utf8').splitlines()
    title, course, authors, school = [s for s in lines[:lines.index(next(s for s in lines if s.startswith('## ')))] if s]
    pages = [[]]
    for line in lines[lines.index(next(s for s in lines if s.startswith('## '))):]:
        if line == '---' or line == '## References':
            pages.append([])
        elif line.strip():
            pages[-1].append(line)
    return (title[2:], course, authors, school), pages


def blocks(lines):
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        if line.startswith('Table '):
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                if not lines[i].startswith('| ---'):
                    rows.append([v.strip() for v in lines[i].strip('|').split('|')])
                i += 1
            yield 'table', (line, rows)
        elif line.startswith('!['):
            yield 'figure', (line, lines[i])
            i += 1
        elif line.startswith('## '):
            yield 'section', line[3:]
        elif line.startswith('### '):
            yield 'subsection', line[4:]
        else:
            yield 'text', line


def tex(text):
    replacements = {'&': r'\&', '%': r'\%', '_': r'\_', '#': r'\#',
                    '−': r'\ensuremath{-}', '×': r'\ensuremath{\times}',
                    '“': '``', '”': "''"}
    return ''.join(replacements.get(c, c) for c in text)


def tex_body(lines):
    out = []
    for kind, value in blocks(lines):
        if kind == 'section':
            out.append(r'\section{' + tex(value.split(' ', 1)[1]) + '}')
        elif kind == 'subsection':
            out.append(r'\subsection*{' + tex(value) + '}')
        elif kind == 'table':
            caption, rows = value
            cols = 'l' + ('r' * (len(rows[0]) - 1))
            out += [r'\par\medskip\noindent\begin{minipage}{\linewidth}\small',
                    r'\emph{' + tex(caption) + r'}\par\smallskip',
                    r'\centering\begin{tabular*}{\linewidth}{@{\extracolsep{\fill}}' + cols + r'@{}}\toprule',
                    ' & '.join(r'\textbf{' + tex(s) + '}' for s in rows[0]) + r'\\\midrule']
            out += [' & '.join(map(tex, row)) + r'\\' for row in rows[1:]]
            out += [r'\bottomrule\end{tabular*}\end{minipage}\par\medskip']
        elif kind == 'figure':
            image_line, value = value
            if 'workflow-' in image_line:
                out += [r'\par\medskip\noindent\begin{minipage}{\linewidth}\centering', r'\includegraphics[width=\linewidth]{workflow-midterm.pdf}\par', r'\raggedright\small\emph{' + tex(value) + r'}\end{minipage}\par\medskip']
                continue
            out += [r'\par\medskip\noindent\begin{minipage}{\linewidth}\centering',
                    r'\includegraphics[width=.89\linewidth,trim=0 0 256bp 0,clip]{risk-coverage.pdf}\par',
                    r'\includegraphics[width=.89\linewidth,trim=254bp 0 0 0,clip]{risk-coverage.pdf}\par',
                    r'\raggedright\small\emph{' + tex(value) + r'}\end{minipage}\par\medskip']
        else:
            out.append(tex(value) + r'\par')
    return '\n'.join(out)


def latex_document(meta, pages):
    title, course, authors, school = meta
    preamble = r'''\documentclass[sigconf,nonacm,10pt]{acmart}
\usepackage{pvldb,multicol}
\geometry{left=.65in,right=.65in,top=.60in,bottom=.65in}
\setlength{\columnsep}{.24in}
\settopmatter{printacmref=false,printfolios=true}
\setcopyright{none}
\renewcommand{\footnotetextcopyrightpermission}[1]{}
\setlength{\parskip}{2pt}
\setlength{\emergencystretch}{1em}
\setlength{\tabcolsep}{3pt}
\renewcommand{\arraystretch}{1.15}
\urlstyle{same}
\hypersetup{colorlinks=true,urlcolor=blue!45!black,linkcolor=black}
\begin{document}'''
    out = [preamble, r'\title{' + tex(title).replace('Judge Identify', r'Judge\\Identify') + '}', r'\subtitle{' + tex(course) + '}',
           r'\author{' + tex(authors) + '}', r'\affiliation{\institution{' + tex(school) +
           r'}\city{San Diego}\country{USA}}', r'\renewcommand{\shortauthors}{DSC 261 Project Team}',
           # acmart builds the title in a full-width box. Use balanced columns below it.
           r'\let\originaltwocolumn\twocolumn\renewcommand{\twocolumn}[1][]{#1}\maketitle\let\twocolumn\originaltwocolumn',
           r'\pagestyle{plain}\raggedbottom']
    for i, page in enumerate(pages[:-1]):
        if i:
            out.append(r'\clearpage')
        out.extend([r'\begin{multicols}{2}\raggedcolumns', tex_body(page), r'\end{multicols}'])
    out += [r'\clearpage\section*{References}']
    for source in pages[-1]:
        citation, link = source.rsplit(' ', 1)
        out.append(r'\noindent\hangindent=1.5em ' + tex(citation) + r' \url{' + link + r'}\par\medskip')
    return '\n'.join(out + [r'\end{document}'])


def render(folder):
    from workflow import export
    export(folder)
    meta, pages = manuscript(folder)
    if shutil.which('pdflatex') and shutil.which('kpsewhich'):
        # Minimal TeX installs need not have the ACM font packages.
        has_fonts = subprocess.run(['kpsewhich', 'libertine.sty'], capture_output=True).returncode == 0
        if has_fonts:
            with TemporaryDirectory() as work:
                stage = Path(work)
                for name in ['acmart.cls', 'pvldb.sty']:
                    shutil.copyfile(folder / 'midterm-template' / name, stage / name)
                shutil.copyfile(folder / 'risk-coverage.pdf', stage / 'risk-coverage.pdf')
                shutil.copyfile(folder / 'workflow-midterm.pdf', stage / 'workflow-midterm.pdf')
                (stage / 'paper.tex').write_text(latex_document(meta, pages), encoding='utf8')
                for _ in range(2):
                    job = subprocess.run(['pdflatex','-interaction=nonstopmode','-halt-on-error','paper.tex'],
                                         cwd=stage, capture_output=True, env={**os.environ,'SOURCE_DATE_EPOCH':'1794182400','FORCE_SOURCE_DATE':'1'})
                    if job.returncode:
                        raise RuntimeError(job.stdout.decode(errors='replace')[-2200:])
                shutil.copyfile(stage / 'paper.pdf', folder / 'midpoint-update.pdf')
                return
    portable_pdf(folder, meta, pages)


def portable_pdf(folder, meta, pages):
    """Use the paper's column layout on systems with only the pinned Python packages."""
    from io import BytesIO
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.platypus import Image, Paragraph, Table, TableStyle, KeepInFrame
    from PIL import Image as Raster

    pdf = Canvas(str(folder / 'midpoint-update.pdf'), pagesize=(612,792), invariant=1)
    title, course, authors, school = meta
    pdf.setTitle(title)
    pdf.setAuthor(authors)
    width, left, right = 251, 47, 314
    body = ParagraphStyle('body',fontName='Times-Roman',fontSize=10,leading=12.2)
    heading = ParagraphStyle('heading',fontName='Times-Bold',fontSize=11,leading=13.2)
    caption = ParagraphStyle('caption',fontName='Times-Italic',fontSize=9,leading=10.7)
    reference = ParagraphStyle('ref',fontName='Times-Roman',fontSize=10,leading=13)
    for number, lines in enumerate(pages,1):
        top = 744
        if number == 1:
            for y, face, size, text in [(738,'Times-Bold',18,title),(708,'Times-Roman',11,course),
                                        (686,'Times-Roman',12,authors),(668,'Times-Italic',10,school)]:
                pdf.setFont(face,size)
                pdf.drawCentredString(306,y,text)
            top = 642
        if number == len(pages):
            pdf.setFont('Times-Bold',13)
            pdf.drawString(left,top,'REFERENCES')
            y = top-21
            for text in lines:
                p = Paragraph(escape(text),reference)
                _,height = p.wrap(518,700)
                p.drawOn(pdf,left,y-height)
                y -= height+10
        else:
            groups = []
            for kind,value in blocks(lines):
                if kind == 'table':
                    label,rows = value
                    table = Table(rows,colWidths=[width/len(rows[0])]*len(rows[0]))
                    table.setStyle(TableStyle([('FONT',(0,0),(-1,0),'Times-Bold',8.7),
                                               ('FONT',(0,1),(-1,-1),'Times-Roman',8.7),
                                               ('LINEABOVE',(0,0),(-1,0),.7,(0,0,0)),
                                               ('LINEBELOW',(0,0),(-1,0),.4,(0,0,0)),
                                               ('LINEBELOW',(0,-1),(-1,-1),.7,(0,0,0)),
                                               ('ALIGN',(1,0),(-1,-1),'RIGHT'),
                                               ('LEFTPADDING',(0,0),(-1,-1),1),
                                               ('RIGHTPADDING',(0,0),(-1,-1),1)]))
                    group = [Paragraph(escape(label),caption),table]
                elif kind == 'figure':
                    image_line, value = value
                    if 'workflow-' in image_line:
                        from workflow import workflow
                        groups.append([workflow(False,width),Paragraph(escape(value),caption)])
                        continue
                    group = []
                    with Raster.open(folder/'risk-coverage.png') as figure:
                        w,h = figure.size
                        for start,end in ((0,w//2),(w//2,w)):
                            data = BytesIO()
                            figure.crop((start,0,end,h)).save(data,format='PNG')
                            data.seek(0)
                            group.append(Image(data, width=width*.9,height=width*.9*h/(end-start)))
                    group.append(Paragraph(escape(value),caption))
                else:
                    style = heading if kind in ('section','subsection') else body
                    group = [Paragraph(escape(value.upper() if kind=='section' else value),style)]
                groups.append(group)
            heights = [sum(item.wrap(width,750)[1]+3 for item in g)+6 for g in groups]
            candidates = [i for i in range(1,len(groups)) if
                          not (len(groups[i-1])==1 and getattr(groups[i-1][0],'style',None) is heading)]
            cut = min(candidates,key=lambda i:abs(sum(heights[:i])-sum(heights[i:])))
            from reportlab.platypus import Spacer
            for x,col in ((left,groups[:cut]),(right,groups[cut:])):
                items = []
                for g in col:
                    for item in g:
                        items.extend([item,Spacer(1,3)])
                    items.append(Spacer(1,6))
                box = KeepInFrame(width,top-52,items,mode='shrink')
                _,height = box.wrapOn(pdf,width,top-52)
                print('MIDTERM_COLUMN',number,round(getattr(box,'_scale',1),4))
                box.drawOn(pdf,x,top-height)
        pdf.setFont('Times-Roman',9)
        pdf.drawCentredString(306,28,str(number))
        pdf.showPage()
    pdf.save()
