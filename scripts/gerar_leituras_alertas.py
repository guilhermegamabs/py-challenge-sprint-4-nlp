from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
DADOS = RAIZ / "dados"
SEED = 20260601
INICIO = datetime(2026, 6, 1, 0, 0)
DIAS_BASELINE = 7 # janela de referencia
DIAS_OBSERVACAO = 7 # janela analisada pelo modulo de alertas
HORAS = (DIAS_BASELINE + DIAS_OBSERVACAO) * 24
GAP_MERGE_H = 6
MAX_EPISODIOS_SENSOR = 3   # teto de alertas por (ativo, sensor) na janela


@dataclass
class Ativo:
    ativo_id: str
    tag: str
    localizacao: str
    tensao_nominal: float
    corrente_nominal: float
    rotacao_nominal: float
    temp_enrolamento: float      # media saudavel
    temp_mancal: float
    vibracao: float              # mm/s RMS
    fator_potencia: float
    cenario: str = "normal"      # cenario injetado na janela de observacao
    ruido: dict = field(default_factory=dict)

ATIVOS = [
    Ativo("MT-001", "W22-100L-2P-3CV-1F", "Linha de Produção A — Bomba Centrífuga 01",
          220.0, 12.5, 3525, 58.0, 46.0, 1.8, 0.82, cenario="oscilacao_tensao_leve"),
    Ativo("MT-002", "W22-132M-4P-15CV-3F", "Área 3 — Compressor Principal",
          220.0, 38.5, 1760, 62.0, 50.0, 2.1, 0.86, cenario="rampa_termica_moderada"),
    Ativo("MT-003", "W22-160L-2P-30CV-3F", "Área 3 — Ventilador de Exaustão",
          220.0, 71.2, 3555, 63.0, 52.0, 2.4, 0.87, cenario="sobrecarga_critica"),
    Ativo("MT-004", "W22-80-4P-1CV-3F", "Linha de Produção B — Esteira Transportadora 02",
          220.0, 3.05, 1720, 45.0, 38.0, 1.2, 0.78, cenario="normal"),
    Ativo("MT-005", "W22-225S-4P-75CV-3F", "Área 5 — Moinho de Bolas",
          380.0, 103.0, 1780, 66.0, 55.0, 2.6, 0.89, cenario="subtensao_leve"),
    Ativo("MT-006", "W22-90L-6P-2CV-3F", "Área 3 — Bomba de Água Gelada",
          220.0, 6.18, 1155, 52.0, 43.0, 1.5, 0.80, cenario="normal"),
    Ativo("MT-007", "WMagnet-IPM-50CV-3F", "Linha de Produção A — Extrusora Principal",
          380.0, 68.5, 1800, 60.0, 48.0, 1.9, 0.95, cenario="queda_fp_moderada"),
    Ativo("MT-008", "W22-112M-4P-7.5CV-3F", "Linha de Produção B — Misturador Industrial",
          220.0, 19.8, 1750, 61.0, 49.0, 2.0, 0.84, cenario="desalinhamento_critico"),
]

TRANSIENTES = [
    ("MT-004", "corrente_a", 40, 5, 0.42),                 # pico de carga na esteira
    ("MT-004", "vibracao_mm_s", 96, 7, 0.55),              # correia desalinhada
    ("MT-001", "temperatura_mancal_c", 66, 6, 11.0),       # falta de lubrificacao
    ("MT-005", "vibracao_mm_s", 120, 9, 1.9),              # desbalanceamento do moinho
    ("MT-007", "temperatura_enrolamento_c", 84, 8, 14.5),  # bloqueio de ventilacao
    ("MT-002", "vibracao_mm_s", 132, 6, 0.75),             # folga na base
    ("MT-006", "tensao_v", 108, 4, -7.5),                  # afundamento de tensao
]

