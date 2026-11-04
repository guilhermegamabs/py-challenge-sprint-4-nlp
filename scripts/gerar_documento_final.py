"""Gera o documento final da Sprint 4 em .docx e .pdf a partir de um único Markdown.

Fonte única: docs/<nome da disciplina>.md. O Markdown é o que se edita; os
dois formatos de entrega são derivados dele, para não divergirem.

O Markdown começa com um bloco entre linhas "---" (chave: valor) que vira a
capa. Depois vem o subconjunto de Markdown que o documento usa: títulos
#/##/###, parágrafos, listas com "-" e "1.", tabelas com pipe, citação ">",
imagem ![legenda](caminho), **negrito**, *itálico* e `código`.

Padrão visual exigido: só preto (e cinza neutro nas linhas de tabela), sem cor;
tabelas sempre na largura do texto.

Uso:  python scripts/gerar_documento_final.py
"""
from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
# O nome do arquivo é o nome da disciplina (exigência da entrega).
NOME = "Processamento de Linguagem Natural, Chatbots & Virtual Agents"
ORIGEM = RAIZ / "docs" / f"{NOME}.md"
DOCX = RAIZ / "docs" / f"{NOME}.docx"
PDF = RAIZ / "docs" / f"{NOME}.pdf"

LARGURA_TEXTO_CM = 21.0 - 2 * 2.2          # A4 menos as margens laterais
ALTURA_MAX_IMG_CM = 21.0                   # cabe na página com título e legenda


# ── capa (front matter) ─────────────────────────────────────────────────────
def separar_capa(texto: str) -> tuple[dict, str]:
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", texto, re.S)
    if not m:
        return {}, texto
    capa: dict = {"integrantes": []}
    for linha in m.group(1).splitlines():
        if ":" not in linha:
            continue
        chave, valor = (p.strip() for p in linha.split(":", 1))
        if chave == "integrante":
            nome, rm = (p.strip() for p in valor.split("|"))
            capa["integrantes"].append((nome, rm))
        else:
            capa[chave] = valor
    return capa, texto[m.end():]


