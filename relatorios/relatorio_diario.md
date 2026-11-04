# Relatório Operacional Diário — Frota de Motores Elétricos

**Período analisado:** 13/06/2026 23:00 a 14/06/2026 23:00  
**Ativos monitorados:** 8  
**Gerado automaticamente pelo módulo PLN (Sprint 3)** — cada afirmação referencia o dado de sensor de origem.

## 1. Resumo executivo

Foram emitidos **14 alertas** no período: 4 críticos, 5 moderados e 5 leves. 2 equipamento(s) em risco, 3 em observação e 2 sem desvio detectado no período.

Prioridade do turno: **MT-003, MT-008** — alertas críticos abertos.

| Ativo | Estado operacional | Alertas (C/M/L) | Sensores envolvidos |
|-------|--------------------|-----------------|---------------------|
| MT-001 | EM OBSERVAÇÃO | 0/1/0 | tensão de alimentação |
| MT-002 | EM OBSERVAÇÃO | 0/1/1 | corrente de linha, temperatura do enrolamento |
| MT-003 | EM RISCO | 2/2/0 | corrente de linha, rotação do eixo, temperatura do enrolamento, temperatura do mancal |
| MT-004 | NORMAL | 0/0/0 | — |
| MT-005 | ESTÁVEL COM DESVIO | 0/0/2 | corrente de linha, tensão de alimentação |
| MT-006 | NORMAL | 0/0/0 | — |
| MT-007 | EM OBSERVAÇÃO | 0/1/1 | corrente de linha, fator de potência |
| MT-008 | EM RISCO | 2/0/1 | temperatura do enrolamento, temperatura do mancal, vibração global |

## 2. Alertas emitidos

### 2.1 Severidade critico (4)

- ALERTA CRÍTICO — motor W22-160L-2P-30CV-3F (Área 3 — Ventilador de Exaustão). A corrente de linha atingiu desvio severo de +25,7% sobre o baseline de 72,1 A de forma sustentada por 5,6 dias, com valor de pico em 90,7 A. Risco de atuação das proteções e parada não programada. Intervenção imediata requerida: avaliar sobrecarga mecânica e proteções antes de manter o ativo em regime — acionar manutenção no turno corrente. [ALT-001 | sensor: corrente_a | pico: 11/06 às 12h00 | baseline 7d = 72,1 A | janela movel: 3h]
- ALERTA CRÍTICO: W22-160L-2P-30CV-3F em condição severa. Leitura de temperatura do enrolamento registrada em 92,3 C (+27,7 C vs. baseline) de forma sustentada por 6 dias. Intervenção imediata requerida — reduzir carga e inspecionar refrigeração e isolamento do enrolamento. Manter o ativo sob supervisão contínua até a intervenção. [ALT-002 | sensor: temperatura_enrolamento_c | pico: 11/06 às 13h00 | baseline 7d = 64,4 C | janela movel: 3h]
- ALERTA CRÍTICO — motor W22-112M-4P-7.5CV-3F (Linha de Produção B — Misturador Industrial). A temperatura do mancal atingiu desvio severo de +17,8 C sobre o baseline de 49,8 C de forma sustentada por 5,1 dias, com valor de pico em 67,1 C. Risco de falha do rolamento por perda de lubrificação. Intervenção imediata requerida: parada para inspeção do mancal e substituição do rolamento — acionar manutenção no turno corrente. [ALT-003 | sensor: temperatura_mancal_c | pico: 13/06 às 14h00 | baseline 7d = 49,8 C | janela movel: 3h]
- ALERTA CRÍTICO: W22-112M-4P-7.5CV-3F em condição severa. Leitura de vibração global registrada em 4,4 mm/s (+112,8% vs. baseline) de forma sustentada por 5 dias. Intervenção imediata requerida — parada para verificação de alinhamento, balanceamento e rolamentos. Manter o ativo sob supervisão contínua até a intervenção. [ALT-004 | sensor: vibracao_mm_s | pico: 12/06 às 15h00 | baseline 7d = 2,1 mm/s | janela movel: 6h]

### 2.2 Severidade moderado (5)

