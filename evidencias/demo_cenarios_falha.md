# Demonstração — três cenários de falha (execução real)

Gerado por `scripts/avaliar_assistente.py` (Qwen2.5-3B Q4, CPU) e transcrito por `scripts/gerar_evidencias.py`. Texto do assistente sem edição.

## Anomalia eletrica — MT-007

**Estado injetado no prompt:** EM OBSERVAÇÃO — desvio moderado em acompanhamento
- Alerta moderado detectado no motor WMagnet-IPM-50CV-3F (Linha de Produção A — Extrusora Principal). O fator de potência apresentou desvio de -0,08 abaixo do baseline de forma sustentada por 4,8 dias, atingindo 0,88. Recomenda-se verificação programada dentro das próximas 24 horas: verificação do regime de carga e do banco de capacitores.
- Alerta moderado detectado: WMagnet-IPM-50CV-3F opera com temperatura do enrolamento em 75,1 C, desvio +13,7 C sobre a referência de 61,5 C nas últimas 8 horas. Causa provável sob avaliação: sistema de refrigeração ou carga acima do regime. Recomenda-se verificação programada dentro das próximas 24 horas.

**Turno 1 — operador:** O fator de potência deste motor caiu de 0,95 para 0,88. O que pode explicar isso?

**Assistente:** [FONTE 1] O fator de potência (pf) é uma medida da eficiência do motor, indicando a proporção da potência real que o motor usa em relação à potência nominal. [FONTE 2] Um desvio moderado no fator de potência pode indicar sobrecarga ou problemas de carga. [FONTE 3] O alerta moderado detectado sugere que o motor opera com carga acima do regime. [FONTE 4] A temperatura do enrolamento em 75,1°C, além do desvio de -0,08, pode indicar sobrecarga ou problemas de refrigeração. [FONTE 1] A recomendação de verificação programada dentro das próximas 24 horas sugere que a causa provável é sobrecarga ou problemas de refrigeração.
Confiança: MÉDIA — calculada pela recuperação (relevância do melhor trecho: 0,73).

*Trechos recuperados:* guia_especificacao p.43 — 7. Características em Regime > 7.3 Regime de Serviço > 7.3.3; guia_especificacao p.58 — 11. Seleção e aplicação dos motores trifásicos > 11.2 Níveis; guia_especificacao p.9 — 1.2 Conceitos Básicos > 1.2.5 Fator de potência; guia_especificacao p.9 — 1.2 Conceitos Básicos > 1.2.5 Fator de potência

*Relevância máx.:* 0.7349 · *confiança do modelo:* ALTA · *números sem fonte literal:* nenhum

**Turno 2 — operador:** A corrente também subiu 10%. Isso muda o diagnóstico?

**Assistente:** [FONTE 1] A subida da corrente, em conjunto com o desvio do fator de potência, sugere sobrecarga ou problemas de carga. [FONTE 2] A recomendação de verificação programada dentro das próximas 24 horas indica a necessidade de avaliação do regime de carga. [FONTE 3] A temperatura do enrolamento em 75,1°C, além do desvio de +13,7°C, sugere problemas de refrigeração. [FONTE 4] A causa provável é sobrecarga ou problemas de refrigeração, conforme a documentação disponível. [FONTE 1] A subida da corrente não altera o diagnóstico, pois a avaliação do regime de carga é a recomendação mais importante.
Confiança: MÉDIA — calculada pela recuperação (relevância do melhor trecho: 0,72).

*Trechos recuperados:* guia_especificacao p.9 — 1.2 Conceitos Básicos > 1.2.5 Fator de potência; guia_especificacao p.20 — 3. Características de Alimentação do Motor Elétrico > trifás; guia_especificacao p.58 — 11. Seleção e aplicação dos motores trifásicos > 11.2 Níveis; guia_especificacao p.43 — 7. Características em Regime > 7.3 Regime de Serviço > 7.3.3

*Relevância máx.:* 0.719 · *confiança do modelo:* ALTA · *números sem fonte literal:* nenhum

## Anomalia mecanica — MT-008

**Estado injetado no prompt:** EM RISCO — alertas críticos abertos
- ALERTA CRÍTICO — motor W22-112M-4P-7.5CV-3F (Linha de Produção B — Misturador Industrial). A temperatura do mancal atingiu desvio severo de +17,8 C sobre o baseline de 49,8 C de forma sustentada por 5,1 dias, com valor de pico em 67,1 C. Risco de falha do rolamento por perda de lubrificação. Intervenção imediata requerida: parada para inspeção do mancal e substituição do rolamento — acionar manutenção no turno corrente.
- ALERTA CRÍTICO: W22-112M-4P-7.5CV-3F em condição severa. Leitura de vibração global registrada em 4,4 mm/s (+112,8% vs. baseline) de forma sustentada por 5 dias. Intervenção imediata requerida — parada para verificação de alinhamento, balanceamento e rolamentos. Manter o ativo sob supervisão contínua até a intervenção.

