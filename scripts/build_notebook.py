from __future__ import annotations

from pathlib import Path

import nbformat as nbf

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "sprint3_pln_alertas.ipynb"

MD = "markdown"
CODE = "code"

CELULAS: list[tuple[str, str]] = [

(MD, """# Sprint 3 — PLN: Geração de Linguagem Natural sobre Alertas

**FIAP × Forzy — Grupo CodeX** · Gêmeo Digital para motores elétricos industriais

Guilherme Gama (RM565293) · Bruno Fernandes Nascimento (RM552574) · Edgar Lódula de Assis (RM565260) · Júlia Aben-Athar (RM566325) · Igor Thiago Nakajima Vieira (RM563632)

A camada de ML entrega número; o operador precisa de frase. Este notebook faz a conversão: **resumos de alerta** em três níveis (§3–4), **classificação dos eventos** de manutenção (§6) e **relatório operacional** rastreável (§7), com avaliação por ROUGE e checklist (§5).
"""),

(MD, """## 1. Ambiente

Roda em CPU. No Colab, suba a pasta `nlp/` completa e execute em ordem.
"""),

(CODE, """# Colab: descomente a linha abaixo na primeira execução
# !pip -q install rouge-score transformers torch scikit-learn pandas matplotlib

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RAIZ = Path.cwd()
if not (RAIZ / "pln").exists() and (RAIZ.parent / "pln").exists():
    RAIZ = RAIZ.parent
sys.path.insert(0, str(RAIZ))

DADOS = RAIZ / "dados"
RELATORIOS = RAIZ / "relatorios"
RELATORIOS.mkdir(exist_ok=True)

pd.set_option("display.width", 160)
pd.set_option("display.max_colwidth", 120)
print("raiz do projeto:", RAIZ)"""),

(MD, """## 2. Dados de entrada

Gerados por `scripts/gerar_leituras_alertas.py` e `scripts/gerar_eventos.py` (semente fixa): séries de sensor, alertas detectados, eventos rotulados e os gabaritos manuais de ROUGE.

Os 7 primeiros dias são o baseline; nos 7 últimos as falhas são injetadas — sobrecarga no MT-003 e desalinhamento no MT-008 (críticos), desvios menores nos demais. MT-004 e MT-006 servem de contraprova.
"""),

(CODE, """leituras = pd.read_csv(DADOS / "leituras_sensores.csv")
alertas = json.loads((DADOS / "alertas.json").read_text(encoding="utf-8"))["alertas"]
eventos = pd.read_csv(DADOS / "eventos_operacionais.csv")
referencias = {r["alerta_id"]: r["resumo_referencia"] for r in
               json.loads((DADOS / "alertas_referencia.json").read_text(encoding="utf-8"))["referencias"]}

print(f"leituras: {leituras.shape[0]} linhas x {leituras.shape[1]} colunas")
print(f"alertas : {len(alertas)}")
print(f"eventos : {len(eventos)}")
leituras.head(3)"""),

(CODE, """df_alertas = pd.DataFrame(alertas)
resumo_sev = (df_alertas.groupby(["severidade", "sensor"]).size()
              .unstack(fill_value=0)
              .reindex(["critico", "moderado", "leve"]))
display(resumo_sev)
print(df_alertas["severidade"].value_counts().reindex(["critico", "moderado", "leve"]).to_string())"""),

(CODE, """# Visualizacao das series que originaram os dois alertas criticos
fig, eixos = plt.subplots(1, 2, figsize=(13, 4))
lt = leituras.copy()
lt["timestamp"] = pd.to_datetime(lt["timestamp"])

for eixo, (ativo, sensor, titulo) in zip(eixos, [
        ("MT-003", "temperatura_enrolamento_c", "MT-003 — temperatura do enrolamento (°C)"),
        ("MT-008", "vibracao_mm_s", "MT-008 — vibração global (mm/s)")]):
    s = lt[lt["ativo_id"] == ativo]
    eixo.plot(s["timestamp"], s[sensor], linewidth=0.9)
    corte = s["timestamp"].min() + pd.Timedelta(days=7)
    base = s[s["timestamp"] < corte][sensor].mean()
    eixo.axhline(base, linestyle="--", color="gray", label=f"baseline 7d = {base:.1f}")
    eixo.axvline(corte, color="crimson", linewidth=1, label="início da observação")
    eixo.set_title(titulo, fontsize=10)
    eixo.tick_params(axis="x", rotation=30, labelsize=7)
    eixo.legend(fontsize=7)
plt.tight_layout()
plt.show()"""),

(MD, """## 3. Templates de narrativa

Seis templates, dois por nível de urgência. Cada nível tem léxico próprio e cada grandeza tem recomendação tabelada — o texto nunca propõe procedimento fora do domínio do ativo.
"""),

(CODE, """from pln.narrativa import (LEXICO, RECOMENDACOES, TEMPLATES, gerar_resumo,
                          gerar_resumos, templates_por_severidade)

# corpo completo de cada template (o marcador `acima_abaixo` é resolvido em
# tempo de renderização para "acima" ou "abaixo", conforme o sinal do desvio)
for t in TEMPLATES:
    print(f"[{t.template_id}] ({t.severidade})")
    print(t.corpo)
    print()"""),

(CODE, """# Tabela de recomendações: uma por (grandeza, severidade) — o texto gerado
# nunca propõe procedimento fora desta tabela
pd.DataFrame(RECOMENDACOES).T[["leve", "moderado", "critico"]]"""),

(CODE, """pd.DataFrame(LEXICO).T[["abertura", "verbo_desvio", "urgencia", "prazo"]]"""),

(MD, """## 4. Geração dos resumos

As variantes de cada nível são alternadas para o painel não repetir a mesma frase. Todo resumo termina com o bloco de rastreabilidade `[ALT-00X | sensor | pico | baseline | janela]`.
"""),

(CODE, """resumos = gerar_resumos(alertas)
df_resumos = pd.DataFrame(resumos)
df_resumos["resumo_referencia"] = df_resumos["alerta_id"].map(referencias)

for sev in ("critico", "moderado", "leve"):
    exemplo = next(r for r in resumos if r["severidade"] == sev)
    print(f"### {sev.upper()}  ({exemplo['template_id']})")
    print(exemplo["texto"])
    print()"""),

(CODE, """# Mesmo alerta renderizado nas duas variantes do seu nivel
alerta_demo = next(a for a in alertas if a["severidade"] == "moderado")
for v in range(len(templates_por_severidade("moderado"))):
    print(f"-- variante {v}")
    print(gerar_resumo(alerta_demo, variante=v, com_rastreio=False)["texto"], "\\n")"""),

(CODE, """df_resumos[["alerta_id", "severidade", "template_id", "texto_sem_rastreio"]].head(24)"""),

(MD, """## 5. Avaliação dos resumos

### 5.1 ROUGE contra referências manuais

24 resumos escritos à mão a partir dos números, **sem** consultar os templates. ROUGE próximo de 1 aqui indicaria gabarito contaminado, não qualidade.
"""),

(CODE, """from pln import avaliacao as av

df_rouge = av.calcular_rouge(df_resumos["texto_sem_rastreio"],
                             df_resumos["resumo_referencia"],
                             df_resumos["alerta_id"])
display(av.resumo_rouge(df_rouge))
display(av.resumo_rouge(df_rouge, df_resumos["severidade"]))"""),

(CODE, """comparacao = df_rouge.merge(
    df_resumos[["alerta_id", "severidade", "texto_sem_rastreio", "resumo_referencia"]],
    left_on="id", right_on="alerta_id")
linha = comparacao.sort_values("rouge1_f", ascending=False).iloc[0]
print(f"melhor par ({linha['alerta_id']}, ROUGE-1 F1 = {linha['rouge1_f']}):\\n")
print("GERADO   :", linha["texto_sem_rastreio"], "\\n")
print("REFERENCIA:", linha["resumo_referencia"])"""),

(MD, """### 5.2 Checklist de clareza, precisão e utilidade

Dez critérios objetivos (`pln/avaliacao.py`): tamanho e legibilidade, identificação do ativo e da grandeza, direção do desvio, recomendação, tom de urgência, rastreabilidade e **anti-alucinação numérica** — todo número da frase é conferido contra o registro de alerta.
"""),

(CODE, """df_check = av.aplicar_checklist(resumos, alertas)
display(av.taxa_aprovacao(df_check).to_frame("aprovação (%)"))
print("score médio do checklist:", round(df_check["score_checklist"].mean(), 3))
print("tamanho médio (palavras):", round(df_check["n_palavras"].mean(), 1))
df_check.head(8)"""),

(MD, """## 6. Classificação textual dos eventos operacionais

168 registros de manutenção rotulados em cinco categorias: corretiva, preventiva, anomalia elétrica, anomalia mecânica e operação normal. Oito são ambíguos de propósito.

Três abordagens no mesmo split 60/40: **zero-shot** (mDeBERTa XNLI, sem treino), **baseline supervisionado** (TF-IDF + Regressão Logística) e o **híbrido** da §6.2. A verbalização das classes foi escolhida comparando três formulações em `scripts/tunar_verbalizacao.py` (0,60 vs. 0,52 vs. 0,50).
"""),

(CODE, """from pln import classificacao as cls

print("categorias:", cls.CATEGORIAS)
pd.DataFrame([{"categoria": c, "hipótese zero-shot": cls.HIPOTESE.format(cls.ROTULOS_ZERO_SHOT[c])}
              for c in cls.CATEGORIAS])"""),

(CODE, """display(eventos["categoria_gold"].value_counts().to_frame("registros"))
eventos.sample(6, random_state=7)[["evento_id", "origem", "texto", "categoria_gold", "ambiguo"]]"""),

(CODE, """# Normalizacao herdada da Sprint 1: NFKD + expansao de abreviacoes, sem stemming
exemplo = eventos["texto"].iloc[0]
print("original  :", exemplo)
print("normalizado:", cls.normalizar(exemplo))"""),

(CODE, """from sklearn.model_selection import train_test_split

treino, teste = train_test_split(eventos, test_size=0.4, random_state=42,
                                 stratify=eventos["categoria_gold"])
pipe = cls.construir_baseline()
pipe.fit(treino["texto"].map(cls.normalizar), treino["categoria_gold"])
pred_base = pipe.predict(teste["texto"].map(cls.normalizar))
av_base = cls.avaliar(teste["categoria_gold"], pred_base, nome="tfidf_logreg")
print("macro-F1 baseline:", av_base["macro_f1"])"""),

(MD, """### 6.1 Inferência zero-shot

Custa alguns minutos em CPU; o resultado fica em `relatorios/classificacao_zero_shot.csv`. Para refazer, mude `RECOMPUTAR = True`.
"""),

(CODE, """RECOMPUTAR = False
caminho_zs = RELATORIOS / "classificacao_zero_shot.csv"

if RECOMPUTAR or not caminho_zs.exists():
    classificador = cls.carregar_zero_shot()
    pred_zs = cls.classificar_zero_shot(eventos["texto"].tolist(), classificador)
    pred_zs.insert(0, "evento_id", eventos["evento_id"].values)
    pred_zs["categoria_gold"] = eventos["categoria_gold"].values
    pred_zs["ambiguo"] = eventos["ambiguo"].values
    pred_zs.to_csv(caminho_zs, index=False, encoding="utf-8")
else:
    pred_zs = pd.read_csv(caminho_zs)

zs_teste = pred_zs[pred_zs["evento_id"].isin(teste["evento_id"])]
av_zs = cls.avaliar(zs_teste["categoria_gold"], zs_teste["pred"], nome="zero_shot_mdeberta")
av_zs_total = cls.avaliar(pred_zs["categoria_gold"], pred_zs["pred"], nome="zero_shot_total_168")
print("macro-F1 zero-shot (teste):", av_zs["macro_f1"])
print("macro-F1 zero-shot (168 registros):", av_zs_total["macro_f1"])"""),

(MD, """### 6.2 Híbrido: zero-shot + regras de intervenção

O zero-shot confunde sintoma com intervenção: *"trocado o retentor do mancal após contaminação da graxa"* cai em `anomalia_mecanica`. A correção é lexical — predição `anomalia_*` com verbo de intervenção (*trocado*, *substituído*, *reparo*) vira manutenção.

> As regras foram desenhadas a partir dos erros deste corpus, então parte do ganho é ajuste ao conjunto.
"""),

(CODE, """pred_zs["pred_hibrido"] = cls.ajustar_por_regras(pred_zs)
zs_teste = pred_zs[pred_zs["evento_id"].isin(teste["evento_id"])]
av_hibrido = cls.avaliar(zs_teste["categoria_gold"], zs_teste["pred_hibrido"],
                         nome="zero_shot+regras")
av_hibrido_total = cls.avaliar(pred_zs["categoria_gold"], pred_zs["pred_hibrido"],
                               nome="zero_shot+regras_total")
print("macro-F1 híbrido (teste):", av_hibrido["macro_f1"])
print("macro-F1 híbrido (168 registros):", av_hibrido_total["macro_f1"])"""),

(MD, """### 6.3 F1 por categoria e matriz de confusão"""),

(CODE, """display(cls.tabela_f1(av_zs, av_hibrido, av_base))
display(cls.matriz_confusao_df(av_zs))
display(cls.matriz_confusao_df(av_hibrido))
display(cls.matriz_confusao_df(av_base))"""),

(CODE, """fig, eixos = plt.subplots(1, 2, figsize=(13, 4.2))
for eixo, avaliacao in zip(eixos, (av_zs, av_hibrido)):
    m = np.array(avaliacao["matriz_confusao"])
    eixo.imshow(m, cmap="Blues")
    eixo.set_xticks(range(len(cls.CATEGORIAS)))
    eixo.set_yticks(range(len(cls.CATEGORIAS)))
    eixo.set_xticklabels([c[:12] for c in cls.CATEGORIAS], rotation=45, ha="right", fontsize=7)
    eixo.set_yticklabels([c[:12] for c in cls.CATEGORIAS], fontsize=7)
    eixo.set_title(f"{avaliacao['nome']} — macro-F1 {avaliacao['macro_f1']}", fontsize=9)
    for i in range(m.shape[0]):
        for j in range(m.shape[1]):
            eixo.text(j, i, m[i, j], ha="center", va="center", fontsize=8,
                      color="white" if m[i, j] > m.max() / 2 else "black")
plt.tight_layout()
plt.show()"""),

(CODE, """# Erros do zero-shot: onde a fronteira entre categorias vizinhas quebra
erros_zs = cls.erros(pred_zs.merge(eventos[["evento_id", "texto"]].rename(
    columns={"texto": "texto_original"}), on="evento_id"))
print(f"{len(erros_zs)} erros em {len(pred_zs)} registros "
      f"({len(erros_zs)/len(pred_zs):.1%})")
print("erros em registros ambíguos:", int(erros_zs["ambiguo"].sum()) if "ambiguo" in erros_zs else 0)
erros_zs.head(12)"""),

(CODE, """display(pd.Series(cls.distribuicao_confianca(pred_zs)).to_frame("valor"))
fig, eixo = plt.subplots(figsize=(6, 3))
eixo.hist(pred_zs["score"], bins=20)
eixo.axvline(0.5, color="crimson", linestyle="--", label="limiar de revisão humana")
eixo.set_xlabel("confiança da predição zero-shot")
eixo.set_ylabel("registros")
eixo.legend(fontsize=8)
plt.tight_layout()
plt.show()"""),

(MD, """## 7. Relatório operacional em linguagem natural

Diário (24 h) e semanal (7 dias), com resumo executivo, alertas, equipamentos em risco, tendências e recomendações.

Nenhuma afirmação entra sem âncora de origem: `[ALT-...]` para alertas, `[FONTE: leituras_sensores.csv | ...]` para frases derivadas da série. Um alerta entra no período quando o **episódio** se sobrepõe à janela, não só quando o pico cai nela.
"""),

(CODE, """from pln.relatorio import calcular_tendencias, gerar_relatorio

eventos_class = pred_zs.merge(eventos[["evento_id", "ativo_id"]], on="evento_id", how="left")
eventos_class["pred"] = eventos_class["pred_hibrido"]   # predição final
relatorio_semanal = gerar_relatorio(alertas, leituras, periodo="semanal",
                                    eventos_classificados=eventos_class)
relatorio_diario = gerar_relatorio(alertas, leituras, periodo="diario")

(RELATORIOS / "relatorio_semanal.md").write_text(relatorio_semanal, encoding="utf-8")
(RELATORIOS / "relatorio_diario.md").write_text(relatorio_diario, encoding="utf-8")

from IPython.display import Markdown
Markdown(relatorio_semanal)"""),

(MD, """### 7.1 Relatório diário"""),

(CODE, """Markdown(relatorio_diario)"""),

(MD, """### 7.2 Tendências — verificação numérica

As frases de tendência da seção 4 do relatório vêm de um ajuste linear sobre a janela; abaixo a mesma tabela em formato numérico, para conferir que o texto reflete o dado.
"""),

(CODE, """import datetime as dt

fim = pd.to_datetime(leituras["timestamp"]).max()
tend = calcular_tendencias(leituras, alertas, fim - dt.timedelta(days=7), fim)
pd.DataFrame(tend)[["ativo_id", "sensor", "inclinacao_dia", "valor_inicial",
                    "valor_final", "n_leituras"]]"""),

(MD, """### 7.3 ROUGE do relatório contra referência manual

`dados/relatorio_referencia.md` traz um resumo executivo da mesma semana escrito manualmente. Comparamos com a seção 1 gerada.
"""),

(CODE, """ref_relatorio = (DADOS / "relatorio_referencia.md").read_text(encoding="utf-8")
secao_gerada = relatorio_semanal.split("## 2.")[0]
av.calcular_rouge([secao_gerada], [ref_relatorio], ["relatorio_semanal"])"""),

(CODE, """# Auditoria de rastreabilidade: proporcao de linhas de conteudo com ancora de origem
import re

linhas = [l for l in relatorio_semanal.splitlines()
          if l.startswith("- ") or l.startswith("**MT-")]
com_ancora = [l for l in linhas if re.search(r"\\[(ALT-\\d+|FONTE:|ALERTAS:)", l)]
print(f"linhas de conteúdo: {len(linhas)} | com âncora de origem: {len(com_ancora)} "
      f"({len(com_ancora)/len(linhas):.0%})")"""),

(CODE, """# Consolidacao das metricas da sprint
metricas = {
    "narrativa": {
        "n_alertas": len(alertas),
        "rouge_f1": av.resumo_rouge(df_rouge)["media_f1"].to_dict(),
        "checklist_score_medio": round(float(df_check["score_checklist"].mean()), 4),
        "checklist_aprovacao_pct": av.taxa_aprovacao(df_check).to_dict(),
    },
    "classificacao": {
        "zero_shot_teste_macro_f1": av_zs["macro_f1"],
        "zero_shot_total_macro_f1": av_zs_total["macro_f1"],
        "hibrido_teste_macro_f1": av_hibrido["macro_f1"],
        "hibrido_total_macro_f1": av_hibrido_total["macro_f1"],
        "baseline_teste_macro_f1": av_base["macro_f1"],
        "zero_shot_f1_por_categoria": av_zs["f1_por_categoria"],
        "hibrido_f1_por_categoria": av_hibrido["f1_por_categoria"],
        "baseline_f1_por_categoria": av_base["f1_por_categoria"],
    },
}
(RELATORIOS / "metricas_sprint3.json").write_text(
    json.dumps(metricas, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(metricas, ensure_ascii=False, indent=2))"""),

(MD, """## 8. Limites identificados e ponte para a Sprint 4

**Narrativa** — geração por template: zero alucinação numérica garantida, variedade linguística limitada a seis variantes, sem correlação de causa entre grandezas. O checklist mede conformidade com regras próprias, não naturalidade percebida.

**Classificador** — zero-shot é sensível à verbalização e confunde sintoma com intervenção; as regras que corrigem isso foram calibradas neste corpus. O baseline supervisionado supera o zero-shot puro com apenas 100 exemplos rotulados.

**Dados** — séries simuladas e corpus de eventos escrito pelo grupo. As métricas validam o pipeline, não são benchmark. O baseline pressupõe 7 dias saudáveis no período de referência.

**Para a Sprint 4** — `resumos_gerados.csv` e `relatorio_semanal.md` viram contexto operacional no prompt do assistente; o estado por ativo vira filtro do retriever; a taxonomia de eventos vira metadado dos chunks.
"""),
]


def main() -> None:
    nb = nbf.v4.new_notebook()
    nb["cells"] = [
        nbf.v4.new_markdown_cell(src) if tipo == MD else nbf.v4.new_code_cell(src)
        for tipo, src in CELULAS
    ]
    nb["metadata"] = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.12"},
        "colab": {"provenance": []},
    }
    nbf.write(nb, DESTINO)
    print(f"{len(nb['cells'])} celulas -> {DESTINO}")


if __name__ == "__main__":
    main()
