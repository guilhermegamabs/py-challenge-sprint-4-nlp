# Sprint 1 — Fundamentos do Ativo e da Base de Dados

Cópia dos entregáveis da Sprint 1 de PLN. A entrega original foi feita por pasta no Drive. O notebook foi reexecutado na Sprint 4, quando passou a rodar também fora do Colab, e está aqui com as saídas visíveis.

| Entregável | Arquivo |
|------------|---------|
| Notebook do pipeline, executado (24 de 24 células) | [`sprint1_pln_corpus.ipynb`](sprint1_pln_corpus.ipynb) |
| Glossário técnico PT/EN, com 170 termos em 7 categorias | [`dados/glossario_pt_en.json`](dados/glossario_pt_en.json) |
| Corpus estruturado do ativo, com 84 registros | [`dados/corpus_estruturado.csv`](dados/corpus_estruturado.csv) · [`.json`](dados/corpus_estruturado.json) |
| Estatísticas do corpus | [`dados/estatisticas_corpus.json`](dados/estatisticas_corpus.json) e os gráficos `dados/*.png` |
| Documento de decisões de padronização | [`Documento_Tecnico_Sprint1_PLN.pdf`](Documento_Tecnico_Sprint1_PLN.pdf) |

## Para reexecutar

O notebook lê os PDFs técnicos da WEG, que não estão neste repositório. São 7 documentos públicos (~21 MB), baixados do site da WEG:

- `WEG-rendimento-nos-motores-monofasicos-001-article-portuguese-web.pdf`
- `WEG-w22-motor-eletrico-monofasico-50069982-brochure-portuguese-web.pdf`
- `WEG-motores-eletricos-guia-de-especificacao-50032749-brochure-portuguese-web.pdf`
- `WEG-motors-specification-of-electric-motors-50039409-brochure-english-web.pdf`
- `WEG-WMO-safe-area-50031142-manual-en-pt-es-de-fr-ru-nl-it-zh.pdf`
- `WEG-danos-em-enrolamentos-motores-monofasicos-50009254-brochure-portuguese-web.pdf`
- `WEG-winding-damages-single-phase-motors-50041274-brochure-english-web.pdf`

Coloque os PDFs em `Documentos do Motor/`, ao lado do notebook; qualquer subpasta serve. No Colab, use `MyDrive/Forzy/Documentos do Motor/`.

```bash
pip install pdfplumber nltk pandas matplotlib seaborn unidecode jupyter
jupyter nbconvert --to notebook --execute --inplace sprint1_pln_corpus.ipynb
```

## Observações registradas na Sprint 4

- **Stopwords acentuadas.** A lista de stopwords é aplicada depois da remoção de acentos. Por isso "nao" aparece entre os termos mais frequentes e as estatísticas de frequência ficam levemente infladas. Isso não afeta as sprints seguintes, que normalizam de outro jeito.
- **Lematização não adotada.** A seção 12 do notebook recomenda lematização com spaCy para as sprints seguintes, mas as Sprints 2 a 4 mantiveram a decisão de não usar stemming nem lematização. O motivo é que os embeddings multilíngues já tratam a variação morfológica.
