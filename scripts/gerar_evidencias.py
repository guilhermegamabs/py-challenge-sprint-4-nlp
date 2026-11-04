"""Figuras e transcrições de evidência da Sprint 4 (pasta evidencias/).

Lê só artefatos já calculados em relatorios/ — não chama LLM nem recalcula métrica.
Uso:  python scripts/gerar_evidencias.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt   # noqa: E402
import pandas as pd               # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
REL = RAIZ / "relatorios"
EVI = RAIZ / "evidencias"
EVI.mkdir(exist_ok=True)

# Só preto e cinza: as figuras vão para o documento final, que não usa cor.
# Nomes por papel: série principal / série secundária / linhas de referência.
AZUL, LARANJA, CINZA = "#000000", "#8c8c8c", "#5a5a5a"   # nomes antigos, valores em escala de cinza
plt.rcParams.update({"figure.dpi": 150, "font.size": 9, "axes.spines.top": False,
                     "axes.spines.right": False})


def fig_relevancia(cmp: dict) -> None:
    rel = cmp["relevancia_recuperacao"]
    fig, ax = plt.subplots(figsize=(9, 2.6))
    for y, grupo, cor, marca, rot in ((1, rel["gabarito_por_id"], AZUL, "o", "gabarito (20)"),
                                      (0, rel["fora_de_escopo_por_id"], LARANJA, "s", "fora de escopo (4)")):
        ax.scatter(list(grupo.values()), [y] * len(grupo), color=cor, marker=marca, label=rot, zorder=3)
        for pid, v in grupo.items():
            ax.annotate(pid, (v, y), fontsize=7, xytext=(0, 7), textcoords="offset points", ha="center")
    ax.axvline(0.60, ls="--", color=CINZA)
    ax.text(0.603, 0.45, "recusa < 0,60", fontsize=8, color=CINZA)
    ax.axvline(0.85, ls=":", color=CINZA)
    ax.text(0.853, 0.45, "ALTA ≥ 0,85", fontsize=8, color=CINZA)
    ax.set_yticks([0, 1], ["fora de escopo", "gabarito"])
    ax.set_ylim(-0.6, 1.7)
    ax.set_xlabel("relevância do melhor trecho recuperado (denso + 0,35 × lexical)")
    ax.set_title("Onde cai cada pergunta — e por que nenhum limiar separa os grupos sem erro")
    fig.tight_layout()
    fig.savefig(EVI / "fig1_relevancia_limiar.png")
    plt.close(fig)


def fig_confianca(depois: pd.DataFrame, antes: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(9, 3))
    niveis = ["ALTA", "MÉDIA", "BAIXA"]
    a = antes["sprint3"]["confianca_exibida"]
    d = depois["confianca_recuperacao"].value_counts().to_dict()
    x = range(len(niveis))
    axes[0].bar([i - 0.2 for i in x], [a.get(n, 0) for n in niveis], 0.4, color=CINZA, label="Sprint 3 (modelo)")
    axes[0].bar([i + 0.2 for i in x], [d.get(n, 0) for n in niveis], 0.4, color=AZUL, label="Sprint 4 (calculada)")
    axes[0].set_xticks(list(x), niveis)
    axes[0].set_ylabel("perguntas do gabarito")
    axes[0].set_title("Confiança exibida ao operador")
    axes[0].legend(frameon=False, fontsize=8)

    g = depois.groupby("confianca_recuperacao")["faithfulness"].agg(["mean", "count"]).reindex(niveis).dropna()
    axes[1].bar(g.index, g["mean"], color=AZUL)
    for i, (m, n) in enumerate(zip(g["mean"], g["count"])):
        axes[1].text(i, m + 0.02, f"{m:.2f}\n(n={int(n)})", ha="center", fontsize=8)
    axes[1].set_ylim(0, 1.15)
    axes[1].set_title("Faithfulness média por nível (Sprint 4)")
    fig.tight_layout()
    fig.savefig(EVI / "fig2_confianca.png")
    plt.close(fig)


def fig_antes_depois(cmp: dict) -> None:
    s3, s4 = cmp["sprint3"], cmp["sprint4"]

    def recusas(b):
        return int(b["fora_de_escopo_recusadas"].split()[0])

    nomes = ["faithfulness", "answer relevancy", "fora de escopo\nrecusadas (de 4)",
             "respostas com nº\nsem fonte literal"]
    v3 = [s3["faithfulness_medio"], s3["answer_relevancy_medio"], recusas(s3),
          len(s3["respostas_com_numero_sem_suporte"])]
    v4 = [s4["faithfulness_medio"], s4["answer_relevancy_medio"], recusas(s4),
          len(s4["respostas_com_numero_sem_suporte"])]
    fig, axes = plt.subplots(1, 4, figsize=(10, 2.8))
    for ax, n, a, b in zip(axes, nomes, v3, v4):
        ax.bar(["S3", "S4"], [a, b], color=[CINZA, AZUL])
        for i, v in enumerate((a, b)):
            ax.text(i, v, f"{v:.3f}" if isinstance(v, float) else str(v), ha="center", va="bottom", fontsize=8)
        ax.set_title(n, fontsize=8.5)
        ax.set_ylim(0, max(a, b) * 1.25 or 1)
    fig.suptitle("Assistente RAG — Sprint 3 × Sprint 4 (mesma régua: corpo da resposta)", fontsize=10)
    fig.tight_layout()
    fig.savefig(EVI / "fig3_antes_depois.png")
    plt.close(fig)


def transcricao_cenarios() -> None:
    cen = json.loads((REL / "cenarios_demo.json").read_text(encoding="utf-8"))
    linhas = ["# Demonstração — três cenários de falha (execução real)", "",
              "Gerado por `scripts/avaliar_assistente.py` (Qwen2.5-3B Q4, CPU) e transcrito por "
              "`scripts/gerar_evidencias.py`. Texto do assistente sem edição.", ""]
    for c in cen:
        linhas += [f"## {c['cenario'].replace('_', ' ').capitalize()} — {c['ativo_id']}", ""]
        if c.get("estado"):
            linhas.append(f"**Estado injetado no prompt:** {c['estado']['situacao']}")
            linhas += [f"- {a}" for a in c["estado"]["alertas"]]
            linhas.append("")
        for i, t in enumerate(c["dialogo"], 1):
            fontes = "; ".join(f"{ch['doc_id']} p.{ch['pagina']} — {ch['secao'][:60]}"
                               for ch in t["chunks"])
            linhas += [f"**Turno {i} — operador:** {t['pergunta']}", "",
                       f"**Assistente:** {t['resposta']}", "",
                       f"*Trechos recuperados:* {fontes}", "",
                       f"*Relevância máx.:* {t.get('relevancia_max')} · *confiança do modelo:* "
                       f"{t['confianca_declarada']} · *números sem fonte literal:* "
                       f"{', '.join(t.get('numeros_sem_suporte') or []) or 'nenhum'}", ""]
    (EVI / "demo_cenarios_falha.md").write_text("\n".join(linhas), encoding="utf-8")


def transcricao_fora_de_escopo() -> None:
    antes = pd.read_csv(REL / "sprint3_baseline" / "fora_de_escopo.csv")
    depois = pd.read_csv(REL / "fora_de_escopo.csv")
    linhas = ["# Perguntas fora de escopo — Sprint 3 × Sprint 4", ""]
    for (_, a), (_, d) in zip(antes.iterrows(), depois.iterrows()):
        linhas += [f"## {a['id']} — {a['pergunta']}", "",
                   f"**Sprint 3** (recusou={a['recusou']}): {a['resposta']}", "",
                   f"**Sprint 4** (recusou={d['recusou']}, recusa por limiar={d['recusa_por_limiar']}, "
                   f"relevância={d['relevancia_max']}): {d['resposta']}", ""]
    (EVI / "fora_de_escopo_antes_depois.md").write_text("\n".join(linhas), encoding="utf-8")


def main() -> None:
    cmp = json.loads((REL / "comparativo_sprint3_sprint4.json").read_text(encoding="utf-8"))
    depois = pd.read_csv(REL / "respostas_assistente.csv")
    fig_relevancia(cmp)
    fig_confianca(depois, cmp)
    fig_antes_depois(cmp)
    transcricao_cenarios()
    transcricao_fora_de_escopo()
    print("evidências em", EVI)


if __name__ == "__main__":
    main()
