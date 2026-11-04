# -*- coding: utf-8 -*-
"""Geracao de linguagem natural a partir dos parametros numericos de alerta."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

SEVERIDADES = ("leve", "moderado", "critico")

LEXICO = {
    "leve": {
        "abertura": "Registro informativo",
        "verbo_desvio": "apresentou variação",
        "qualificador": "pequena",
        "urgencia": "Nenhuma ação imediata requerida",
        "prazo": "acompanhar na próxima ronda",
    },
    "moderado": {
        "abertura": "Alerta moderado detectado",
        "verbo_desvio": "apresentou desvio",
        "qualificador": "relevante",
        "urgencia": "Recomenda-se verificação programada",
        "prazo": "dentro das próximas 24 horas",
    },
    "critico": {
        "abertura": "ALERTA CRÍTICO",
        "verbo_desvio": "atingiu desvio severo",
        "qualificador": "severa",
        "urgencia": "Intervenção imediata requerida",
        "prazo": "acionar manutenção no turno corrente",
    },
}

RECOMENDACOES = {
    "temperatura_enrolamento_c": {
        "leve": "verificar limpeza das aletas e obstruções no fluxo de ar",
        "moderado": "verificação do sistema de refrigeração e conferência da carga acionada",
        "critico": "reduzir carga e inspecionar refrigeração e isolamento do enrolamento",
    },
    "temperatura_mancal_c": {
        "leve": "conferir nível e validade da graxa na próxima rota de lubrificação",
        "moderado": "inspeção do mancal e revisão do plano de lubrificação",
        "critico": "parada para inspeção do mancal e substituição do rolamento",
    },
    "corrente_a": {
        "leve": "confrontar a leitura com o regime de carga do processo",
        "moderado": "verificação da carga acionada e do equilíbrio entre fases",
        "critico": "avaliar sobrecarga mecânica e proteções antes de manter o ativo em regime",
    },
    "tensao_v": {
        "leve": "registrar a ocorrência no acompanhamento de qualidade de energia",
        "moderado": "verificação do barramento de alimentação e das conexões do painel",
        "critico": "acionar a equipe elétrica para avaliação imediata da alimentação",
    },
    "rotacao_rpm": {
        "leve": "confirmar a estabilidade da carga acoplada",
        "moderado": "verificação do escorregamento e da carga aplicada ao eixo",
        "critico": "avaliar travamento mecânico ou perda de torque antes de religar",
    },
    "vibracao_mm_s": {
        "leve": "incluir o ativo na próxima coleta de análise de vibração",
        "moderado": "medição de vibração dedicada e conferência de alinhamento",
        "critico": "parada para verificação de alinhamento, balanceamento e rolamentos",
    },
    "fator_potencia": {
        "leve": "acompanhar o regime de carga durante o turno",
        "moderado": "verificação do regime de carga e do banco de capacitores",
        "critico": "avaliação imediata da correção de reativo da instalação",
    },
}

ARTIGOS = {
    "temperatura_enrolamento_c": "a",
    "temperatura_mancal_c": "a",
    "corrente_a": "a",
    "tensao_v": "a",
    "rotacao_rpm": "a",
    "vibracao_mm_s": "a",
    "fator_potencia": "o",
}

MESES = ("janeiro", "fevereiro", "março", "abril", "maio", "junho",
         "julho", "agosto", "setembro", "outubro", "novembro", "dezembro")


def _num(valor: float, casas: int = 1) -> str:
    """Numero em padrao pt-BR (virgula decimal), sem casas irrelevantes."""
    texto = f"{valor:.{casas}f}".replace(".", ",")
    return texto.rstrip("0").rstrip(",") if "," in texto else texto


def formatar_magnitude(alerta: dict) -> str:
    """`+18,8 C`, `-3,4%`, `-0,08` conforme o modo de magnitude do sensor."""
    mag = float(alerta["magnitude"])
    sinal = "+" if mag > 0 else "-"
    valor = _num(abs(mag), 2 if alerta["sensor"] == "fator_potencia" else 1)
    if alerta["modo_magnitude"] == "percentual":
        return f"{sinal}{valor}%"
    unidade = alerta.get("unidade") or ""
    return f"{sinal}{valor}{(' ' + unidade) if unidade else ''}"


def formatar_valor(alerta: dict, chave: str) -> str:
    casas = 2 if alerta["sensor"] == "fator_potencia" else 1
    unidade = alerta.get("unidade") or ""
    return f"{_num(float(alerta[chave]), casas)}{(' ' + unidade) if unidade else ''}"


def formatar_periodo(alerta: dict) -> str:
    """Descreve a janela temporal do desvio em linguagem de operador."""
    dur = int(alerta["duracao_h"])
    if dur <= 1:
        return "em leitura pontual"
    if dur < 24:
        return f"nas últimas {dur} horas"
    dias = dur / 24
    return f"de forma sustentada por {_num(dias)} dias"


def formatar_timestamp(ts: str) -> str:
    d = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
    return f"{d.day:02d}/{d.month:02d} às {d.hour:02d}h{d.minute:02d}"


@dataclass(frozen=True)
class Template:
    """Template de narrativa. `corpo` usa os slots preenchidos em `montar_slots`."""
    template_id: str
    severidade: str
    corpo: str


TEMPLATES: tuple[Template, ...] = (
    Template(
        "T-LEVE-01", "leve",
        "{abertura} no motor {tag} ({localizacao}). {artigo_cap} {sensor_rotulo} {verbo_desvio} "
        "de {magnitude} em relação ao baseline de {baseline} {periodo}, sem "
        "ultrapassar os limites operacionais. {urgencia}: {recomendacao}."
    ),
    Template(
        "T-LEVE-02", "leve",
        "{tag} sob observação: {sensor_rotulo} em {valor_atual} contra {baseline} de "
        "referência ({magnitude}), {periodo}. Desvio de baixa criticidade — {recomendacao}."
    ),
    Template(
        "T-MOD-01", "moderado",
        "{abertura} no motor {tag} ({localizacao}). {artigo_cap} {sensor_rotulo} {verbo_desvio} de "
        "{magnitude} acima_abaixo do baseline {periodo}, atingindo {valor_atual}. "
        "{urgencia} {prazo}: {recomendacao}."
    ),
    Template(
        "T-MOD-02", "moderado",
        "{abertura}: {tag} opera com {sensor_rotulo} em {valor_atual}, desvio {magnitude} "
        "sobre a referência de {baseline} {periodo}. Causa provável sob avaliação: "
        "{causa_provavel}. {urgencia} {prazo}."
    ),
    Template(
        "T-CRIT-01", "critico",
        "{abertura} — motor {tag} ({localizacao}). {artigo_cap} {sensor_rotulo} {verbo_desvio} de "
        "{magnitude} sobre o baseline de {baseline} {periodo}, com valor de pico em "
        "{valor_atual}. Risco de {consequencia}. {urgencia}: {recomendacao} — {prazo}."
    ),
    Template(
        "T-CRIT-02", "critico",
        "{abertura}: {tag} em condição {qualificador}. Leitura de {sensor_rotulo} registrada em "
        "{valor_atual} ({magnitude} vs. baseline) {periodo}. {urgencia} — {recomendacao}. "
        "Manter o ativo sob supervisão contínua até a intervenção."
    ),
)

CONSEQUENCIA = {
    "temperatura_enrolamento_c": "degradação do isolamento do enrolamento",
    "temperatura_mancal_c": "falha do rolamento por perda de lubrificação",
    "corrente_a": "atuação das proteções e parada não programada",
    "tensao_v": "sobreaquecimento por operação fora da faixa de tensão",
    "rotacao_rpm": "perda de produtividade e sobrecarga do acionamento",
    "vibracao_mm_s": "falha mecânica progressiva do conjunto rotativo",
    "fator_potencia": "penalização de reativo e sobrecarga da instalação",
}


def templates_por_severidade(severidade: str) -> list[Template]:
    return [t for t in TEMPLATES if t.severidade == severidade]


def montar_slots(alerta: dict) -> dict:
    sev = alerta["severidade"]
    lex = LEXICO[sev]
    sensor = alerta["sensor"]
    rotulo = alerta["sensor_rotulo"]
    return {
        **lex,
        "tag": alerta["tag"],
        "ativo_id": alerta["ativo_id"],
        "localizacao": alerta["localizacao"],
        "sensor_rotulo": rotulo,
        "sensor_rotulo_cap": rotulo[0].upper() + rotulo[1:],
        "artigo": ARTIGOS[sensor],
        "artigo_cap": ARTIGOS[sensor].upper(),
        "magnitude": formatar_magnitude(alerta),
        "baseline": formatar_valor(alerta, "baseline"),
        "valor_atual": formatar_valor(alerta, "valor_atual"),
        "periodo": formatar_periodo(alerta),
        "timestamp": formatar_timestamp(alerta["timestamp"]),
        "recomendacao": RECOMENDACOES[sensor][sev],
        "consequencia": CONSEQUENCIA[sensor],
        "causa_provavel": alerta["causa_provavel"],
    }


def _resolver_direcao(texto: str, alerta: dict) -> str:
    """Substitui o marcador `acima_abaixo` pela preposicao correta do desvio."""
    direcao = "acima" if float(alerta["magnitude"]) > 0 else "abaixo"
    return texto.replace("acima_abaixo", direcao)


def rastreio(alerta: dict) -> str:
    """Sufixo de rastreabilidade: liga a frase ao dado de sensor de origem."""
    return (f"[{alerta['alerta_id']} | sensor: {alerta['sensor']} | "
            f"pico: {formatar_timestamp(alerta['timestamp'])} | "
            f"baseline 7d = {formatar_valor(alerta, 'baseline')} | "
            f"janela movel: {alerta['janela_h']}h]")


def gerar_resumo(alerta: dict, variante: int = 0, com_rastreio: bool = True) -> dict:
    """Gera a narrativa de um alerta."""
    sev = alerta["severidade"]
    if sev not in SEVERIDADES:
        raise ValueError(f"severidade desconhecida: {sev}")
    opcoes = templates_por_severidade(sev)
    template = opcoes[variante % len(opcoes)]
    texto = template.corpo.format(**montar_slots(alerta))
    texto = _resolver_direcao(texto, alerta)
    trace = rastreio(alerta)
    return {
        "alerta_id": alerta["alerta_id"],
        "ativo_id": alerta["ativo_id"],
        "severidade": sev,
        "template_id": template.template_id,
        "texto": f"{texto} {trace}" if com_rastreio else texto,
        "texto_sem_rastreio": texto,
        "rastreio": trace,
    }


def gerar_resumos(alertas: Iterable[dict], com_rastreio: bool = True) -> list[dict]:
    """Gera resumos alternando as variantes de template dentro de cada severidade."""
    contador = {s: 0 for s in SEVERIDADES}
    saida = []
    for alerta in alertas:
        sev = alerta["severidade"]
        saida.append(gerar_resumo(alerta, variante=contador[sev], com_rastreio=com_rastreio))
        contador[sev] += 1
    return saida
