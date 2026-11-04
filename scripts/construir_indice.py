from __future__ import annotations

import statistics
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from pln import rag  # noqa: E402

BASE_PADRAO = Path(r"F:\FIAP\Segundo Ano\Challenge Sprints\challenge-sprint-1"
                   r"\processamento-linguagem-natural\Documentos do Motor")


def main() -> None:
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE_PADRAO
    if not base.exists():
        raise SystemExit(f"pasta de documentos nao encontrada: {base}")

    chunks = rag.construir_chunks(base)
    print(f"{len(chunks)} chunks de {len({c['doc_id'] for c in chunks})} documentos")

    linhas = []
    for doc_id in sorted({c["doc_id"] for c in chunks}):
        sub = [c for c in chunks if c["doc_id"] == doc_id]
        linhas.append({
            "doc_id": doc_id,
            "titulo": sub[0]["titulo_doc"],
            "tipo": sub[0]["tipo_doc"],
            "chunks": len(sub),
            "secoes": len({c["secao"] for c in sub}),
            "paginas": len({c["pagina"] for c in sub}),
            "chars_medio": round(statistics.mean(c["n_chars"] for c in sub)),
        })
    resumo = pd.DataFrame(linhas)
    (RAIZ / "relatorios").mkdir(exist_ok=True)
    resumo.to_csv(RAIZ / "relatorios" / "chunks_resumo.csv", index=False, encoding="utf-8")
    print(resumo.to_string(index=False))

    indice = rag.IndiceVetorial(chunks).construir()
    indice.salvar(RAIZ / "indice_rag")
    print(f"indice salvo em {RAIZ / 'indice_rag'}")


if __name__ == "__main__":
    main()