SENSORES = {
    "temperatura_enrolamento_c": {"rotulo": "temperatura do enrolamento", "unidade": "C",
                                  "janela_h": 3, "modo": "absoluto",
                                  "limiares": (5.0, 12.0, 20.0)},
    "temperatura_mancal_c": {"rotulo": "temperatura do mancal", "unidade": "C",
                             "janela_h": 3, "modo": "absoluto",
                             "limiares": (4.0, 9.0, 15.0)},
    "corrente_a": {"rotulo": "corrente de linha", "unidade": "A",
                   "janela_h": 3, "modo": "percentual",
                   "limiares": (5.0, 12.0, 20.0)},
    "tensao_v": {"rotulo": "tensão de alimentação", "unidade": "V",
                 "janela_h": 3, "modo": "percentual",
                 "limiares": (2.0, 4.0, 6.0)},
    "rotacao_rpm": {"rotulo": "rotação do eixo", "unidade": "RPM",
                    "janela_h": 3, "modo": "percentual",
                    "limiares": (0.5, 1.5, 3.0)},
    "vibracao_mm_s": {"rotulo": "vibração global", "unidade": "mm/s",
                      "janela_h": 6, "modo": "percentual",
                      "limiares": (25.0, 60.0, 100.0)},
    "fator_potencia": {"rotulo": "fator de potência", "unidade": "",
                       "janela_h": 6, "modo": "absoluto",
                       "limiares": (0.03, 0.06, 0.10)},
}

CAUSA_PROVAVEL = {
    "temperatura_enrolamento_c": ("sistema de refrigeração ou carga acima do regime",
                                  "termica"),
    "temperatura_mancal_c": ("lubrificação ou pré-carga do rolamento", "mecanica"),
    "corrente_a": ("sobrecarga mecânica no acionamento", "eletrica"),
    "tensao_v": ("qualidade de energia no barramento de alimentação", "eletrica"),
    "rotacao_rpm": ("escorregamento por variação de carga", "mecanica"),
    "vibracao_mm_s": ("desalinhamento, desbalanceamento ou desgaste de rolamento",
                      "mecanica"),
    "fator_potencia": ("regime de carga parcial ou banco de capacitores", "eletrica"),
}

def _perfil_carga(h: int) -> float:
    """Fator de carga por hora do dia: turno diurno mais carregado."""
    hora = h % 24
    return 0.82 + 0.18 * np.sin((hora - 6) / 24 * 2 * np.pi) ** 2 + (0.06 if 8 <= hora <= 18 else 0.0)


def _rampa(h: int, inicio_h: int, duracao_h: int) -> float:
    """Rampa 0 -> 1 iniciando em inicio_h e saturando apos duracao_h."""
    if h < inicio_h:
        return 0.0
    return float(min(1.0, (h - inicio_h) / duracao_h))


