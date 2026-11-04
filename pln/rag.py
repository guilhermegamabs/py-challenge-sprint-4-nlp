# -*- coding: utf-8 -*-
"""Pipeline RAG sobre a documentacao tecnica dos motores (Sprint 4)."""

from __future__ import annotations

import json
import pickle
import re
import unicodedata
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

MODELO_EMBEDDING = "paraphrase-multilingual-MiniLM-L12-v2"   # reusado da Sprint 2

@dataclass
class Documento:
    doc_id: str
    titulo: str
    caminho: str
    tipo: str                     # manual | guia | catalogo | artigo
    paginas_pt: tuple[int, ...] | None = None   # None = documento inteiro em PT


def catalogo_padrao(base: Path) -> list[Documento]:
    """Documentos tecnicos em portugues usados pelo assistente."""
    g = "Guias de Instalação, Configuração e Operação"
    return [
        Documento(
            "guia_especificacao",
            "WEG — Guia de Especificação de Motores Elétricos",
            f"{g}/WEG-motores-eletricos-guia-de-especificacao-50032749-brochure-portuguese-web.pdf",
            "guia"),
        Documento(
            "manual_wmo",
            "WEG — Manual de Instalação, Operação e Manutenção (WMO Safe Area)",
            "Novos/WEG-WMO-safe-area-50031142-manual-en-pt-es-de-fr-ru-nl-it-zh.pdf",
            "manual",
            paginas_pt=tuple(range(15, 21))),   # secao PORTUGUES do manual multilingue
        Documento(
            "catalogo_w22",
            "WEG — Catálogo Técnico W22 Motor Elétrico Monofásico",
            "Catálogos Técnicos de Produtos/WEG-w22-motor-eletrico-monofasico-50069982-brochure-portuguese-web.pdf",
            "catalogo"),
        Documento(
            "danos_enrolamento",
            "WEG — Danos em Enrolamentos de Motores Monofásicos",
            "Novos/WEG-danos-em-enrolamentos-motores-monofasicos-50009254-brochure-portuguese-web.pdf",
            "artigo"),
        Documento(
            "rendimento_monofasicos",
            "WEG — Rendimento nos Motores Monofásicos",
            "Artigos Técnicos/WEG-rendimento-nos-motores-monofasicos-001-article-portuguese-web.pdf",
            "artigo"),
    ]


_HIFEN = re.compile(r"(\w)-\n(\w)")
_ESPACOS = re.compile(r"[ \t]+")
_QUEBRAS = re.compile(r"\n{3,}")


def limpar(texto: str) -> str:
    """Junta palavras hifenizadas na quebra de linha e normaliza espacos."""
    t = texto.replace("\r", "")
    t = _HIFEN.sub(r"\1\2", t)
    t = _ESPACOS.sub(" ", t)
    return _QUEBRAS.sub("\n\n", t).strip()


_LINHA_SUMARIO = re.compile(r"\.{4,}\s*\d+")


def _é_sumario(texto: str) -> bool:
    """Pagina de indice: muitas linhas com pontilhado seguido de numero de pagina."""
    linhas = [l for l in texto.splitlines() if l.strip()]
    if len(linhas) < 6:
        return False
    return sum(bool(_LINHA_SUMARIO.search(l)) for l in linhas) / len(linhas) > 0.3


def extrair_paginas(doc: Documento, base: Path) -> list[dict]:
    """Texto por pagina, ja filtrado pelo idioma quando o PDF e multilingue."""
    import fitz  # PyMuPDF

    pdf = fitz.open(base / doc.caminho)
    paginas = []
    for i, pagina in enumerate(pdf):
        if doc.paginas_pt is not None and i not in doc.paginas_pt:
            continue
        texto = limpar(pagina.get_text())
        if len(texto) < 120:          # capa, pagina de figura, verso em branco
            continue
        if _é_sumario(texto):         # indice impresso: repete titulos e polui a busca
            continue
        paginas.append({"doc_id": doc.doc_id, "pagina": i + 1, "texto": texto})
    return paginas


def sumario(doc: Documento, base: Path) -> list[tuple[int, str, int]]:
    """Sumario embutido no PDF: (nivel, titulo, pagina). Vazio quando nao existe."""
    import fitz

    return [tuple(x[:3]) for x in fitz.open(base / doc.caminho).get_toc()]


MAX_CHARS = 1100          # teto por chunk: cabe no contexto sem diluir o topico
MIN_CHARS = 220           # abaixo disso o trecho nao sustenta uma resposta
SOBREPOSICAO = 180        # continuidade entre janelas da mesma secao


def _normalizar_titulo(t: str) -> str:
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9 ]+", " ", t).strip()


