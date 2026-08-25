"""Valida um roteiro de resolução ANTES de virar vídeo.

Duas travas independentes:

  1. GABARITO (trava dura) — o roteiro declara `alternativa_calculada`; ela tem de
     ser igual ao gabarito oficial. Uma modelagem errada do enunciado não cai na
     alternativa certa por acaso. Esta trava reprova sempre que falha.

  2. SYMPY (checagem da aritmética) — conforme `validacao.tipo`, o SymPy recomputa a
     grandeza e confere o valor. Cobre os tipos abaixo; se o tipo não for coberto,
     NÃO reprova por isso (a trava de gabarito continua valendo), apenas marca a
     aritmética como "não verificada automaticamente".

Tipos de verificação SymPy:
  - "expressao"       : avalia `expr` (com `vars`) e compara com `esperado`.
  - "equacao"         : resolve `equacao` em `var`, filtra domínio, confere que
                        `valor_esperado` é raiz e que `resposta_formula` nele dá
                        `resposta_esperada`.
  - "contagem_raizes" : resolve o polinômio auxiliar `polinomio` em `var`, conta as
                        raízes reais distintas e multiplica por `solucoes_por_raiz`,
                        comparando com `esperado`.
"""
import json
import sys

import sympy as sp


def _sym(nome, spec):
    kw = {}
    if spec.get("positivo"):
        kw["positive"] = True
    if spec.get("inteiro"):
        kw["integer"] = True
    return sp.Symbol(nome, **kw)


def verificar_sympy(v):
    tipo = v.get("tipo")
    vars = {n: _sym(n, s) for n, s in v.get("vars", {}).items()}

    if tipo == "expressao":
        expr = sp.sympify(v["expr"], locals=vars)
        calc = sp.simplify(expr)
        esp = sp.nsimplify(v["esperado"])
        if sp.simplify(calc - esp) != 0:
            return False, f"expressão dá {calc}, esperado {esp}"
        return True, f"expressão confere: {calc}"

    if tipo == "equacao":
        var = vars.get(v["var"]) or _sym(v["var"], v.get("var_spec", {}))
        eq = sp.sympify(v["equacao"], locals={**vars, v["var"]: var})
        raizes = sp.solve(eq, var)
        if v.get("dominio") == "positivo":
            raizes = [x for x in raizes if x.is_positive]
        if sp.nsimplify(v["valor_esperado"]) not in [sp.nsimplify(x) for x in raizes]:
            return False, f"valor {v['valor_esperado']} não está nas raízes {raizes}"
        formula = sp.sympify(v["resposta_formula"], locals={**vars, v["var"]: var})
        calc = formula.subs(var, v["valor_esperado"])
        if sp.nsimplify(calc) != sp.nsimplify(v["resposta_esperada"]):
            return False, f"fórmula dá {calc}, esperado {v['resposta_esperada']}"
        return True, f"raiz e fórmula conferem (resposta {calc})"

    if tipo == "contagem_raizes":
        var = vars.get(v["var"]) or sp.Symbol(v["var"])
        poly = sp.sympify(v["polinomio"], locals={**vars, v["var"]: var})
        reais = [r for r in sp.solve(poly, var) if r.is_real]
        n = len(set(reais)) * v.get("solucoes_por_raiz", 1)
        if n != v["esperado"]:
            return False, f"contagem dá {n} (raízes {reais}), esperado {v['esperado']}"
        return True, f"contagem confere: {len(set(reais))} raízes × " \
                     f"{v.get('solucoes_por_raiz',1)} = {n}"

    return None, f"tipo '{tipo}' não coberto — aritmética NÃO verificada"


def validar(caminho):
    r = json.load(open(caminho))
    v = r["validacao"]
    erros, avisos = [], []

    # trava dura: gabarito
    calc = v.get("alternativa_calculada", "").upper()
    gab = r["gabarito"].upper()
    if calc != gab:
        erros.append(f"GABARITO: resolução aponta '{calc}', gabarito oficial é '{gab}'")

    # coerência: passo de resposta bate com o gabarito
    pr = next((p for p in r["passos"] if p["acao"] == "resposta"), None)
    if pr and pr.get("alternativa", "").upper() != gab:
        erros.append(f"ROTEIRO: passo resposta '{pr.get('alternativa')}' ≠ gabarito '{gab}'")

    # checagem da aritmética
    ok, msg = verificar_sympy(v)
    if ok is False:
        erros.append(f"SYMPY: {msg}")
    elif ok is None:
        avisos.append(f"SYMPY: {msg}")

    return erros, avisos


if __name__ == "__main__":
    erros, avisos = validar(sys.argv[1])
    for a in avisos:
        print("  ⚠", a)
    if erros:
        print("REPROVADO — não renderizar:")
        for e in erros:
            print("  ✗", e)
        sys.exit(1)
    print("APROVADO — gabarito confere" +
          ("" if avisos else " e aritmética verificada no SymPy"))
