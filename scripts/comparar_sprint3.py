"""Comparativo antes/depois: assistente da Sprint 3 x assistente da Sprint 4.

O baseline (relatorios/sprint3_baseline/) é reavaliado com o MESMO critério da
Sprint 4 — métricas sobre o corpo da resposta, sem a linha de confiança — para
que a diferença medida venha das mudanças no assistente, não da régua.
Os números originais publicados na Sprint 3 também ficam no JSON, para rastreio.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from pln import avaliacao_rag as arag                                   # noqa: E402
from pln import rag                                                     # noqa: E402
from pln.assistente import (nivel_confianca, numeros_sem_suporte,       # noqa: E402
                            relevancia, remover_confianca)

BASE = RAIZ / "relatorios" / "sprint3_baseline"
REL = RAIZ / "relatorios"


def reavaliar_baseline() -> tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.read_csv(BASE / "respostas_assistente.csv")
    df["corpo"] = df["resposta"].map(remover_confianca)

    juiz = arag.JuizNLI()
    fiel = [juiz.faithfulness(c, r) for c, r in zip(df["contexto"], df["corpo"])]
    df["faithfulness_corpo"] = [f["faithfulness"] for f in fiel]

    indice = rag.IndiceVetorial.carregar(RAIZ / "indice_rag")
    df["answer_relevancy_corpo"] = arag.answer_relevancy(
        indice.carregar_modelo(), df["pergunta"], df["corpo"])
    df["numeros_sem_suporte"] = [";".join(numeros_sem_suporte(c, x, p)) for c, x, p in
                                 zip(df["corpo"], df["contexto"], df["pergunta"])]

    # Qual nível a régua nova daria às recuperações do baseline (mesmo índice).
    retriever = rag.Retriever(indice)
    dados = json.loads((RAIZ / "dados" / "perguntas_troubleshooting.json").read_text(encoding="utf-8"))
    fam = {"anomalia_eletrica": ["eletrica"], "anomalia_mecanica": ["mecanica"],
           "manutencao_preventiva": ["manutencao"]}
    cat = {p["id"]: p["categoria"] for p in dados["perguntas"]}
    df["relevancia_max"] = [
        round(max(relevancia(c) for c in retriever.buscar(p, k=4, familias=fam.get(cat[i]))), 4)
        for i, p in zip(df["id"], df["pergunta"])]

    fora = pd.read_csv(BASE / "fora_de_escopo.csv")
    fora["relevancia_max"] = [round(max(relevancia(c) for c in retriever.buscar(p, k=4)), 4)
                              for p in fora["pergunta"]]
    return df, fora


def main() -> None:
    antes, fora_antes = reavaliar_baseline()
    depois = pd.read_csv(REL / "respostas_assistente.csv")
    fora_depois = pd.read_csv(REL / "fora_de_escopo.csv")
    publicado = json.loads((BASE / "metricas_assistente.json").read_text(encoding="utf-8"))

    def bloco(df, fora, fiel, relev, conf_modelo, conf_sistema):
        return {
            "faithfulness_medio": round(float(df[fiel].mean()), 4),
            "answer_relevancy_medio": round(float(df[relev].mean()), 4),
            "respostas_com_citacao_pct": round(float((df["n_fontes_citadas"] > 0).mean()) * 100, 1),
            "fora_de_escopo_recusadas": f"{int(fora['recusou'].sum())} de {len(fora)}",
            "fora_de_escopo_nao_recusadas": fora.loc[fora["recusou"] == 0, "id"].tolist(),
            "confianca_exibida": df[conf_sistema].value_counts().to_dict(),
            "confianca_do_modelo": df[conf_modelo].value_counts().to_dict(),
            "respostas_com_numero_sem_suporte": df.loc[
                df["numeros_sem_suporte"].fillna("") != "", "id"].tolist(),
            "tempo_medio_s": round(float(df["segundos"].mean()), 1),
        }

    # Na Sprint 3 o usuário via a confiança declarada pelo modelo.
    comparativo = {
        "criterio": "métricas sobre o corpo da resposta (sem a linha de confiança)",
        "sprint3": bloco(antes, fora_antes, "faithfulness_corpo", "answer_relevancy_corpo",
                         "confianca_declarada", "confianca_declarada"),
        "sprint4": bloco(depois, fora_depois, "faithfulness", "answer_relevancy",
                         "confianca_declarada", "confianca_recuperacao"),
        "sprint3_publicado_original": {
            "faithfulness_medio": publicado["faithfulness_medio"],
            "answer_relevancy_medio": publicado["answer_relevancy_medio"],
            "observacao": "calculado com a linha de confiança dentro da resposta",
        },
        "relevancia_recuperacao": {
            "gabarito_min": float(antes["relevancia_max"].min()),
            "gabarito_por_id": dict(zip(antes["id"], antes["relevancia_max"])),
            "fora_de_escopo_por_id": dict(zip(fora_antes["id"], fora_antes["relevancia_max"])),
        },
        "nivel_que_a_regua_nova_daria_ao_baseline": {
            i: nivel_confianca([r]) for i, r in zip(antes["id"], antes["relevancia_max"])},
    }

    por_pergunta = antes[["id", "categoria", "pergunta", "faithfulness_corpo",
                          "answer_relevancy_corpo", "confianca_declarada",
                          "numeros_sem_suporte", "corpo"]].merge(
        depois[["id", "faithfulness", "answer_relevancy", "confianca_recuperacao",
                "confianca_declarada", "relevancia_max", "recusa_por_limiar",
                "numeros_sem_suporte", "corpo"]],
        on="id", suffixes=("_sprint3", "_sprint4"))
    por_pergunta = por_pergunta.rename(columns={
        "faithfulness_corpo": "faithfulness_sprint3", "faithfulness": "faithfulness_sprint4",
        "answer_relevancy_corpo": "answer_relevancy_sprint3",
        "answer_relevancy": "answer_relevancy_sprint4"})

    (REL / "comparativo_sprint3_sprint4.json").write_text(
        json.dumps(comparativo, ensure_ascii=False, indent=2), encoding="utf-8")
    por_pergunta.to_csv(REL / "comparativo_por_pergunta.csv", index=False, encoding="utf-8")
    print(json.dumps({k: comparativo[k] for k in ("sprint3", "sprint4")},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