def _normalizar_linhas(texto: str) -> str:
    """Versao plana do texto preservando as quebras de linha (para casar titulos)."""
    t = unicodedata.normalize("NFKD", texto)
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9 \n]+", " ", t)


def _ocorrencias_em_inicio_de_linha(plano: str, alvo: str) -> list[int]:
    """Posicoes em que o titulo abre uma linha — descarta citacoes no meio do texto."""
    posicoes, procura = [], 0
    while True:
        idx = plano.find(alvo, procura)
        if idx < 0:
            return posicoes
        inicio_linha = plano.rfind("\n", 0, idx) + 1
        if not plano[inicio_linha:idx].strip():
            posicoes.append(idx)
        procura = idx + 1


_NUMERO_SECAO = re.compile(r"^(\d+(?:\.\d+)*)")


def _nivel_do_titulo(titulo: str, nivel_toc: int) -> int:
    """Profundidade pela numeracao da secao (1.6.3 -> 3); cai no nivel do TOC."""
    m = _NUMERO_SECAO.match(titulo.strip())
    return len(m.group(1).split(".")) if m else nivel_toc


def _caminho_hierarquico(pilha: list[tuple[int, str]]) -> str:
    return " > ".join(t for _, t in pilha)


def _janelas(texto: str, max_chars: int = MAX_CHARS,
             sobreposicao: int = SOBREPOSICAO) -> list[str]:
    """Divide um texto longo em janelas, cortando em fim de frase quando possivel."""
    if len(texto) <= max_chars:
        return [texto]
    partes, inicio = [], 0
    while inicio < len(texto):
        fim = min(inicio + max_chars, len(texto))
        if fim < len(texto):
            corte = max(texto.rfind(". ", inicio + max_chars // 2, fim),
                        texto.rfind("\n", inicio + max_chars // 2, fim))
            if corte > 0:
                fim = corte + 1
        partes.append(texto[inicio:fim].strip())
        if fim >= len(texto):
            break
        inicio = max(fim - sobreposicao, inicio + 1)
    return [p for p in partes if p]


def chunks_por_sumario(doc: Documento, paginas: Sequence[dict],
                       toc: Sequence[tuple[int, str, int]]) -> list[dict]:
    """Segmenta pelo sumario do PDF, localizando cada titulo dentro da pagina."""
    texto_total, marcas = [], []
    posicao = 0
    for p in paginas:
        texto_total.append(p["texto"])
        marcas.append((posicao, p["pagina"]))
        posicao += len(p["texto"]) + 2
    inteiro = "\n\n".join(texto_total)
    plano = _normalizar_linhas(inteiro)

    def pagina_de(pos: int) -> int:
        atual = marcas[0][1]
        for inicio, pg in marcas:
            if inicio <= pos:
                atual = pg
            else:
                break
        return atual

    achados = []
    for nivel, titulo, pagina_toc in toc:
        alvo = _normalizar_titulo(titulo)
        if len(alvo) < 4:
            continue
        posicoes = _ocorrencias_em_inicio_de_linha(plano, alvo)
        if not posicoes:                 # titulo nao localizado (figura, tabela)
            continue
        idx = min(posicoes, key=lambda p: abs(pagina_de(p) - pagina_toc))
        achados.append((idx, _nivel_do_titulo(titulo, nivel), titulo.strip()))

    if not achados:
        return []

    achados.sort(key=lambda a: a[0])     # segmentacao segue a ordem do documento

    saida: list[dict] = []
    pilha: list[tuple[int, str]] = []
    for i, (pos, nivel, titulo) in enumerate(achados):
        fim = achados[i + 1][0] if i + 1 < len(achados) else len(inteiro)
        corpo = inteiro[pos:fim].strip()
        while pilha and pilha[-1][0] >= nivel:
            pilha.pop()
        pilha.append((nivel, titulo))
        if len(corpo) < MIN_CHARS:
            continue
        caminho = _caminho_hierarquico(pilha)
        for j, janela in enumerate(_janelas(corpo)):
            saida.append({
                "doc_id": doc.doc_id,
                "secao": caminho,
                "titulo_secao": titulo,
                "pagina": pagina_de(pos),
                "parte": j,
                "texto": janela,
            })
    return saida


_CABECALHO = re.compile(r"^(?:\d+(?:\.\d+)*\s+)?[A-ZÁÂÃÀÉÊÍÓÔÕÚÇ][^\n]{4,70}$")


_TITULO_NUMERADO = re.compile(
    r"^(\d+(?:\.\d+){0,3})[ \t]+([A-ZÁÂÃÀÉÊÍÓÔÕÚÇ][A-ZÁÂÃÀÉÊÍÓÔÕÚÇ0-9 ,\-/()]{3,60})$",
    re.M)


def chunks_por_cabecalho(doc: Documento, paginas: Sequence[dict]) -> list[dict]:
    """Segmenta por titulos numerados encontrados no corpo (PDF sem sumario)."""
    texto_total, marcas, posicao = [], [], 0
    for p in paginas:
        texto_total.append(p["texto"])
        marcas.append((posicao, p["pagina"]))
        posicao += len(p["texto"]) + 2
    inteiro = "\n\n".join(texto_total)

    titulos = [(m.start(), m.group(1), m.group(0).strip())
               for m in _TITULO_NUMERADO.finditer(inteiro)]
    if len(titulos) < 3:
        return []

    def pagina_de(pos: int) -> int:
        atual = marcas[0][1]
        for inicio, pg in marcas:
            if inicio <= pos:
                atual = pg
            else:
                break
        return atual

    saida, pilha = [], []
    for i, (pos, numero, titulo) in enumerate(titulos):
        fim = titulos[i + 1][0] if i + 1 < len(titulos) else len(inteiro)
        corpo = inteiro[pos:fim].strip()
        nivel = len(numero.split("."))
        while pilha and pilha[-1][0] >= nivel:
            pilha.pop()
        pilha.append((nivel, titulo))
        if len(corpo) < MIN_CHARS:
            continue
        for j, janela in enumerate(_janelas(corpo)):
            saida.append({
                "doc_id": doc.doc_id,
                "secao": _caminho_hierarquico(pilha),
                "titulo_secao": titulo,
                "pagina": pagina_de(pos),
                "parte": j,
                "texto": janela,
            })
    return saida


def chunks_por_pagina(doc: Documento, paginas: Sequence[dict]) -> list[dict]:
    """Fallback por pagina: cabecalho detectado + janelas do corpo."""
    saida = []
    for p in paginas:
        linhas = [l.strip() for l in p["texto"].splitlines() if l.strip()]
        titulo = next((l for l in linhas[:6] if _CABECALHO.match(l)), None)
        titulo = titulo or f"Página {p['pagina']}"
        corpo = p["texto"]
        for j, janela in enumerate(_janelas(corpo)):
            if len(janela) < MIN_CHARS:
                continue
            saida.append({
                "doc_id": doc.doc_id,
                "secao": titulo,
                "titulo_secao": titulo,
                "pagina": p["pagina"],
                "parte": j,
                "texto": janela,
            })
    return saida


PALAVRAS_FAMILIA = {
    "eletrica": ("tensão", "corrente", "fase", "isolamento", "enrolamento",
                 "partida", "fator de potência", "frequência", "alimentação",
                 "inversor", "aterramento", "curto", "sobrecarga"),
    "mecanica": ("rolamento", "mancal", "vibração", "alinhamento", "acoplamento",
                 "eixo", "lubrificação", "graxa", "balanceamento", "ruído",
                 "fixação", "base"),
    "termica": ("temperatura", "aquecimento", "refrigeração", "ventilação",
                "térmica", "classe de isolamento", "elevação de temperatura",
                "sobretemperatura"),
    "manutencao": ("manutenção", "inspeção", "preventiva", "periodicidade",
                   "armazenagem", "limpeza", "substituição", "intervalo"),
}


def marcar_familias(texto: str) -> list[str]:
    """Rotula o chunk pelas familias tecnicas presentes (pode ser mais de uma)."""
    baixo = texto.lower()
    return [fam for fam, termos in PALAVRAS_FAMILIA.items()
            if sum(t in baixo for t in termos) >= 2]


def construir_chunks(base: Path, docs: Sequence[Documento] | None = None) -> list[dict]:
    """Executa extracao + chunking para todos os documentos do catalogo."""
    docs = list(docs or catalogo_padrao(base))
    todos: list[dict] = []
    for doc in docs:
        paginas = extrair_paginas(doc, base)
        toc = sumario(doc, base)
        chunks = chunks_por_sumario(doc, paginas, toc) if toc else []
        if not chunks:
            chunks = chunks_por_cabecalho(doc, paginas)
        if not chunks:
            chunks = chunks_por_pagina(doc, paginas)
        for c in chunks:
            c["titulo_doc"] = doc.titulo
            c["tipo_doc"] = doc.tipo
            c["familias"] = marcar_familias(c["texto"])
            c["n_chars"] = len(c["texto"])
        todos.extend(chunks)

    for i, c in enumerate(todos, start=1):
        c["chunk_id"] = f"CH-{i:04d}"
    return todos


def texto_indexavel(chunk: dict) -> str:
    """O cabecalho entra no texto embutido: preserva o contexto tecnico da secao."""
    return f"{chunk['titulo_doc']} — {chunk['secao']}\n{chunk['texto']}"


@dataclass
class IndiceVetorial:
    chunks: list[dict]
    modelo_nome: str = MODELO_EMBEDDING
    _index: object | None = field(default=None, repr=False)
    _modelo: object | None = field(default=None, repr=False)

    def carregar_modelo(self):
        if self._modelo is None:
            from sentence_transformers import SentenceTransformer
            self._modelo = SentenceTransformer(self.modelo_nome)
        return self._modelo

    def construir(self, batch_size: int = 32) -> "IndiceVetorial":
        import faiss

        modelo = self.carregar_modelo()
        vetores = modelo.encode([texto_indexavel(c) for c in self.chunks],
                                batch_size=batch_size, show_progress_bar=False,
                                normalize_embeddings=True)
        vetores = np.asarray(vetores, dtype="float32")
        self._index = faiss.IndexFlatIP(vetores.shape[1])   # cosseno (vetores normalizados)
        self._index.add(vetores)
        return self

    def buscar(self, consulta: str, k: int = 10) -> list[tuple[dict, float]]:
        modelo = self.carregar_modelo()
        q = np.asarray(modelo.encode([consulta], normalize_embeddings=True), dtype="float32")
        scores, indices = self._index.search(q, min(k, len(self.chunks)))
        return [(self.chunks[i], float(s)) for i, s in zip(indices[0], scores[0]) if i >= 0]

    def salvar(self, destino: Path) -> None:
        import faiss

        destino.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(destino / "faiss.index"))
        (destino / "chunks.json").write_text(
            json.dumps(self.chunks, ensure_ascii=False, indent=1), encoding="utf-8")
        with open(destino / "meta.pkl", "wb") as f:
            pickle.dump({"modelo": self.modelo_nome, "n": len(self.chunks)}, f)

    @classmethod
    def carregar(cls, origem: Path) -> "IndiceVetorial":
        import faiss

        chunks = json.loads((origem / "chunks.json").read_text(encoding="utf-8"))
        with open(origem / "meta.pkl", "rb") as f:
            meta = pickle.load(f)
        obj = cls(chunks, meta["modelo"])
        obj._index = faiss.read_index(str(origem / "faiss.index"))
        return obj


_PALAVRA = re.compile(r"[a-zà-ú0-9]{4,}", re.I)


def _termos(texto: str) -> set[str]:
    plano = unicodedata.normalize("NFKD", texto.lower())
    plano = "".join(c for c in plano if not unicodedata.combining(c))
    return set(_PALAVRA.findall(plano))


PESOS = {"denso": 1.0, "lexical": 0.35, "familia": 0.25, "ativo": 0.15}


@dataclass
class Retriever:
    """Busca densa com re-ranking por sinal lexical e contexto operacional."""
    indice: IndiceVetorial
    k_denso: int = 20

    def buscar(self, pergunta: str, k: int = 4,
               familias: Sequence[str] | None = None,
               termos_ativo: Sequence[str] | None = None,
               reranking: bool = True) -> list[dict]:
        brutos = self.indice.buscar(pergunta, k=self.k_denso)
        if not reranking:
            return [{**c, "score": s, "score_denso": s} for c, s in brutos[:k]]

        termos_pergunta = _termos(pergunta)
        resultados = []
        for chunk, denso in brutos:
            termos_chunk = _termos(texto_indexavel(chunk))
            lexical = (len(termos_pergunta & termos_chunk) / len(termos_pergunta)
                       if termos_pergunta else 0.0)
            fam = (len(set(familias or []) & set(chunk["familias"])) /
                   max(len(familias or []), 1)) if familias else 0.0
            ativo = 0.0
            if termos_ativo:
                alvo = _termos(" ".join(termos_ativo))
                ativo = len(alvo & termos_chunk) / max(len(alvo), 1)
            score = (PESOS["denso"] * denso + PESOS["lexical"] * lexical +
                     PESOS["familia"] * fam + PESOS["ativo"] * ativo)
            resultados.append({**chunk, "score": round(score, 4),
                               "score_denso": round(denso, 4),
                               "score_lexical": round(lexical, 4),
                               "score_familia": round(fam, 4),
                               "score_ativo": round(ativo, 4)})
        resultados.sort(key=lambda r: r["score"], reverse=True)
        return resultados[:k]


def formatar_contexto(chunks: Sequence[dict], max_chars: int = 3000) -> str:
    """Monta o bloco de contexto do prompt, com fonte citavel por trecho."""
    partes, total = [], 0
    for i, c in enumerate(chunks, start=1):
        cabecalho = (f"[FONTE {i}] {c['titulo_doc']} — {c['secao']} "
                     f"(p. {c['pagina']})")
        bloco = f"{cabecalho}\n{c['texto']}"
        if total + len(bloco) > max_chars:
            break
        partes.append(bloco)
        total += len(bloco)
    return "\n\n".join(partes)
