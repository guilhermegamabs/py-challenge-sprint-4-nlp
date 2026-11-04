# -*- coding: utf-8 -*-
"""Relatorio operacional em linguagem natural (diario e semanal)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable, Sequence

import numpy as np
import pandas as pd

from .narrativa import (SEVERIDADES, formatar_timestamp, formatar_valor, gerar_resumo,
                        _num)

ORDEM_SEVERIDADE = {"critico": 0, "moderado": 1, "leve": 2}

ESTADO_POR_SEVERIDADE = {
    "critico": ("EM RISCO", "requer intervenção no turno corrente"),
    "moderado": ("EM OBSERVAÇÃO", "requer verificação programada"),
    "leve": ("ESTÁVEL COM DESVIO", "segue operando dentro dos limites"),
    None: ("NORMAL", "sem desvios detectados no período"),
}

LIMIAR_TENDENCIA = {
    "temperatura_enrolamento_c": 0.8,
    "temperatura_mancal_c": 0.6,
    "corrente_a": 0.5,
    "tensao_v": 0.6,
    "rotacao_rpm": 2.0,
    "vibracao_mm_s": 0.05,
    "fator_potencia": 0.005,
}

ROTULO_SENSOR = {
    "temperatura_enrolamento_c": "temperatura do enrolamento",
    "temperatura_mancal_c": "temperatura do mancal",
    "corrente_a": "corrente de linha",
    "tensao_v": "tensão de alimentação",
    "rotacao_rpm": "rotação do eixo",
    "vibracao_mm_s": "vibração global",
    "fator_potencia": "fator de potência",
}

UNIDADE_SENSOR = {
    "temperatura_enrolamento_c": "C",
    "temperatura_mancal_c": "C",
    "corrente_a": "A",
    "tensao_v": "V",
    "rotacao_rpm": "RPM",
    "vibracao_mm_s": "mm/s",
    "fator_potencia": "",
}


def _fonte_leitura(ativo_id: str, sensor: str, ini: datetime, fim: datetime, n: int) -> str:
    return (f"[FONTE: leituras_sensores.csv | {ativo_id} | {sensor} | "
            f"{ini.strftime('%d/%m')}-{fim.strftime('%d/%m')} | n={n}]")


def estado_do_ativo(alertas_ativo: Sequence[dict]) -> tuple[str, str, str | None]:
    """Estado operacional textual derivado da severidade maxima do ativo."""
    if not alertas_ativo:
        rotulo, frase = ESTADO_POR_SEVERIDADE[None]
        return rotulo, frase, None
    pior = min(alertas_ativo, key=lambda a: ORDEM_SEVERIDADE[a["severidade"]])["severidade"]
    rotulo, frase = ESTADO_POR_SEVERIDADE[pior]
    return rotulo, frase, pior


def calcular_tendencias(leituras: pd.DataFrame, alertas: Sequence[dict],
                        inicio: datetime, fim: datetime) -> list[dict]:
    """Inclinacao linear (unidade/dia) dos sensores com alerta no periodo."""
    df = leituras.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    janela = df[(df["timestamp"] >= inicio) & (df["timestamp"] <= fim)]

    pares = {(a["ativo_id"], a["sensor"]) for a in alertas}
    tendencias = []
    for ativo_id, sensor in sorted(pares):
        serie = janela[janela["ativo_id"] == ativo_id][["timestamp", sensor]].dropna()
        if len(serie) < 6:
            continue
        horas = (serie["timestamp"] - serie["timestamp"].min()).dt.total_seconds() / 3600
        coef = np.polyfit(horas / 24.0, serie[sensor].astype(float), 1)[0]
        if abs(coef) < LIMIAR_TENDENCIA.get(sensor, 0.0):
            continue
        tendencias.append({
            "ativo_id": ativo_id,
            "sensor": sensor,
            "sensor_rotulo": ROTULO_SENSOR[sensor],
            "unidade": UNIDADE_SENSOR[sensor],
            "inclinacao_dia": round(float(coef), 3),
            "n_leituras": int(len(serie)),
            "inicio": serie["timestamp"].min(),
            "fim": serie["timestamp"].max(),
            "valor_inicial": round(float(serie[sensor].iloc[0]), 2),
            "valor_final": round(float(serie[sensor].iloc[-1]), 2),
        })
    tendencias.sort(key=lambda t: abs(t["inclinacao_dia"]), reverse=True)
    return tendencias


def frase_tendencia(t: dict) -> str:
    direcao = "alta" if t["inclinacao_dia"] > 0 else "queda"
    un = f" {t['unidade']}" if t["unidade"] else ""
    return (f"{t['ativo_id']}: tendência de {direcao} da {t['sensor_rotulo']} a "
            f"{_num(abs(t['inclinacao_dia']), 2)}{un}/dia "
            f"({_num(t['valor_inicial'], 1)}{un} -> {_num(t['valor_final'], 1)}{un}). "
            + _fonte_leitura(t["ativo_id"], t["sensor"], t["inicio"], t["fim"], t["n_leituras"]))


def prioridade_recomendacao(alerta: dict) -> str:
    """Prazo sugerido conforme severidade — usado no bloco de recomendacoes."""
    return {"critico": "IMEDIATO", "moderado": "24 h", "leve": "próxima ronda"}[alerta["severidade"]]


def gerar_relatorio(alertas: Sequence[dict], leituras: pd.DataFrame,
                    periodo: str = "semanal",
                    referencia: datetime | None = None,
                    eventos_classificados: pd.DataFrame | None = None,
                    ativos_monitorados: Iterable[str] | None = None) -> str:
    """Monta o relatorio operacional em Markdown."""
    df = leituras.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    fim = referencia or df["timestamp"].max()
    dias = 1 if periodo == "diario" else 7
    inicio = fim - timedelta(days=dias)

    def _sobrepoe(a: dict) -> bool:
        ini_ep = datetime.strptime(a["timestamp_inicio"], "%Y-%m-%d %H:%M:%S")
        fim_ep = ini_ep + timedelta(hours=int(a["duracao_h"]))
        return ini_ep <= fim and fim_ep >= inicio

    sel = [a for a in alertas if _sobrepoe(a)]
    sel.sort(key=lambda a: (ORDEM_SEVERIDADE[a["severidade"]], a["ativo_id"]))

    universo = sorted(set(ativos_monitorados) if ativos_monitorados
                      else df["ativo_id"].unique().tolist())
    por_ativo: dict[str, list[dict]] = {a: [] for a in universo}
    for a in sel:
        por_ativo.setdefault(a["ativo_id"], []).append(a)

    contagem = {s: sum(1 for a in sel if a["severidade"] == s) for s in SEVERIDADES}
    em_risco = [a for a in universo
                if any(x["severidade"] == "critico" for x in por_ativo[a])]
    em_observacao = [a for a in universo
                     if a not in em_risco
                     and any(x["severidade"] == "moderado" for x in por_ativo[a])]
    normais = [a for a in universo if not por_ativo[a]]

    L: list[str] = []
    titulo = "Relatório Operacional Diário" if periodo == "diario" else "Relatório Operacional Semanal"
    L.append(f"# {titulo} — Frota de Motores Elétricos")
    L.append("")
    L.append(f"**Período analisado:** {inicio.strftime('%d/%m/%Y %H:%M')} a "
             f"{fim.strftime('%d/%m/%Y %H:%M')}  ")
    L.append(f"**Ativos monitorados:** {len(universo)}  ")
    L.append(f"**Gerado automaticamente pelo módulo PLN (Sprint 3)** — "
             f"cada afirmação referencia o dado de sensor de origem.")
    L.append("")

    L.append("## 1. Resumo executivo")
    L.append("")
    L.append(f"Foram emitidos **{len(sel)} alertas** no período: "
             f"{contagem['critico']} críticos, {contagem['moderado']} moderados e "
             f"{contagem['leve']} leves. "
             f"{len(em_risco)} equipamento(s) em risco, {len(em_observacao)} em observação e "
             f"{len(normais)} sem desvio detectado no período.")
    L.append("")
    if em_risco:
        L.append(f"Prioridade do turno: **{', '.join(em_risco)}** — alertas críticos abertos.")
        L.append("")

    L.append("| Ativo | Estado operacional | Alertas (C/M/L) | Sensores envolvidos |")
    L.append("|-------|--------------------|-----------------|---------------------|")
    for ativo in universo:
        lista = por_ativo[ativo]
        rotulo, _, _ = estado_do_ativo(lista)
        c = sum(1 for x in lista if x["severidade"] == "critico")
        m = sum(1 for x in lista if x["severidade"] == "moderado")
        lv = sum(1 for x in lista if x["severidade"] == "leve")
        sensores = ", ".join(sorted({ROTULO_SENSOR[x["sensor"]] for x in lista})) or "—"
        L.append(f"| {ativo} | {rotulo} | {c}/{m}/{lv} | {sensores} |")
    L.append("")

    L.append("## 2. Alertas emitidos")
    L.append("")
    if not sel:
        L.append("Nenhum alerta emitido no período.")
        L.append("")
    for i_sev, sev in enumerate(sorted(SEVERIDADES, key=ORDEM_SEVERIDADE.get), start=1):
        grupo = [a for a in sel if a["severidade"] == sev]
        if not grupo:
            continue
        L.append(f"### 2.{i_sev} Severidade {sev} ({len(grupo)})")
        L.append("")
        for i, alerta in enumerate(grupo):
            resumo = gerar_resumo(alerta, variante=i)
            L.append(f"- {resumo['texto']}")
        L.append("")

    L.append("## 3. Equipamentos em risco")
    L.append("")
    if not em_risco and not em_observacao:
        L.append("Nenhum equipamento classificado como em risco ou em observação no período.")
        L.append("")
    for ativo in em_risco + em_observacao:
        lista = sorted(por_ativo[ativo], key=lambda a: ORDEM_SEVERIDADE[a["severidade"]])
        rotulo, frase, pior = estado_do_ativo(lista)
        tag = lista[0]["tag"]
        loc = lista[0]["localizacao"]
        sensores = ", ".join(sorted({ROTULO_SENSOR[x["sensor"]] for x in lista}))
        ids = ", ".join(x["alerta_id"] for x in lista)
        L.append(f"**{ativo} — {tag}** ({loc}) — estado **{rotulo}**: {frase}. "
                 f"Grandezas afetadas: {sensores}. "
                 f"Alerta de maior severidade: {lista[0]['alerta_id']}, "
                 f"{lista[0]['sensor_rotulo']} em {formatar_valor(lista[0], 'valor_atual')} "
                 f"contra baseline de {formatar_valor(lista[0], 'baseline')} "
                 f"({formatar_timestamp(lista[0]['timestamp'])}). "
                 f"[ALERTAS: {ids}]")
        L.append("")

    L.append("## 4. Tendências observadas")
    L.append("")
    tend = calcular_tendencias(df, sel, inicio, fim)
    if not tend:
        L.append("Nenhuma tendência acima do limiar de reporte no período.")
        L.append("")
    for t in tend[:8]:
        L.append(f"- {frase_tendencia(t)}")
    if tend:
        L.append("")

    if eventos_classificados is not None and len(eventos_classificados):
        L.append("## 5. Eventos registrados (classificação automática)")
        L.append("")
        cont = eventos_classificados["pred"].value_counts()
        total_ev = int(cont.sum())
        L.append(f"{total_ev} registros textuais processados pelo classificador de eventos "
                 f"no histórico do período, distribuídos em: "
                 + ", ".join(f"{k.replace('_', ' ')} ({v})" for k, v in cont.items())
                 + ". [FONTE: eventos_operacionais.csv | classificador zero-shot]")
        L.append("")
        secao_reco = 6
    else:
        secao_reco = 5

    L.append(f"## {secao_reco}. Recomendações preliminares")
    L.append("")
    if not sel:
        L.append("Manter o plano de manutenção preventiva vigente.")
    else:
        L.append("| Prazo | Ativo | Ação recomendada | Origem |")
        L.append("|-------|-------|------------------|--------|")
        vistos = set()
        for alerta in sel:
            chave = (alerta["ativo_id"], alerta["sensor"])
            if chave in vistos:
                continue
            vistos.add(chave)
            resumo = gerar_resumo(alerta, com_rastreio=False)
            from .narrativa import RECOMENDACOES
            acao = RECOMENDACOES[alerta["sensor"]][alerta["severidade"]]
            L.append(f"| {prioridade_recomendacao(alerta)} | {alerta['ativo_id']} | "
                     f"{acao} | {alerta['alerta_id']} ({alerta['sensor']}) |")
    L.append("")
    L.append("---")
    L.append("")
    L.append("*Relatório gerado por `pln.relatorio.gerar_relatorio`. "
             "Baseline = média das leituras dos 7 dias anteriores ao período de observação. "
             "Alertas derivados de média móvel vs. baseline, conforme "
             "`scripts/gerar_leituras_alertas.py`.*")
    return "\n".join(L)
