"""Prints de evidência: células reais dos notebooks executados -> PNG.

Cada print é uma célula (código + saída) tirada do .ipynb já executado, com o
número de execução e o nome do notebook visíveis. Nada é recalculado: a
imagem mostra exatamente o que está salvo no notebook. A renderização é feita
pelo Edge/Chrome em modo headless, e a imagem é recortada no fim do conteúdo.

Sem cor: o documento final é só preto e cinza.

Uso:  python scripts/gerar_prints.py [caminho do notebook da Sprint 2]
"""
from __future__ import annotations

import base64
import html
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageChops

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "evidencias" / "prints"
S1 = RAIZ / "sprints_anteriores" / "sprint1" / "sprint1_pln_corpus.ipynb"
S2 = Path(sys.argv[1]) if len(sys.argv) > 1 else (
    RAIZ.parents[1] / "challenge-sprint-2" / "processamento-linguagem-natural" / "sprint2_pln_consulta.ipynb")
S3 = RAIZ / "sprint3_pln_alertas.ipynb"
S4 = RAIZ / "sprint4_pln_rag.ipynb"
LOG = RAIZ / "evidencias" / "log_avaliacao_assistente_sprint4_final.txt"

MAX_LINHAS_CODIGO = 14
LARGURA_PX = 1100

# (arquivo, título, [(notebook, índice da célula, filtro opcional da saída)])
PRINTS = [
    ("p01_s1_preprocessamento.png", "Sprint 1 — pipeline de pré-processamento aplicado às causas de falha",
     [(S1, 25, None)]),
    ("p02_s1_estatisticas.png", "Sprint 1 — estatísticas do corpus",
     [(S1, 19, None)]),
    ("p03_s2_consulta.png", "Sprint 2 — consulta semântica em linguagem natural sobre o cadastro",
     [(S2, 25, None)]),
    ("p04_s2_metricas.png", "Sprint 2 — Precision@k e Recall@k nas 18 consultas-teste",
     [(S2, 21, None)]),
    ("p05_s3_resumos.png", "Sprint 3 — resumos de alerta gerados por severidade",
     [(S3, 12, None)]),
    ("p06_s3_classificacao.png", "Sprint 3 — classificação de eventos: híbrido × zero-shot × TF-IDF",
     [(S3, 28, None), (S3, 30, None)]),
    ("p07_s4_retriever.png", "Sprint 4 — retriever com e sem re-ranking",
     [(S4, 10, None)]),
    ("p08_s4_fora_de_escopo.png", "Sprint 4 — perguntas fora de escopo recusadas",
     [(S4, 23, None)]),
    ("p09_s4_cenario_eletrico.png", "Sprint 4 — cenário de falha elétrica (MT-007)",
     [(S4, 25, "ANOMALIA ELETRICA")]),
    ("p10_s4_cenario_mecanico.png", "Sprint 4 — cenário de falha mecânica (MT-008)",
     [(S4, 25, "ANOMALIA MECANICA")]),
    ("p11_s4_cenario_manutencao.png", "Sprint 4 — cenário de manutenção planejada (MT-004)",
     [(S4, 25, "MANUTENCAO PREVENTIVA")]),
    ("p12_s4_antes_depois.png", "Sprint 4 — antes × depois e limiar de recusa",
     [(S4, 27, None), (S4, 29, None)]),
]

CSS = """
body{margin:0;padding:18px;background:#fff;color:#111;font:14px/1.45 'Segoe UI',Calibri,sans-serif;width:%dpx}
.top{font-weight:600;font-size:15px;border-bottom:2px solid #111;padding-bottom:6px;margin-bottom:12px}
.cel{margin:0 0 14px 0}
.arq{font:12px Consolas,monospace;color:#555;margin-bottom:3px}
.ent{display:flex}.saida{display:flex;margin-top:4px}
.prompt{width:62px;flex:none;font:12px Consolas,monospace;color:#555;padding-top:6px}
.codigo{flex:1;background:#f3f3f3;border:1px solid #cfcfcf;padding:6px 8px;
        font:12.5px/1.4 Consolas,monospace;white-space:pre-wrap;word-break:break-word}
.out{flex:1;min-width:0;font:12.5px/1.4 Consolas,monospace;white-space:pre-wrap;word-break:break-word}
.out img{max-width:100%%}
.out table{border-collapse:collapse;font:12.5px 'Segoe UI',Calibri,sans-serif;white-space:normal}
.out th,.out td{border:1px solid #bbb;padding:3px 7px;text-align:right}
.out th{background:#eee}
.out .html{white-space:normal}
""" % (LARGURA_PX - 36)


def carregar(nb_path: Path) -> list:
    return json.loads(nb_path.read_text(encoding="utf-8"))["cells"]


