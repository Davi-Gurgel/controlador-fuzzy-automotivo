"""
Mini-Projeto 2 - Controlador Fuzzy (Mamdani) para Compra Automotiva
===================================================================

Caminho B da especificacao: reescrita do Mini-Projeto 1 (sistema baseado em
regras IF-THEN nitidas em `experta`) substituindo a pontuacao crisp por
*inferencia fuzzy* com scikit-fuzzy.

No MP1 a adequacao de cada carro era a soma de fatos `Ponto` (+1, -1, +0.5)
disparados por limiares ABRUPTOS (preco > orcamento, seguranca < 4, ...).
Aqui a adequacao vira uma variavel continua [0-100] obtida por um controlador
Mamdani com 3 entradas linguisticas e 14 regras fuzzy.

Restricoes genuinamente binarias do dominio (categoria exigida e rejeicao a
combustao) continuam como filtros crisp de elegibilidade -- nao faz sentido
fuzzificar "isto e um SUV": ou e, ou nao e. O fuzzy entra exatamente onde o
MP1 usava limiares arbitrarios sobre grandezas continuas.

Execucao:
    uv run python fuzzy_compra.py
"""

import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl


# ======================================================================
# 1. VARIAVEIS LINGUISTICAS  (universos + funcoes de pertinencia)
# ======================================================================
# As 3 entradas sao grandezas CONTINUAS sobre as quais o MP1 aplicava cortes
# nitidos. Os termos e os pontos de quebra das MFs sao justificados pelo
# dominio (faixas reais de orcamento, escala de seguranca 0-5, indice de
# economia 0-10), nao escolhidos arbitrariamente.

#  preco_relativo = preco_do_carro / orcamento * 100  (% do orcamento)
#  -> permite uma regiao de "quase no orcamento" que o corte rigido do MP1
#     (preco > orcamento => elimina) nao conseguia expressar.
preco_rel = ctrl.Antecedent(np.arange(0, 151, 1), "preco_relativo")
#  seguranca = nota Euro-NCAP-like de 0 a 5 (mesma escala do catalogo do MP1)
seguranca = ctrl.Antecedent(np.arange(0, 5.01, 0.05), "seguranca")
#  eficiencia = indice 0-10 combinando consumo + custo de manutencao
eficiencia = ctrl.Antecedent(np.arange(0, 10.01, 0.05), "eficiencia")
#  adequacao = quanto o carro combina com o perfil (saida defuzzificada)
adequacao = ctrl.Consequent(np.arange(0, 101, 1), "adequacao")

# --- preco relativo: barato bem abaixo / em torno do orcamento / acima ---
preco_rel["barato"] = fuzz.trapmf(preco_rel.universe, [0, 0, 55, 80])
preco_rel["no_orcamento"] = fuzz.trapmf(preco_rel.universe, [60, 85, 100, 115])
preco_rel["caro"] = fuzz.trapmf(preco_rel.universe, [100, 115, 150, 150])

# --- seguranca: baixa (<3.5) / media (~3.5) / alta (>=4.5) ---
seguranca["baixa"] = fuzz.trapmf(seguranca.universe, [0, 0, 2, 3.5])
seguranca["media"] = fuzz.trimf(seguranca.universe, [2.5, 3.5, 4.5])
seguranca["alta"] = fuzz.trapmf(seguranca.universe, [3.5, 4.5, 5, 5])

# --- eficiencia (economia geral): ruim / mediana / otima ---
eficiencia["ruim"] = fuzz.trapmf(eficiencia.universe, [0, 0, 3, 5])
eficiencia["mediana"] = fuzz.trimf(eficiencia.universe, [3.5, 5.5, 7.5])
eficiencia["otima"] = fuzz.trapmf(eficiencia.universe, [6, 8, 10, 10])

# --- adequacao (saida): rejeitar / considerar / recomendar ---
adequacao["rejeitar"] = fuzz.trapmf(adequacao.universe, [0, 0, 20, 40])
adequacao["considerar"] = fuzz.trimf(adequacao.universe, [25, 50, 75])
adequacao["recomendar"] = fuzz.trapmf(adequacao.universe, [60, 80, 100, 100])


