# -*- coding: utf-8 -*-
"""Classificacao textual dos eventos operacionais em cinco categorias."""

from __future__ import annotations

import re
import unicodedata
from typing import Sequence

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.pipeline import Pipeline, FeatureUnion

CATEGORIAS = (
    "manutencao_corretiva",
    "manutencao_preventiva",
    "anomalia_eletrica",
    "anomalia_mecanica",
    "operacao_normal",
)

ROTULOS_ZERO_SHOT = {
    "manutencao_corretiva": "conserto apos quebra",
    "manutencao_preventiva": "inspecao programada",
    "anomalia_eletrica": "problema eletrico",
    "anomalia_mecanica": "problema mecanico",
    "operacao_normal": "funcionamento normal",
}

HIPOTESE = "O texto trata de {}."

ROTULOS_ALTERNATIVOS = {
    "manutencao_corretiva": "reparo executado no equipamento apos uma falha",
    "manutencao_preventiva": "manutencao programada, inspecao ou lubrificacao de rotina",
    "anomalia_eletrica": "desvio eletrico observado, como corrente ou tensao fora do normal",
    "anomalia_mecanica": "desvio mecanico observado, como vibracao, ruido ou mancal quente",
    "operacao_normal": "registro de operacao normal, sem desvio nem intervencao",
}

MODELO_ZERO_SHOT = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"


ABREVIACOES = {
    r"\bmt\b": "motor",
    r"\bos\b": "ordem de servico",
    r"\bpm\b": "manutencao preventiva",
    r"\bmc\b": "manutencao corretiva",
    r"\bla\b": "lado acoplado",
    r"\bloa\b": "lado oposto ao acoplamento",
    r"\brpm\b": "rotacoes por minuto",
    r"\bvib\b": "vibracao",
    r"\btemp\b": "temperatura",
}


def normalizar(texto: str, expandir: bool = True) -> str:
    """Minusculas, remocao de acentos (NFKD) e expansao de abreviacoes."""
    t = unicodedata.normalize("NFKD", str(texto))
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    t = re.sub(r"[^\w\s,.%-]", " ", t)
    if expandir:
        for padrao, alvo in ABREVIACOES.items():
            t = re.sub(padrao, alvo, t)
    return re.sub(r"\s+", " ", t).strip()


def carregar_zero_shot(modelo: str = MODELO_ZERO_SHOT):
    """Instancia o pipeline zero-shot (baixa o modelo na primeira execucao)."""
    from transformers import pipeline  # import tardio: evita custo quando nao usado

    return pipeline("zero-shot-classification", model=modelo)


def classificar_zero_shot(textos: Sequence[str], classificador,
                          batch_size: int = 8) -> pd.DataFrame:
    """Aplica o classificador zero-shot e devolve rotulo previsto + score."""
    rotulos = [ROTULOS_ZERO_SHOT[c] for c in CATEGORIAS]
    inverso = {ROTULOS_ZERO_SHOT[c]: c for c in CATEGORIAS}

    saidas = classificador(list(textos), candidate_labels=rotulos,
                           hypothesis_template=HIPOTESE, batch_size=batch_size)
    if isinstance(saidas, dict):
        saidas = [saidas]

    linhas = []
    for texto, out in zip(textos, saidas):
        scores = {inverso[lab]: sc for lab, sc in zip(out["labels"], out["scores"])}
        melhor = max(scores, key=scores.get)
        linhas.append({
            "texto": texto,
            "pred": melhor,
            "score": scores[melhor],
            **{f"score_{c}": scores[c] for c in CATEGORIAS},
        })
    return pd.DataFrame(linhas)


def construir_baseline(C: float = 4.0) -> Pipeline:
    """TF-IDF palavra (1-2 gramas) + caractere (3-5 gramas) -> LogisticRegression."""
    caracteristicas = FeatureUnion([
        ("palavra", TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)),
        ("caractere", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5),
                                      min_df=2, sublinear_tf=True)),
    ])
    return Pipeline([
        ("features", caracteristicas),
        ("clf", LogisticRegression(C=C, max_iter=2000, class_weight="balanced")),
    ])


