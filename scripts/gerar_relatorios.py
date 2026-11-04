from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from pln import avaliacao as av
from pln.narrativa import gerar_resumos
from pln.relatorio import gerar_relatorio


def main() -> None:
    alertas = json.loads((RAIZ / "dados" / "alertas.json").read_text(encoding="utf-8"))["alertas"]
    referencias = {r["alerta_id"]: r["resumo_referencia"] for r in
                   json.loads((RAIZ / "dados" / "alertas_referencia.json")
                              .read_text(encoding="utf-8"))["referencias"]}
    leituras = pd.read_csv(RAIZ / "dados" / "leituras_sensores.csv")

    resumos = gerar_resumos(alertas)
    df_resumos = pd.DataFrame(resumos)
    df_resumos["resumo_referencia"] = df_resumos["alerta_id"].map(referencias)
    df_resumos.to_csv(RAIZ / "relatorios" / "resumos_gerados.csv",
                      index=False, encoding="utf-8")

    df_rouge = av.calcular_rouge(df_resumos["texto_sem_rastreio"],
                                 df_resumos["resumo_referencia"],
                                 df_resumos["alerta_id"])
    df_check = av.aplicar_checklist(resumos, alertas)
    df_check.to_csv(RAIZ / "relatorios" / "checklist_narrativa.csv",
                    index=False, encoding="utf-8")

    metricas = {
        "n_alertas": len(alertas),
        "rouge_global_f1": av.resumo_rouge(df_rouge)["media_f1"].to_dict(),
        "rouge_por_severidade_f1": av.resumo_rouge(
            df_rouge, df_resumos["severidade"]).to_dict(),
        "checklist_taxa_aprovacao_pct": av.taxa_aprovacao(df_check).to_dict(),
        "checklist_score_medio": round(float(df_check["score_checklist"].mean()), 4),
        "tamanho_medio_palavras": round(float(df_check["n_palavras"].mean()), 1),
    }

    caminho_zs = RAIZ / "relatorios" / "classificacao_zero_shot.csv"
    eventos = None
    if caminho_zs.exists():
        eventos = pd.read_csv(caminho_zs)
        eventos_meta = pd.read_csv(RAIZ / "dados" / "eventos_operacionais.csv")
        eventos = eventos.merge(eventos_meta[["evento_id", "ativo_id"]], on="evento_id",
                                how="left")
        if "pred_hibrido" in eventos.columns:   # predicao final = zero-shot + regras
            eventos["pred"] = eventos["pred_hibrido"]

    semanal = gerar_relatorio(alertas, leituras, periodo="semanal",
                              eventos_classificados=eventos)
    diario = gerar_relatorio(alertas, leituras, periodo="diario",
                             eventos_classificados=None)
    (RAIZ / "relatorios" / "relatorio_semanal.md").write_text(semanal, encoding="utf-8")
    (RAIZ / "relatorios" / "relatorio_diario.md").write_text(diario, encoding="utf-8")

    ref_relatorio = RAIZ / "dados" / "relatorio_referencia.md"
    if ref_relatorio.exists():
        gerado_secao = semanal.split("## 2.")[0]
        metricas["rouge_relatorio_semanal_f1"] = av.calcular_rouge(
            [gerado_secao], [ref_relatorio.read_text(encoding="utf-8")],
            ["relatorio_semanal"]).iloc[0].to_dict()

    (RAIZ / "relatorios" / "metricas_narrativa.json").write_text(
        json.dumps(metricas, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(metricas, ensure_ascii=False, indent=2))
    print("\n--- previa do relatorio semanal ---\n")
    print("\n".join(semanal.splitlines()[:40]))


if __name__ == "__main__":
    main()