def filtrar_texto(texto: str, chave: str | None) -> str:
    """Recorta um bloco de cenário da saída (separados por linhas de '=')."""
    if not chave:
        return texto
    blocos = texto.split("=" * 78)
    for b in blocos:
        if chave in b:
            return "=" * 78 + b.rstrip() + "\n"
    raise ValueError(f"bloco {chave!r} não encontrado")


def html_celula(nb_path: Path, idx: int, chave: str | None) -> str:
    cel = carregar(nb_path)[idx]
    assert cel["cell_type"] == "code", (nb_path, idx)
    n = cel.get("execution_count") or " "
    linhas = "".join(cel["source"]).splitlines()
    if len(linhas) > MAX_LINHAS_CODIGO:
        linhas = linhas[:MAX_LINHAS_CODIGO] + [f"# … (+{len(linhas) - MAX_LINHAS_CODIGO} linhas — código completo no notebook)"]
    partes = [f'<div class="cel"><div class="arq">{html.escape(nb_path.name)} · célula [{n}]</div>',
              f'<div class="ent"><div class="prompt">In [{n}]:</div>'
              f'<div class="codigo">{html.escape(chr(10).join(linhas))}</div></div>']
    # O Jupyter grava o stdout em pedaços; junta os consecutivos num bloco só.
    saidas = []
    for o in cel.get("outputs", []):
        if o["output_type"] == "stream" and o.get("name") == "stderr":
            continue                          # avisos de biblioteca não são evidência
        if (o["output_type"] == "stream" and saidas and saidas[-1]["output_type"] == "stream"):
            saidas[-1] = {**saidas[-1], "text": "".join(saidas[-1]["text"]) + "".join(o["text"])}
        else:
            saidas.append(o)
    for o in saidas:
        dados = o.get("data", {})
        if o["output_type"] == "stream":
            conteudo = f"{html.escape(filtrar_texto(''.join(o['text']), chave).strip(chr(10)))}"
        elif "image/png" in dados:
            conteudo = f'<img src="data:image/png;base64,{dados["image/png"].strip()}">'
        elif "text/html" in dados:
            conteudo = f'<div class="html">{"".join(dados["text/html"])}</div>'
        elif "text/plain" in dados:
            conteudo = html.escape("".join(dados["text/plain"]))
        else:
            continue
        partes.append(f'<div class="saida"><div class="prompt">Out:</div><div class="out">{conteudo}</div></div>')
    return "".join(partes) + "</div>"


def html_log() -> str:
    linhas = [l for l in LOG.read_text(encoding="utf-8").splitlines() if l.strip()]
    corte = next(i for i, l in enumerate(linhas) if "metricas de geracao" in l)
    trecho = linhas[:corte + 1] + ["…"]
    return (f'<div class="arq">{LOG.name}</div>'
            f'<div class="codigo" style="background:#111;color:#eee">{html.escape(chr(10).join(trecho))}</div>')


def navegador() -> str:
    # Chrome primeiro: nesta máquina o Edge headless sai com código 0 sem gravar o PNG.
    for p in (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"):
        if Path(p).exists():
            return p
    achado = shutil.which("msedge") or shutil.which("chrome")
    if not achado:
        raise SystemExit("Edge ou Chrome não encontrado")
    return achado


def capturar(corpo: str, titulo: str, destino: Path, tmp: Path) -> None:
    pagina = tmp / (destino.stem + ".html")
    pagina.write_text(f'<!doctype html><meta charset="utf-8"><style>{CSS}</style>'
                      f'<body><div class="top">{html.escape(titulo)}</div>{corpo}</body>',
                      encoding="utf-8")
    bruto = tmp / (destino.stem + "_bruto.png")
    # Perfil próprio: sem ele, com o navegador já aberto, o headless se anexa à
    # instância existente e sai sem gravar a imagem.
    subprocess.run([navegador(), "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    f"--user-data-dir={tmp / 'perfil'}", "--no-first-run",
                    f"--window-size={LARGURA_PX},6000", "--force-device-scale-factor=1.5",
                    f"--screenshot={bruto}", pagina.as_uri()],
                   check=True, capture_output=True, timeout=120)
    img = Image.open(bruto).convert("RGB")
    fundo = Image.new("RGB", img.size, (255, 255, 255))
    caixa = ImageChops.difference(img, fundo).getbbox()
    margem = 24
    img = img.crop((0, 0, img.width, min(img.height, caixa[3] + margem)))
    img.convert("L").save(destino, optimize=True)        # sem cor


def main() -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        for arquivo, titulo, celulas in PRINTS:
            corpo = "".join(html_celula(nb, i, ch) for nb, i, ch in celulas)
            capturar(corpo, titulo, DESTINO / arquivo, tmp)
            print("ok", arquivo)
        capturar(html_log(), "Sprint 4 — log real da avaliação do assistente (execução em CPU)",
                 DESTINO / "p13_s4_log_execucao.png", tmp)
        print("ok p13_s4_log_execucao.png")


if __name__ == "__main__":
    main()
