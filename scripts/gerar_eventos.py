from __future__ import annotations

import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
DADOS = RAIZ / "dados"
SEED = 3
INICIO = datetime(2026, 6, 8, 6, 0)

ATIVOS = ["MT-001", "MT-002", "MT-003", "MT-004", "MT-005", "MT-006", "MT-007", "MT-008"]

EVENTOS: dict[str, list[str]] = {
    "manutencao_corretiva": [
        "Motor parou em operacao. Aberto o cabecote, rolamento traseiro travado, substituido por rolamento 6206 ZZ novo.",
        "Substituicao do enrolamento apos queima da fase S. Motor enviado para rebobinamento na oficina externa.",
        "Troca do ventilador de refrigeracao quebrado. Equipamento voltou a operar as 14h20.",
        "Reaperto de emergencia dos terminais da caixa de ligacao apos desarme por mau contato.",
        "Realizada a troca do contator queimado do painel do compressor. Retorno a producao no mesmo turno.",
        "Acoplamento rompeu durante partida. Substituido elemento elastico e realizado alinhamento a laser.",
        "Corrigido vazamento de graxa no mancal LA. Retentor substituido e mancal relubrificado.",
        "Motor desarmou por rele termico. Identificado curto entre espiras, retirado de operacao para reparo.",
        "Substituido o sensor PT100 do enrolamento que apresentava leitura travada em 0 C.",
        "Reparo do eixo com desgaste no assento do rolamento. Metalizacao e retifica realizados.",
        "Troca da tampa defletora danificada apos impacto. Motor liberado apos teste em vazio.",
        "Correcao de curto no cabo de alimentacao entre inversor e motor. Trecho de 6 metros substituido.",
        "Rebobinamento concluido, motor testado em bancada e reinstalado na bomba centrifuga.",
        "Troca do rolamento dianteiro apos ruido metalico intenso e travamento parcial do eixo.",
        "Substituida a chave seccionadora que fundiu durante o acionamento do misturador.",
        "Equipamento parado desde ontem. Realizada troca do disjuntor motor e religamento.",
        "Reparada trinca na base do motor com solda e novo torqueamento dos chumbadores.",
        "Retirado corpo estranho preso no ventilador que provocou parada por sobrecarga.",
        "Substituicao emergencial do capacitor de partida do motor monofasico.",
        "Motor apresentou fumaca e parou. Desmontado, constatada queima total, encaminhado ao rebobinamento.",
        "Realizado o reaperto e substituicao dos bornes oxidados que causaram falha de partida.",
        "Trocada a polia do lado acionado que apresentava rasgo no canal. Correias tambem substituidas.",
        "Ventoinha substituida apos quebra da helice. Temperatura normalizou depois da troca.",
        "Corrigida a falha do encoder que impedia o inversor de manter a rotacao. Encoder novo instalado.",
        "Manutencao de emergencia no domingo: troca de mancal do lado acoplado do ventilador de exaustao.",
        "Feito reparo provisorio na caixa de ligacao ate a chegada da peca definitiva.",
        "Substituido o rele de sobrecarga que atuava indevidamente com carga nominal.",
        "Motor retornou da oficina apos reparo do estator. Instalado e testado sem carga por 30 minutos.",
        "Trocado o retentor do mancal traseiro apos contaminacao da graxa por agua de lavagem.",
        "Corrigido o desalinhamento severo apos quebra do calco. Motor recalçado e realinhado.",
        "Substituicao do inversor de frequencia queimado do misturador industrial.",
        "Realizada a troca completa dos rolamentos LA e LOA apos falha catastrofica em operacao.",
    ],
    "manutencao_preventiva": [
        "Executada a rota mensal de lubrificacao dos mancais conforme plano do fabricante.",
        "Inspecao visual programada realizada. Sem anormalidades nas conexoes e na carcaca.",
        "Medicao periodica de resistencia de isolamento com megohmetro. Valores dentro da faixa esperada.",
        "Realizada limpeza das aletas e do defletor durante a parada programada de sabado.",
        "Coleta trimestral de analise de vibracao para acompanhamento de tendencia.",
        "Reaperto preventivo dos parafusos de fixacao da base conforme torque de projeto.",
        "Termografia programada nas conexoes do painel executada sem apontamentos.",
        "Substituicao preventiva dos rolamentos ao atingir 20 mil horas de operacao.",
        "Verificacao do alinhamento a laser dentro do plano semestral de manutencao.",
        "Ensaio de resistencia ohmica das fases realizado na parada anual da planta.",
        "Troca programada da graxa do mancal seguindo intervalo de 4000 horas.",
        "Inspecao preditiva por ultrassom no mancal LOA. Sem indicio de falha incipiente.",
        "Checklist semanal de preventiva concluido: fixacao, ruido, temperatura e limpeza ok.",
        "Realizado o plano de manutencao preventiva trimestral com limpeza interna e sopragem.",
        "Calibracao anual dos sensores de temperatura do enrolamento efetuada pelo laboratorio.",
        "Programada e executada a inspecao das escovas e do sistema de aterramento do eixo.",
        "Feita a preventiva de painel: limpeza dos filtros e verificacao dos contatores.",
        "Substituicao programada das correias de transmissao no intervalo previsto.",
        "Inspecao preventiva dos cabos de alimentacao e eletrodutos sem apontamento de risco.",
        "Executada rota de lubrificacao automatizada. Doseador reabastecido com graxa Mobil XHP 222.",
        "Analise de oleo do redutor coletada conforme cronograma preditivo mensal.",
        "Realizado o teste funcional das protecoes do rele de sobrecarga na parada programada.",
        "Verificacao de folga axial do eixo dentro do escopo da preventiva semestral.",
        "Limpeza preventiva do trocador de calor do motor de 75 CV durante o turno noturno.",
        "Inspecao boroscopica programada do entreferro sem constatacao de danos.",
        "Aplicada rotina preventiva de reaperto eletrico nos terminais com torquimetro.",
        "Programa preditivo: nova medicao de vibracao para atualizar a linha de base do ativo.",
        "Realizada a manutencao preventiva de 6 meses com troca de retentores e graxa.",
        "Executada inspecao preventiva pos-chuva nas instalacoes eletricas da area externa.",
        "Ensaios de indice de polarizacao executados na campanha preventiva de junho.",
        "Substituidos filtros de ar do ambiente do motor conforme plano preventivo.",
        "Revisao programada do acoplamento com verificacao de desgaste do elastomero.",
    ],
    "anomalia_eletrica": [
        "Corrente da fase R subiu para 82 A contra 68 A das demais fases. Desequilibrio evidente.",
        "Tensao de alimentacao caiu para 208 V durante o pico de carga da tarde.",
        "Fator de potencia registrando 0,78 apos ontem, abaixo do historico de 0,95.",
        "Observado aquecimento anormal no borne da fase T, sem intervencao ate o momento.",
        "Corrente de partida acima do esperado, disjuntor no limite de atuacao.",
        "Registrada oscilacao de tensao de mais ou menos 12 V no barramento do painel.",
        "Consumo do motor 18 por cento acima do baseline sem aumento de carga no processo.",
        "Alarme de desequilibrio de tensao entre fases persistindo desde a madrugada.",
        "Termografia mostrou ponto quente de 96 C na conexao do cabo de alimentacao.",
        "Corrente de fuga para terra aumentou de 2 mA para 11 mA nas ultimas 24 horas.",
        "Distorcao harmonica total de corrente subiu para 9 por cento apos entrada do novo inversor.",
        "Motor com resistencia de isolamento em queda, 3,2 MOhm contra 80 MOhm de referencia.",
        "Rele de sobrecarga atuando de forma intermitente sem sobrecarga mecanica aparente.",
        "Registrado afundamento de tensao de 15 por cento por 4 segundos na rede da area 3.",
        "Leitura do amperimetro do painel oscilando entre 60 e 90 A sem variacao de processo.",
        "Sinal de corrente com componente de sequencia negativa acima do limite normativo.",
        "Detectada elevacao de temperatura no enrolamento associada a sobrecorrente na fase S.",
        "Anomalia eletrica: queda do fator de potencia acompanhada de aumento de corrente reativa.",
        "Corrente do motor subiu 22 por cento apos manobra na subestacao, sem mudanca de carga.",
        "Sensor indica tensao 6 por cento abaixo do nominal de forma continua nas ultimas 100 horas.",
        "Painel acusando falha de fase intermitente durante a operacao do misturador.",
        "Aumento do ruido eletrico no sinal de corrente coletado pelo supervisorio.",
        "Verificado nivel de tensao de neutro elevado em relacao ao terra na alimentacao do ativo.",
        "Anomalia registrada pelo digital twin: corrente eficaz fora da faixa esperada para a carga.",
        "Desvio eletrico detectado, corrente 12 por cento acima do baseline por mais de 3 horas.",
        "Consumo reativo do ativo cresceu de forma continua durante o turno da noite.",
        "Sistema apontou sobretensao de 254 V sustentada por 20 minutos.",
        "Instabilidade na leitura de tensao do inversor indicando possivel problema de rede.",
        "Corrente desequilibrada entre fases em 9 por cento, acima do limite de 5 por cento.",
        "Disjuntor no limiar termico devido a corrente elevada persistente, sem desarme.",
        "Diferenca de 14 A entre a fase mais carregada e a menos carregada do motor de 30 CV.",
        "Elevacao progressiva da corrente sem elevacao de vibracao, sugerindo origem eletrica.",
    ],
    "anomalia_mecanica": [
        "Vibracao global subiu de 2,0 para 4,3 mm por segundo no mancal do lado acoplado.",
        "Ruido metalico intermitente audivel na regiao do rolamento traseiro.",
        "Temperatura do mancal LOA 17 C acima do baseline sem variacao de carga.",
        "Detectado desalinhamento angular entre motor e bomba na inspecao de vibracao.",
        "Aumento do nivel de vibracao em 1x RPM indicando desbalanceamento do rotor.",
        "Folga percebida na base do motor com movimento visivel durante a partida.",
        "Espectro de vibracao mostra pico na frequencia de passagem de esferas do rolamento.",
        "Eixo com batimento radial fora da tolerancia medido com relogio comparador.",
        "Correia de transmissao patinando e gerando ruido agudo durante a aceleracao.",
        "Aquecimento do mancal dianteiro acompanhado de escurecimento da graxa.",
        "Vibracao acima da zona C da ISO 10816 registrada no ventilador de exaustao.",
        "Presenca de limalha metalica proxima ao mancal, indicio de desgaste interno.",
        "Rotacao oscilando 2 por cento abaixo do nominal com carga constante.",
        "Ruido de raspagem sugere contato entre ventoinha e tampa defletora.",
        "Registrado aumento de vibracao axial apos a troca do elemento do acoplamento.",
        "Mancal LA operando a 78 C, 15 C acima da media historica do equipamento.",
        "Detectada frequencia de engrenamento anormal no redutor acoplado ao motor.",
        "Vibracao dobrou nas ultimas 48 horas sem alteracao de corrente, indicio mecanico.",
        "Chumbador solto identificado durante a inspecao de ruido excessivo.",
        "Motor apresenta trepidacao na partida e estabiliza apos 10 segundos.",
        "Analise de envelope indica falha incipiente na pista externa do rolamento.",
        "Aumento simultaneo de temperatura de mancal e vibracao no misturador industrial.",
        "Percebido desgaste no assento do rolamento durante inspecao com o motor parado.",
        "Ruido de impacto ciclico sincronizado com a rotacao do eixo.",
        "Vibracao de 7,8 mm por segundo medida no moinho de bolas, acima do limite de alarme.",
        "Eixo com dificuldade de giro manual, sugerindo travamento parcial do mancal.",
        "Sinal de vibracao com harmonicos de 2x RPM tipico de desalinhamento paralelo.",
        "Ventilador do motor com pas empenadas gerando desbalanceamento perceptivel.",
        "Elevacao da temperatura do mancal apos a ultima lubrificacao, possivel excesso de graxa.",
        "Detectada folga axial superior a 0,6 mm no conjunto rotativo.",
        "Ruido anormal de rolamento identificado por ultrassom durante a ronda operacional.",
        "Vibracao do motor da esteira aumentou durante a operacao com carga maxima.",
    ],
    "operacao_normal": [
        "Ronda operacional das 8h sem anormalidades. Leituras estaveis em todos os pontos.",
        "Motor operando a 58 C, corrente 12,3 A e 3520 RPM, tudo dentro da faixa esperada.",
        "Turno encerrado sem ocorrencias no equipamento. Producao dentro da meta.",
        "Partida do compressor realizada normalmente as 6h05, sem alarmes.",
        "Leituras do supervisorio estaveis nas ultimas 24 horas.",
        "Equipamento em regime nominal, vibracao em 1,8 mm por segundo.",
        "Sem desvios registrados no diario de bordo deste turno.",
        "Parametros eletricos e mecanicos dentro dos limites, operacao continua.",
        "Motor da bomba operando em carga parcial conforme demanda da linha.",
        "Registro de rotina: temperatura de enrolamento 61 C, estavel desde a madrugada.",
        "Equipamento desligado conforme programacao de producao, sem falhas.",
        "Operacao normal durante todo o final de semana, sem intervencao necessaria.",
        "Verificacao rapida no inicio do turno, tudo conforme.",
        "Ativo em operacao ha 96 horas seguidas sem alarme.",
        "Leitura de corrente 36,8 A, compativel com a carga atual do compressor.",
        "Ronda noturna concluida, nenhum ruido ou aquecimento anormal identificado.",
        "Sistema de refrigeracao funcionando normalmente, temperatura estavel.",
        "Motor retomou operacao apos troca de turno, sem observacoes.",
        "Indicadores do digital twin em verde para o ativo durante todo o dia.",
        "Producao normal, equipamento sem apontamentos no periodo.",
        "Rotacao de 1755 RPM medida, coerente com o valor nominal do motor.",
        "Nada a relatar. Equipamento operando conforme padrao.",
        "Estado operacional estavel, ultima leitura sem desvios em relacao ao baseline.",
        "Motor trabalhando em 70 por cento da carga nominal, sem aquecimento.",
        "Checagem visual de rotina realizada. Carcaca limpa e sem vazamentos.",
        "Sem alarmes no periodo monitorado, ativo classificado como saudavel.",
        "Fator de potencia em 0,86, dentro da referencia historica do equipamento.",
        "Operacao continua sem desvio, proxima inspecao programada para a semana que vem.",
        "Todos os pontos de medicao dentro da tolerancia estabelecida no projeto.",
        "Equipamento reiniciado apos parada programada de producao e operando normalmente.",
        "Leituras de tensao em 220 V e corrente em 18,5 A, condicao normal de trabalho.",
        "Turno sem intercorrencias, motor da extrusora estavel em 1798 RPM.",
    ],
}