**Turno 1 — operador:** A vibração deste motor mais que dobrou em cinco dias. O que verificar primeiro?

**Assistente:** A primeira coisa a verificar é o alinhamento do motor [FONTE 1]. Em seguida, verifique o balanceamento do motor [FONTE 2]. Além disso, verifique o rolamento e a lubrificação do mancal [FONTE 1]. Se necessário, faça a inspeção e a substituição do rolamento [FONTE 1].
Confiança: MÉDIA — calculada pela recuperação (relevância do melhor trecho: 0,68).

*Trechos recuperados:* guia_especificacao p.15 — 1.6 Materiais e Sistemas de Isolação; guia_especificacao p.35 — 7. Características em Regime > 7.1.2 Vida útil do motor; guia_especificacao p.33 — 6. Motofreio Trifásico > 6.4 Conjugado de Frenagem; guia_especificacao p.30 — 4. Características de aceleração > 5.1 Variação do Número de

*Relevância máx.:* 0.6771 · *confiança do modelo:* ALTA · *números sem fonte literal:* nenhum

**Turno 2 — operador:** O alinhamento foi conferido e está correto. O que mais pode causar isso?

**Assistente:** O desbalanceamento do motor também pode causar vibração [FONTE 2]. A temperatura do mancal foi a principal causa apontada [FONTE 1]. Outro fator a ser verificado é a lubrificação do rolamento [FONTE 2]. A vibração também pode ser causada por desalinhamento [FONTE 1].
Confiança: MÉDIA — calculada pela recuperação (relevância do melhor trecho: 0,70).

*Trechos recuperados:* guia_especificacao p.15 — 1.6 Materiais e Sistemas de Isolação; guia_especificacao p.35 — 7. Características em Regime > 7.1.2 Vida útil do motor; guia_especificacao p.13 — 1.5 Motor de Indução Trifásico; guia_especificacao p.33 — 6. Motofreio Trifásico > 6.4 Conjugado de Frenagem

*Relevância máx.:* 0.6984 · *confiança do modelo:* ALTA · *números sem fonte literal:* nenhum

## Manutencao preventiva — MT-004

**Estado injetado no prompt:** ESTÁVEL COM DESVIO — apenas desvios leves

**Turno 1 — operador:** Este motor vai ficar parado por três meses. Que cuidados de armazenamento devo tomar?

**Assistente:** Como o motor está parado há apenas três meses, não há necessidade de realizar a manutenção descrita nos trechos [FONTE 2] e [FONTE 3]. No entanto, para evitar a formação de óleo no rolamento, recomenda-se armazenar o motor horizontalmente, com óleo ISO VG 68 no rolamento, e girar o eixo semanalmente [FONTE 2]. Além disso, é recomendável relubrificar os rolamentos abertos antes do comissionamento do motor, se o período de armazenamento for superior a seis meses [FONTE 2]. Não há necessidade de desmontar ou trocar os ímãs permanentes neste caso [FONTE 1].
Confiança: MÉDIA — calculada pela recuperação (relevância do melhor trecho: 0,62).

*Trechos recuperados:* manual_wmo p.20 — 5 MANUTENÇÃO; manual_wmo p.16 — 2 TRANSPORTE, ARMAZENAMENTO E MANUSEIO; manual_wmo p.16 — 2 TRANSPORTE, ARMAZENAMENTO E MANUSEIO; guia_especificacao p.35 — 7. Características em Regime > 7.1.2 Vida útil do motor

*Relevância máx.:* 0.6203 · *confiança do modelo:* ALTA · *números sem fonte literal:* nenhum

**Turno 2 — operador:** E o que preciso inspecionar quando ele voltar a operar?

**Assistente:** Para o retorno ao operação, inspecione a temperatura ambiente e a presença de desvios leves no estado do ativo [FONTE 1]. Verifique a lubrificação dos rolamentos e a presença de óleo no rolamento [FONTE 2].
Confiança: MÉDIA — calculada pela recuperação (relevância do melhor trecho: 0,65).

*Trechos recuperados:* manual_wmo p.20 — 5 MANUTENÇÃO; guia_especificacao p.35 — 7. Características em Regime > 7.1.2 Vida útil do motor; manual_wmo p.16 — 2 TRANSPORTE, ARMAZENAMENTO E MANUSEIO; rendimento_monofasicos p.4 — WEG em Revista

*Relevância máx.:* 0.6492 · *confiança do modelo:* ALTA · *números sem fonte literal:* nenhum
