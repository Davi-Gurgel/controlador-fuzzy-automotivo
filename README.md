# Controlador Fuzzy (Mamdani) — Compra Automotiva

**Mini-Projeto 2** da disciplina de Sistemas Baseados em Conhecimento — **Caminho B**:
reescrita do **Mini-Projeto 1** (sistema de regras IF–THEN nítidas em `experta`)
substituindo a pontuação crisp por **inferência fuzzy Mamdani** com
[`scikit-fuzzy`](https://pythonhosted.org/scikit-fuzzy/).

> 📹 **Vídeo de apresentação:** _(adicionar link aqui antes de postar no Classroom)_

## Membros do grupo

- Miguel de Queiroz Fernandes Soares
- Artur Coelho Batista Guedes Pereira
- Rafael Torres Nóbrega Gomes
- Davi de Oliveira Gurgel

## Domínio

O sistema recomenda um carro de um catálogo a partir do perfil do comprador, o mesmo
domínio do MP1. No MP1 a adequação de cada veículo era a **soma de pontos discretos**
(+1, −1, +0.5) disparados por **limiares abruptos** (`preço > orçamento` elimina,
`segurança < 4` elimina, `consumo == 'alto'` penaliza). Esses cortes são arbitrários:
um carro a R$ 120.001 com orçamento de R$ 120.000 era descartado tão duramente quanto
um de R$ 300.000.

Aqui a **adequação** vira uma variável **contínua [0–100]** produzida por um controlador
**Mamdani**, e as transições entre as faixas passam a ser **graduais**.

## Arquitetura do controlador

**Tipo:** Mamdani · **3 entradas**, **1 saída** · **3 termos por variável** · **14 regras**.

### Variáveis linguísticas e funções de pertinência

| Variável | Tipo | Universo | Termos | Justificativa |
|---|---|---|---|---|
| `preco_relativo` | entrada | 0–150 (% do orçamento) | barato · no_orcamento · caro | `preço/orçamento×100`; cria a região "quase coube" inexistente no corte rígido do MP1 |
| `seguranca` | entrada | 0–5 | baixa · media · alta | mesma escala de nota do catálogo do MP1 |
| `eficiencia` | entrada | 0–10 | ruim · mediana · otima | índice combinando consumo + custo de manutenção |
| `adequacao` | **saída** | 0–100 | rejeitar · considerar · recomendar | grau de recomendação; defuzzificado por centroide |

As restrições **binárias** do domínio (categoria exigida, rejeição a combustão)
**permanecem crisp** como filtro de elegibilidade — não faz sentido fuzzificar
"isto é um SUV". O fuzzy entra exatamente onde o MP1 usava limiares arbitrários sobre
grandezas **contínuas**.

### Cobertura da base de regras (sem lacunas)

As 14 regras cobrem as **3×3×3 = 27** combinações de termos das entradas. `caro` é
vetado por R1 (9 combinações); `segurança baixa` é tratada por R2–R3; o restante é
graduado por R4–R14:

| preço \ (seg, efic.) | barato | no_orcamento | caro |
|---|---|---|---|
| **seg baixa** (qualquer efic.) | R3 (considerar) | R2 (rejeitar) | R1 (rejeitar) |
| **seg média**, efic. ruim | R11 | R11 | R1 |
| **seg média**, efic. mediana | R10 | R13 | R1 |
| **seg média**, efic. ótima | R7 | R9 | R1 |
| **seg alta**, efic. ruim | R12 | R14 | R1 |
| **seg alta**, efic. mediana | R5 | R8 | R1 |
| **seg alta**, efic. ótima | R4 | R6 | R1 |

> Cobertura verificada empiricamente: varredura de **13.671 pontos** do espaço de
> entradas — **0 lacunas** (todo ponto dispara ≥1 regra) e saída sempre defuzzificável.

## Casos de teste

O notebook traz **3 casos do controlador** (entradas → saída defuzzificada →
interpretação comentada no código) e a aplicação aos **4 perfis do MP1**:

| Caso (controlador) | Entradas | Adequação | Leitura |
|---|---|---|---|
| A — compra ideal | preço_rel 60 %, seg 5, efic 9 | ≈ 84 | **recomendar** (R4 forte) |
| B — estoura orçamento | preço_rel 130 %, seg 5, efic 9 | ≈ 16 | **rejeitar** (R1 veta apesar do resto) |
| C — fronteira | preço_rel 95 %, seg 3.5, efic 5.5 | ≈ 50 | **considerar** (R13) |

Nos 4 perfis do catálogo, **3 coincidem** com o MP1. O **Caso 2 diverge**: o fuzzy
prefere o *SUV Híbrido Urbano* (eficiente, no orçamento, segurança máxima) ao
*SUV Espaçoso Seguro* que o MP1 premiava por porta-malas grande — ambas plausíveis.

## Como executar

Pré-requisito: [`uv`](https://docs.astral.sh/uv/) instalado. O `uv` resolve as
dependências do `pyproject.toml` automaticamente; **não é preciso criar venv à mão**.

### Abrir o notebook (com gráficos das funções de pertinência)

```bash
uv run --with jupyter --with matplotlib jupyter lab SBC_Fuzzy_Compra_Automotiva.ipynb
```

Para executar o notebook inteiro de uma vez (gera as saídas e valida os `assert`s dos casos de teste):

```bash
uv run --with jupyter --with matplotlib \
  jupyter nbconvert --to notebook --execute --inplace SBC_Fuzzy_Compra_Automotiva.ipynb
```

> No **Google Colab**, descomente a célula `%pip install -q scikit-fuzzy networkx packaging`
> no topo do notebook e execute todas as células em ordem.

## Comparativo fuzzy × regras (MP1)

| Aspecto | MP1 (IF–THEN nítido, `experta`) | MP2 (fuzzy Mamdani, `scikit-fuzzy`) |
|---|---|---|
| Limiares | cortes rígidos (`>`, `<`, `==`) | transições suaves (funções de pertinência) |
| Orquestração | `salience`, fases, fatos `Eliminado`/`Ponto` | inferência agrega tudo, **sem ordem manual** |
| Saída | soma de pontos discretos | adequação contínua defuzzificada |
| Expressividade | "passou/não passou" do limiar | "quase coube", "segurança razoável" |
| Rastreabilidade | alta (regra-a-regra) | menor (agregação difusa) |
| Custo | controle imperativo de conflito/desempate | calibrar funções de pertinência |

**Resumo:** o fuzzy reduz a complexidade de *controle de fluxo* (sem `salience`/fases) e
ganha expressividade nas decisões de fronteira; em troca, perde a rastreabilidade
regra-a-regra do MP1 e exige calibrar as funções de pertinência.