AMBIGUOS = [
    ("Ruido no mancal identificado na ronda; programada troca de rolamento para sabado.",
     "anomalia_mecanica"),
    ("Durante a preventiva foi constatado desequilibrio de corrente entre fases.",
     "anomalia_eletrica"),
    ("Reaperto dos terminais executado durante inspecao de rotina, sem falha previa.",
     "manutencao_preventiva"),
    ("Motor parado para troca de rolamento apos alarme de vibracao critica.",
     "manutencao_corretiva"),
    ("Vibracao levemente acima do usual, porem dentro do limite de alarme; sem acao.",
     "anomalia_mecanica"),
    ("Equipamento operando normal apos a substituicao do contator realizada ontem.",
     "operacao_normal"),
    ("Inspecao encontrou aquecimento no borne; correcao agendada para a proxima parada.",
     "anomalia_eletrica"),
    ("Lubrificacao antecipada devido a leitura de temperatura de mancal em elevacao.",
     "manutencao_preventiva"),
]


def main() -> None:
    rng = random.Random(SEED)
    registros = []
    idx = 1
    ts = INICIO

    pares = [(t, c) for c, textos in EVENTOS.items() for t in textos] + \
            [(t, c) for t, c in AMBIGUOS]
    rng.shuffle(pares)

    for texto, categoria in pares:
        ativo = rng.choice(ATIVOS)
        registros.append({
            "evento_id": f"EV-{idx:03d}",
            "ativo_id": ativo,
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "origem": rng.choice(["ordem_servico", "diario_de_bordo", "supervisorio",
                                  "ronda_operacional"]),
            "texto": texto,
            "categoria_gold": categoria,
            "ambiguo": int(any(texto == t for t, _ in AMBIGUOS)),
        })
        ts += timedelta(minutes=rng.randint(35, 190))
        idx += 1

    df = pd.DataFrame(registros)
    destino = DADOS / "eventos_operacionais.csv"
    DADOS.mkdir(parents=True, exist_ok=True)
    df.to_csv(destino, index=False, encoding="utf-8")

    print(f"{len(df)} eventos -> {destino}")
    print(df["categoria_gold"].value_counts().to_string())
    print(f"ambiguos: {int(df['ambiguo'].sum())}")


if __name__ == "__main__":
    main()