# ── leitura do Markdown em blocos ────────────────────────────────────────────
def blocos(texto: str) -> list[tuple[str, object]]:
    linhas = texto.splitlines()
    saida: list[tuple[str, object]] = []
    i = 0
    while i < len(linhas):
        linha = linhas[i].rstrip()
        if not linha.strip() or linha.strip() == "---":
            i += 1
            continue
        if linha.strip() == "<!-- nova-pagina -->":
            saida.append(("quebra", None))
            i += 1
            continue
        m = re.match(r"^(#{1,3})\s+(.*)", linha)
        if m:
            saida.append((f"h{len(m.group(1))}", m.group(2).strip()))
            i += 1
            continue
        m = re.match(r"^!\[(.*?)\]\((.*?)\)", linha.strip())
        if m:
            saida.append(("img", (m.group(1), m.group(2))))
            i += 1
            continue
        if linha.lstrip().startswith("|"):
            tabela = []
            while i < len(linhas) and linhas[i].lstrip().startswith("|"):
                cel = [c.strip() for c in linhas[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cel):
                    tabela.append(cel)
                i += 1
            saida.append(("tabela", tabela))
            continue
        if re.match(r"^\s*(-|\d+\.)\s+", linha):
            itens, numerada = [], bool(re.match(r"^\s*\d+\.", linha))
            while i < len(linhas) and re.match(r"^\s*(-|\d+\.)\s+", linhas[i]):
                item = re.sub(r"^\s*(-|\d+\.)\s+", "", linhas[i]).strip()
                i += 1
                while i < len(linhas) and linhas[i].startswith("   ") and linhas[i].strip():
                    item += " " + linhas[i].strip()
                    i += 1
                itens.append(item)
            saida.append(("ol" if numerada else "ul", itens))
            continue
        if linha.startswith(">"):
            partes = []
            while i < len(linhas) and linhas[i].startswith(">"):
                partes.append(linhas[i].lstrip("> ").strip())
                i += 1
            saida.append(("quote", " ".join(partes)))
            continue
        partes = [linha.strip()]
        i += 1
        while (i < len(linhas) and linhas[i].strip() and not re.match(
                r"^(#{1,3}\s|\||!\[|>|\s*(-|\d+\.)\s|---)", linhas[i])):
            partes.append(linhas[i].strip())
            i += 1
        saida.append(("p", " ".join(partes)))
    return saida


_INLINE = re.compile(r"(\*\*.+?\*\*|`.+?`|\*[^*\s][^*]*?\*)")


def trechos(texto: str) -> list[tuple[str, str]]:
    """Quebra o texto em (estilo, conteúdo): n=normal, b=negrito, i=itálico, c=código."""
    out = []
    for parte in _INLINE.split(texto):
        if not parte:
            continue
        if parte.startswith("**"):
            out.append(("b", parte[2:-2]))
        elif parte.startswith("`"):
            out.append(("c", parte[1:-1]))
        elif parte.startswith("*") and parte.endswith("*") and len(parte) > 2:
            out.append(("i", parte[1:-1]))
        else:
            out.append(("n", parte))
    return out


def pesos_colunas(tabela: list[list[str]]) -> list[float]:
    """Fração da largura do texto para cada coluna; a soma é sempre 1.

    Cada coluna recebe primeiro o mínimo para a palavra mais longa dela caber
    sem ser partida (inclusive no cabeçalho, em negrito); a sobra é dividida
    pelo volume médio de texto. Sem largura fixa o Word dimensiona pelo
    conteúdo e a tabela passa da margem."""
    total = LARGURA_TEXTO_CM * 28.35            # pontos
    pt_por_char, folga = 5.0, 12.0              # ~Calibri 8,5–9 pt + padding da célula
    n_col = max(len(l) for l in tabela)
    minimos, volumes = [], []
    for c in range(n_col):
        textos = [re.sub(r"[*`]", "", l[c]) if c < len(l) else "" for l in tabela]
        maior = max((len(p) for t in textos for p in t.split()), default=4)
        minimos.append(min(maior, 22) * pt_por_char + folga)   # identificador longo pode quebrar
        volumes.append(max(sum(len(t) for t in textos) / len(textos), 1))
    soma_min = sum(minimos)
    if soma_min >= total:
        return [m / soma_min for m in minimos]
    sobra = total - soma_min
    larguras = [m + sobra * v / sum(volumes) for m, v in zip(minimos, volumes)]
    return [w / total for w in larguras]


# ── DOCX ────────────────────────────────────────────────────────────────────
def gerar_docx(capa: dict, bs) -> None:
    from docx import Document
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt, RGBColor

    PRETO = RGBColor(0, 0, 0)
    doc = Document()
    for s in doc.sections:
        s.left_margin = s.right_margin = Cm(2.2)
        s.top_margin = s.bottom_margin = Cm(2.0)
    base = doc.styles["Normal"]
    base.font.name = "Calibri"
    base.font.size = Pt(10.5)
    base.font.color.rgb = PRETO
    # Os estilos de título do Word vêm azuis no tema padrão: força preto.
    for nome in ("Heading 1", "Heading 2", "Heading 3", "Title"):
        doc.styles[nome].font.color.rgb = PRETO

    def inline(par, texto, tamanho=None):
        for estilo, conteudo in trechos(texto):
            run = par.add_run(conteudo)
            run.bold = estilo == "b"
            run.italic = estilo == "i"
            run.font.color.rgb = PRETO
            if estilo == "c":
                run.font.name = "Consolas"
                run.font.size = Pt(9)
            elif tamanho:
                run.font.size = Pt(tamanho)

    def centralizado(texto, tamanho, negrito=False, antes=0, depois=6):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(antes)
        p.paragraph_format.space_after = Pt(depois)
        r = p.add_run(texto)
        r.bold = negrito
        r.font.size = Pt(tamanho)
        r.font.color.rgb = PRETO
        return p

    def tabela_largura_texto(t, pesos):
        """Largura fixa = largura do texto, colunas proporcionais."""
        t.autofit = False
        tblPr = t._tbl.tblPr
        layout = OxmlElement("w:tblLayout")
        layout.set(qn("w:type"), "fixed")
        tblPr.append(layout)
        largura = OxmlElement("w:tblW")
        largura.set(qn("w:w"), str(int(LARGURA_TEXTO_CM * 567)))   # 567 twips por cm
        largura.set(qn("w:type"), "dxa")
        tblPr.append(largura)
        # Com layout fixo o Word usa a grade (w:gridCol), não a largura da célula.
        for gc, p in zip(t._tbl.tblGrid.findall(qn("w:gridCol")), pesos):
            gc.set(qn("w:w"), str(int(LARGURA_TEXTO_CM * 567 * p)))
        for linha in t.rows:
            for cel, p in zip(linha.cells, pesos):
                cel.width = Cm(LARGURA_TEXTO_CM * p)

    # Capa
    if capa:
        centralizado(capa.get("instituicao", ""), 12, negrito=True)
        centralizado(capa.get("desafio", ""), 11)
        centralizado(capa.get("disciplina", ""), 11, depois=90)
        centralizado(capa.get("projeto", ""), 18, negrito=True, depois=12)
        centralizado(capa.get("titulo", ""), 14, depois=80)
        centralizado(f"Professor: {capa.get('professor', '')}", 11, negrito=True, depois=14)
        centralizado(f"Integrantes — {capa.get('grupo', '')}", 11, negrito=True, depois=4)
        t = doc.add_table(rows=0, cols=2)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for nome, rm in capa["integrantes"]:
            cels = t.add_row().cells
            for cel, txt, al in ((cels[0], nome, WD_ALIGN_PARAGRAPH.RIGHT),
                                 (cels[1], rm, WD_ALIGN_PARAGRAPH.LEFT)):
                p = cel.paragraphs[0]
                p.alignment = al
                r = p.add_run(txt)
                r.font.size = Pt(11)
                r.font.color.rgb = PRETO
        tabela_largura_texto(t, [0.5, 0.5])
        centralizado("Repositório GitHub", 11, negrito=True, antes=40, depois=2)
        centralizado(capa.get("repositorio", ""), 10.5, depois=80)
        centralizado(capa.get("local_data", ""), 11)
        doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    for tipo, conteudo in bs:
        if tipo in ("h1", "h2", "h3"):
            nivel = int(tipo[1])
            h = doc.add_heading(level=nivel)
            run = h.add_run(conteudo.replace("**", ""))
            run.font.color.rgb = PRETO
            run.font.size = Pt({1: 18, 2: 14, 3: 12}[nivel])
        elif tipo == "p":
            inline(doc.add_paragraph(), conteudo)
        elif tipo == "quote":
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.8)
            inline(p, conteudo)
            for r in p.runs:
                r.italic = True
        elif tipo in ("ul", "ol"):
            for item in conteudo:
                inline(doc.add_paragraph(style="List Bullet" if tipo == "ul" else "List Number"), item)
        elif tipo == "tabela":
            n_col = max(len(l) for l in conteudo)
            t = doc.add_table(rows=0, cols=n_col)
            t.style = "Table Grid"
            t.alignment = WD_TABLE_ALIGNMENT.CENTER
            for li, linha in enumerate(conteudo):
                cels = t.add_row().cells
                for ci in range(n_col):
                    txt = linha[ci] if ci < len(linha) else ""
                    par = cels[ci].paragraphs[0]
                    inline(par, txt if li else f"**{txt.replace('**', '')}**", tamanho=9)
            tabela_largura_texto(t, pesos_colunas(conteudo))
            doc.add_paragraph()
        elif tipo == "quebra":
            doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        elif tipo == "img":
            from PIL import Image as PILImage

            legenda, caminho = conteudo
            arq = (ORIGEM.parent / caminho).resolve()
            if arq.exists():
                w, h = PILImage.open(arq).size
                if LARGURA_TEXTO_CM * h / w > ALTURA_MAX_IMG_CM:
                    doc.add_picture(str(arq), height=Cm(ALTURA_MAX_IMG_CM))
                else:
                    doc.add_picture(str(arq), width=Cm(LARGURA_TEXTO_CM))
                doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
                cap = doc.add_paragraph()
                r = cap.add_run(legenda)
                r.italic = True
                r.font.size = Pt(9)
                r.font.color.rgb = PRETO
    doc.save(DOCX)