def simular_leituras(rng: np.random.Generator) -> pd.DataFrame:
    linhas = []
    h_obs = DIAS_BASELINE * 24  # primeira hora da janela de observacao

    for at in ATIVOS:
        for h in range(HORAS):
            ts = INICIO + timedelta(hours=h)
            carga = _perfil_carga(h)

            temp_enr = at.temp_enrolamento * (0.94 + 0.09 * carga) + rng.normal(0, 0.8)
            temp_man = at.temp_mancal * (0.95 + 0.07 * carga) + rng.normal(0, 0.6)
            corrente = at.corrente_nominal * (0.90 + 0.12 * carga) + rng.normal(0, 0.012 * at.corrente_nominal)
            tensao = at.tensao_nominal + rng.normal(0, 1.4)
            rotacao = at.rotacao_nominal * (1.0 - 0.004 * carga) + rng.normal(0, 1.6)
            vibracao = at.vibracao * (0.95 + 0.10 * carga) + rng.normal(0, 0.05)
            fp = at.fator_potencia + rng.normal(0, 0.006)

            if at.cenario == "rampa_termica_moderada":
                r = _rampa(h, h_obs + 24, 60)
                temp_enr += 16.0 * r
                corrente += 0.05 * at.corrente_nominal * r
            elif at.cenario == "sobrecarga_critica":
                r = _rampa(h, h_obs + 12, 72)
                temp_enr += 26.0 * r
                corrente += 0.24 * at.corrente_nominal * r
                rotacao -= 0.018 * at.rotacao_nominal * r
                temp_man += 8.0 * r
            elif at.cenario == "desalinhamento_critico":
                r = _rampa(h, h_obs + 30, 66)
                vibracao += 1.15 * at.vibracao * r
                temp_man += 17.0 * r
                temp_enr += 9.0 * r
            elif at.cenario == "subtensao_leve":
                r = _rampa(h, h_obs + 48, 24)
                tensao -= 0.028 * at.tensao_nominal * r
                corrente += 0.06 * at.corrente_nominal * r
            elif at.cenario == "queda_fp_moderada":
                r = _rampa(h, h_obs + 36, 36)
                fp -= 0.075 * r
                corrente += 0.08 * at.corrente_nominal * r
            elif at.cenario == "oscilacao_tensao_leve":
                r = _rampa(h, h_obs + 60, 12)
                tensao += rng.normal(0, 2.2) + 5.2 * r

            linhas.append({
                "ativo_id": at.ativo_id,
                "tag": at.tag,
                "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "temperatura_enrolamento_c": round(float(temp_enr), 2),
                "temperatura_mancal_c": round(float(temp_man), 2),
                "corrente_a": round(float(corrente), 2),
                "tensao_v": round(float(tensao), 1),
                "rotacao_rpm": round(float(rotacao), 1),
                "vibracao_mm_s": round(float(vibracao), 2),
                "fator_potencia": round(float(fp), 3),
            })

    df = pd.DataFrame(linhas)

    h_idx = (pd.to_datetime(df["timestamp"]) - INICIO).dt.total_seconds() // 3600
    for ativo_id, sensor, inicio_rel, dur, delta in TRANSIENTES:
        ini = h_obs + inicio_rel
        mask = (df["ativo_id"] == ativo_id) & (h_idx >= ini) & (h_idx < ini + dur)
        pos = (h_idx[mask] - ini + 0.5) / dur
        perfil = np.sin(pos * np.pi) ** 0.5
        df.loc[mask, sensor] = (df.loc[mask, sensor] + delta * perfil).round(2)

    return df


def _severidade(magnitude_abs: float, limiares: tuple[float, float, float]) -> str | None:
    leve, moderado, critico = limiares
    if magnitude_abs >= critico:
        return "critico"
    if magnitude_abs >= moderado:
        return "moderado"
    if magnitude_abs >= leve:
        return "leve"
    return None


