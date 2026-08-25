"""Renderizador determinístico: lê um roteiro JSON e desenha o vídeo.

Este arquivo NÃO conhece nenhuma questão específica. Ele percorre os passos do
roteiro e chama o componente de quadro correspondente a cada `acao`. A mesma lógica
serve para qualquer questão — o que muda é só o JSON. Adicionar uma questão nova é
escrever um roteiro, não código.

Também emite um arquivo de narração (`<id>.narracao.txt`) com o texto de cada passo,
para o professor gravar o áudio lendo os trechos na ordem.

Uso:
  ROTEIRO=/caminho/x.json manim -qm render.py Aula
"""
import json
import os

from manim import *

from quadro import QuadroDidatico, FUNDO, DESTAQUE

ROTEIRO = os.environ["ROTEIRO"]
# pasta com os áudios por passo + manifesto (opcional). Se presente, cada cena dura
# o tempo REAL da fala daquele passo e o áudio entra no início da cena — sincronia
# por construção. Sem ela, o ritmo é estimado por contagem de palavras.
AUDIO_DIR = os.environ.get("AUDIO_DIR")

# ações que ESCREVEM no quadro em sequência (empilham em cima do que já tem);
# todas as outras desenham conteúdo novo e centralizado, então precisam
# limpar qualquer fórmula acumulada antes — ver QuadroDidatico.limpar_texto
ACOES_QUE_ACUMULAM = {"escrever", "transformar", "resposta", "cabecalho"}

# ritmo de locução didática em PT-BR: ~2,3 palavras por segundo. Cada passo fica na
# tela pelo tempo estimado da sua narração, para o vídeo mudo já nascer no compasso
# da fala e casar quando o professor gravar o áudio por cima.
PALAVRAS_POR_SEG = 2.3
FALA_MINIMA = 2.5


def duracao_fala(texto):
    if not texto:
        return FALA_MINIMA
    return max(FALA_MINIMA, len(texto.split()) / PALAVRAS_POR_SEG)


