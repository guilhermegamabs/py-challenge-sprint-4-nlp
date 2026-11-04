# -*- coding: utf-8 -*-
"""Metricas do pipeline RAG e do assistente conversacional (Sprint 4)."""

from __future__ import annotations

import re
from typing import Sequence

import numpy as np
import pandas as pd


def chunk_e_relevante(chunk: dict, fontes_gold: Sequence[dict]) -> bool:
    """Chunk relevante: documento certo e secao declarada no gabarito."""
    for fonte in fontes_gold:
        if chunk["doc_id"] != fonte["doc_id"]:
            continue
        if fonte["secao_contem"].lower() in chunk["secao"].lower():
            return True
    return False


def avaliar_recuperacao(retriever, perguntas: Sequence[dict], k: int = 4,
                        reranking: bool = True, usar_contexto: bool = False,
                        contexto_por_categoria: dict | None = None) -> pd.DataFrame:
    """Roda o retriever em cada pergunta e mede precisao, recall, hit e MRR."""
    linhas = []
    for p in perguntas:
        familias = None
        if usar_contexto and contexto_por_categoria:
            familias = contexto_por_categoria.get(p["categoria"])
        recuperados = retriever.buscar(p["pergunta"], k=k, familias=familias,
                                       reranking=reranking)
        marcas = [chunk_e_relevante(c, p["fontes_gold"]) for c in recuperados]
        docs_cobertos = {
            (c["doc_id"], f["secao_contem"])
            for c in recuperados for f in p["fontes_gold"]
            if chunk_e_relevante(c, [f])
        }
        primeira = next((i + 1 for i, m in enumerate(marcas) if m), 0)
        linhas.append({
            "id": p["id"],
            "categoria": p["categoria"],
            "precision": round(sum(marcas) / len(marcas), 4) if marcas else 0.0,
            "recall": round(len(docs_cobertos) / len(p["fontes_gold"]), 4),
            "hit": int(primeira > 0),
            "rr": round(1 / primeira, 4) if primeira else 0.0,
            "primeira_posicao": primeira,
            "top1_doc": recuperados[0]["doc_id"] if recuperados else "",
            "top1_secao": recuperados[0]["secao"][:60] if recuperados else "",
        })
    return pd.DataFrame(linhas)


def resumo_recuperacao(df: pd.DataFrame, nome: str) -> dict:
    return {
        "configuracao": nome,
        "context_precision": round(float(df["precision"].mean()), 4),
        "context_recall": round(float(df["recall"].mean()), 4),
        "hit_rate": round(float(df["hit"].mean()), 4),
        "mrr": round(float(df["rr"].mean()), 4),
    }


_FIM_DE_FRASE = re.compile(r"(?<=[.!?])\s+")


def sentencas(texto: str, minimo: int = 25) -> list[str]:
    """Frases da resposta, descartando fragmentos curtos (titulos, marcadores)."""
    limpo = re.sub(r"\[FONTE[^\]]*\]", " ", texto)
    return [s.strip() for s in _FIM_DE_FRASE.split(limpo) if len(s.strip()) >= minimo]


class JuizNLI:
    """Entailment sentenca-a-sentenca usando o modelo NLI multilingue offline."""

    def __init__(self, modelo: str = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"):
        from transformers import pipeline

        self._pipe = pipeline("zero-shot-classification", model=modelo)

    def sustenta(self, contexto: str, afirmacao: str, max_contexto: int = 1400) -> float:
        """Probabilidade de o contexto sustentar a afirmacao (0 a 1)."""
        saida = self._pipe(contexto[:max_contexto], candidate_labels=[afirmacao],
                           hypothesis_template="{}", multi_label=True)
        return float(saida["scores"][0])

    def faithfulness(self, contexto: str, resposta: str, limiar: float = 0.5) -> dict:
        frases = sentencas(resposta)
        if not frases:
            return {"faithfulness": 0.0, "n_sentencas": 0, "sentencas_sem_suporte": []}
        scores = [self.sustenta(contexto, f) for f in frases]
        apoiadas = [s >= limiar for s in scores]
        return {
            "faithfulness": round(sum(apoiadas) / len(apoiadas), 4),
            "score_medio": round(float(np.mean(scores)), 4),
            "n_sentencas": len(frases),
            "sentencas_sem_suporte": [f for f, ok in zip(frases, apoiadas) if not ok],
        }


def answer_relevancy(modelo_embedding, perguntas: Sequence[str],
                     respostas: Sequence[str]) -> list[float]:
    """Similaridade de cosseno entre a pergunta e a resposta gerada."""
    v_perg = modelo_embedding.encode(list(perguntas), normalize_embeddings=True)
    v_resp = modelo_embedding.encode(list(respostas), normalize_embeddings=True)
    return [round(float(np.dot(a, b)), 4) for a, b in zip(v_perg, v_resp)]


def cobertura_referencia(respostas: Sequence[str],
                         referencias: Sequence[str]) -> pd.DataFrame:
    """ROUGE da resposta gerada contra a resposta de referencia do gabarito."""
    from .avaliacao import calcular_rouge

    return calcular_rouge(respostas, referencias)
