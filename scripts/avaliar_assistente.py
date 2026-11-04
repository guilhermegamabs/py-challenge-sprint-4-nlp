from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from pln import rag                      # noqa: E402
from pln import avaliacao_rag as arag    # noqa: E402
from pln.assistente import Assistente    # noqa: E402

CONTEXTO_POR_CATEGORIA = {
    "anomalia_eletrica": ["eletrica"],
    "anomalia_mecanica": ["mecanica"],
    "manutencao_preventiva": ["manutencao"],
    "especificacao": None,
}


def avaliar_retriever(retriever, perguntas) -> dict:
    configs = [
        ("denso_puro", dict(reranking=False)),
        ("denso_lexical", dict(reranking=True)),
        ("denso_lexical_contexto", dict(reranking=True, usar_contexto=True,
                                        contexto_por_categoria=CONTEXTO_POR_CATEGORIA)),
    ]
    saida = {"por_configuracao": [], "por_k": []}
    for nome, kw in configs:
        df = arag.avaliar_recuperacao(retriever, perguntas, k=4, **kw)
        saida["por_configuracao"].append(arag.resumo_recuperacao(df, nome))
        if nome == "denso_lexical":
            saida["detalhe_denso_lexical"] = df.to_dict(orient="records")
    for k in (1, 3, 4, 6, 10):
        df = arag.avaliar_recuperacao(retriever, perguntas, k=k)
        r = arag.resumo_recuperacao(df, f"k={k}")
        r["k"] = k
        saida["por_k"].append(r)
    return saida


def responder_gabarito(assistente, perguntas, parcial: Path | None = None) -> pd.DataFrame:
    """Gera as respostas do gabarito, salvando a cada item."""
    linhas = []
    ja_feitas = {}
    if parcial is not None and parcial.exists():
        anterior = pd.read_csv(parcial)
        ja_feitas = {r["id"]: r for r in anterior.to_dict(orient="records")}
        print(f"reaproveitando {len(ja_feitas)} respostas de {parcial.name}", flush=True)

    for i, p in enumerate(perguntas, start=1):
        if p["id"] in ja_feitas:
            linhas.append(ja_feitas[p["id"]])
            continue
        t0 = time.time()
        r = assistente.responder(p["pergunta"],
                                 familias=CONTEXTO_POR_CATEGORIA.get(p["categoria"]),
                                 usar_memoria=False)
        linhas.append({
            "id": p["id"],
            "categoria": p["categoria"],
            "pergunta": p["pergunta"],
            "resposta": r["resposta"],
            "resposta_referencia": p["resposta_referencia"],
            "contexto": r["contexto"],
            "corpo": r["corpo"],
            "chunks": ";".join(c["chunk_id"] for c in r["chunks"]),
            "relevancia_max": r["relevancia_max"],
            "recusa_por_limiar": int(r["recusa_por_limiar"]),
            "confianca_recuperacao": r["confianca_recuperacao"],
            "confianca_declarada": r["confianca_declarada"],
            "numeros_sem_suporte": ";".join(r["numeros_sem_suporte"]),
            "n_fontes_citadas": len(r["fontes_citadas"]),
            "segundos": round(time.time() - t0, 1),
        })
        print(f"[{i}/{len(perguntas)}] {p['id']} ({linhas[-1]['segundos']}s)", flush=True)
        if parcial is not None:
            pd.DataFrame(linhas).to_csv(parcial, index=False, encoding="utf-8")
    return pd.DataFrame(linhas)


def avaliar_fora_de_escopo(assistente, itens) -> pd.DataFrame:
    marcas = ("não trata", "nao trata", "não cobre", "nao cobre", "não há informa",
              "nao ha informa", "não consta", "nao consta", "fora do escopo",
              "não está disponível", "nao esta disponivel", "não disponível",
              "não inclui", "nao inclui", "não menciona", "nao menciona")
    linhas = []
    for item in itens:
        assistente.limpar_memoria()
        r = assistente.responder(item["pergunta"], usar_memoria=False)
        texto = r["resposta"].lower()
        linhas.append({
            "id": item["id"],
            "pergunta": item["pergunta"],
            "resposta": r["resposta"],
            "recusou": int(any(m in texto for m in marcas)),
            "recusa_por_limiar": int(r["recusa_por_limiar"]),
            "relevancia_max": r["relevancia_max"],
            "confianca_recuperacao": r["confianca_recuperacao"],
            "confianca_declarada": r["confianca_declarada"],
            "motivo_gabarito": item["motivo"],
        })
        print(f"[fora de escopo] {item['id']} recusou={linhas[-1]['recusou']}", flush=True)
    return pd.DataFrame(linhas)


