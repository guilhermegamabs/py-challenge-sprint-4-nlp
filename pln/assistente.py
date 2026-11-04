# -*- coding: utf-8 -*-
"""Assistente conversacional de troubleshooting (Sprint 4)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Sequence

import os

MODELO_LLM = os.environ.get(
    "MODELO_LLM",
    "Qwen/Qwen2.5-3B-Instruct-GGUF::qwen2.5-3b-instruct-q4_k_m.gguf")

PROMPT_SISTEMA = """Você é um assistente técnico especialista em motores elétricos industriais, \
apoiando operadores de manutenção de uma planta industrial.

Regras obrigatórias:
1. Responda SOMENTE com base nos trechos fornecidos em FONTES e no ESTADO DO ATIVO. \
Não use conhecimento externo e não invente números, normas ou procedimentos.
2. TODA frase apoiada em um trecho deve terminar com a marca da fonte, no formato [FONTE 1], \
[FONTE 2], etc. Frases sem marca de fonte serão consideradas sem embasamento.
3. Se as FONTES não cobrirem a pergunta, diga explicitamente que a documentação disponível \
não trata do assunto e não tente adivinhar.
4. Números, faixas e nomes de normas devem ser copiados literalmente das FONTES. \
Nunca cite uma norma, tabela ou valor que não apareça no texto fornecido.
5. Escreva em português técnico acessível, direto, em no máximo 6 frases.
6. Termine com uma linha no formato: Confiança: ALTA|MÉDIA|BAIXA — seguida de uma \
justificativa curta baseada na aderência dos trechos recuperados à pergunta.

Exemplo FICTÍCIO, de outro aparelho, só para mostrar o formato — nunca copie o conteúdo dele:
"A lâmpada da geladeira não acende quando o interruptor da porta está travado [FONTE 1]. \
Recomenda-se testar o interruptor antes de trocar a lâmpada [FONTE 2]. \
Confiança: ALTA — os trechos recuperados tratam diretamente da causa perguntada." """
# Sprint 4 — três tentativas, todas medidas (relatorios/sprint4_iteracao*/):
# 1) Sprint 3: exemplo de desalinhamento/correia, DENTRO do corpus -> T16 copiou.
# 2) compressor com "filtro a cada 2 000 horas" -> vazou para T18 (pego pelo
#    verificador de números).
# 3) só marcadores <...> -> o modelo perdeu o formato: respostas vazias e
#    recusa fora de escopo caiu para 2 de 4.
# Versão final: aparelho doméstico, sem números, declarado fictício.

TEMPLATE_USUARIO = """{estado}FONTES:
{contexto}

PERGUNTA DO OPERADOR: {pergunta}