# ── PDF ─────────────────────────────────────────────────────────────────────
def gerar_pdf(capa: dict, bs) -> None:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (Image, KeepTogether, ListFlowable, ListItem, PageBreak,
                                    Paragraph, SimpleDocTemplate, Spacer, Table,
                                    TableStyle)

    # Fonte TrueType com acentos e símbolos (°, ×, →, ≥); Helvetica padrão não cobre tudo.
    fontes = Path("C:/Windows/Fonts")
    fam, fam_b, fam_i, mono = "Helvetica", "Helvetica-Bold", "Helvetica-Oblique", "Courier"
    if (fontes / "calibri.ttf").exists():
        pdfmetrics.registerFont(TTFont("Calibri", str(fontes / "calibri.ttf")))
        pdfmetrics.registerFont(TTFont("Calibri-B", str(fontes / "calibrib.ttf")))
        pdfmetrics.registerFont(TTFont("Calibri-I", str(fontes / "calibrii.ttf")))
        pdfmetrics.registerFontFamily("Calibri", normal="Calibri", bold="Calibri-B",
                                      italic="Calibri-I", boldItalic="Calibri-B")
        fam, fam_b, fam_i = "Calibri", "Calibri-B", "Calibri-I"
    if (fontes / "consola.ttf").exists():
        pdfmetrics.registerFont(TTFont("Consolas", str(fontes / "consola.ttf")))
        mono = "Consolas"

    preto = colors.black
    est = getSampleStyleSheet()
    corpo = ParagraphStyle("corpo", parent=est["BodyText"], fontName=fam, fontSize=10,
                           leading=13.5, alignment=TA_JUSTIFY, spaceAfter=5, textColor=preto)
    cel = ParagraphStyle("cel", parent=corpo, fontSize=8.5, leading=10.5, alignment=0, spaceAfter=0)
    cit = ParagraphStyle("cit", parent=corpo, fontName=fam_i, leftIndent=14)
    leg = ParagraphStyle("leg", parent=corpo, fontName=fam_i, fontSize=8.5, alignment=TA_CENTER)
    # keepWithNext: título nunca fica sozinho no pé da página.
    hs = {1: ParagraphStyle("h1", fontName=fam_b, fontSize=17, leading=21, textColor=preto, spaceBefore=6, spaceAfter=8, keepWithNext=1),
          2: ParagraphStyle("h2", fontName=fam_b, fontSize=13.5, leading=17, textColor=preto, spaceBefore=12, spaceAfter=6, keepWithNext=1),
          3: ParagraphStyle("h3", fontName=fam_b, fontSize=11.5, leading=14, textColor=preto, spaceBefore=8, spaceAfter=4, keepWithNext=1)}

    def centro(tamanho, negrito=False, depois=6):
        return ParagraphStyle(f"c{tamanho}{negrito}{depois}", fontName=fam_b if negrito else fam,
                              fontSize=tamanho, leading=tamanho * 1.3, alignment=TA_CENTER,
                              textColor=preto, spaceAfter=depois)

    def html(texto: str) -> str:
        out = []
        for estilo, c in trechos(texto):
            c = c.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            out.append({"b": f"<b>{c}</b>", "i": f"<i>{c}</i>",
                        "c": f'<font face="{mono}" size="8.5">{c}</font>'}.get(estilo, c))
        return "".join(out)

    corpo_esq = ParagraphStyle("corpo_esq", parent=corpo, alignment=0)

    def estilo_de(texto: str):
        """Justificado, exceto quando há código/caminho longo no parágrafo.

        Um caminho como relatorios/sprint4_..._composta.json não pode ser quebrado;
        justificado, o reportlab estica os espaços da linha anterior para
        compensar e abre buracos entre as palavras."""
        longo = any(e == "c" and len(c) >= 18 for e, c in trechos(texto))
        return corpo_esq if longo else corpo

    largura = A4[0] - 4.4 * cm
    story = []

    if capa:
        story += [
            Paragraph(capa.get("instituicao", ""), centro(12, True)),
            Paragraph(capa.get("desafio", ""), centro(11)),
            Paragraph(capa.get("disciplina", ""), centro(11)),
            Spacer(1, 3.2 * cm),
            Paragraph(capa.get("projeto", ""), centro(18, True, 14)),
            Paragraph(capa.get("titulo", ""), centro(14)),
            Spacer(1, 2.6 * cm),
            Paragraph(f"<b>Professor:</b> {capa.get('professor', '')}", centro(11, depois=18)),
            Paragraph(f"Integrantes — {capa.get('grupo', '')}", centro(11, True, 6)),
        ]
        linhas = [[Paragraph(n, ParagraphStyle("nm", parent=centro(11), alignment=2)),
                   Paragraph(rm, ParagraphStyle("rm", parent=centro(11), alignment=0))]
                  for n, rm in capa["integrantes"]]
        t = Table(linhas, colWidths=[largura * 0.55, largura * 0.45])
        t.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 6),
                               ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                               ("TOPPADDING", (0, 0), (-1, -1), 1),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
        story += [t, Spacer(1, 1.6 * cm),
                  Paragraph("Repositório GitHub", centro(11, True, 2)),
                  Paragraph(capa.get("repositorio", ""), centro(10.5)),
                  Spacer(1, 2.4 * cm),
                  Paragraph(capa.get("local_data", ""), centro(11)),
                  PageBreak()]

    for tipo, conteudo in bs:
        if tipo in ("h1", "h2", "h3"):
            story.append(Paragraph(html(conteudo.replace("**", "")), hs[int(tipo[1])]))
        elif tipo == "p":
            story.append(Paragraph(html(conteudo), estilo_de(conteudo)))
        elif tipo == "quote":
            story.append(Paragraph(html(conteudo), cit))
        elif tipo in ("ul", "ol"):
            story.append(ListFlowable(
                [ListItem(Paragraph(html(i), estilo_de(i)), leftIndent=12) for i in conteudo],
                bulletType="bullet" if tipo == "ul" else "1", start=None if tipo == "ul" else 1,
                bulletFontName=fam, bulletFontSize=8 if tipo == "ul" else 10,
                bulletColor=preto, leftIndent=14))
        elif tipo == "tabela":
            n_col = max(len(l) for l in conteudo)
            dados = [[Paragraph(f"<b>{html((l[c] if c < len(l) else '').replace('**', ''))}</b>"
                                if li == 0 else html(l[c] if c < len(l) else ""), cel)
                      for c in range(n_col)]
                     for li, l in enumerate(conteudo)]
            t = Table(dados, colWidths=[largura * p for p in pesos_colunas(conteudo)], repeatRows=1)
            t.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, preto),
                ("LINEBELOW", (0, 0), (-1, 0), 1.0, preto),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            story += [t, Spacer(1, 8)]
        elif tipo == "quebra":
            story.append(PageBreak())
        elif tipo == "img":
            legenda, caminho = conteudo
            arq = (ORIGEM.parent / caminho).resolve()
            if arq.exists():
                w, h = ImageReader(str(arq)).getSize()
                larg, alt = largura, largura * h / w
                if alt > ALTURA_MAX_IMG_CM * cm:          # imagem alta: reduz mantendo a proporção
                    alt = ALTURA_MAX_IMG_CM * cm
                    larg = alt * w / h
                # Imagem e legenda juntas: a legenda nunca fica órfã na página seguinte.
                story += [KeepTogether([Image(str(arq), width=larg, height=alt),
                                        Paragraph(html(legenda), leg)]), Spacer(1, 10)]

    # Título (ou sequência de títulos) vai junto com o bloco seguinte numa
    # KeepTogether: o keepWithNext do estilo não segurou nos testes.
    agrupado, i = [], 0
    while i < len(story):
        f = story[i]
        if isinstance(f, Paragraph) and f.style.name in ("h1", "h2", "h3"):
            grupo = [f]
            i += 1
            while i < len(story) and (isinstance(story[i], Paragraph)
                                      and story[i].style.name in ("h1", "h2", "h3")):
                grupo.append(story[i])
                i += 1
            if i < len(story) and not isinstance(story[i], PageBreak):
                grupo.append(story[i])
                i += 1
            agrupado.append(KeepTogether(grupo))
        else:
            agrupado.append(f)
            i += 1
    story = agrupado

    def rodape(canvas, doc_):
        if doc_.page == 1 and capa:
            return                               # capa sem rodapé
        canvas.saveState()
        canvas.setFont(fam, 8)
        canvas.setFillColor(preto)
        canvas.drawString(2.2 * cm, 1.2 * cm, "FIAP × Forzy — Grupo CodeX · Sprint 4 — Documentação final PLN")
        canvas.drawRightString(A4[0] - 2.2 * cm, 1.2 * cm, f"{doc_.page}")
        canvas.restoreState()

    SimpleDocTemplate(str(PDF), pagesize=A4, leftMargin=2.2 * cm, rightMargin=2.2 * cm,
                      topMargin=2 * cm, bottomMargin=2 * cm,
                      title="Documentação Final — Solução PLN",
                      author="Grupo CodeX").build(story, onFirstPage=rodape, onLaterPages=rodape)


def main() -> None:
    capa, corpo = separar_capa(ORIGEM.read_text(encoding="utf-8"))
    bs = blocos(corpo)
    gerar_docx(capa, bs)
    gerar_pdf(capa, bs)
    print(f"capa + {len(bs)} blocos -> {DOCX.name}, {PDF.name}")


if __name__ == "__main__":
    main()