def avaliar(y_true: Sequence[str], y_pred: Sequence[str],
            nome: str = "modelo") -> dict:
    """F1 por categoria + macro/weighted F1 + matriz de confusao."""
    relatorio = classification_report(y_true, y_pred, labels=list(CATEGORIAS),
                                      output_dict=True, zero_division=0)
    matriz = confusion_matrix(y_true, y_pred, labels=list(CATEGORIAS))
    return {
        "nome": nome,
        "f1_por_categoria": {c: round(relatorio[c]["f1-score"], 4) for c in CATEGORIAS},
        "precision_por_categoria": {c: round(relatorio[c]["precision"], 4) for c in CATEGORIAS},
        "recall_por_categoria": {c: round(relatorio[c]["recall"], 4) for c in CATEGORIAS},
        "suporte": {c: int(relatorio[c]["support"]) for c in CATEGORIAS},
        "macro_f1": round(f1_score(y_true, y_pred, average="macro", zero_division=0), 4),
        "weighted_f1": round(f1_score(y_true, y_pred, average="weighted", zero_division=0), 4),
        "acuracia": round(relatorio["accuracy"], 4),
        "matriz_confusao": matriz.tolist(),
        "categorias": list(CATEGORIAS),
    }


def tabela_f1(*avaliacoes: dict) -> pd.DataFrame:
    """Consolida varias avaliacoes em uma tabela categoria x modelo."""
    dados = {}
    for av in avaliacoes:
        dados[av["nome"]] = {**av["f1_por_categoria"], "MACRO-F1": av["macro_f1"]}
    return pd.DataFrame(dados).round(3)


def matriz_confusao_df(avaliacao: dict) -> pd.DataFrame:
    return pd.DataFrame(avaliacao["matriz_confusao"],
                        index=[f"real:{c}" for c in avaliacao["categorias"]],
                        columns=[f"pred:{c}" for c in avaliacao["categorias"]])


def erros(df: pd.DataFrame, coluna_pred: str = "pred",
          coluna_gold: str = "categoria_gold") -> pd.DataFrame:
    """Subconjunto de erros para inspecao qualitativa no notebook."""
    err = df[df[coluna_pred] != df[coluna_gold]]
    colunas = [c for c in ("evento_id", "texto", coluna_gold, coluna_pred, "score", "ambiguo")
               if c in err.columns]
    return err[colunas]


def distribuicao_confianca(df: pd.DataFrame, limiar: float = 0.5) -> dict:
    """Fracao de predicoes abaixo do limiar de confianca (candidatas a revisao humana)."""
    if "score" not in df.columns:
        return {}
    baixa = df["score"] < limiar
    return {
        "limiar": limiar,
        "fracao_baixa_confianca": round(float(baixa.mean()), 4),
        "score_medio": round(float(df["score"].mean()), 4),
        "score_mediano": round(float(np.median(df["score"])), 4),
    }


MARCADORES_INTERVENCAO = (
    "trocad", "troca ", "troca d", "substitu", "reparo", "reparad", "corrigid",
    "corrigi", "rebobinamento", "reinstalad", "instalado", "realizada a troca",
    "retirado de operacao", "recalc", "solda",
)
MARCADORES_PROGRAMADA = (
    "preventiv", "programad", "rotina", "plano", "cronograma", "inspecao",
    "periodic", "anual", "trimestral", "semestral", "mensal", "checklist",
    "calibracao", "rota de lubrificacao", "preditiv",
)


def ajustar_por_regras(df: pd.DataFrame, coluna_pred: str = "pred",
                       coluna_texto: str = "texto") -> pd.Series:
    """Reclassifica anomalias que, no texto, descrevem intervencao ja executada."""
    ajustada = []
    for _, linha in df.iterrows():
        pred = linha[coluna_pred]
        texto = normalizar(linha[coluna_texto], expandir=False)
        if pred.startswith("anomalia") and any(m in texto for m in MARCADORES_INTERVENCAO):
            pred = ("manutencao_preventiva"
                    if any(m in texto for m in MARCADORES_PROGRAMADA)
                    else "manutencao_corretiva")
        ajustada.append(pred)
    return pd.Series(ajustada, index=df.index)