def detectar_alertas(df: pd.DataFrame) -> list[dict]:
    alertas: list[dict] = []
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    corte = INICIO + timedelta(days=DIAS_BASELINE)
    meta_ativo = {a.ativo_id: a for a in ATIVOS}

    for ativo_id, g in df.groupby("ativo_id", sort=True):
        g = g.sort_values("timestamp").reset_index(drop=True)
        base = g[g["timestamp"] < corte]
        obs = g[g["timestamp"] >= corte]

        for sensor, cfg in SENSORES.items():
            b_mean = float(base[sensor].mean())
            b_std = float(base[sensor].std(ddof=0))
            janela = cfg["janela_h"]
            movel = obs[sensor].rolling(janela, min_periods=janela).mean()

            desvio = movel - b_mean
            if cfg["modo"] == "percentual":
                magnitude = desvio / b_mean * 100.0
            else:
                magnitude = desvio

            sev = magnitude.abs().map(lambda m: _severidade(m, cfg["limiares"]))
            ativo_flag = np.array(sev.notna().to_numpy(), dtype=bool, copy=True)

            n = len(ativo_flag)
            ultimo = -999
            for k in range(n):
                if ativo_flag[k]:
                    if 0 < k - ultimo <= GAP_MERGE_H:
                        ativo_flag[ultimo + 1:k] = True
                    ultimo = k

            i = 0
            episodios_sensor: list[dict] = []
            while i < n:
                if not ativo_flag[i]:
                    i += 1
                    continue
                j = i
                while j + 1 < n and ativo_flag[j + 1]:
                    j += 1
                bloco = slice(i, j + 1)
                mags = magnitude.iloc[bloco]
                idx_pico = mags.abs().idxmax()
                mag_pico = float(magnitude.loc[idx_pico])
                sev_max = _severidade(abs(mag_pico), cfg["limiares"])
                duracao = int(j - i + 1)
                inicio_ts = obs["timestamp"].iloc[i]
                pico_ts = obs["timestamp"].loc[idx_pico]
                at = meta_ativo[ativo_id]
                causa, familia = CAUSA_PROVAVEL[sensor]

                episodios_sensor.append({
                    "alerta_id": "",  # atribuido apos ordenacao
                    "ativo_id": ativo_id,
                    "tag": at.tag,
                    "localizacao": at.localizacao,
                    "sensor": sensor,
                    "sensor_rotulo": cfg["rotulo"],
                    "unidade": cfg["unidade"],
                    "tipo_desvio": "alta" if mag_pico > 0 else "queda",
                    "modo_magnitude": cfg["modo"],
                    "magnitude": round(mag_pico, 2),
                    "baseline": round(b_mean, 2),
                    "baseline_desvio_padrao": round(b_std, 3),
                    "valor_atual": round(float(obs[sensor].loc[idx_pico]), 2),
                    "z_score": round(mag_pico / b_std, 2) if cfg["modo"] == "absoluto" and b_std > 0
                               else round((float(obs[sensor].loc[idx_pico]) - b_mean) / b_std, 2) if b_std > 0 else 0.0,
                    "janela_h": janela,
                    "duracao_h": duracao,
                    "severidade": sev_max,
                    "timestamp_inicio": inicio_ts.strftime("%Y-%m-%d %H:%M:%S"),
                    "timestamp": pico_ts.strftime("%Y-%m-%d %H:%M:%S"),
                    "causa_provavel": causa,
                    "familia": familia,
                    "cenario_simulado": at.cenario,
                })
                i = j + 1

            episodios_sensor.sort(key=lambda e: abs(e["magnitude"]), reverse=True)
            alertas.extend(episodios_sensor[:MAX_EPISODIOS_SENSOR])

    ordem = {"critico": 0, "moderado": 1, "leve": 2}
    alertas.sort(key=lambda a: (ordem[a["severidade"]], a["ativo_id"], a["sensor"]))
    for k, a in enumerate(alertas, start=1):
        a["alerta_id"] = f"ALT-{k:03d}"
    return alertas


def main() -> None:
    rng = np.random.default_rng(SEED)
    DADOS.mkdir(parents=True, exist_ok=True)

    df = simular_leituras(rng)
    caminho_leituras = DADOS / "leituras_sensores.csv"
    df.to_csv(caminho_leituras, index=False, encoding="utf-8")

    alertas = detectar_alertas(df)
    payload = {
        "metadata": {
            "descricao": "Alertas detectados por desvio de media movel vs baseline de 7 dias.",
            "gerado_por": "scripts/gerar_leituras_alertas.py",
            "seed": SEED,
            "janela_baseline_dias": DIAS_BASELINE,
            "janela_observacao_dias": DIAS_OBSERVACAO,
            "total_alertas": len(alertas),
            "por_severidade": {
                s: sum(1 for a in alertas if a["severidade"] == s)
                for s in ("critico", "moderado", "leve")
            },
        },
        "alertas": alertas,
    }
    (DADOS / "alertas.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"leituras: {len(df)} linhas -> {caminho_leituras}")
    print(f"alertas : {len(alertas)} -> {DADOS / 'alertas.json'}")
    for s in ("critico", "moderado", "leve"):
        print(f"  {s:9s}: {payload['metadata']['por_severidade'][s]}")
    for a in alertas:
        print(f"  {a['alerta_id']} {a['ativo_id']} {a['sensor']:26s} "
              f"{a['severidade']:8s} mag={a['magnitude']:+8.2f} dur={a['duracao_h']}h")


if __name__ == "__main__":
    main()