class Aula(ThreeDScene):
    # ThreeDScene nasce com phi=0 (visão de cima, igual a uma Scene 2D comum), então
    # todo roteiro sem passo 3D renderiza idêntico a antes. Só o passo "solido_3d"
    # inclina a câmera, e sempre devolve pra phi=0 no final — o resto do motor
    # (quadro.py inteiro) não precisa saber que a cena é 3D-capable.
    def construct(self):
        self.camera.background_color = FUNDO
        r = json.load(open(ROTEIRO))
        q = QuadroDidatico(self)
        narracao = []

        # durações reais da fala, se houver áudio gerado
        duracoes = {}
        if AUDIO_DIR and os.path.exists(os.path.join(AUDIO_DIR, "manifesto.json")):
            for m in json.load(open(os.path.join(AUDIO_DIR, "manifesto.json"))):
                duracoes[m["passo"]] = m

        for idx, p in enumerate(r["passos"]):
            if p.get("narracao"):
                narracao.append(p["narracao"])
            # com áudio: cena dura a fala real + respiro; áudio entra no início da cena
            m = duracoes.get(idx)
            if m and m.get("wav"):
                self.add_sound(m["wav"])
                fala = m["dur"] + 0.8
            else:
                fala = duracao_fala(p.get("narracao"))
            acao = p["acao"]
            if acao not in ACOES_QUE_ACUMULAM:
                q.limpar_texto()

            if acao == "titulo":
                q.montar_cabecalho(p["texto"], p.get("subtitulo"), fala=fala)
            elif acao == "enunciado":
                q.mostrar_enunciado(p["texto"], p.get("alternativas"), fala=fala)
            elif acao == "figura":
                q.mostrar_figura(p["caminho"], legenda=p.get("legenda"),
                                 fixar=p.get("fixar", False), fala=fala)
            elif acao == "cabecalho":
                q.fixar_enunciado(p["latex"], fala=fala)
            elif acao == "escrever":
                q.escrever(p["latex"], destaque=p.get("destaque", False),
                           nota=p.get("nota"), fala=fala)
            elif acao == "transformar":
                q.transformar(p["latex"], operacao=p.get("operacao"), fala=fala)
            elif acao == "resposta":
                q.resposta(p["latex"], p["alternativa"], fala=fala)
            elif acao == "grafico":
                q.mostrar_grafico(p["funcoes"], dominio=p.get("dominio"),
                                   imagem=p.get("imagem"), pontos=p.get("pontos"),
                                   legenda=p.get("legenda"), fixar=p.get("fixar", False),
                                   fala=fala)
            elif acao == "linha_numerica":
                q.mostrar_linha_numerica(p["dominio"], pontos=p.get("pontos"),
                                          intervalos=p.get("intervalos"),
                                          fixar=p.get("fixar", False), fala=fala)
            elif acao == "arvore":
                q.mostrar_arvore(p["niveis"], fixar=p.get("fixar", False), fala=fala)
            elif acao == "geometria":
                q.mostrar_geometria(p["elementos"], fixar=p.get("fixar", False), fala=fala)
            elif acao == "grade":
                q.mostrar_grade(n=p.get("n"), colunas=p.get("colunas"),
                                 linhas=p.get("linhas"), caminho=p.get("caminho"),
                                 caminhos=p.get("caminhos"),
                                 diagonal=p.get("diagonal", False),
                                 sombrear=p.get("sombrear"),
                                 linha_extra_desloc=p.get("linha_extra_desloc"),
                                 pontos=p.get("pontos"), fixar=p.get("fixar", False),
                                 fala=fala)
            elif acao == "tabuleiro":
                q.mostrar_tabuleiro(p["linhas"], p["colunas"], p["pecas"],
                                     fixar=p.get("fixar", False), fala=fala)
            elif acao == "esboco":
                q.mostrar_esboco(p["elementos"], fixar=p.get("fixar", False), fala=fala)
            elif acao == "ciclo_trigo":
                q.mostrar_ciclo_trigo(angulos=p.get("angulos"), faixa=p.get("faixa"),
                                       linha_valor=p.get("linha_valor"),
                                       fixar=p.get("fixar", False), fala=fala)
            elif acao == "plano_complexo":
                q.mostrar_plano_complexo(p["pontos"], dominio=p.get("dominio"),
                                          imagem=p.get("imagem"), vetores=p.get("vetores", False),
                                          poligono=p.get("poligono", False),
                                          raio_circulo=p.get("raio_circulo"),
                                          fixar=p.get("fixar", False), fala=fala)
            elif acao == "vetores_2d":
                q.mostrar_vetores(p["vetores"], somar=p.get("somar", False),
                                   rotulo_soma=p.get("rotulo_soma", "u+v"),
                                   dominio=p.get("dominio"), imagem=p.get("imagem"),
                                   fixar=p.get("fixar", False), fala=fala)
            elif acao == "grade_polar":
                q.mostrar_grade_polar(p["raio_max"], pontos=p.get("pontos"),
                                       passo_raio=p.get("passo_raio"),
                                       segmento=p.get("segmento", False),
                                       fixar=p.get("fixar", False), fala=fala)
            elif acao == "tabela_dados":
                q.mostrar_tabela(p["cabecalho"], p["linhas"],
                                  destacar_coluna=p.get("destacar_coluna"),
                                  fixar=p.get("fixar", False), fala=fala)
            elif acao == "solido_3d":
                q.mostrar_solido_3d(p["tipo"], raio=p.get("raio", 1.5),
                                     altura=p.get("altura", 3.0),
                                     corte_altura=p.get("corte_altura"),
                                     rotular_raio=p.get("rotular_raio"),
                                     rotular_altura=p.get("rotular_altura"), fala=fala)
            elif acao == "anim_pg_infinita":
                q.anim_pg_infinita(p["primeiro_termo"], p["razao"],
                                    max_iteracoes=p.get("max_iteracoes", 6),
                                    fixar=p.get("fixar", False), fala=fala)
            elif acao == "anim_riemann":
                q.anim_riemann(p["expr"], p["dominio"], iteracoes=p.get("iteracoes"),
                                fixar=p.get("fixar", False), fala=fala)
            elif acao == "anim_seno":
                q.anim_seno(funcao=p.get("funcao", "seno"),
                             frequencia=p.get("frequencia", 1.0),
                             voltas=p.get("voltas", 1.0),
                             fixar=p.get("fixar", False), fala=fala)
            elif acao == "anim_discriminante":
                q.anim_discriminante(p["coeficientes"], p["k_inicial"], p["k_final"],
                                      k_critico=p.get("k_critico"),
                                      dominio=p.get("dominio"), imagem=p.get("imagem"),
                                      fixar=p.get("fixar", False), fala=fala)
            elif acao == "anim_peneira":
                q.anim_peneira(p["numero_maximo"], primos_a_filtrar=p.get("primos_a_filtrar"),
                                fixar=p.get("fixar", False), fala=fala)
            elif acao == "anim_corrida":
                q.anim_corrida(p["expr1"], p["expr2"], p["dominio"],
                                rotulo1=p.get("rotulo1", "f(x)"),
                                rotulo2=p.get("rotulo2", "g(x)"),
                                fixar=p.get("fixar", False), fala=fala)
            elif acao == "anim_fibonacci":
                q.anim_fibonacci(n_quadrados=p.get("n_quadrados", 7),
                                  fixar=p.get("fixar", False), fala=fala)
            elif acao == "anim_hanoi":
                q.anim_hanoi(n_discos=p.get("n_discos", 4),
                              fixar=p.get("fixar", False), fala=fala)
            elif acao == "regioes_circulo":
                q.mostrar_regioes_circulo(p["sequencia"],
                                            fixar=p.get("fixar", False), fala=fala)
            else:
                raise ValueError(f"ação desconhecida no roteiro: {acao}")

        self.wait(1.0)

        # roteiro de narração para o professor gravar
        saida = ROTEIRO.replace(".json", ".narracao.txt")
        with open(saida, "w") as fh:
            fh.write(f"# Narração — {r['id']}\n")
            fh.write("# Leia cada bloco na ordem; grave um trecho por bloco.\n\n")
            for i, txt in enumerate(narracao, 1):
                fh.write(f"[{i}] {txt}\n\n")