# ======================================================================
# 2. BASE DE REGRAS FUZZY  (14 regras)
# ======================================================================
# Cobre as 3x3x3 = 27 combinacoes possiveis de termos das entradas SEM
# LACUNAS (ver tabela de cobertura no README). Limiar duro do MP1 vira
# implicacao fuzzy; o "AND" e o minimo, o "OR/NOT" sao max/complemento.
REGRAS = [
    # -- Veto orcamentario (substitui R1 do MP1: preco > orcamento => elimina)
    ctrl.Rule(preco_rel["caro"], adequacao["rejeitar"]),                                                  # R1
    # -- Piso de seguranca (substitui R3 do MP1: seguranca < 4 => elimina)
    ctrl.Rule(seguranca["baixa"] & preco_rel["no_orcamento"], adequacao["rejeitar"]),                     # R2
    ctrl.Rule(seguranca["baixa"] & preco_rel["barato"], adequacao["considerar"]),                         # R3
    # -- Casos fortes => recomendar
    ctrl.Rule(preco_rel["barato"] & seguranca["alta"] & eficiencia["otima"], adequacao["recomendar"]),    # R4
    ctrl.Rule(preco_rel["barato"] & seguranca["alta"] & eficiencia["mediana"], adequacao["recomendar"]),  # R5
    ctrl.Rule(preco_rel["no_orcamento"] & seguranca["alta"] & eficiencia["otima"], adequacao["recomendar"]),  # R6
    ctrl.Rule(preco_rel["barato"] & seguranca["media"] & eficiencia["otima"], adequacao["recomendar"]),   # R7
    # -- Casos intermediarios => considerar
    ctrl.Rule(preco_rel["no_orcamento"] & seguranca["alta"] & eficiencia["mediana"], adequacao["considerar"]),  # R8
    ctrl.Rule(preco_rel["no_orcamento"] & seguranca["media"] & eficiencia["otima"], adequacao["considerar"]),   # R9
    ctrl.Rule(preco_rel["barato"] & seguranca["media"] & eficiencia["mediana"], adequacao["considerar"]),       # R10
    ctrl.Rule(seguranca["media"] & eficiencia["ruim"] & ~preco_rel["caro"], adequacao["considerar"]),           # R11
    ctrl.Rule(preco_rel["barato"] & seguranca["alta"] & eficiencia["ruim"], adequacao["considerar"]),           # R12
    ctrl.Rule(preco_rel["no_orcamento"] & seguranca["media"] & eficiencia["mediana"], adequacao["considerar"]), # R13
    ctrl.Rule(preco_rel["no_orcamento"] & seguranca["alta"] & eficiencia["ruim"], adequacao["considerar"]),     # R14
]

SISTEMA = ctrl.ControlSystem(REGRAS)


def avaliar(preco_relativo, nota_seguranca, indice_eficiencia):
    """Roda o controlador Mamdani e devolve a adequacao defuzzificada (centroide)."""
    sim = ctrl.ControlSystemSimulation(SISTEMA)
    sim.input["preco_relativo"] = float(np.clip(preco_relativo, 0, 150))
    sim.input["seguranca"] = float(nota_seguranca)
    sim.input["eficiencia"] = float(indice_eficiencia)
    sim.compute()
    return float(sim.output["adequacao"])


# ======================================================================
# 3. CATALOGO (identico ao MP1) + mapeamento crisp -> indice de eficiencia
# ======================================================================
CONSUMO_SCORE = {"baixo": 9, "medio": 5, "alto": 1}
MANUT_SCORE = {"baixa": 9, "media": 5, "alta": 1}

CATALOGO = [
    dict(modelo="Hatch Hibrido Compacto", preco=115000, categoria="hatch", consumo="baixo", manutencao="baixa", seguranca=5, motor="hibrido"),
    dict(modelo="Hatch Entrada Seguro",   preco=78000,  categoria="hatch", consumo="medio", manutencao="baixa", seguranca=5, motor="combustao"),
    dict(modelo="Hatch Popular Basico",   preco=72000,  categoria="hatch", consumo="medio", manutencao="baixa", seguranca=3, motor="combustao"),
    dict(modelo="Sedan Familiar",         preco=135000, categoria="sedan", consumo="medio", manutencao="media", seguranca=4, motor="combustao"),
    dict(modelo="SUV Espacoso Seguro",    preco=185000, categoria="SUV",   consumo="medio", manutencao="media", seguranca=5, motor="combustao"),
    dict(modelo="SUV Pesado Luxo",        preco=230000, categoria="SUV",   consumo="alto",  manutencao="alta",  seguranca=5, motor="combustao"),
    dict(modelo="SUV Hibrido Urbano",     preco=198000, categoria="SUV",   consumo="baixo", manutencao="baixa", seguranca=5, motor="hibrido"),
]


def indice_eficiencia(carro):
    """Converte os rotulos crisp de consumo/manutencao do MP1 em indice 0-10."""
    return (CONSUMO_SCORE[carro["consumo"]] + MANUT_SCORE[carro["manutencao"]]) / 2.0


def elegivel(carro, perfil):
    """Restricoes BINARIAS do dominio permanecem crisp (nao se fuzzifica categoria)."""
    cat = perfil.get("categoria_exigida")
    if cat not in (None, "", "qualquer") and carro["categoria"] != cat:
        return False, f"categoria {carro['categoria']} != {cat}"
    if perfil.get("rejeita_combustao") and carro["motor"] == "combustao":
        return False, "rejeita combustao"
    return True, ""


