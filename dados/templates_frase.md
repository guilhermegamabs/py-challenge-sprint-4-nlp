# Templates de Frase — Enriquecimento Textual da Interface

Sprint 2 PLN / Forzy × FIAP — Grupo CodeX

Documento descreve os templates de frase usados pela interface do Digital Twin para substituir dados brutos de sensor por linguagem compreensível ao operador.

---

## 1. Estrutura básica

Cada template combina quatro slots:

| Slot | Origem |
|------|--------|
| `{tag}` | Campo `tag` do cadastro (`corpus_estendido.csv`) |
| `{estado_qualitativo}` | Classificação derivada de regras sobre `leitura_atual` |
| `{leituras_chave}` | Subset normalizado das leituras correntes (máx. 3 grandezas) |
| `{timestamp}` | `data_extracao` da leitura mais recente |

---

## 2. Variantes por estado

### 2.1 Estado **normal**

Critérios (todos verdadeiros):
- temperatura ≤ 70 °C
- corrente ≤ 110 % da nominal
- rotação dentro de ±2 % da nominal

Templates (rotação alternada na UI):

```
Motor {tag} operando dentro dos parametros normais. Ultima leitura: {leituras_chave}.
{tag} em operacao estavel. Leituras recentes: {leituras_chave}.
Equipamento {tag} OK. {leituras_chave} medidos as {timestamp}.
```

**Exemplo** (MT-001):
> Motor W22-100L-2P-3CV-1F operando dentro dos parametros normais. Ultima leitura: 220V, 12.3A, 3520 RPM.

---

### 2.2 Estado **alerta**

Critérios (qualquer um):
- 70 °C < temperatura ≤ 80 °C
- corrente entre 110–125 % da nominal
- desvio de rotação entre ±2 % e ±5 %

Templates:

```
Atencao em {tag}: {grandeza_critica} fora da faixa ideal ({valor}). Leituras: {leituras_chave}.
Motor {tag} apresentando {grandeza_critica} elevada. Verificar condicao operacional. Ultima leitura: {leituras_chave}.
```

**Exemplo** (MT-002, 72 °C):
> Atencao em W22-132M-4P-15CV-3F: temperatura fora da faixa ideal (72°C). Leituras: 220V, 36.8A, 1755 RPM.

---

### 2.3 Estado **crítico**

Critérios (qualquer um):
- temperatura > 80 °C
- corrente > 125 % da nominal
- desvio de rotação > ±5 %

Templates:

```
CRITICO: Motor {tag} com {grandeza_critica} em nivel critico ({valor}). Acionar manutencao. Leituras: {leituras_chave}.
{tag} requer intervencao imediata - {grandeza_critica} = {valor}. Status as {timestamp}.
```

**Exemplo** (MT-008, 89 °C):
> CRITICO: Motor W22-112M-4P-7.5CV-3F com temperatura em nivel critico (89°C). Acionar manutencao. Leituras: 220V, 18.5A, 1745 RPM.

---

## 3. Regras de composição

1. **Unidade junto ao número.** `380V`, não `380 volts`. `1745 RPM`, não `1745`.
2. **Máx. 3 leituras** na frase principal — preferência: tensão, corrente, rotação. Temperatura entra quando é a grandeza crítica.
3. **Linguagem do operador.** Usar `tensão`, `corrente`, `rotação`, `temperatura`. Evitar jargão de datasheet (`η%`, `IC411`, `cosφ`) na descrição corrente — manter restrito a tela de ficha técnica.
4. **Identificador**: sempre usar `tag` (W22-...) como primeira referência. Operador reconhece a TAG, não o `ativo_id` interno.
5. **Estado qualitativo** vem antes da listagem numérica — operador lê o status primeiro, números depois.
6. **Mensagens críticas em caixa alta** apenas no prefixo (`CRITICO:`) — corpo da frase em sentence case para legibilidade.
7. **Sem ponto-flutuante longo** — arredondar para 1 casa decimal (`12.3A`, não `12.345A`).
8. **Localização opcional** — adicionar `({localizacao})` somente quando a UI mostra lista multi-ativo.

---

## 4. Mapeamento `leitura_atual` → slots

O campo `OP001.leitura_atual` do corpus tem formato:

```
Tensao 220V Corrente 12.3A Rotacao 3520rpm Temperatura 58C
```

Parser por regex extrai:
- `tensao` → grupo após `Tensao` até espaço.
- `corrente` → grupo após `Corrente`.
- `rotacao` → grupo após `Rotacao`.
- `temperatura` → grupo após `Temperatura` (sufixo `C` removido na composição).

Saída normalizada (dict): `{"tensao": "220V", "corrente": "12.3A", "rotacao": "3520 RPM", "temperatura": 58}`.

---

## 5. Exemplos completos (todos os ativos do corpus estendido)

| Ativo | Estado | Frase gerada |
|-------|--------|--------------|
| MT-001 | normal | Motor W22-100L-2P-3CV-1F operando dentro dos parametros normais. Ultima leitura: 220V, 12.3A, 3520 RPM. |
| MT-002 | alerta | Atencao em W22-132M-4P-15CV-3F: temperatura fora da faixa ideal (72°C). Leituras: 220V, 36.8A, 1755 RPM. |
| MT-003 | critico | CRITICO: Motor W22-160L-2P-30CV-3F com temperatura em nivel critico (81°C). Acionar manutencao. Leituras: 220V, 68.5A, 3548 RPM. |
| MT-004 | normal | Motor W22-80-4P-1CV-3F em operacao estavel. Leituras recentes: 220V, 2.8A, 1715 RPM. |
| MT-005 | normal | Motor W22-225S-4P-75CV-3F operando dentro dos parametros normais. Ultima leitura: 380V, 98.5A, 1775 RPM. |
| MT-006 | normal | Equipamento W22-90L-6P-2CV-3F OK. 220V, 5.9A, 1150 RPM medidos as 2026-05-22. |
| MT-007 | normal | Motor WMagnet-IPM-50CV-3F em operacao estavel. Leituras recentes: 380V, 65.2A, 1798 RPM. |
| MT-008 | critico | CRITICO: Motor W22-112M-4P-7.5CV-3F com temperatura em nivel critico (89°C). Acionar manutencao. Leituras: 220V, 18.5A, 1745 RPM. |

---

## 6. Extensibilidade

- **Multi-ativo (planta → equip → ativo)**: prefixar com `{planta}/{equipamento}/` quando dispoiniel na hierarquia.
- **Histórico**: variar tempo verbal (`opera` → `operou nas ultimas 24h`) usando agregado de leituras.
- **i18n**: estrutura por slots permite renderizar EN a partir do glossário PT/EN da Sprint 1 sem reescrever lógica.
