from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from pln import classificacao as cls  # noqa: E402

SEED = 42
TEST_SIZE = 0.4


def main() -> None:
    df = pd.read_csv(RAIZ / "dados" / "eventos_operacionais.csv")
    treino, teste = train_test_split(
        df, test_size=TEST_SIZE, random_state=SEED, stratify=df["categoria_gold"]
    )

    pipe = cls.construir_baseline()
    pipe.fit(treino["texto"].map(cls.normalizar), treino["categoria_gold"])
    pred_base = pipe.predict(teste["texto"].map(cls.normalizar))
    av_base = cls.avaliar(teste["categoria_gold"], pred_base, nome="tfidf_logreg")

    caminho_zs = RAIZ / "relatorios" / "classificacao_zero_shot.csv"
    if caminho_zs.exists() and os.environ.get("RECOMPUTAR_ZERO_SHOT") != "1":
        print(f"reaproveitando {caminho_zs.name}", flush=True)
        pred_zs = pd.read_csv(caminho_zs)
    else:
        print("carregando modelo zero-shot...", flush=True)
        zs = cls.carregar_zero_shot()
        print(f"inferindo em {len(df)} eventos (CPU)...", flush=True)
        pred_zs = cls.classificar_zero_shot(df["texto"].tolist(), zs)
        pred_zs.insert(0, "evento_id", df["evento_id"].values)
        pred_zs["categoria_gold"] = df["categoria_gold"].values
        pred_zs["ambiguo"] = df["ambiguo"].values

    pred_zs["pred_hibrido"] = cls.ajustar_por_regras(pred_zs)
    pred_zs.to_csv(caminho_zs, index=False, encoding="utf-8")

    av_zs_total = cls.avaliar(pred_zs["categoria_gold"], pred_zs["pred"],
                              nome="zero_shot_mdeberta_total")
    sub = pred_zs[pred_zs["evento_id"].isin(teste["evento_id"])]
    av_zs_teste = cls.avaliar(sub["categoria_gold"], sub["pred"],
                              nome="zero_shot_mdeberta")
    av_hib_teste = cls.avaliar(sub["categoria_gold"], sub["pred_hibrido"],
                               nome="zero_shot_regras")
    av_hib_total = cls.avaliar(pred_zs["categoria_gold"], pred_zs["pred_hibrido"],
                               nome="zero_shot_regras_total")

    metricas = {
        "config": {"seed": SEED, "test_size": TEST_SIZE,
                   "n_total": int(len(df)), "n_treino": int(len(treino)),
                   "n_teste": int(len(teste)),
                   "modelo_zero_shot": cls.MODELO_ZERO_SHOT},
        "zero_shot_teste": av_zs_teste,
        "zero_shot_total": av_zs_total,
        "hibrido_teste": av_hib_teste,
        "hibrido_total": av_hib_total,
        "baseline_teste": av_base,
        "confianca_zero_shot": cls.distribuicao_confianca(pred_zs),
    }
    (RAIZ / "relatorios" / "metricas_classificacao.json").write_text(
        json.dumps(metricas, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== macro-F1 ===")
    print(f"zero-shot (teste) : {av_zs_teste['macro_f1']}")
    print(f"zero-shot (total) : {av_zs_total['macro_f1']}")
    print(f"zs+regras (teste) : {av_hib_teste['macro_f1']}")
    print(f"zs+regras (total) : {av_hib_total['macro_f1']}")
    print(f"tfidf+logreg      : {av_base['macro_f1']}")
    print("\n=== F1 por categoria (teste) ===")
    print(cls.tabela_f1(av_zs_teste, av_hib_teste, av_base).to_string())
    print("\n=== erros zero-shot (total) ===")
    e = cls.erros(pred_zs)
    print(f"{len(e)} erros de {len(pred_zs)}")
    for _, r in e.head(15).iterrows():
        print(f"  {r['evento_id']} gold={r['categoria_gold']:22s} pred={r['pred']:22s} "
              f"score={r['score']:.2f} amb={r['ambiguo']} | {r['texto'][:80]}")


if __name__ == "__main__":
    main()