def recomendar(nome, perfil, mp1_escolheu=None):
    """Pontua cada carro elegivel com o controlador fuzzy e ordena por adequacao."""
    print(f"\n=== {nome} ===")
    print(f"Perfil: orcamento R$ {perfil['orcamento']:,} | "
          f"categoria={perfil.get('categoria_exigida')} | "
          f"rejeita_combustao={perfil.get('rejeita_combustao', False)}")
    ranking = []
    for carro in CATALOGO:
        ok, motivo = elegivel(carro, perfil)
        if not ok:
            print(f"  [x] {carro['modelo']:<24} eliminado ({motivo})")
            continue
        pr = carro["preco"] / perfil["orcamento"] * 100.0
        ef = indice_eficiencia(carro)
        score = avaliar(pr, carro["seguranca"], ef)
        ranking.append((score, carro, pr, ef))
    ranking.sort(key=lambda t: t[0], reverse=True)
    print("  Ranking fuzzy (adequacao defuzzificada 0-100):")
    for score, carro, pr, ef in ranking:
        print(f"    {carro['modelo']:<24} adequacao={score:5.1f}  "
              f"(preco_rel={pr:5.1f}%, seg={carro['seguranca']}, ef={ef:.1f})")
    if ranking:
        venc = ranking[0][1]["modelo"]
        print(f"  >> Recomendacao fuzzy: {venc} (adequacao {ranking[0][0]:.1f})")
        if mp1_escolheu:
            igual = "IGUAL ao MP1" if venc == mp1_escolheu else f"DIFERE do MP1 (MP1 -> {mp1_escolheu})"
            print(f"     [comparacao MP1: {igual}]")
    return ranking


# ======================================================================
# 4. CASOS DE TESTE DO CONTROLADOR  (entradas -> saida -> interpretacao)
# ======================================================================
def casos_de_teste_controlador():
    """3 casos diretos exigidos pela rubrica: entradas, saida defuzzificada
    e interpretacao comentada do controlador Mamdani isolado."""
    print("\n" + "#" * 70)
    print("# CASOS DE TESTE DO CONTROLADOR FUZZY (entrada -> saida -> leitura)")
    print("#" * 70)

    # ---- Caso A: carro "dos sonhos" dentro do orcamento ----
    # Entradas: barato (60% do orc.), seguranca maxima (5), eficiencia otima (9)
    a = avaliar(preco_relativo=60, nota_seguranca=5, indice_eficiencia=9)
    print(f"\n[A] preco_rel=60%  seg=5.0  ef=9.0  ->  adequacao = {a:.1f}")
    print("    Interpretacao: dispara R4 (barato & alta & otima => recomendar) com")
    print("    forca alta; centroide cai na regiao 'recomendar' (~84). Compra ideal.")
    assert a > 75, "Caso A deveria ser fortemente recomendado"

    # ---- Caso B: carro acima do orcamento, mesmo sendo otimo no resto ----
    # Entradas: caro (130% do orc.), seguranca maxima, eficiencia otima
    b = avaliar(preco_relativo=130, nota_seguranca=5, indice_eficiencia=9)
    print(f"\n[B] preco_rel=130% seg=5.0  ef=9.0  ->  adequacao = {b:.1f}")
    print("    Interpretacao: R1 (caro => rejeitar) domina e veta o veiculo, mesmo")
    print("    com seguranca/eficiencia maximas; centroide na regiao 'rejeitar' (~16).")
    print("    Equivale ao corte R1 do MP1, mas de forma graduada e nao binaria.")
    assert b < 30, "Caso B deveria ser rejeitado pelo veto de orcamento"

    # ---- Caso C: caso de fronteira / intermediario ----
    # Entradas: no_orcamento (95%), seguranca media (3.5), eficiencia mediana (5.5)
    c = avaliar(preco_relativo=95, nota_seguranca=3.5, indice_eficiencia=5.5)
    print(f"\n[C] preco_rel=95%  seg=3.5  ef=5.5  ->  adequacao = {c:.1f}")
    print("    Interpretacao: nenhum extremo; R13 (no_orcamento & media & mediana =>")
    print("    considerar) lidera. Centroide no meio (~50): 'da pra considerar'.")
    print("    Um SBC crisp precisaria de um limiar artificial para decidir aqui.")
    assert 35 < c < 65, "Caso C deveria ser intermediario"

    print("\n  -> 3 casos de teste do controlador OK.")


if __name__ == "__main__":
    casos_de_teste_controlador()

    print("\n" + "#" * 70)
    print("# RECOMENDACAO SOBRE O CATALOGO (mesmos perfis do MP1)")
    print("#" * 70)
    recomendar("Caso 1 - Urbano/economia, orc 120k",
               dict(orcamento=120000, categoria_exigida="qualquer", rejeita_combustao=False),
               mp1_escolheu="Hatch Hibrido Compacto")
    recomendar("Caso 2 - Familia grande/viagem, SUV, orc 200k",
               dict(orcamento=200000, categoria_exigida="SUV", rejeita_combustao=False),
               mp1_escolheu="SUV Espacoso Seguro")
    recomendar("Caso 3 - Orcamento baixo 80k, seguranca, hatch",
               dict(orcamento=80000, categoria_exigida="hatch", rejeita_combustao=False),
               mp1_escolheu="Hatch Entrada Seguro")
    recomendar("Caso 4 - Rejeita combustao, urbano, SUV, orc 210k",
               dict(orcamento=210000, categoria_exigida="SUV", rejeita_combustao=True),
               mp1_escolheu="SUV Hibrido Urbano")
    print()