def rodar_cenarios(assistente, contexto_sprint3: dict) -> list[dict]:
    """Tres cenarios de falha com o estado operacional real injetado no prompt."""
    cenarios = [
        {
            "cenario": "anomalia_eletrica",
            "ativo_id": "MT-007",
            "familias": ["eletrica"],
            "turnos": [
                "O fator de potência deste motor caiu de 0,95 para 0,88. O que pode explicar isso?",
                "A corrente também subiu 10%. Isso muda o diagnóstico?",
            ],
        },
        {
            "cenario": "anomalia_mecanica",
            "ativo_id": "MT-008",
            "familias": ["mecanica"],
            "turnos": [
                "A vibração deste motor mais que dobrou em cinco dias. O que verificar primeiro?",
                "O alinhamento foi conferido e está correto. O que mais pode causar isso?",
            ],
        },
        {
            "cenario": "manutencao_preventiva",
            "ativo_id": "MT-004",
            "familias": ["manutencao"],
            "turnos": [
                "Este motor vai ficar parado por três meses. Que cuidados de armazenamento devo tomar?",
                "E o que preciso inspecionar quando ele voltar a operar?",
            ],
        },
    ]
    saida = []
    for c in cenarios:
        assistente.limpar_memoria()
        estado = contexto_sprint3.get(c["ativo_id"])
        dialogo = []
        for turno in c["turnos"]:
            r = assistente.responder(turno, estado=estado, familias=c["familias"])
            dialogo.append({
                "pergunta": turno,
                "resposta": r["resposta"],
                "chunks": r["chunks"],
                "relevancia_max": r["relevancia_max"],
                "recusa_por_limiar": r["recusa_por_limiar"],
                "confianca_recuperacao": r["confianca_recuperacao"],
                "confianca_declarada": r["confianca_declarada"],
                "numeros_sem_suporte": r["numeros_sem_suporte"],
            })
            print(f"[cenario {c['cenario']}] turno respondido", flush=True)
        saida.append({**c, "estado": estado, "dialogo": dialogo})
    return saida


def contexto_operacional() -> dict:
    """Monta o estado por ativo a partir dos artefatos da Sprint 3."""
    alertas = json.loads((RAIZ / "dados" / "alertas.json").read_text(encoding="utf-8"))["alertas"]
    resumos = pd.read_csv(RAIZ / "relatorios" / "resumos_gerados.csv")
    ordem = {"critico": 0, "moderado": 1, "leve": 2}
    estados = {}
    for a in alertas:
        e = estados.setdefault(a["ativo_id"], {
            "ativo_id": a["ativo_id"], "tag": a["tag"], "pior": "leve", "alertas": []})
        if ordem[a["severidade"]] < ordem[e["pior"]]:
            e["pior"] = a["severidade"]
        texto = resumos.loc[resumos["alerta_id"] == a["alerta_id"], "texto_sem_rastreio"]
        if len(texto) and a["severidade"] != "leve":
            e["alertas"].append(texto.iloc[0])
    rotulo = {"critico": "EM RISCO — alertas críticos abertos",
              "moderado": "EM OBSERVAÇÃO — desvio moderado em acompanhamento",
              "leve": "ESTÁVEL COM DESVIO — apenas desvios leves"}
    for e in estados.values():
        e["situacao"] = rotulo[e.pop("pior")]
        e["alertas"] = e["alertas"][:3]
    return estados


