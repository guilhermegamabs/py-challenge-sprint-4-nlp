# Challenge Sprint 4 — PLN: Documentação Final da Solução

**FIAP × Forzy — Grupo CodeX** · Gêmeo digital para motores elétricos industriais

## Integrantes

| Nome | RM |
|------|-----|
| Guilherme Gama | RM565293 |
| Bruno Fernandes Nascimento | RM552574 |
| Edgar Lódula de Assis | RM565260 |
| Júlia Aben-Athar | RM566325 |
| Igor Thiago Nakajima Vieira | RM563632 |

📸 **Demonstração em funcionamento:** sequência de 13 prints no Anexo do documento final, com os arquivos em [`evidencias/prints/`](evidencias/prints/). O enunciado aceita vídeo ou sequência de prints.

Vídeo das Sprints 3/4 (agosto): https://youtu.be/KrBUtJiwFvA

## Entregáveis

| Entregável | Arquivo |
|------------|---------|
| Documento final (4 seções do enunciado + anexo de prints) | [PDF](<docs/Processamento de Linguagem Natural, Chatbots & Virtual Agents.pdf>) · [DOCX](<docs/Processamento de Linguagem Natural, Chatbots & Virtual Agents.docx>) · [fonte .md](<docs/Processamento de Linguagem Natural, Chatbots & Virtual Agents.md>) |
| Notebook Sprint 1 (executado), com glossário, corpus e documento | [`sprints_anteriores/sprint1/`](sprints_anteriores/sprint1/) |
| Notebook Sprint 2 (executado) | repositório [`py-challenge-sprint-2-nlp`](https://github.com/guilhermegamabs/py-challenge-sprint-2-nlp/blob/main/sprint2_pln_consulta.ipynb) |
| Notebook Sprint 3 (executado) | [`sprint3_pln_alertas.ipynb`](sprint3_pln_alertas.ipynb) |
| Notebook Sprint 4 — RAG, com seção antes × depois (executado) | [`sprint4_pln_rag.ipynb`](sprint4_pln_rag.ipynb) |
| Demonstração: três cenários de falha | [`evidencias/demo_cenarios_falha.md`](evidencias/demo_cenarios_falha.md) |
| Fora de escopo, Sprint 3 × Sprint 4 | [`evidencias/fora_de_escopo_antes_depois.md`](evidencias/fora_de_escopo_antes_depois.md) |
| Logs de execução e figuras | `evidencias/log_*.txt` · `evidencias/fig*.png` |

## O que mudou desde a Sprint 3

O assistente RAG já tinha sido entregue em agosto. Nesta sprint ele recebeu ajustes que corrigem falhas medidas na avaliação anterior:

- **Recusa determinística.** Quando a relevância do melhor trecho recuperado fica abaixo de 0,60, o LLM nem é chamado. Com isso, F02 (inversor de concorrente) deixou de ser alucinada.
- **Confiança calculada.** A confiança exibida ao operador vem da recuperação, não do modelo, que antes declarava ALTA em 100% das respostas.
- **Exemplo do prompt trocado.** O exemplo antigo estava dentro do corpus e era copiado nas respostas. Três variantes foram medidas; todas estão em `relatorios/sprint4_iteracao*`.
- **Verificador de números sem fonte literal.** Detecta casos como 155 °C virando 150 °C.
- **Consulta composta no diálogo.** Corrige uma regressão: o limiar recusava perguntas de seguimento.

| Métrica (mesma régua) | Sprint 3 | Sprint 4 |
|-----------------------|----------|----------|
| Fora de escopo recusadas | 3 de 4 | **4 de 4** |
| Confiança exibida | 20 × ALTA | 7 ALTA · 12 MÉDIA · 1 BAIXA |
| Answer relevancy | 0,725 | 0,734 |
| Faithfulness | 0,743 | 0,678 |
| Recusa indevida no gabarito | 0 | 1 (T13) |

A queda de faithfulness e a recusa indevida estão discutidas no documento, nas seções 1.3, 1.5 e 3.

## Estrutura

```
pln/          narrativa · classificacao · relatorio · avaliacao · rag · assistente · avaliacao_rag
dados/        séries, alertas, eventos, gabaritos (ROUGE e troubleshooting)
indice_rag/   índice FAISS + chunks com seção, página e famílias técnicas
relatorios/   saídas finais; sprint3_baseline/ e sprint4_iteracao*/ para comparação
scripts/      geração, avaliação, comparativo, evidências, notebooks e documento
evidencias/   logs, figuras e transcrições
docs/         documento final (.md → .docx/.pdf)
sprints_anteriores/sprint1/   notebook executado, glossário, corpus e documento da Sprint 1
```

A pasta `chalenge-sprint-3/` foi mantida como entregue em agosto, como referência do "antes".

## Como rodar

```bash
pip install rouge-score transformers torch scikit-learn sentence-transformers faiss-cpu pymupdf llama-cpp-python huggingface_hub pandas numpy matplotlib jupyter python-docx reportlab
```

| Passo | Comando |
|-------|---------|
| Avaliar o assistente (~12 min em CPU) | `python scripts/avaliar_assistente.py` |
| Só os cenários de diálogo (~3 min) | `python scripts/avaliar_assistente.py --so-cenarios` |
| Comparativo Sprint 3 × 4 (~7 min) | `python scripts/comparar_sprint3.py` |
| Evidências (figuras e transcrições) | `python scripts/gerar_evidencias.py` |
| Prints do anexo (precisa de Chrome ou Edge) | `python scripts/gerar_prints.py` |
| Notebook Sprint 4 | `python scripts/build_notebook_sprint4.py` e executar `sprint4_pln_rag.ipynb` |
| Documento .docx/.pdf | `python scripts/gerar_documento_final.py` |

Para usar um modelo `.gguf` já baixado, defina `MODELO_LLM` com o caminho do arquivo. Sem ela, o Qwen2.5-3B-Instruct Q4_K_M é baixado do Hugging Face.

**Colab:** os notebooks leem resultados pré-computados de `relatorios/`. As células que chamam o LLM estão desligadas por padrão (`RODAR_AO_VIVO = False`).
