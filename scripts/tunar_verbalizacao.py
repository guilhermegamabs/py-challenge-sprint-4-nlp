from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from pln import classificacao as cls

VARIANTES = {
    "v1_descritiva": (
        "Este registro de manutencao industrial descreve {}.",
        {
            "manutencao_corretiva": "reparo executado no equipamento apos uma falha",
            "manutencao_preventiva": "manutencao programada, inspecao ou lubrificacao de rotina",
            "anomalia_eletrica": "desvio eletrico observado, como corrente ou tensao fora do normal",
            "anomalia_mecanica": "desvio mecanico observado, como vibracao, ruido ou mancal quente",
            "operacao_normal": "registro de operacao normal, sem desvio nem intervencao",
        },
    ),
    "v2_curta": (
        "O texto trata de {}.",
        {
            "manutencao_corretiva": "conserto apos quebra",
            "manutencao_preventiva": "inspecao programada",
            "anomalia_eletrica": "problema eletrico",
            "anomalia_mecanica": "problema mecanico",
            "operacao_normal": "funcionamento normal",
        },
    ),
    "v3_acao_vs_observacao": (
        "Neste registro, o time de manutencao {}.",
        {
            "manutencao_corretiva": "trocou ou consertou uma peca porque o equipamento falhou",
            "manutencao_preventiva": "executou inspecao, lubrificacao ou troca programada antes de falhar",
            "anomalia_eletrica": "apenas observou uma medida eletrica anormal, como corrente, tensao ou fator de potencia",
            "anomalia_mecanica": "apenas observou um sintoma mecanico anormal, como vibracao, ruido, folga ou mancal quente",
            "operacao_normal": "registrou que o equipamento esta operando normalmente",
        },
    ),
}


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    df = pd.read_csv(RAIZ / "dados" / "eventos_operacionais.csv")
    amostra, _ = train_test_split(df, train_size=n, random_state=11,
                                  stratify=df["categoria_gold"])

    classificador = cls.carregar_zero_shot()
    resultados = []
    for nome, (hipotese, rotulos) in VARIANTES.items():
        cls.HIPOTESE = hipotese
        cls.ROTULOS_ZERO_SHOT = rotulos
        t0 = time.time()
        pred = cls.classificar_zero_shot(amostra["texto"].tolist(), classificador)
        macro = f1_score(amostra["categoria_gold"], pred["pred"],
                         average="macro", zero_division=0)
        por_classe = f1_score(amostra["categoria_gold"], pred["pred"],
                              labels=list(cls.CATEGORIAS), average=None, zero_division=0)
        resultados.append({"variante": nome, "macro_f1": round(float(macro), 4),
                           "segundos": round(time.time() - t0, 1),
                           **{c: round(float(v), 3) for c, v in zip(cls.CATEGORIAS, por_classe)}})
        print(resultados[-1], flush=True)

    print("\n" + pd.DataFrame(resultados).sort_values("macro_f1", ascending=False).to_string(index=False))


if __name__ == "__main__":
    main()