def main() -> None:
    destino = RAIZ / "relatorios"
    destino.mkdir(exist_ok=True)

    if "--so-cenarios" in sys.argv:
        # Os cenários usam memória e estado; o gabarito não. Mudança que só
        # afeta diálogo (consulta com o turno anterior) não exige refazer tudo.
        indice = rag.IndiceVetorial.carregar(RAIZ / "indice_rag")
        cenarios = rodar_cenarios(Assistente(rag.Retriever(indice)), contexto_operacional())
        (destino / "cenarios_demo.json").write_text(
            json.dumps(cenarios, ensure_ascii=False, indent=2), encoding="utf-8")
        return
    dados = json.loads((RAIZ / "dados" / "perguntas_troubleshooting.json")
                       .read_text(encoding="utf-8"))
    perguntas, fora = dados["perguntas"], dados["fora_de_escopo"]

    indice = rag.IndiceVetorial.carregar(RAIZ / "indice_rag")
    retriever = rag.Retriever(indice)

    print("== retriever ==", flush=True)
    metricas_ret = avaliar_retriever(retriever, perguntas)
    (destino / "metricas_retriever.json").write_text(
        json.dumps(metricas_ret, ensure_ascii=False, indent=2), encoding="utf-8")
    for r in metricas_ret["por_configuracao"]:
        print(r, flush=True)

    print("\n== respostas do assistente ==", flush=True)
    assistente = Assistente(retriever)
    print(f"backend: {assistente.backend} | modelo: {assistente.modelo_nome}", flush=True)
    df = responder_gabarito(assistente, perguntas,
                            parcial=destino / "respostas_parcial.csv")
    df.to_csv(destino / "respostas_assistente.csv", index=False, encoding="utf-8")

    print("\n== fora de escopo ==", flush=True)
    df_fora = avaliar_fora_de_escopo(assistente, fora)
    df_fora.to_csv(destino / "fora_de_escopo.csv", index=False, encoding="utf-8")

    print("\n== cenarios de demonstracao ==", flush=True)
    cenarios = rodar_cenarios(assistente, contexto_operacional())
    (destino / "cenarios_demo.json").write_text(
        json.dumps(cenarios, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n== metricas de geracao ==", flush=True)
    # Sprint 4: métricas sobre o CORPO da resposta. A linha de confiança é
    # metadado do sistema, não afirmação técnica; na Sprint 3 ela entrava no
    # juiz NLI e contava como frase sem suporte. O baseline é recalculado com
    # o mesmo critério em scripts/comparar_sprint3.py.
    juiz = arag.JuizNLI()
    fiel = [juiz.faithfulness(c, r) for c, r in zip(df["contexto"], df["corpo"])]
    df["faithfulness"] = [f["faithfulness"] for f in fiel]
    df["n_sentencas"] = [f["n_sentencas"] for f in fiel]

    modelo_emb = indice.carregar_modelo()
    df["answer_relevancy"] = arag.answer_relevancy(modelo_emb, df["pergunta"], df["corpo"])
    rouge = arag.cobertura_referencia(df["corpo"], df["resposta_referencia"])
    df["rouge1_f"] = rouge["rouge1_f"].values
    df["rougeL_f"] = rouge["rougeL_f"].values
    df.to_csv(destino / "respostas_assistente.csv", index=False, encoding="utf-8")

    metricas = {
        "modelo_llm": assistente.modelo_nome,
        "n_perguntas": len(df),
        "faithfulness_medio": round(float(df["faithfulness"].mean()), 4),
        "answer_relevancy_medio": round(float(df["answer_relevancy"].mean()), 4),
        "rouge1_f_medio": round(float(df["rouge1_f"].mean()), 4),
        "rougeL_f_medio": round(float(df["rougeL_f"].mean()), 4),
        "respostas_com_citacao_pct": round(float((df["n_fontes_citadas"] > 0).mean()) * 100, 1),
        "confianca_declarada_pct": round(
            float((df["confianca_declarada"] != "NAO_DECLARADA").mean()) * 100, 1),
        "tempo_medio_s": round(float(df["segundos"].mean()), 1),
        "por_categoria": df.groupby("categoria")[
            ["faithfulness", "answer_relevancy", "rouge1_f"]].mean().round(4).to_dict(),
        "fora_de_escopo_recusa_pct": round(float(df_fora["recusou"].mean()) * 100, 1),
        "fora_de_escopo_recusa_por_limiar": int(df_fora["recusa_por_limiar"].sum()),
        "recusas_indevidas_no_gabarito": df.loc[df["recusa_por_limiar"] == 1, "id"].tolist(),
        "distribuicao_confianca_recuperacao": df["confianca_recuperacao"].value_counts().to_dict(),
        "distribuicao_confianca_modelo": df["confianca_declarada"].value_counts().to_dict(),
        "respostas_com_numero_sem_suporte": df.loc[
            df["numeros_sem_suporte"].fillna("") != "", "id"].tolist(),
        "faithfulness_por_confianca": df.groupby("confianca_recuperacao")[
            "faithfulness"].mean().round(4).to_dict(),
        "sentencas_sem_suporte": {
            row["id"]: f["sentencas_sem_suporte"]
            for row, f in zip(df.to_dict(orient="records"), fiel)
            if f["sentencas_sem_suporte"]
        },
    }
    (destino / "metricas_assistente.json").write_text(
        json.dumps(metricas, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in metricas.items()
                      if k not in ("sentencas_sem_suporte", "por_categoria")},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
