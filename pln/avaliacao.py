# -*- coding: utf-8 -*-
"""Avaliacao dos textos gerados: ROUGE + checklist de clareza, precisao e utilidade."""

from __future__ import annotations

import re
import unicodedata
from typing import Sequence

import pandas as pd
from rouge_score import rouge_scorer

TIPOS_ROUGE = ("rouge1", "rouge2", "rougeL")

VERBOS_ACAO = (
    "verificar", "verificacao", "inspecionar", "inspecao", "parada", "reduzir",
    "acionar", "conferir", "confrontar", "avaliar", "avaliacao", "medicao",
    "registrar", "incluir", "acompanhar", "confirmar", "manter", "revisao",
)

MARCADORES_URGENCIA = {
    "critico": ("imediata", "imediato", "turno corrente", "supervisao continua"),
    "moderado": ("verificacao programada", "24 horas", "proximas 24"),
    "leve": ("nenhuma acao imediata", "baixa criticidade", "proxima ronda", "observacao"),
}

LIMITES_TAMANHO = (18, 75)
MAX_PALAVRAS_FRASE = 42      # frase longa demais prejudica leitura em painel


def normalizar_texto(texto: str) -> str:
    t = unicodedata.normalize("NFKD", str(texto))
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t.lower()).strip()


def calcular_rouge(gerados: Sequence[str], referencias: Sequence[str],
                   ids: Sequence[str] | None = None) -> pd.DataFrame:
    """ROUGE-1/2/L (precision, recall, F1) por par gerado/referencia."""
    scorer = rouge_scorer.RougeScorer(list(TIPOS_ROUGE), use_stemmer=False)
    linhas = []
    for i, (ger, ref) in enumerate(zip(gerados, referencias)):
        s = scorer.score(normalizar_texto(ref), normalizar_texto(ger))
        linha = {"id": ids[i] if ids is not None else i}
        for tipo in TIPOS_ROUGE:
            linha[f"{tipo}_p"] = round(s[tipo].precision, 4)
            linha[f"{tipo}_r"] = round(s[tipo].recall, 4)
            linha[f"{tipo}_f"] = round(s[tipo].fmeasure, 4)
        linhas.append(linha)
    return pd.DataFrame(linhas)


def resumo_rouge(df_rouge: pd.DataFrame, agrupar_por: pd.Series | None = None) -> pd.DataFrame:
    """Media das F1 de ROUGE, global ou por grupo (ex.: severidade)."""
    colunas = [f"{t}_f" for t in TIPOS_ROUGE]
    if agrupar_por is None:
        return df_rouge[colunas].mean().to_frame("media_f1").round(4)
    tmp = df_rouge.copy()
    tmp["_grupo"] = list(agrupar_por)
    return tmp.groupby("_grupo")[colunas].mean().round(4)


def _numeros(texto: str) -> set[str]:
    """Numeros citados no texto, normalizados (virgula -> ponto, sem zeros a direita)."""
    brutos = re.findall(r"\d+(?:[.,]\d+)?", texto)
    saida = set()
    for b in brutos:
        v = b.replace(",", ".")
        try:
            f = float(v)
        except ValueError:
            continue
        saida.add(f"{f:.2f}".rstrip("0").rstrip("."))
    return saida


def _numeros_permitidos(alerta: dict) -> set[str]:
    """Numeros que a narrativa pode citar: derivados do proprio registro de alerta."""
    dur = int(alerta["duracao_h"])
    valores = [
        abs(float(alerta["magnitude"])), float(alerta["valor_atual"]),
        float(alerta["baseline"]), dur, dur / 24, int(alerta["janela_h"]),
    ]
    permitidos = set()
    for v in valores:
        for casas in (0, 1, 2):
            permitidos.add(f"{round(float(v), casas):.2f}".rstrip("0").rstrip("."))
    permitidos.update(re.findall(r"\d+", alerta["timestamp"]))
    permitidos.update(x.lstrip("0") or "0" for x in re.findall(r"\d+", alerta["timestamp"]))
    permitidos.update({"24", "7"})
    return permitidos


def checklist(resumo: dict, alerta: dict) -> dict:
    """Aplica os criterios de clareza, precisao, utilidade e rastreabilidade."""
    texto = resumo["texto_sem_rastreio"]
    norm = normalizar_texto(texto)
    palavras = norm.split()
    frases = [f for f in re.split(r"[.!?]\s+", norm) if f.strip()]

    tamanho_ok = LIMITES_TAMANHO[0] <= len(palavras) <= LIMITES_TAMANHO[1]
    frases_ok = all(len(f.split()) <= MAX_PALAVRAS_FRASE for f in frases)
    sem_placeholder = "{" not in texto and "}" not in texto and "acima_abaixo" not in texto

    tag_ok = normalizar_texto(alerta["tag"]) in norm
    grandeza_ok = normalizar_texto(alerta["sensor_rotulo"]) in norm
    texto_medidas = texto
    for identificador in (alerta["tag"], alerta["localizacao"], alerta["ativo_id"]):
        texto_medidas = re.sub(re.escape(identificador), " ", texto_medidas, flags=re.I)
    citados = _numeros(texto_medidas)
    permitidos = _numeros_permitidos(alerta)
    numeros_invalidos = sorted(citados - permitidos)
    sem_alucinacao = not numeros_invalidos
    direcao_ok = (("acima" in norm or "alta" in norm or "+" in texto)
                  if float(alerta["magnitude"]) > 0
                  else ("abaixo" in norm or "queda" in norm or "-" in texto))

    acao_ok = any(v in norm for v in VERBOS_ACAO)
    urgencia_ok = any(m in norm for m in MARCADORES_URGENCIA[alerta["severidade"]])

    rastreio_ok = (alerta["alerta_id"] in resumo["texto"]
                   and alerta["sensor"] in resumo["texto"])

    itens = {
        "clareza_tamanho": tamanho_ok,
        "clareza_frases_curtas": frases_ok,
        "clareza_sem_placeholder": sem_placeholder,
        "precisao_identifica_ativo": tag_ok,
        "precisao_identifica_grandeza": grandeza_ok,
        "precisao_sem_numero_alucinado": sem_alucinacao,
        "precisao_direcao_do_desvio": direcao_ok,
        "utilidade_recomendacao": acao_ok,
        "utilidade_tom_de_urgencia": urgencia_ok,
        "rastreabilidade_fonte": rastreio_ok,
    }
    return {
        "alerta_id": alerta["alerta_id"],
        "severidade": alerta["severidade"],
        "template_id": resumo["template_id"],
        "n_palavras": len(palavras),
        **itens,
        "numeros_invalidos": ";".join(numeros_invalidos),
        "score_checklist": round(sum(itens.values()) / len(itens), 3),
    }


def aplicar_checklist(resumos: Sequence[dict], alertas: Sequence[dict]) -> pd.DataFrame:
    indice = {a["alerta_id"]: a for a in alertas}
    return pd.DataFrame([checklist(r, indice[r["alerta_id"]]) for r in resumos])


def taxa_aprovacao(df_checklist: pd.DataFrame) -> pd.Series:
    """Percentual de resumos que atendem cada item do checklist."""
    colunas = [c for c in df_checklist.columns
               if df_checklist[c].dtype == bool]
    return (df_checklist[colunas].mean() * 100).round(1)