Responda em no máximo 6 frases. Feche CADA frase com a marca da fonte usada — \
[FONTE 1], [FONTE 2], [FONTE 3] ou [FONTE 4] — e termine com a linha \
"Confiança: ALTA|MÉDIA|BAIXA — justificativa"."""

# Sprint 4: a confiança passa a ser medida pela relevância da recuperação SEM os
# bônus de família e de ativo do re-ranking. Esses bônus dependem do contexto
# operacional (sempre presente nas perguntas do gabarito, ausente nas fora de
# escopo) e inflavam o score: na Sprint 3 o limiar antigo (0,75 sobre o score
# composto) marcou ALTA nas 20 perguntas e não discriminava nada.
LIMIAR_RECUSA = 0.60   # abaixo disso o LLM nem é chamado: a recusa é determinística
LIMIAR_CONFIANCA = {"ALTA": 0.85, "MÉDIA": LIMIAR_RECUSA}

MENSAGEM_RECUSA = (
    "A documentação técnica disponível não trata deste assunto com aderência "
    "suficiente para uma resposta segura. Consulte a engenharia de manutenção "
    "ou o canal responsável pela informação.")


def relevancia(chunk: dict) -> float:
    """Relevância do trecho: sinal denso + lexical, sem bônus de contexto."""
    from .rag import PESOS

    if "score_denso" not in chunk:
        return float(chunk.get("score", 0.0))
    return float(chunk["score_denso"]) + PESOS["lexical"] * float(chunk.get("score_lexical", 0.0))


def nivel_confianca(relevancias: Sequence[float]) -> str:
    """Nível calculado pela recuperação — é ele que governa a resposta exibida."""
    if not relevancias:
        return "BAIXA"
    melhor = max(relevancias)
    if melhor >= LIMIAR_CONFIANCA["ALTA"]:
        return "ALTA"
    if melhor >= LIMIAR_CONFIANCA["MÉDIA"]:
        return "MÉDIA"
    return "BAIXA"


_NUMERO = re.compile(r"\d+(?:[.,]\d+)?")


def _normalizar_numero(n: str) -> str:
    return n.replace(",", ".").rstrip("0").rstrip(".") if "." in n.replace(",", ".") else n


_MILHAR = re.compile(r"(?<=\d)[  .](?=\d{3}(?!\d)(?![.,]\d))")   # "2 000"/"1.500" -> "2000"/"1500"


def numeros_sem_suporte(resposta: str, contexto: str, pergunta: str = "") -> list[str]:
    """Números da resposta que não aparecem no contexto recuperado nem na pergunta.

    Detecta o padrão de alucinação visto na Sprint 3 (155 °C virou 150 °C).
    Também sinaliza valores CALCULADOS pelo modelo (ex.: 1 000 x 0,88 = 880):
    não são necessariamente errados, mas não têm fonte literal e pedem conferência.
    Ignora os índices das marcas [FONTE n]."""
    corpo = _MILHAR.sub("", re.sub(r"\[FONTE[^\]]*\]", " ", resposta))
    base = _MILHAR.sub("", contexto + "\n" + pergunta)
    no_contexto = {_normalizar_numero(n) for n in _NUMERO.findall(base)}
    faltando = []
    for n in _NUMERO.findall(corpo):
        if _normalizar_numero(n) not in no_contexto and n not in faltando:
            faltando.append(n)
    return faltando


def bloco_estado(estado: dict | None) -> str:
    """Contexto operacional da Sprint 3 renderizado para o prompt."""
    if not estado:
        return ""
    linhas = [f"ESTADO DO ATIVO {estado['ativo_id']} ({estado.get('tag', '')}):",
              f"- Situação: {estado.get('situacao', 'não informada')}"]
    for resumo in estado.get("alertas", []):
        linhas.append(f"- {resumo}")
    return "\n".join(linhas) + "\n\n"


@dataclass
class Assistente:
    """LLM local + retriever + memoria de curto prazo."""

    retriever: object
    modelo_nome: str = MODELO_LLM
    k_chunks: int = 4
    max_novos_tokens: int = 260
    memoria_turnos: int = 3
    historico: list[dict] = field(default_factory=list)
    _tok: object | None = field(default=None, repr=False)
    _llm: object | None = field(default=None, repr=False)

    @property
    def backend(self) -> str:
        if "::" in self.modelo_nome or self.modelo_nome.lower().endswith(".gguf"):
            return "llama_cpp"
        return "transformers"

    def carregar(self):
        if self._llm is not None:
            return self._llm

        if self.backend == "llama_cpp":
            from huggingface_hub import hf_hub_download
            from llama_cpp import Llama

            if "::" in self.modelo_nome:
                repo, arquivo = self.modelo_nome.split("::", 1)
                caminho = hf_hub_download(repo, arquivo)
            else:   # caminho local de um .gguf já baixado (MODELO_LLM=...)
                caminho = self.modelo_nome
            self._llm = Llama(model_path=caminho, n_ctx=4096, n_threads=6,
                              verbose=False, seed=0)
        else:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer

            self._tok = AutoTokenizer.from_pretrained(self.modelo_nome)
            self._llm = AutoModelForCausalLM.from_pretrained(
                self.modelo_nome, dtype=torch.bfloat16, low_cpu_mem_usage=True)
            self._llm.eval()
        return self._llm

    def _gerar(self, mensagens: list[dict]) -> str:
        self.carregar()

        if self.backend == "llama_cpp":
            saida = self._llm.create_chat_completion(
                mensagens, max_tokens=self.max_novos_tokens, temperature=0.0)
            texto = saida["choices"][0]["message"]["content"].strip()
            return _cortar_apos_confianca(texto)

        import torch

        entrada = self._tok.apply_chat_template(
            mensagens, add_generation_prompt=True, return_tensors="pt", return_dict=True)
        with torch.no_grad():
            saida = self._llm.generate(**entrada, max_new_tokens=self.max_novos_tokens,
                                       do_sample=False,
                                       pad_token_id=self._tok.eos_token_id)
        novos = saida[0][entrada["input_ids"].shape[1]:]
        return _cortar_apos_confianca(
            self._tok.decode(novos, skip_special_tokens=True).strip())

    def limpar_memoria(self) -> None:
        self.historico = []

    def _mensagens(self, pergunta_formatada: str) -> list[dict]:
        mensagens = [{"role": "system", "content": PROMPT_SISTEMA}]
        for turno in self.historico[-self.memoria_turnos:]:
            mensagens.append({"role": "user", "content": turno["pergunta_curta"]})
            mensagens.append({"role": "assistant", "content": turno["resposta"]})
        mensagens.append({"role": "user", "content": pergunta_formatada})
        return mensagens

    def responder(self, pergunta: str, estado: dict | None = None,
                  familias: Sequence[str] | None = None,
                  usar_memoria: bool = True) -> dict:
        """Recupera, monta o prompt e gera a resposta fundamentada."""
        from .rag import formatar_contexto

        termos_ativo = [estado["tag"]] if estado and estado.get("tag") else None
        # Sprint 4: pergunta de seguimento ("isso muda o diagnóstico?") é elíptica;
        # buscada sozinha, recupera trecho irrelevante e cai abaixo do limiar de
        # recusa. A consulta de busca carrega a pergunta do turno anterior.
        consulta = pergunta
        if usar_memoria and self.historico:
            consulta = f"{self.historico[-1]['pergunta']} {pergunta}"
        chunks = self.retriever.buscar(consulta, k=self.k_chunks, familias=familias,
                                       termos_ativo=termos_ativo)
        contexto = formatar_contexto(chunks)
        relevancias = [relevancia(c) for c in chunks]
        melhor = max(relevancias) if relevancias else 0.0
        confianca = nivel_confianca(relevancias)

        if melhor < LIMIAR_RECUSA:
            # Sprint 4: recuperação fraca demais -> recusa sem chamar o LLM.
            # Na Sprint 3 o modelo recebia trechos "parecidos" e inventava
            # (F02: configurou o inversor de um concorrente citando a WEG).
            corpo, declarada, recusa = MENSAGEM_RECUSA, "NAO_GERADA", True
        else:
            conteudo = TEMPLATE_USUARIO.format(estado=bloco_estado(estado),
                                               contexto=contexto, pergunta=pergunta)
            mensagens = self._mensagens(conteudo) if usar_memoria else [
                {"role": "system", "content": PROMPT_SISTEMA},
                {"role": "user", "content": conteudo}]
            bruta = self._gerar(mensagens)
            corpo, declarada, recusa = remover_confianca(bruta), confianca_declarada(bruta), False

        # A linha de confiança exibida é a calculada; a do modelo fica só no registro.
        relev_txt = f"{melhor:.2f}".replace(".", ",")
        resposta = (f"{corpo}\nConfiança: {confianca} — calculada pela recuperação "
                    f"(relevância do melhor trecho: {relev_txt}).")

        registro = {
            "pergunta": pergunta,
            "pergunta_curta": pergunta,
            "resposta": resposta,
            "corpo": corpo,
            "contexto": contexto,
            "chunks": [{"chunk_id": c["chunk_id"], "doc_id": c["doc_id"],
                        "secao": c["secao"], "pagina": c["pagina"],
                        "score": c["score"], "relevancia": round(r, 4)}
                       for c, r in zip(chunks, relevancias)],
            "relevancia_max": round(melhor, 4),
            "recusa_por_limiar": recusa,
            "confianca_recuperacao": confianca,
            "confianca_declarada": declarada,
            "numeros_sem_suporte": [] if recusa else numeros_sem_suporte(
                corpo, contexto + "\n" + bloco_estado(estado), pergunta),
            "fontes_citadas": sorted(set(int(n) for n in
                                         re.findall(r"\[FONTE (\d+)\]", corpo))),
        }
        if usar_memoria:
            self.historico.append(registro)
        return registro


_CONFIANCA = re.compile(r"confian[çc]a\s*:\s*(ALTA|M[ÉE]DIA|BAIXA)", re.I)


def _cortar_apos_confianca(texto: str) -> str:
    """Corta o texto apos a linha de confianca, que encerra a resposta."""
    m = _CONFIANCA.search(texto)
    if not m:
        return texto
    fim = texto.find("\n", m.end())
    return (texto if fim < 0 else texto[:fim]).strip()


def remover_confianca(texto: str) -> str:
    """Corpo da resposta sem a linha de confiança declarada pelo modelo."""
    m = _CONFIANCA.search(texto)
    return texto if not m else texto[:m.start()].strip()


def confianca_declarada(resposta: str) -> str:
    """Nivel de confianca que o proprio modelo declarou no fim da resposta."""
    m = _CONFIANCA.search(resposta)
    if not m:
        return "NAO_DECLARADA"
    return m.group(1).upper().replace("EDIA", "ÉDIA")