- Alerta moderado detectado no motor W22-100L-2P-3CV-1F (Linha de Produção A — Bomba Centrífuga 01). A tensão de alimentação apresentou desvio de +4,5% acima do baseline de forma sustentada por 4,1 dias, atingindo 230,1 V. Recomenda-se verificação programada dentro das próximas 24 horas: verificação do barramento de alimentação e das conexões do painel. [ALT-006 | sensor: tensao_v | pico: 11/06 às 20h00 | baseline 7d = 220,1 V | janela movel: 3h]
- Alerta moderado detectado: W22-132M-4P-15CV-3F opera com temperatura do enrolamento em 82 C, desvio +18,8 C sobre a referência de 63,5 C de forma sustentada por 5,2 dias. Causa provável sob avaliação: sistema de refrigeração ou carga acima do regime. Recomenda-se verificação programada dentro das próximas 24 horas. [ALT-007 | sensor: temperatura_enrolamento_c | pico: 12/06 às 15h00 | baseline 7d = 63,5 C | janela movel: 3h]
- Alerta moderado detectado no motor W22-160L-2P-30CV-3F (Área 3 — Ventilador de Exaustão). A rotação do eixo apresentou desvio de -1,9% abaixo do baseline de forma sustentada por 5,6 dias, atingindo 3472,5 RPM. Recomenda-se verificação programada dentro das próximas 24 horas: verificação do escorregamento e da carga aplicada ao eixo. [ALT-008 | sensor: rotacao_rpm | pico: 14/06 às 01h00 | baseline 7d = 3541,7 RPM | janela movel: 3h]
- Alerta moderado detectado: W22-160L-2P-30CV-3F opera com temperatura do mancal em 61,7 C, desvio +9,2 C sobre a referência de 52,8 C de forma sustentada por 4,7 dias. Causa provável sob avaliação: lubrificação ou pré-carga do rolamento. Recomenda-se verificação programada dentro das próximas 24 horas. [ALT-009 | sensor: temperatura_mancal_c | pico: 13/06 às 15h00 | baseline 7d = 52,8 C | janela movel: 3h]
- Alerta moderado detectado no motor WMagnet-IPM-50CV-3F (Linha de Produção A — Extrusora Principal). O fator de potência apresentou desvio de -0,08 abaixo do baseline de forma sustentada por 4,8 dias, atingindo 0,88. Recomenda-se verificação programada dentro das próximas 24 horas: verificação do regime de carga e do banco de capacitores. [ALT-011 | sensor: fator_potencia | pico: 14/06 às 19h00 | baseline 7d = 0,95 | janela movel: 6h]

### 2.3 Severidade leve (5)

- Registro informativo no motor W22-132M-4P-15CV-3F (Área 3 — Compressor Principal). A corrente de linha apresentou variação de +7% em relação ao baseline de 39 A nas últimas 4 horas, sem ultrapassar os limites operacionais. Nenhuma ação imediata requerida: confrontar a leitura com o regime de carga do processo. [ALT-014 | sensor: corrente_a | pico: 14/06 às 12h00 | baseline 7d = 39 A | janela movel: 3h]
- W22-225S-4P-75CV-3F sob observação: corrente de linha em 111,9 A contra 104,2 A de referência (+8,3%), de forma sustentada por 4,3 dias. Desvio de baixa criticidade — confrontar a leitura com o regime de carga do processo. [ALT-020 | sensor: corrente_a | pico: 13/06 às 10h00 | baseline 7d = 104,2 A | janela movel: 3h]
- Registro informativo no motor W22-225S-4P-75CV-3F (Área 5 — Moinho de Bolas). A tensão de alimentação apresentou variação de -3,4% em relação ao baseline de 380,1 V de forma sustentada por 4,2 dias, sem ultrapassar os limites operacionais. Nenhuma ação imediata requerida: registrar a ocorrência no acompanhamento de qualidade de energia. [ALT-021 | sensor: tensao_v | pico: 11/06 às 11h00 | baseline 7d = 380,1 V | janela movel: 3h]
- WMagnet-IPM-50CV-3F sob observação: corrente de linha em 77,7 A contra 69,4 A de referência (+10,1%), de forma sustentada por 4,6 dias. Desvio de baixa criticidade — confrontar a leitura com o regime de carga do processo. [ALT-023 | sensor: corrente_a | pico: 11/06 às 12h00 | baseline 7d = 69,4 A | janela movel: 3h]
- Registro informativo no motor W22-112M-4P-7.5CV-3F (Linha de Produção B — Misturador Industrial). A temperatura do enrolamento apresentou variação de +10,4 C em relação ao baseline de 62,4 C de forma sustentada por 4,4 dias, sem ultrapassar os limites operacionais. Nenhuma ação imediata requerida: verificar limpeza das aletas e obstruções no fluxo de ar. [ALT-024 | sensor: temperatura_enrolamento_c | pico: 13/06 às 13h00 | baseline 7d = 62,4 C | janela movel: 3h]

## 3. Equipamentos em risco

**MT-003 — W22-160L-2P-30CV-3F** (Área 3 — Ventilador de Exaustão) — estado **EM RISCO**: requer intervenção no turno corrente. Grandezas afetadas: corrente de linha, rotação do eixo, temperatura do enrolamento, temperatura do mancal. Alerta de maior severidade: ALT-001, corrente de linha em 90,7 A contra baseline de 72,1 A (11/06 às 12h00). [ALERTAS: ALT-001, ALT-002, ALT-008, ALT-009]

**MT-008 — W22-112M-4P-7.5CV-3F** (Linha de Produção B — Misturador Industrial) — estado **EM RISCO**: requer intervenção no turno corrente. Grandezas afetadas: temperatura do enrolamento, temperatura do mancal, vibração global. Alerta de maior severidade: ALT-003, temperatura do mancal em 67,1 C contra baseline de 49,8 C (13/06 às 14h00). [ALERTAS: ALT-003, ALT-004, ALT-024]

**MT-001 — W22-100L-2P-3CV-1F** (Linha de Produção A — Bomba Centrífuga 01) — estado **EM OBSERVAÇÃO**: requer verificação programada. Grandezas afetadas: tensão de alimentação. Alerta de maior severidade: ALT-006, tensão de alimentação em 230,1 V contra baseline de 220,1 V (11/06 às 20h00). [ALERTAS: ALT-006]

**MT-002 — W22-132M-4P-15CV-3F** (Área 3 — Compressor Principal) — estado **EM OBSERVAÇÃO**: requer verificação programada. Grandezas afetadas: corrente de linha, temperatura do enrolamento. Alerta de maior severidade: ALT-007, temperatura do enrolamento em 82 C contra baseline de 63,5 C (12/06 às 15h00). [ALERTAS: ALT-007, ALT-014]

**MT-007 — WMagnet-IPM-50CV-3F** (Linha de Produção A — Extrusora Principal) — estado **EM OBSERVAÇÃO**: requer verificação programada. Grandezas afetadas: corrente de linha, fator de potência. Alerta de maior severidade: ALT-011, fator de potência em 0,88 contra baseline de 0,95 (14/06 às 19h00). [ALERTAS: ALT-011, ALT-023]

## 4. Tendências observadas

- MT-003: tendência de alta da rotação do eixo a 2,65 RPM/dia (3472,4 RPM -> 3475,7 RPM). [FONTE: leituras_sensores.csv | MT-003 | rotacao_rpm | 13/06-14/06 | n=25]
- MT-003: tendência de queda da temperatura do enrolamento a 1,42 C/dia (91,5 C -> 89,7 C). [FONTE: leituras_sensores.csv | MT-003 | temperatura_enrolamento_c | 13/06-14/06 | n=25]
- MT-001: tendência de queda da tensão de alimentação a 0,68 V/dia (228 V -> 223,3 V). [FONTE: leituras_sensores.csv | MT-001 | tensao_v | 13/06-14/06 | n=25]
- MT-003: tendência de queda da corrente de linha a 0,67 A/dia (89,9 A -> 90,3 A). [FONTE: leituras_sensores.csv | MT-003 | corrente_a | 13/06-14/06 | n=25]

## 5. Recomendações preliminares

| Prazo | Ativo | Ação recomendada | Origem |
|-------|-------|------------------|--------|
| IMEDIATO | MT-003 | avaliar sobrecarga mecânica e proteções antes de manter o ativo em regime | ALT-001 (corrente_a) |
| IMEDIATO | MT-003 | reduzir carga e inspecionar refrigeração e isolamento do enrolamento | ALT-002 (temperatura_enrolamento_c) |
| IMEDIATO | MT-008 | parada para inspeção do mancal e substituição do rolamento | ALT-003 (temperatura_mancal_c) |
| IMEDIATO | MT-008 | parada para verificação de alinhamento, balanceamento e rolamentos | ALT-004 (vibracao_mm_s) |
| 24 h | MT-001 | verificação do barramento de alimentação e das conexões do painel | ALT-006 (tensao_v) |
| 24 h | MT-002 | verificação do sistema de refrigeração e conferência da carga acionada | ALT-007 (temperatura_enrolamento_c) |
| 24 h | MT-003 | verificação do escorregamento e da carga aplicada ao eixo | ALT-008 (rotacao_rpm) |
| 24 h | MT-003 | inspeção do mancal e revisão do plano de lubrificação | ALT-009 (temperatura_mancal_c) |
| 24 h | MT-007 | verificação do regime de carga e do banco de capacitores | ALT-011 (fator_potencia) |
| próxima ronda | MT-002 | confrontar a leitura com o regime de carga do processo | ALT-014 (corrente_a) |
| próxima ronda | MT-005 | confrontar a leitura com o regime de carga do processo | ALT-020 (corrente_a) |
| próxima ronda | MT-005 | registrar a ocorrência no acompanhamento de qualidade de energia | ALT-021 (tensao_v) |
| próxima ronda | MT-007 | confrontar a leitura com o regime de carga do processo | ALT-023 (corrente_a) |
| próxima ronda | MT-008 | verificar limpeza das aletas e obstruções no fluxo de ar | ALT-024 (temperatura_enrolamento_c) |

---

*Relatório gerado por `pln.relatorio.gerar_relatorio`. Baseline = média das leituras dos 7 dias anteriores ao período de observação. Alertas derivados de média móvel vs. baseline, conforme `scripts/gerar_leituras_alertas.py`.*