"""Componentes fixos do quadro didático.

Toda a decisão de LAYOUT e de RITMO mora aqui. O renderizador só chama estes métodos;
nenhuma questão mexe neste arquivo. Corrigir o visual uma vez conserta todos os vídeos.

Ritmo: cada método recebe `fala` = duração estimada da narração daquele passo (s). O
método escreve a fórmula e depois espera o resto do tempo, para o passo inteiro durar
~`fala`. Assim o vídeo mudo já tem o compasso da voz e casa quando o áudio entra.
"""
import numpy as np
import sympy as sp
from manim import *

# Paleta "No Alvo": preto tático + dourado + branco, igual à identidade visual
# do projeto (logo/banner). Antes era tema de lousa verde-escura; agora usa o
# mesmo par preto/dourado do banner, com branco quente para o texto principal.
FUNDO = "#0b0b0d"
GIZ = "#f7f7f4"
DESTAQUE = "#e6a93c"
APOIO = "#c4c4c0"
NOTA = "#f0c869"

TOPO_TRABALHO = 2.0
BASE_TRABALHO = -3.3
ESQUERDA = -6.2


class QuadroDidatico:
    def __init__(self, scene):
        self.scene = scene
        self.linhas = VGroup()
        self.cabecalho = None
        self.enunciado_fixo = None
        self.figura_fixa = None

    def _pausa(self, fala, ja_gasto):
        """Espera o que falta para o passo durar `fala` segundos."""
        resto = (fala or 0) - ja_gasto
        self.scene.wait(max(0.4, resto))

    def limpar_texto(self):
        """Tira do quadro qualquer fórmula acumulada em `self.linhas` antes de
        um passo que desenha conteúdo novo e centralizado (título, enunciado,
        figura, diagrama, animação). Sem isso, texto de passos `escrever`
        anteriores (que nunca se apaga sozinho — é pensado pra ir empilhando,
        como um quadro-negro) ficava atrás/por cima do desenho novo sempre que
        um diagrama vinha logo depois de uma ou mais linhas escritas."""
        if len(self.linhas) > 0:
            self.scene.play(FadeOut(self.linhas), run_time=0.5)
            self.linhas = VGroup()

    # ----------------------------------------------------------- título
    def montar_cabecalho(self, titulo, subtitulo=None, fala=None):
        t = Text(titulo, font_size=40, color=GIZ)
        grupo = VGroup(t)
        if subtitulo:
            s = Text(subtitulo, font_size=24, color=APOIO).next_to(t, DOWN, buff=0.25)
            grupo.add(s)
        grupo.move_to(ORIGIN)
        self.scene.play(Write(t), run_time=1.4)
        if subtitulo:
            self.scene.play(FadeIn(grupo[1], shift=UP * 0.15), run_time=0.7)
        self._pausa(fala, 2.1)
        self.scene.play(FadeOut(grupo), run_time=0.6)

    # ----------------------------------------------------------- enunciado completo
    def mostrar_enunciado(self, texto, alternativas=None, fala=None):
        titulo = Text("ENUNCIADO", font_size=26, color=APOIO).to_edge(UP, buff=0.6)
        corpo = Paragraph(*self._quebrar(texto, 58), alignment="left",
                          line_spacing=1.0, font_size=27, color=GIZ)
        corpo.set(width=min(corpo.width, 11.5))
        corpo.next_to(titulo, DOWN, buff=0.6)
        grupo = VGroup(titulo, corpo)
        if alternativas:
            alt = Text(alternativas, font_size=25, color=DESTAQUE)
            alt.set(width=min(alt.width, 11.0)).next_to(corpo, DOWN, buff=0.7)
            grupo.add(alt)
        self.scene.play(Write(titulo), run_time=0.7)
        self.scene.play(FadeIn(corpo, shift=UP * 0.2), run_time=1.6)
        if alternativas:
            self.scene.play(FadeIn(grupo[2], shift=UP * 0.15), run_time=0.9)
        self._pausa(fala, 3.2)
        self.scene.play(FadeOut(grupo), run_time=0.7)

    def _quebrar(self, texto, largura):
        palavras, linhas, atual = texto.split(), [], ""
        for w in palavras:
            if len(atual) + len(w) + 1 > largura:
                linhas.append(atual); atual = w
            else:
                atual = f"{atual} {w}".strip()
        if atual:
            linhas.append(atual)
        return linhas

    # ----------------------------------------------------------- figura da questão
    def mostrar_figura(self, caminho, legenda=None, fixar=False, fala=None):
        """Exibe a figura da questão. Com fixar=True ela encolhe e vai para o canto,
        ficando visível durante a resolução — como o desenho que o professor deixa
        no canto do quadro."""
        vetor = caminho.lower().endswith(".svg")
        if vetor:
            # SVG: o Manim DESENHA traço a traço (Create), como o professor no quadro.
            # potrace vetoriza o CONTORNO do traço, então preenchemos em vez de dar
            # stroke — senão a linha sai oca/dupla.
            img = SVGMobject(caminho)
            img.set(height=4.2).set_fill(GIZ, opacity=1).set_stroke(GIZ, width=0.6)
        else:
            img = ImageMobject(caminho)
            img.set(height=min(4.2, img.height))
        img.move_to(ORIGIN).shift(DOWN * 0.2)
        grupo = Group(img) if not vetor else VGroup(img)
        if legenda:
            leg = Text(legenda, font_size=22, color=APOIO).next_to(img, DOWN, buff=0.3)
            grupo.add(leg)
        if vetor:
            self.scene.play(Create(img), run_time=min(4.0, max(2.0, (fala or 3) * 0.5)))
            if legenda:
                self.scene.play(FadeIn(grupo[1]), run_time=0.5)
            self._pausa(fala, 3.0)
        else:
            self.scene.play(FadeIn(grupo, scale=0.95), run_time=1.0)
            self._pausa(fala, 1.0)
        if fixar:
            # encolhe e ancora no canto superior direito, fora da área de escrita
            self.scene.play(
                img.animate.set(height=2.0).to_corner(UR, buff=0.4),
                *( [FadeOut(grupo[1])] if legenda else [] ), run_time=1.0)
            self.figura_fixa = img
        else:
            self.scene.play(FadeOut(grupo), run_time=0.6)

    def _fixar_no_canto(self, grupo, fixar, altura=2.0):
        """Mesmo gesto do `fixar` da figura: encolhe e ancora no canto superior
        direito, fora da área de escrita, ou some da tela."""
        if fixar:
            self.scene.play(
                grupo.animate.set(height=min(altura, grupo.height)).to_corner(UR, buff=0.4),
                run_time=1.0)
            self.figura_fixa = grupo
        else:
            self.scene.play(FadeOut(grupo), run_time=0.6)

    # ----------------------------------------------------------- diagramas
    # Vocabulário tipado de propósito: cada diagrama tem parâmetros com forma
    # fixa (números, listas, referências por nome) — é o jeito de dar um vídeo
    # com cara de 3Blue1Brown / MindYourDecisions sem abrir a porta pra um
    # roteiro gerado por IA desenhar SVG livre e sair algo esdrúxulo. Dentro de
    # cada tipo os parâmetros dão bastante liberdade (nº de pontos, de níveis,
    # de células da malha); quem não muda é o jeito como cada tipo é desenhado.

    def mostrar_grafico(self, funcoes, dominio=None, imagem=None, pontos=None,
                         legenda=None, fixar=False, fala=None):
        """Plano cartesiano simples com até 3 funções y=f(x).

        funcoes: [{"expr": "x**2 - 1", "cor": (opcional), "rotulo": "f(x)" (opcional)}]
        dominio: [xmin, xmax] do eixo x (padrão -5..5)
        imagem:  [ymin, ymax] do eixo y (padrão -5..5)
        pontos:  [{"x": 1, "y": 0, "rotulo": "A" (opcional)}] — marca pontos no gráfico
        """
        xmin, xmax = dominio or [-5, 5]
        ymin, ymax = imagem or [-5, 5]
        eixos = Axes(x_range=[xmin, xmax, 1], y_range=[ymin, ymax, 1],
                     x_length=6.4, y_length=3.6,
                     axis_config={"color": APOIO, "stroke_width": 1.5,
                                  "font_size": 20, "tip_width": 0.15,
                                  "tip_height": 0.15})
        eixos.move_to(ORIGIN).shift(DOWN * 0.2)
        grupo = VGroup(eixos)

        var = sp.Symbol("x")
        cores = [DESTAQUE, GIZ, APOIO]
        curvas = []
        for i, f in enumerate(funcoes[:3]):
            fn = sp.lambdify(var, sp.sympify(f["expr"]), "numpy")
            cor = f.get("cor", cores[i % len(cores)])
            curva = eixos.plot(fn, x_range=[xmin, xmax], color=cor, stroke_width=3.5)
            curvas.append(curva)
            grupo.add(curva)
            if f.get("rotulo"):
                rot = MathTex(f["rotulo"], font_size=26, color=cor)
                rot.next_to(curva.get_end(), UR, buff=0.08)
                grupo.add(rot)

        extras = VGroup()
        for p in (pontos or []):
            dot = Dot(eixos.c2p(p["x"], p["y"]), color=GIZ, radius=0.06)
            extras.add(dot)
            if p.get("rotulo"):
                extras.add(Text(p["rotulo"], font_size=20, color=GIZ).next_to(dot, UP, buff=0.1))
        if legenda:
            extras.add(Text(legenda, font_size=22, color=APOIO).next_to(eixos, DOWN, buff=0.3))
        grupo.add(extras)

        self.scene.play(Create(eixos), run_time=1.0)
        gasto = 1.0
        for curva in curvas:
            self.scene.play(Create(curva), run_time=1.1)
            gasto += 1.1
        if len(extras):
            self.scene.play(FadeIn(extras), run_time=0.6)
            gasto += 0.6
        self._pausa(fala, gasto)
        self._fixar_no_canto(grupo, fixar, altura=2.0)

    def mostrar_linha_numerica(self, dominio, pontos=None, intervalos=None,
                                fixar=False, fala=None):
        """Reta numérica — pra intervalo, desigualdade, MDC/MMC, etc.

        dominio: [min, max]
        pontos: [{"x": 2, "rotulo": "2" (opcional), "aberto": False}] — bola cheia/vazia
        intervalos: [{"de": 1, "ate": 4, "cor": (opcional)}] — trecho pintado sobre a reta
        """
        xmin, xmax = dominio
        linha = NumberLine(x_range=[xmin, xmax, 1], length=10.5, color=APOIO,
                           include_numbers=True, font_size=22)
        linha.move_to(ORIGIN)
        grupo = VGroup(linha)

        for it in (intervalos or []):
            trecho = Line(linha.n2p(it["de"]), linha.n2p(it["ate"]),
                         color=it.get("cor", DESTAQUE), stroke_width=5)
            grupo.add(trecho)
        extras = VGroup()
        for p in (pontos or []):
            aberto = p.get("aberto", False)
            dot = Dot(linha.n2p(p["x"]), color=DESTAQUE, radius=0.09,
                     fill_opacity=0 if aberto else 1, stroke_width=2.5,
                     stroke_color=DESTAQUE)
            extras.add(dot)
            if p.get("rotulo"):
                extras.add(Text(p["rotulo"], font_size=22, color=GIZ).next_to(dot, UP, buff=0.15))
        grupo.add(extras)

        self.scene.play(Create(linha), run_time=1.0)
        gasto = 1.0
        if len(grupo) > 1:
            self.scene.play(FadeIn(VGroup(*list(grupo)[1:])), run_time=0.7)
            gasto += 0.7
        self._pausa(fala, gasto)
        self._fixar_no_canto(grupo, fixar, altura=1.2)

    def mostrar_arvore(self, niveis, fixar=False, fala=None):
        """Árvore de possibilidades por níveis — pra contagem e probabilidade.

        niveis: [["3 pretos", "2 vermelhos", "1 branco"], ["vaga 1", "vaga 2", ...], ...]
        Cada nó de um nível se liga a TODOS os nós do nível seguinte (é o caso do
        princípio multiplicativo). Só essa forma, de propósito — vira ilegível se
        virar um grafo arbitrário.
        """
        colunas = []
        for nivel in niveis:
            nos = VGroup()
            for rotulo in nivel:
                txt = Text(rotulo, font_size=20, color=GIZ)
                caixa = SurroundingRectangle(txt, color=APOIO, buff=0.15, stroke_width=1.5)
                nos.add(VGroup(caixa, txt))
            nos.arrange(DOWN, buff=0.35)
            colunas.append(nos)
        grupo = VGroup(*colunas).arrange(RIGHT, buff=1.4, aligned_edge=UP)
        grupo.move_to(ORIGIN).shift(DOWN * 0.1)
        if grupo.width > 11.5:
            grupo.set(width=11.5)
        if grupo.height > 4.4:
            grupo.set(height=4.4)

        self.scene.play(FadeIn(colunas[0]), run_time=0.5)
        gasto = 0.5
        for i in range(1, len(colunas)):
            ramos = VGroup(*[Line(a.get_right(), b.get_left(), color=APOIO, stroke_width=1.2)
                             for a in colunas[i - 1] for b in colunas[i]])
            grupo.add(ramos)
            self.scene.play(Create(ramos), run_time=0.5)
            self.scene.play(FadeIn(colunas[i]), run_time=0.5)
            gasto += 1.0
        self._pausa(fala, gasto)
        self._fixar_no_canto(grupo, fixar, altura=2.4)

    def mostrar_geometria(self, elementos, fixar=False, fala=None):
        """Desenho geométrico a partir de uma lista de elementos TIPADOS — só estes
        cinco tipos, de propósito, pra nunca virar um SVG livre e esdrúxulo:

          {"tipo": "ponto", "nome": "A", "x": 0, "y": 0, "rotulo": "A" (opcional)}
          {"tipo": "segmento", "de": "A", "ate": "B"}
          {"tipo": "circulo", "centro": "O", "raio": 1.5}
          {"tipo": "poligono", "vertices": ["A", "B", "C"]}
          {"tipo": "angulo", "vertice": "B", "de": "A", "ate": "C", "rotulo": "θ" (opcional)}

        Coordenadas em unidades livres — a função reescala pra caber no quadro.
        """
        pontos = {e["nome"]: np.array([e["x"], e["y"], 0.0])
                  for e in elementos if e["tipo"] == "ponto"}

        grupo = VGroup()
        marcas = VGroup()
        for e in elementos:
            t = e["tipo"]
            if t == "segmento":
                grupo.add(Line(pontos[e["de"]], pontos[e["ate"]], color=GIZ, stroke_width=3))
            elif t == "circulo":
                grupo.add(Circle(radius=e["raio"], color=GIZ, stroke_width=3)
                         .move_to(pontos[e["centro"]]))
            elif t == "poligono":
                grupo.add(Polygon(*[pontos[v] for v in e["vertices"]],
                                  color=GIZ, stroke_width=3, fill_opacity=0))
            elif t == "angulo":
                l1 = Line(pontos[e["vertice"]], pontos[e["de"]])
                l2 = Line(pontos[e["vertice"]], pontos[e["ate"]])
                grupo.add(Angle(l1, l2, radius=0.4, color=DESTAQUE))
                if e.get("rotulo"):
                    meio = Angle(l1, l2, radius=0.65).point_from_proportion(0.5)
                    marcas.add(MathTex(e["rotulo"], font_size=24, color=DESTAQUE).move_to(meio))
        # rótulo de cada ponto sai para FORA da figura (direção centro→ponto), não
        # num canto fixo — senão em vértices com ângulo marcado o texto cai em
        # cima do arco, que sempre aponta para dentro.
        centro = np.mean(list(pontos.values()), axis=0) if pontos else ORIGIN
        for nome, p in pontos.items():
            grupo.add(Dot(p, color=GIZ, radius=0.05))
            direcao = p - centro
            direcao = direcao / np.linalg.norm(direcao) if np.linalg.norm(direcao) > 1e-6 else UR
            rotulo = next((e.get("rotulo", nome) for e in elementos
                          if e["tipo"] == "ponto" and e["nome"] == nome), nome)
            marcas.add(Text(rotulo, font_size=22, color=APOIO).move_to(p + direcao * 0.32))
        grupo.add(marcas)

        grupo.move_to(ORIGIN).shift(DOWN * 0.2)
        if grupo.width > 6.5:
            grupo.set(width=6.5)
        if grupo.height > 4.2:
            grupo.set(height=4.2)

        self.scene.play(Create(grupo), run_time=1.4)
        self._pausa(fala, 1.4)
        self._fixar_no_canto(grupo, fixar, altura=2.2)

    def mostrar_grade(self, n=None, colunas=None, linhas=None, caminho=None,
                       caminhos=None, diagonal=False, sombrear=None,
                       linha_extra_desloc=None, pontos=None, fixar=False, fala=None):
        """Malha (por padrão n×n) — pra contagem de caminhos (Catalan, problema
        da urna/eleição, princípio da reflexão), tabuleiro, arranjos em grade.
        Origem em (0,0) no canto inferior esquerdo.

        n: tamanho da malha n×n (padrão quando `colunas`/`linhas` não são dados)
        colunas, linhas: dá pra usar uma malha retangular em vez de quadrada —
                         útil pra mostrar a reflexão de um caminho, que termina
                         fora do quadrado original (ver `linha_extra_desloc`)
        caminho: atalho pra um único caminho em destaque — lista de passos
                 "D" (direita) / "C" (cima) a partir de (0,0)
        caminhos: lista de caminhos, pra mostrar mais de um ao mesmo tempo (ex.:
                  o caminho ruim e o caminho refletido lado a lado) — cada item
                  {"passos": ["D","C",...], "cor": "destaque"|"apoio"|"nota"|"giz"
                  (padrão "destaque"), "tracejado": False}
        diagonal: True desenha a diagonal (0,0)–(n,n)
        linha_extra_desloc: desenha uma reta tracejada paralela à diagonal,
                            deslocada esse tanto de células (ex.: 1 pra y=x+1 —
                            a reta que separa caminho bom de caminho ruim)
        sombrear: "acima" ou "abaixo" — sombreia de leve o lado proibido da diagonal
        pontos: [{"i":1,"j":2,"rotulo":"P"}] — marca um ponto específico da
                malha (i=coluna, j=linha, 0-based) com bolinha e rótulo
        """
        colunas = colunas or n
        linhas_n = linhas or n
        lado = min(0.7, 4.4 / max(colunas, linhas_n))
        origem = np.array([-colunas * lado / 2, -linhas_n * lado / 2, 0.0])

        def pt(i, j):
            return origem + np.array([i * lado, j * lado, 0.0])

        grade = VGroup(
            *[Line(pt(i, 0), pt(i, linhas_n), color=APOIO, stroke_width=1)
              for i in range(colunas + 1)],
            *[Line(pt(0, j), pt(colunas, j), color=APOIO, stroke_width=1)
              for j in range(linhas_n + 1)])
        grupo = VGroup(grade)

        sombra = None
        if sombrear == "acima":
            sombra = Polygon(pt(0, 0), pt(0, linhas_n), pt(colunas, linhas_n),
                             fill_color=GIZ, fill_opacity=0.06, stroke_width=0)
        elif sombrear == "abaixo":
            sombra = Polygon(pt(0, 0), pt(colunas, 0), pt(colunas, linhas_n),
                             fill_color=GIZ, fill_opacity=0.06, stroke_width=0)
        if sombra:
            grupo.add(sombra)

        # diagonal fica discreta (mesma cor da malha) de propósito: ela é só o
        # limite de referência, quem precisa se destacar são os caminhos
        diag = Line(pt(0, 0), pt(colunas, colunas), color=APOIO, stroke_width=2.5) if diagonal else None
        if diag:
            grupo.add(diag)

        # sólida e fina, de propósito: tracejado fica reservado pro caminho
        # refletido, senão os dois se confundem (mesma cor, mesmo estilo)
        extra = None
        if linha_extra_desloc is not None:
            d = linha_extra_desloc
            extra = Line(pt(0, d), pt(colunas - d, colunas),
                        color=NOTA, stroke_width=1.5)
            grupo.add(extra)

        self.scene.play(Create(grade), run_time=1.2)
        gasto = 1.2
        if sombra:
            self.scene.play(FadeIn(sombra), run_time=0.5)
            gasto += 0.5
        if diag:
            self.scene.play(Create(diag), run_time=0.6)
            gasto += 0.6
        if extra:
            self.scene.play(Create(extra), run_time=0.6)
            gasto += 0.6

        paleta = {"giz": GIZ, "destaque": DESTAQUE, "apoio": APOIO, "nota": NOTA}
        lista = caminhos or ([{"passos": caminho, "cor": "destaque"}] if caminho else [])
        for c in lista:
            i = j = 0
            vertices = [pt(0, 0)]
            for passo in c["passos"]:
                if passo.upper().startswith("D"):
                    i += 1
                else:
                    j += 1
                vertices.append(pt(i, j))
            cor = paleta.get(c.get("cor", "destaque"), DESTAQUE)
            trilha = VMobject(color=cor, stroke_width=5).set_points_as_corners(vertices)
            if c.get("tracejado"):
                trilha = DashedVMobject(trilha, num_dashes=max(8, len(vertices) * 2))
            grupo.add(trilha)
            tempo = min(2.5, 0.25 * len(c["passos"]))
            self.scene.play(Create(trilha), run_time=tempo)
            gasto += tempo

        marcas = VGroup()
        for p in (pontos or []):
            coord = pt(p["i"], p["j"])
            marcas.add(Dot(coord, color=GIZ, radius=0.07))
            if p.get("rotulo"):
                marcas.add(Text(p["rotulo"], font_size=22, color=GIZ).next_to(coord, UR, buff=0.08))
        if len(marcas):
            grupo.add(marcas)
            self.scene.play(FadeIn(marcas), run_time=0.5)
            gasto += 0.5

        self._pausa(fala, gasto)
        self._fixar_no_canto(grupo, fixar, altura=2.4)

    def mostrar_tabuleiro(self, linhas, colunas, pecas, fixar=False, fala=None):
        """Tabuleiro `linhas`×`colunas` coberto por peças de dominó (1×2) — pra
        recorrência de cobertura ("de quantos jeitos cobrir um tabuleiro 2×n"),
        clássico de Fibonacci em contagem.

        pecas: [{"col":0, "linha":0, "orientacao":"V"|"H", "cor": (opcional)}]
        (col,linha) é a célula inferior-esquerda da peça, 0-based. "V" ocupa
        (col,linha) e (col,linha+1); "H" ocupa (col,linha) e (col+1,linha). As
        peças precisam cobrir o tabuleiro certinho — sem sobrepor, sem buraco —
        senão o desenho sai incoerente com a própria contagem que ele ilustra.
        `cor` é opcional (nome da paleta); sem ela, alterna automaticamente pra
        as peças ficarem visualmente distintas.
        """
        lado = min(0.8, 6.0 / colunas, 3.6 / linhas)
        origem = np.array([-colunas * lado / 2, -linhas * lado / 2, 0.0])

        def pt(i, j):
            return origem + np.array([i * lado, j * lado, 0.0])

        grade = VGroup(
            *[Line(pt(i, 0), pt(i, linhas), color=APOIO, stroke_width=1)
              for i in range(colunas + 1)],
            *[Line(pt(0, j), pt(colunas, j), color=APOIO, stroke_width=1)
              for j in range(linhas + 1)])
        grupo = VGroup(grade)

        paleta = {"giz": GIZ, "destaque": DESTAQUE, "apoio": APOIO, "nota": NOTA}
        cores = [DESTAQUE, APOIO, NOTA, GIZ]
        pares = VGroup()
        for i, d in enumerate(pecas):
            c, r = d["col"], d["linha"]
            fim = pt(c + 1, r + 2) if d["orientacao"] == "V" else pt(c + 2, r + 1)
            inicio = pt(c, r)
            cor = paleta.get(d.get("cor"), cores[i % len(cores)])
            peca = Rectangle(width=abs(fim[0] - inicio[0]), height=abs(fim[1] - inicio[1]),
                             color=cor, stroke_width=2.5, fill_color=cor, fill_opacity=0.45)
            peca.move_to((inicio + fim) / 2)
            pares.add(peca)
        grupo.add(pares)

        self.scene.play(Create(grade), run_time=1.0)
        gasto = 1.0
        self.scene.play(FadeIn(pares), run_time=1.0)
        gasto += 1.0
        self._pausa(fala, gasto)
        self._fixar_no_canto(grupo, fixar, altura=2.2)

    def mostrar_esboco(self, elementos, fixar=False, fala=None):
        """Canvas livre pra quando a questão pede um desenho que não é gráfico,
        reta, árvore, geometria nem malha (ex.: diagrama de Venn, urna, esquema
        de fluxo simples). Dá liberdade de composição SEM abrir espaço pra SVG
        arbitrário: só estas seis primitivas, cor sempre por NOME da paleta
        ("giz"|"destaque"|"apoio"|"nota" — nunca hex, pra nunca fugir da
        identidade visual) e no máximo 14 elementos (o resto é ignorado — o
        objetivo é um esboço tipo quadro-negro, não uma infografia carregada).

          {"tipo": "ponto", "x":.., "y":.., "cor": (opcional)}
          {"tipo": "segmento", "x1":.., "y1":.., "x2":.., "y2":.., "cor": (opcional)}
          {"tipo": "seta", "x1":.., "y1":.., "x2":.., "y2":.., "cor": (opcional)}
          {"tipo": "circulo", "x":.., "y":.., "raio":.., "cor":.., "preencher": False,
           "opacidade": 0.12}
          {"tipo": "retangulo", "x":.., "y":.., "largura":.., "altura":.., "cor":..,
           "preencher": False, "opacidade": 0.12}
          {"tipo": "texto", "x":.., "y":.., "texto": "...", "cor":.., "tamanho": 22}

        Coordenadas em unidades livres — a função reescala pra caber no quadro.
        """
        paleta = {"giz": GIZ, "destaque": DESTAQUE, "apoio": APOIO, "nota": NOTA}
        grupo = VGroup()
        for e in elementos[:14]:
            cor = paleta.get(e.get("cor"), GIZ)
            t = e["tipo"]
            if t == "ponto":
                grupo.add(Dot(np.array([e["x"], e["y"], 0.0]), color=cor, radius=0.05))
            elif t == "segmento":
                grupo.add(Line(np.array([e["x1"], e["y1"], 0.0]),
                               np.array([e["x2"], e["y2"], 0.0]), color=cor, stroke_width=3))
            elif t == "seta":
                grupo.add(Arrow(np.array([e["x1"], e["y1"], 0.0]),
                                np.array([e["x2"], e["y2"], 0.0]), color=cor,
                                stroke_width=3, buff=0, tip_length=0.2))
            elif t == "circulo":
                c = Circle(radius=e["raio"], color=cor, stroke_width=3,
                          fill_opacity=e.get("opacidade", 0.12) if e.get("preencher") else 0)
                c.move_to([e["x"], e["y"], 0.0])
                grupo.add(c)
            elif t == "retangulo":
                r = Rectangle(width=e["largura"], height=e["altura"], color=cor,
                              stroke_width=3,
                              fill_opacity=e.get("opacidade", 0.12) if e.get("preencher") else 0)
                r.move_to([e["x"], e["y"], 0.0])
                grupo.add(r)
            elif t == "texto":
                grupo.add(Text(e["texto"], font_size=e.get("tamanho", 22), color=cor)
                         .move_to([e["x"], e["y"], 0.0]))

        grupo.move_to(ORIGIN).shift(DOWN * 0.2)
        if grupo.width > 8.5:
            grupo.set(width=8.5)
        if grupo.height > 4.4:
            grupo.set(height=4.4)

        self.scene.play(Create(grupo), run_time=1.4)
        self._pausa(fala, 1.4)
        self._fixar_no_canto(grupo, fixar, altura=2.2)

    def mostrar_ciclo_trigo(self, angulos=None, faixa=None, linha_valor=None,
                             fixar=False, fala=None):
        """Círculo trigonométrico — pra inequação trigonométrica, arco côngruo,
        simetria de sinal entre quadrantes.

        angulos: [{"rad": "pi/3", "rotulo": "\\pi/3"}] — ponto marcado no ciclo
                 ("rad" é uma expressão SymPy em radianos, ex. "pi/3", "5*pi/6")
        faixa: {"de": "pi/3", "ate": "2*pi/3", "cor": (opcional)} — setor
               sombreado entre dois ângulos (a região-solução de uma inequação)
        linha_valor: {"y": "sqrt(3)/2", "rotulo": "√3/2"} — reta horizontal de
                     referência (ex.: pra sen(x) > valor)
        """
        R = 1.8
        circulo = Circle(radius=R, color=APOIO, stroke_width=2)
        eixos = VGroup(
            Line(LEFT * R * 1.25, RIGHT * R * 1.25, color=APOIO, stroke_width=1),
            Line(DOWN * R * 1.25, UP * R * 1.25, color=APOIO, stroke_width=1))
        grupo = VGroup(eixos, circulo)

        setor = None
        if faixa:
            de = float(sp.sympify(faixa["de"]))
            ate = float(sp.sympify(faixa["ate"]))
            setor = Sector(radius=R, start_angle=de, angle=(ate - de),
                           color=faixa.get("cor", DESTAQUE), fill_opacity=0.25,
                           stroke_width=0)
            grupo.add(setor)

        linha = None
        if linha_valor:
            y = float(sp.sympify(linha_valor["y"]))
            linha = Line(np.array([-R, y, 0.0]), np.array([R, y, 0.0]),
                        color=NOTA, stroke_width=2)
            grupo.add(linha)
            if linha_valor.get("rotulo"):
                rot = MathTex(linha_valor["rotulo"], font_size=22, color=NOTA)
                rot.next_to(linha, RIGHT, buff=0.1)
                grupo.add(rot)

        marcas = VGroup()
        for a in (angulos or []):
            rad = float(sp.sympify(a["rad"]))
            p = np.array([R * np.cos(rad), R * np.sin(rad), 0.0])
            marcas.add(Line(ORIGIN, p, color=GIZ, stroke_width=1.5))
            marcas.add(Dot(p, color=DESTAQUE, radius=0.06))
            if a.get("rotulo"):
                direcao = p / (np.linalg.norm(p) or 1)
                marcas.add(MathTex(a["rotulo"], font_size=22, color=GIZ)
                          .move_to(p + direcao * 0.35))
        grupo.add(marcas)
        grupo.move_to(ORIGIN).shift(DOWN * 0.2)

        self.scene.play(Create(VGroup(eixos, circulo)), run_time=1.0)
        gasto = 1.0
        if setor:
            self.scene.play(FadeIn(setor), run_time=0.6)
            gasto += 0.6
        extras = VGroup(*([linha] if linha else []), marcas)
        if len(extras):
            self.scene.play(FadeIn(extras), run_time=0.8)
            gasto += 0.8
        self._pausa(fala, gasto)
        self._fixar_no_canto(grupo, fixar, altura=2.2)

    def mostrar_plano_complexo(self, pontos, dominio=None, imagem=None,
                                vetores=False, poligono=False,
                                raio_circulo=None, fixar=False, fala=None):
        """Plano de Argand-Gauss — números complexos, raízes da unidade,
        rotação por multiplicação, lugares geométricos simples.

        pontos: [{"re": 2, "im": 0, "rotulo": "2"}]
        vetores: True desenha uma seta da origem até cada ponto, em vez de bolinha
        poligono: True conecta os pontos em ordem (ex.: raízes formando um quadrado)
        raio_circulo: raio de uma circunferência de referência centrada na origem
        """
        xmin, xmax = dominio or [-3, 3]
        ymin, ymax = imagem or [-3, 3]
        eixos = Axes(x_range=[xmin, xmax, 1], y_range=[ymin, ymax, 1],
                     x_length=5.6, y_length=5.6,
                     axis_config={"color": APOIO, "stroke_width": 1.5, "font_size": 20,
                                  "tip_width": 0.15, "tip_height": 0.15})
        eixos.move_to(ORIGIN).shift(DOWN * 0.2)
        rot_re = Text("Re", font_size=20, color=APOIO).next_to(eixos.x_axis.get_end(), UP, buff=0.1)
        rot_im = Text("Im", font_size=20, color=APOIO).next_to(eixos.y_axis.get_end(), RIGHT, buff=0.1)
        grupo = VGroup(eixos, rot_re, rot_im)

        circ = None
        if raio_circulo:
            circ = ParametricFunction(
                lambda t: eixos.c2p(raio_circulo * np.cos(t), raio_circulo * np.sin(t)),
                t_range=[0, 2 * np.pi], color=NOTA, stroke_width=1.5)
            grupo.add(circ)

        marcas = VGroup()
        coords = [eixos.c2p(p["re"], p["im"]) for p in pontos]
        for p, coord in zip(pontos, coords):
            if vetores:
                marcas.add(Arrow(eixos.c2p(0, 0), coord, color=DESTAQUE, buff=0,
                                 stroke_width=3, tip_length=0.18))
            else:
                marcas.add(Dot(coord, color=DESTAQUE, radius=0.06))
            if p.get("rotulo"):
                marcas.add(MathTex(p["rotulo"], font_size=24, color=GIZ)
                          .next_to(coord, UR, buff=0.1))
        if poligono and len(coords) >= 3:
            marcas.add(Polygon(*coords, color=GIZ, stroke_width=2, fill_opacity=0))
        grupo.add(marcas)

        self.scene.play(Create(eixos), FadeIn(rot_re, rot_im), run_time=1.0)
        gasto = 1.0
        if circ:
            self.scene.play(Create(circ), run_time=0.6)
            gasto += 0.6
        self.scene.play(FadeIn(marcas), run_time=0.8)
        gasto += 0.8
        self._pausa(fala, gasto)
        self._fixar_no_canto(grupo, fixar, altura=2.2)

    def mostrar_vetores(self, vetores, somar=False, rotulo_soma="u+v",
                         dominio=None, imagem=None, fixar=False, fala=None):
        """Vetores no plano — soma pela regra do paralelogramo, pra geometria
        analítica com vetores (produto escalar, projeção, área).

        vetores: [{"x": 3, "y": 4, "rotulo": "u", "cor": (opcional)}] — até 3,
                 todos saindo da origem
        somar: True (só com exatamente 2 vetores) também desenha a soma e
               completa o paralelogramo com lados fantasma tracejados
        """
        xmin, xmax = dominio or [-1, 6]
        ymin, ymax = imagem or [-1, 6]
        eixos = Axes(x_range=[xmin, xmax, 1], y_range=[ymin, ymax, 1],
                     x_length=5.6, y_length=5.6,
                     axis_config={"color": APOIO, "stroke_width": 1.5, "font_size": 20,
                                  "tip_width": 0.15, "tip_height": 0.15})
        eixos.move_to(ORIGIN).shift(DOWN * 0.2)
        grupo = VGroup(eixos)

        cores = [DESTAQUE, APOIO, NOTA]
        setas = VGroup()
        for i, v in enumerate(vetores[:3]):
            p = eixos.c2p(v["x"], v["y"])
            cor = v.get("cor", cores[i % len(cores)])
            setas.add(Arrow(eixos.c2p(0, 0), p, color=cor, buff=0,
                            stroke_width=3.5, tip_length=0.2))
            if v.get("rotulo"):
                setas.add(MathTex(v["rotulo"], font_size=26, color=cor).next_to(p, UR, buff=0.1))
        grupo.add(setas)

        fantasma = VGroup()
        if somar and len(vetores) == 2:
            a = eixos.c2p(vetores[0]["x"], vetores[0]["y"])
            b = eixos.c2p(vetores[1]["x"], vetores[1]["y"])
            soma_p = eixos.c2p(vetores[0]["x"] + vetores[1]["x"],
                               vetores[0]["y"] + vetores[1]["y"])
            fantasma.add(DashedLine(a, soma_p, color=GIZ, stroke_width=1.5))
            fantasma.add(DashedLine(b, soma_p, color=GIZ, stroke_width=1.5))
            fantasma.add(Arrow(eixos.c2p(0, 0), soma_p, color=GIZ, buff=0,
                               stroke_width=3.5, tip_length=0.2))
            fantasma.add(MathTex(rotulo_soma, font_size=24, color=GIZ).next_to(soma_p, UR, buff=0.1))
        grupo.add(fantasma)

        self.scene.play(Create(eixos), run_time=1.0)
        gasto = 1.0
        self.scene.play(Create(setas), run_time=1.0)
        gasto += 1.0
        if len(fantasma):
            self.scene.play(Create(fantasma), run_time=1.0)
            gasto += 1.0
        self._pausa(fala, gasto)
        self._fixar_no_canto(grupo, fixar, altura=2.2)

    def mostrar_grade_polar(self, raio_max, pontos=None, passo_raio=None,
                             segmento=False, fixar=False, fala=None):
        """Grade polar — coordenadas polares, radar, ângulo central entre dois
        pontos (lei dos cossenos).

        raio_max: maior raio da grade
        passo_raio: espaçamento entre os círculos concêntricos (padrão raio_max/4)
        pontos: [{"r": 6, "theta": "pi/6", "rotulo": "A"}] — "theta" em radianos,
                expressão SymPy
        segmento: True liga os pontos com um segmento (útil pra mostrar distância)
        """
        passo = passo_raio or max(1, raio_max / 4)
        escala = 2.2 / raio_max
        circulos = VGroup(*[Circle(radius=r * escala, color=APOIO, stroke_width=1)
                            for r in np.arange(passo, raio_max + 1e-6, passo)])
        raios = VGroup(*[Line(ORIGIN, escala * raio_max * np.array([np.cos(a), np.sin(a), 0.0]),
                              color=APOIO, stroke_width=1)
                         for a in np.linspace(0, 2 * np.pi, 8, endpoint=False)])
        grupo = VGroup(circulos, raios)

        marcas = VGroup()
        coords = []
        for p in (pontos or []):
            theta = float(sp.sympify(p["theta"]))
            r = p["r"] * escala
            coord = np.array([r * np.cos(theta), r * np.sin(theta), 0.0])
            coords.append(coord)
            marcas.add(Dot(coord, color=DESTAQUE, radius=0.06))
            if p.get("rotulo"):
                direcao = coord / (np.linalg.norm(coord) or 1)
                marcas.add(Text(p["rotulo"], font_size=22, color=GIZ)
                          .move_to(coord + direcao * 0.3))
        if segmento and len(coords) == 2:
            marcas.add(Line(coords[0], coords[1], color=NOTA, stroke_width=2.5))
        grupo.add(marcas)
        grupo.move_to(ORIGIN).shift(DOWN * 0.2)

        self.scene.play(Create(VGroup(circulos, raios)), run_time=1.1)
        gasto = 1.1
        if len(marcas):
            self.scene.play(FadeIn(marcas), run_time=0.8)
            gasto += 0.8
        self._pausa(fala, gasto)
        self._fixar_no_canto(grupo, fixar, altura=2.2)

    def mostrar_tabela(self, cabecalho, linhas, destacar_coluna=None,
                        fixar=False, fala=None):
        """Tabela de dados — estatística (distribuição de frequência, médias),
        ou qualquer contagem organizada em linhas e colunas.

        cabecalho: ["Faixa", "Frequência", "Ponto médio"]
        linhas: [["[4,6)", "10", "5"], ["[6,8)", "20", "7"]] — cada linha com o
                mesmo número de colunas do cabeçalho
        destacar_coluna: índice 0-based de uma coluna pra destacar em dourado
                         (ex.: a coluna que acabou de ser calculada)
        """
        n_col = len(cabecalho)
        celulas = []
        for j, txt in enumerate(cabecalho):
            cor = DESTAQUE if j == destacar_coluna else APOIO
            celulas.append(Text(txt, font_size=22, color=cor, weight=BOLD))
        for linha in linhas:
            for j, txt in enumerate(linha):
                cor = DESTAQUE if j == destacar_coluna else GIZ
                celulas.append(Text(str(txt), font_size=22, color=cor))

        grade = VGroup(*celulas).arrange_in_grid(rows=len(linhas) + 1, cols=n_col,
                                                  buff=(0.6, 0.35))
        cabecalho_grp = VGroup(*celulas[:n_col])
        linha_cab = Line(cabecalho_grp.get_corner(DL) + LEFT * 0.2 + DOWN * 0.15,
                         cabecalho_grp.get_corner(DR) + RIGHT * 0.2 + DOWN * 0.15,
                         color=APOIO, stroke_width=1.5)
        grupo = VGroup(grade, linha_cab)
        grupo.move_to(ORIGIN).shift(DOWN * 0.2)
        if grupo.width > 10.5:
            grupo.set(width=10.5)

        self.scene.play(FadeIn(cabecalho_grp), Create(linha_cab), run_time=0.8)
        gasto = 0.8
        self.scene.play(FadeIn(VGroup(*celulas[n_col:])), run_time=1.0)
        gasto += 1.0
        self._pausa(fala, gasto)
        self._fixar_no_canto(grupo, fixar, altura=2.6)

    def mostrar_solido_3d(self, tipo, raio=1.5, altura=3.0, corte_altura=None,
                           rotular_raio=None, rotular_altura=None, fala=None):
        """Sólido em perspectiva 3D — cone, cilindro ou esfera — pra geometria
        espacial, troncos, secção transversal paralela à base.

        tipo: "cone" | "cilindro" | "esfera"
        raio, altura: dimensões (altura ignorada em "esfera")
        corte_altura: altura medida A PARTIR DA BASE de uma secção transversal
                      a desenhar (só em "cone"/"cilindro"); pra cone, o raio da
                      secção é calculado por semelhança de triângulos
        rotular_raio, rotular_altura: texto opcional pras dimensões

        Sem `fixar`: a câmera começa plana, inclina só pra este passo e volta a
        plana no final — manter o sólido "grudado" no canto não faz sentido
        depois que a câmera volta à visão de cima usada no resto do vídeo.
        """
        # tudo que já está na tela (linhas escritas, figura fixa, enunciado
        # fixo) mora na MESMA câmera da cena — se não escondermos antes de
        # inclinar, aparece torto durante o trecho 3D. Some e traz de volta.
        presente = VGroup(self.linhas)
        if self.figura_fixa is not None:
            presente.add(self.figura_fixa)
        if self.enunciado_fixo is not None:
            presente.add(self.enunciado_fixo)
        tinha_algo = len(self.linhas) or self.figura_fixa is not None or self.enunciado_fixo is not None
        if tinha_algo:
            self.scene.play(FadeOut(presente), run_time=0.3)

        self.scene.set_camera_orientation(phi=65 * DEGREES, theta=-50 * DEGREES)

        comum = dict(fill_color=APOIO, fill_opacity=0.35, stroke_color=GIZ,
                     stroke_width=0.4, checkerboard_colors=False)
        if tipo == "esfera":
            solido = Sphere(radius=raio, **comum)
        elif tipo == "cilindro":
            solido = Cylinder(radius=raio, height=altura, **comum)
            solido.shift(OUT * altura / 2)  # nasce centrado; base vai pra z=0
        else:
            solido = Cone(base_radius=raio, height=altura, direction=Z_AXIS,
                         show_base=True, **comum)
            solido.shift(OUT * altura)  # nasce com ápice em z=0, base abaixo

        grupo = VGroup(solido)

        secao = None
        if corte_altura is not None and tipo in ("cone", "cilindro"):
            r_secao = raio * (altura - corte_altura) / altura if tipo == "cone" else raio
            secao = Circle(radius=r_secao, color=DESTAQUE, fill_color=DESTAQUE,
                           fill_opacity=0.55, stroke_width=1.5)
            secao.shift(OUT * corte_altura)
            grupo.add(secao)

        marcas = VGroup()
        afastamento = raio + 0.7
        if rotular_altura:
            eixo = DashedLine(RIGHT * afastamento, RIGHT * afastamento + OUT * altura,
                              color=DESTAQUE, stroke_width=2, dash_length=0.12)
            marcas.add(eixo, Text(rotular_altura, font_size=24, color=DESTAQUE, weight=BOLD)
                      .move_to(RIGHT * (afastamento + 0.55) + OUT * altura / 2))
        if rotular_raio:
            base_r = Line(ORIGIN, RIGHT * raio + IN * 0.001, color=DESTAQUE, stroke_width=2)
            marcas.add(base_r, Text(rotular_raio, font_size=24, color=DESTAQUE, weight=BOLD)
                      .move_to(RIGHT * raio / 2 + UP * 0.35))
        grupo.add(marcas)

        self.scene.play(Create(solido), run_time=1.6)
        gasto = 1.6
        if secao:
            self.scene.play(FadeIn(secao), run_time=0.7)
            gasto += 0.7
        if len(marcas):
            self.scene.play(FadeIn(marcas), run_time=0.6)
            gasto += 0.6
        self._pausa(fala, gasto)
        self.scene.play(FadeOut(grupo), run_time=0.6)
        self.scene.set_camera_orientation(phi=0, theta=-90 * DEGREES)
        if tinha_algo:
            self.scene.play(FadeIn(presente), run_time=0.3)

    # ----------------------------------------------------------- animações
    # Templates de animação — cada um é uma máquina de estados curta e linear
    # (2-4 transições), não uma simulação livre. Servem pra ilustrar um
    # PROCESSO (convergência, refinamento, geração) em vez de um estado
    # estático — é o próximo degrau do estilo 3Blue1Brown/MindYourDecisions.

    def anim_pg_infinita(self, primeiro_termo, razao, max_iteracoes=6,
                          fixar=False, fala=None):
        """Soma de uma PG infinita como um retângulo se enchendo fatia a fatia
        — mostra visualmente que a soma converge pra área total, sem nunca
        ultrapassar. Pra PG infinita, fração geratriz, paradoxo de convergência.

        primeiro_termo: fração da largura ocupada na 1ª fatia (0 < a1 < 1)
        razao: razão da PG, 0 < q < 1
        max_iteracoes: nº de fatias a desenhar (a área residual fica cada vez
                       menor; não precisa ir além de uns 6-7 fatias visíveis)
        """
        largura, altura_r = 5.0, 2.8
        retangulo = Rectangle(width=largura, height=altura_r, color=APOIO, stroke_width=2)
        grupo = VGroup(retangulo)

        fatias = VGroup()
        x0 = -largura / 2
        restante = largura
        termo = primeiro_termo * largura
        cores = [DESTAQUE, NOTA]
        for k in range(max_iteracoes):
            w = min(termo, restante)
            if w < 0.02:
                break
            fatia = Rectangle(width=w, height=altura_r, color=cores[k % 2],
                              fill_color=cores[k % 2], fill_opacity=0.55, stroke_width=1)
            fatia.move_to([x0 + w / 2, 0, 0])
            fatias.add(fatia)
            x0 += w
            restante -= w
            termo *= razao
        grupo.add(fatias)
        grupo.move_to(ORIGIN).shift(DOWN * 0.2)

        self.scene.play(Create(retangulo), run_time=0.8)
        gasto = 0.8
        for fatia in fatias:
            self.scene.play(FadeIn(fatia), run_time=0.4)
            gasto += 0.4
        self._pausa(fala, gasto)
        self._fixar_no_canto(grupo, fixar, altura=1.6)

    def anim_riemann(self, expr, dominio, iteracoes=None, fixar=False, fala=None):
        """Retângulos de Riemann se refinando até a área sob a curva — pra
        introduzir área sob o gráfico / ideia de integral (função positiva).

        expr: expressão SymPy de f(x), positiva em todo o domínio
        dominio: [a, b]
        iteracoes: lista crescente do nº de retângulos (padrão [4,8,16,32])
        """
        iteracoes = iteracoes or [4, 8, 16, 32]
        a, b = dominio
        var = sp.Symbol("x")
        fn = sp.lambdify(var, sp.sympify(expr), "numpy")
        ymax = max(1.0, float(np.max(fn(np.linspace(a, b, 60)))) * 1.25)
        eixos = Axes(x_range=[min(0, a) - 0.5, b + 0.5, max(1, (b - a) / 5)],
                    y_range=[0, ymax, ymax / 4], x_length=6.2, y_length=3.4,
                    axis_config={"color": APOIO, "stroke_width": 1.5, "font_size": 20,
                                 "tip_width": 0.15, "tip_height": 0.15})
        eixos.move_to(ORIGIN).shift(DOWN * 0.2)
        curva = eixos.plot(fn, x_range=[a, b], color=GIZ, stroke_width=3)
        grupo = VGroup(eixos, curva)

        def retangulos(n):
            return eixos.get_riemann_rectangles(
                curva, x_range=[a, b], dx=(b - a) / n,
                color=[DESTAQUE, NOTA], fill_opacity=0.65,
                stroke_width=0.5, stroke_color=FUNDO)

        self.scene.play(Create(eixos), Create(curva), run_time=1.2)
        gasto = 1.2
        retangs = retangulos(iteracoes[0])
        self.scene.play(FadeIn(retangs), run_time=0.8)
        gasto += 0.8
        for n in iteracoes[1:]:
            novos = retangulos(n)
            self.scene.play(Transform(retangs, novos), run_time=0.9)
            gasto += 0.9
        grupo.add(retangs)
        self._pausa(fala, gasto)
        self._fixar_no_canto(grupo, fixar, altura=2.2)

    def anim_seno(self, funcao="seno", frequencia=1.0, voltas=1.0,
                  fixar=False, fala=None):
        """Desenrolamento do ciclo trigonométrico até a senoide — a
        correspondência entre uma volta no círculo e um período da onda. Pra
        periodicidade, imagem de função trigonométrica, gráfico de sen(kx).

        funcao: "seno" | "cosseno"
        frequencia: multiplica o ângulo (mostra compressão de período — sen(kx))
        voltas: quantas voltas completas do ciclo animar
        """
        R = 1.1
        valor = np.sin if funcao == "seno" else np.cos
        centro = LEFT * 3.3

        ciclo = Circle(radius=R, color=APOIO, stroke_width=1.5).move_to(centro)
        eixo_onda = Axes(x_range=[0, voltas * TAU, PI / 2], y_range=[-1.3, 1.3, 1],
                         x_length=5.3, y_length=2.3,
                         axis_config={"color": APOIO, "stroke_width": 1.5, "font_size": 16,
                                      "tip_width": 0.12, "tip_height": 0.12})
        eixo_onda.move_to(RIGHT * 1.6)
        grupo = VGroup(ciclo, eixo_onda)

        t = ValueTracker(0.0)
        ponto = always_redraw(lambda: Dot(
            centro + R * np.array([np.cos(t.get_value()), np.sin(t.get_value()), 0.0]),
            color=DESTAQUE, radius=0.06))
        raio_linha = always_redraw(lambda: Line(centro, ponto.get_center(),
                                                 color=APOIO, stroke_width=1.5))
        projecao = always_redraw(lambda: DashedLine(
            ponto.get_center(),
            eixo_onda.c2p(t.get_value(), valor(t.get_value() * frequencia)),
            color=NOTA, stroke_width=1.2))
        onda = always_redraw(lambda: eixo_onda.plot(
            lambda x: valor(x * frequencia), x_range=[0, max(0.001, t.get_value())],
            color=DESTAQUE, stroke_width=3))
        ponto_onda = always_redraw(lambda: Dot(
            eixo_onda.c2p(t.get_value(), valor(t.get_value() * frequencia)),
            color=DESTAQUE, radius=0.06))

        self.scene.play(Create(ciclo), Create(eixo_onda), run_time=1.0)
        self.scene.add(ponto, raio_linha, projecao, onda, ponto_onda)
        tempo_varredura = max(2.0, 1.8 * voltas)
        self.scene.play(t.animate.set_value(voltas * TAU), run_time=tempo_varredura,
                        rate_func=linear)
        gasto = 1.0 + tempo_varredura

        grupo.add(ponto, raio_linha, projecao, onda, ponto_onda)
        self._pausa(fala, gasto)
        self._fixar_no_canto(grupo, fixar, altura=2.2)

    def anim_discriminante(self, coeficientes, k_inicial, k_final, k_critico=None,
                            dominio=None, imagem=None, fixar=False, fala=None):
        """Parábola deslizando conforme um parâmetro k muda, com o discriminante
        lido ao lado em tempo real — pra condição de tangência, nº de raízes
        reais, sinal do trinômio do 2º grau.

        coeficientes: [a, b, c] como strings SymPy podendo depender de k,
                      ex. ["1", "-4", "k"]
        k_inicial, k_final: percurso do parâmetro que a animação varre
        k_critico: valor de k pra pausar e destacar no meio do caminho
                   (ex. onde Δ=0) — opcional
        dominio, imagem: [xmin,xmax]/[ymin,ymax] dos eixos (padrão -5..5)
        """
        xmin, xmax = dominio or [-5, 5]
        ymin, ymax = imagem or [-5, 5]
        eixos = Axes(x_range=[xmin, xmax, 1], y_range=[ymin, ymax, 1],
                     x_length=6.0, y_length=3.6,
                     axis_config={"color": APOIO, "stroke_width": 1.5, "font_size": 18,
                                  "tip_width": 0.15, "tip_height": 0.15})
        eixos.move_to(ORIGIN).shift(LEFT * 0.8 + DOWN * 0.2)
        grupo = VGroup(eixos)

        var_x, var_k = sp.symbols("x k")
        a_e, b_e, c_e = [sp.sympify(c) for c in coeficientes]

        def coefs(kval):
            return (float(a_e.subs(var_k, kval)), float(b_e.subs(var_k, kval)),
                    float(c_e.subs(var_k, kval)))

        kt = ValueTracker(k_inicial)
        curva = always_redraw(lambda: eixos.plot(
            lambda x, ab=coefs(kt.get_value()): ab[0] * x**2 + ab[1] * x + ab[2],
            x_range=[xmin, xmax], color=DESTAQUE, stroke_width=3))
        rotulo = always_redraw(lambda: Text(
            f"Δ = {(lambda a, b, c: b*b - 4*a*c)(*coefs(kt.get_value())):.1f}",
            font_size=24, color=GIZ).to_corner(UR, buff=0.5))

        self.scene.play(Create(eixos), run_time=1.0)
        self.scene.add(curva, rotulo)
        gasto = 1.0
        tempo = max(2.5, abs(k_final - k_inicial) * 0.8)
        if k_critico is not None:
            self.scene.play(kt.animate.set_value(k_critico), run_time=tempo / 2, rate_func=linear)
            self.scene.wait(0.5)
            self.scene.play(kt.animate.set_value(k_final), run_time=tempo / 2, rate_func=linear)
            gasto += tempo + 0.5
        else:
            self.scene.play(kt.animate.set_value(k_final), run_time=tempo, rate_func=linear)
            gasto += tempo

        grupo.add(curva, rotulo)
        self._pausa(fala, gasto)
        self._fixar_no_canto(grupo, fixar, altura=2.2)

    def anim_peneira(self, numero_maximo, primos_a_filtrar=None, fixar=False, fala=None):
        """Peneira de Eratóstenes — números primos sobrevivendo numa grade, o
        resto apagado em ondas por múltiplo. Pra números primos, MMC/MDC,
        teoria dos números. Recomendado `numero_maximo` até uns 30-40 pra
        continuar legível.

        numero_maximo: até que número mostrar
        primos_a_filtrar: sequência de primos a aplicar (padrão: todos os
                          primos ≤ raiz de numero_maximo)
        """
        if primos_a_filtrar is None:
            primos_a_filtrar = [p for p in range(2, int(numero_maximo ** 0.5) + 1)
                                if all(p % d for d in range(2, p))]

        cols = min(10, numero_maximo)
        celulas = {}
        grade = VGroup()
        for num in range(1, numero_maximo + 1):
            txt = Text(str(num), font_size=20, color=GIZ)
            celulas[num] = txt
            grade.add(txt)
        grade.arrange_in_grid(rows=(numero_maximo + cols - 1) // cols, cols=cols, buff=0.35)
        grade.move_to(ORIGIN).shift(DOWN * 0.2)
        if grade.width > 10.5:
            grade.set(width=10.5)

        self.scene.play(FadeIn(grade), run_time=1.0)
        gasto = 1.0
        vivos = set(range(2, numero_maximo + 1))
        for p in primos_a_filtrar:
            if p not in vivos:
                continue
            celulas[p].set_color(DESTAQUE)
            self.scene.play(Circumscribe(celulas[p], color=DESTAQUE), run_time=0.5)
            gasto += 0.5
            mortos = [m for m in range(p * p, numero_maximo + 1, p) if m in vivos and m != p]
            if mortos:
                self.scene.play(*[FadeOut(celulas[m], scale=0.5) for m in mortos], run_time=0.6)
                gasto += 0.6
                for m in mortos:
                    vivos.discard(m)
        for num in vivos:
            celulas[num].set_color(DESTAQUE)
        if vivos:
            self.scene.play(*[Indicate(celulas[n], color=DESTAQUE) for n in sorted(vivos)], run_time=0.8)
            gasto += 0.8

        self._pausa(fala, gasto)
        self._fixar_no_canto(grade, fixar, altura=2.4)

    def anim_corrida(self, expr1, expr2, dominio, rotulo1="f(x)", rotulo2="g(x)",
                      fixar=False, fala=None):
        """Duas curvas "correndo" lado a lado até o ponto de cruzamento — pra
        comparar crescimento (ex. exponencial ultrapassando linear/polinomial,
        juros compostos vs. simples).

        expr1, expr2: expressões SymPy de f(x) e g(x)
        dominio: [xmin, xmax] — precisa cobrir o cruzamento pra ele aparecer
        rotulo1, rotulo2: rótulos (LaTeX) de cada curva
        """
        xmin, xmax = dominio
        var = sp.Symbol("x")
        f1 = sp.lambdify(var, sp.sympify(expr1), "numpy")
        f2 = sp.lambdify(var, sp.sympify(expr2), "numpy")
        xs = np.linspace(xmin, xmax, 200)
        ymax = max(1.0, float(np.max(np.abs(f1(xs)))), float(np.max(np.abs(f2(xs))))) * 1.15

        eixos = Axes(x_range=[xmin, xmax, max(1, (xmax - xmin) / 6)],
                     y_range=[0, ymax, ymax / 4], x_length=6.4, y_length=3.6,
                     axis_config={"color": APOIO, "stroke_width": 1.5, "font_size": 18,
                                  "tip_width": 0.15, "tip_height": 0.15})
        eixos.move_to(ORIGIN).shift(DOWN * 0.2)
        c1 = eixos.plot(f1, x_range=[xmin, xmax], color=GIZ, stroke_width=3)
        c2 = eixos.plot(f2, x_range=[xmin, xmax], color=DESTAQUE, stroke_width=3)
        r1 = MathTex(rotulo1, font_size=24, color=GIZ).next_to(c1.get_end(), UR, buff=0.1)
        r2 = MathTex(rotulo2, font_size=24, color=DESTAQUE).next_to(c2.get_end(), UR, buff=0.1)
        grupo = VGroup(eixos, c1, c2, r1, r2)

        diffs = f1(xs) - f2(xs)
        cruz = None
        for i in range(1, len(xs)):
            if diffs[i - 1] * diffs[i] < 0:
                cruz = xs[i]
                break

        self.scene.play(Create(eixos), run_time=1.0)
        gasto = 1.0
        self.scene.play(Create(c1), Create(c2), run_time=1.5)
        gasto += 1.5
        self.scene.play(FadeIn(r1), FadeIn(r2), run_time=0.5)
        gasto += 0.5
        if cruz is not None:
            ponto = Dot(eixos.c2p(cruz, f1(cruz)), color=NOTA, radius=0.08)
            grupo.add(ponto)
            self.scene.play(FadeIn(ponto, scale=1.5), Flash(ponto, color=NOTA), run_time=0.6)
            gasto += 0.6

        self._pausa(fala, gasto)
        self._fixar_no_canto(grupo, fixar, altura=2.2)

    def anim_fibonacci(self, n_quadrados=7, fixar=False, fala=None):
        """Espiral de quadrados de Fibonacci — cada quadrado aparece em
        sequência, lado igual ao termo da sequência (1,1,2,3,5,8,13,...),
        formando o retângulo áureo. Pra recorrência, razão áurea, Fibonacci.

        n_quadrados: quantos termos mostrar (padrão 7 — mais que isso o
                     primeiro quadrado fica minúsculo demais pra ler)
        """
        fib = [1, 1]
        while len(fib) < n_quadrados:
            fib.append(fib[-1] + fib[-2])

        caixa = [0.0, 0.0, float(fib[0]), float(fib[0])]
        posicoes = [(0.0, 0.0, float(fib[0]))]
        direcoes = ["direita", "cima", "esquerda", "baixo"]
        for i in range(1, n_quadrados):
            lado = float(fib[i])
            d = direcoes[(i - 1) % 4]
            x0, y0, x1, y1 = caixa
            if d == "direita":
                novo = (x1, y0, lado)
                caixa = [x0, y0, x1 + lado, y1]
            elif d == "cima":
                novo = (x0, y1, lado)
                caixa = [x0, y0, x1, y1 + lado]
            elif d == "esquerda":
                novo = (x0 - lado, y1 - lado, lado)
                caixa = [x0 - lado, y0, x1, y1]
            else:
                novo = (x1 - lado, y0 - lado, lado)
                caixa = [x0, y0 - lado, x1, y1]
            posicoes.append(novo)

        cores = [DESTAQUE, APOIO, NOTA, GIZ]
        # calcula escala E o centro final ANTES de animar — cada quadrado já
        # nasce na posição centralizada certa, em vez de todos aparecerem fora
        # do centro e só recentralizar (sem animação) no final
        escala = 5.4 / max(caixa[2] - caixa[0], caixa[3] - caixa[1])
        cx = (caixa[0] + caixa[2]) / 2 * escala
        cy = (caixa[1] + caixa[3]) / 2 * escala + 0.2

        grupo = VGroup()
        gasto = 0.0
        for i, (x0, y0, lado) in enumerate(posicoes):
            quad = Square(side_length=lado * escala, color=cores[i % len(cores)], stroke_width=2.5)
            quad.move_to([(x0 + lado / 2) * escala - cx, (y0 + lado / 2) * escala - cy, 0.0])
            rotulo = Text(str(fib[i]), font_size=min(28, 13 + lado * 1.8), color=GIZ)
            rotulo.move_to(quad.get_center())
            grupo.add(quad, rotulo)
            self.scene.play(Create(quad), FadeIn(rotulo), run_time=0.5)
            gasto += 0.5

        # segura um instante no espiral completo antes de sumir — sem isso o
        # corte vem logo depois do último quadrado, parece abrupto
        self.scene.wait(0.7)
        gasto += 0.7
        self._pausa(fala, gasto)
        self._fixar_no_canto(grupo, fixar, altura=2.6)

    def anim_hanoi(self, n_discos=4, fixar=False, fala=None):
        """Torre de Hanói resolvida visualmente com o número mínimo de
        movimentos — pra motivar a recorrência T(n) = 2·T(n-1) + 1.

        n_discos: quantidade de discos (padrão 4 — o total de movimentos é
                  2^n - 1; acima de 5-6 discos a animação fica arrastada)
        """
        xs = {"A": -3.6, "B": 0.0, "C": 3.6}
        base_y = -1.6
        alt = 0.32

        pinos = VGroup(*[Line([x, base_y, 0], [x, base_y + 3.2, 0], color=APOIO, stroke_width=3)
                        for x in xs.values()])
        bases = VGroup(*[Line([x - 1.3, base_y, 0], [x + 1.3, base_y, 0], color=APOIO, stroke_width=3)
                        for x in xs.values()])
        rotulos = VGroup(*[Text(nome, font_size=22, color=APOIO).next_to(np.array([x, base_y, 0]), DOWN, buff=0.2)
                           for nome, x in xs.items()])
        grupo = VGroup(pinos, bases, rotulos)

        cores = [DESTAQUE, APOIO, NOTA, GIZ, DESTAQUE, APOIO]
        discos = {}
        pilhas = {"A": [], "B": [], "C": []}
        for tam in range(n_discos, 0, -1):
            largura = 0.5 + tam * 0.35
            cor = cores[(tam - 1) % len(cores)]
            d = RoundedRectangle(width=largura, height=alt * 0.85, corner_radius=0.05,
                                 color=cor, fill_color=cor, fill_opacity=0.85, stroke_width=1)
            nivel = len(pilhas["A"])
            d.move_to([xs["A"], base_y + alt * (nivel + 0.6), 0])
            discos[tam] = d
            pilhas["A"].append(tam)
            grupo.add(d)

        self.scene.play(Create(pinos), Create(bases), FadeIn(rotulos), run_time=0.8)
        self.scene.play(FadeIn(VGroup(*discos.values())), run_time=0.6)
        gasto = 1.4

        def movimentos(n, o, d, a):
            if n == 0:
                return []
            return movimentos(n - 1, o, a, d) + [(n, o, d)] + movimentos(n - 1, a, d, o)

        total_mov = 2 ** n_discos - 1
        tempo_mov = max(0.1, min(0.35, 5.0 / total_mov))
        topo_y = base_y + alt * (n_discos + 1.8)
        for tam, origem, destino in movimentos(n_discos, "A", "C", "B"):
            pilhas[origem].remove(tam)
            disco = discos[tam]
            # o disco MAIOR só se move UMA vez em toda a sequência — é
            # exatamente o "+1" da recorrência T(n) = 2·T(n-1) + 1 (antes dele,
            # os n-1 discos menores resolveram um T(n-1); depois, resolvem
            # outro). Pausa e destaca esse instante, em vez de deixar corrido.
            eh_o_maior = tam == n_discos
            if eh_o_maior:
                rotulo_rec = MathTex("T(n) = 2\\cdot T(n-1) + 1", font_size=30, color=DESTAQUE)
                rotulo_rec.to_edge(UP, buff=0.5)
                self.scene.play(Circumscribe(disco, color=DESTAQUE), run_time=0.6)
                self.scene.play(FadeIn(rotulo_rec, shift=DOWN * 0.15), run_time=0.5)
                self.scene.wait(0.7)
                gasto += 0.6 + 0.5 + 0.7
            x_atual = disco.get_center()[0]
            x_destino = xs[destino]
            y_destino = base_y + alt * (len(pilhas[destino]) + 0.6)
            self.scene.play(disco.animate.move_to([x_atual, topo_y, 0]), run_time=tempo_mov)
            self.scene.play(disco.animate.move_to([x_destino, topo_y, 0]), run_time=tempo_mov)
            self.scene.play(disco.animate.move_to([x_destino, y_destino, 0]), run_time=tempo_mov)
            pilhas[destino].append(tam)
            gasto += tempo_mov * 3
            if eh_o_maior:
                self.scene.wait(0.4)
                self.scene.play(FadeOut(rotulo_rec), run_time=0.4)
                gasto += 0.4 + 0.4

        self._pausa(fala, gasto)
        self._fixar_no_canto(grupo, fixar, altura=2.4)

    def mostrar_regioes_circulo(self, sequencia, fixar=False, fala=None):
        """Sequência de círculos com n pontos e todas as cordas entre eles —
        o problema de Moser. Mostra a hipótese de indução se formando
        (1, 2, 4, 8, 16 regiões, dobrando a cada ponto) e QUEBRANDO em n=6
        (31, não 32) — cada passo some antes do próximo aparecer, pra nunca
        acumular bagunça visual mesmo em n=5/6.

        sequencia: [{"n": 2, "regioes": "2"}, {"n": 3, "regioes": "4"}, ...,
                    {"n": 6, "regioes": "31 (não 32!)"}] — um item por passo
        """
        gasto = 0.0
        cena_final = VGroup()
        for idx, item in enumerate(sequencia):
            n = item["n"]
            R = 2.0
            pontos = [R * np.array([np.cos(2 * np.pi * k / n - np.pi / 2),
                                    np.sin(2 * np.pi * k / n - np.pi / 2), 0.0])
                      for k in range(n)]
            circulo = Circle(radius=R, color=APOIO, stroke_width=2)
            # buff maior que o offset do número do ponto (R + 0.32, ver abaixo):
            # pra n par sempre existe um ponto exatamente no topo do círculo,
            # e com buff=0.3 o rótulo colidia direto com o número desse ponto
            rotulo_n = Text(f"n = {n}", font_size=24, color=APOIO).next_to(circulo, UP, buff=0.55)

            # cada ponto ganha um número (1,2,3...) — ajuda a acompanhar a
            # contagem, principalmente em n=5/6 onde fica mais cordas
            pontos_mob = []
            for k, p in enumerate(pontos):
                direcao = p / (np.linalg.norm(p) or 1)
                numero = Text(str(k + 1), font_size=18, color=GIZ).move_to(p + direcao * 0.32)
                dot = Dot(p, color=DESTAQUE, radius=0.07)
                pontos_mob.append(VGroup(dot, numero))

            # cordas em grupos por ponto de origem (1→todos, depois 2→resto,
            # ...) — revela mais devagar E na mesma ordem que se contaria à
            # mão, em vez de um Create() só com tudo de uma vez
            grupos_cordas = []
            for i in range(n):
                novas = VGroup(*[Line(pontos[i], pontos[j], color=GIZ, stroke_width=1.5)
                                for j in range(i + 1, n)])
                if len(novas):
                    grupos_cordas.append(novas)

            texto_reg = str(item.get("regioes", "")).strip()
            rotulo_reg = None
            if texto_reg:
                # último item da sequência é o "furo" na hipótese — destaca
                cor_reg = DESTAQUE if idx < len(sequencia) - 1 else NOTA
                rotulo_reg = Text(texto_reg, font_size=26, color=cor_reg).next_to(circulo, DOWN, buff=0.35)

            cena = VGroup(circulo, rotulo_n, *pontos_mob, *grupos_cordas)
            if rotulo_reg:
                cena.add(rotulo_reg)
            cena.move_to(ORIGIN).shift(DOWN * 0.1)

            self.scene.play(Create(circulo), FadeIn(rotulo_n), run_time=0.5)
            gasto += 0.5
            for par in pontos_mob:
                self.scene.play(FadeIn(par, scale=1.3), run_time=0.22)
                gasto += 0.22
            for novas in grupos_cordas:
                tempo = max(0.35, 0.22 * len(novas))
                self.scene.play(Create(novas), run_time=tempo)
                gasto += tempo
            if rotulo_reg:
                self.scene.play(FadeIn(rotulo_reg, scale=1.15), run_time=0.4)
                gasto += 0.4

            ultimo = idx == len(sequencia) - 1
            self.scene.wait(0.9 if ultimo else 0.4)
            gasto += 0.9 if ultimo else 0.4
            if not ultimo:
                self.scene.play(FadeOut(cena), run_time=0.3)
                gasto += 0.3
            else:
                cena_final = cena

        self._pausa(fala, gasto)
        self._fixar_no_canto(cena_final, fixar, altura=2.4)

    # ----------------------------------------------------------- cabeçalho fixo
    def fixar_enunciado(self, latex, fala=None):
        eq = MathTex(latex, font_size=34, color=GIZ).to_edge(UP, buff=0.45)
        regua = Line(LEFT * 6.5, RIGHT * 6.5, color=APOIO, stroke_width=1.5)
        regua.next_to(eq, DOWN, buff=0.2)
        self.enunciado_fixo = VGroup(eq, regua)
        self.scene.play(Write(eq), run_time=1.3)
        self.scene.play(Create(regua), run_time=0.5)
        self._pausa(fala, 1.8)

    # ----------------------------------------------------------- linhas + rolagem
    def _posicao_proxima(self, altura):
        # figura ancorada no canto ocupa o topo à direita: desce a 1ª linha
        topo = TOPO_TRABALHO - 1.4 if self.figura_fixa is not None else TOPO_TRABALHO
        if not self.linhas:
            return topo
        base = self.linhas[-1].get_bottom()[1]
        return base - 0.4 - altura / 2

    def _rolar_se_preciso(self, altura_nova):
        y = self._posicao_proxima(altura_nova)
        if y - altura_nova / 2 >= BASE_TRABALHO:
            return
        desloc = BASE_TRABALHO - (y - altura_nova / 2) + 0.15
        self.scene.play(self.linhas.animate.shift(UP * desloc), run_time=0.7)
        for ln in list(self.linhas):
            if ln.get_bottom()[1] > TOPO_TRABALHO + 0.3:
                self.scene.play(FadeOut(ln), run_time=0.3)
                self.linhas.remove(ln)

    def escrever(self, latex, cor=GIZ, destaque=False, nota=None, fala=None,
                 run_time=1.6):
        eq = MathTex(latex, font_size=44, color=(DESTAQUE if destaque else cor))
        self._rolar_se_preciso(eq.height)
        y = self._posicao_proxima(eq.height)
        eq.move_to([ESQUERDA + eq.width / 2, y, 0])
        self.scene.play(Write(eq), run_time=run_time)
        self.linhas.add(eq)
        gasto = run_time
        if destaque:
            cx = SurroundingRectangle(eq, color=DESTAQUE, buff=0.12, stroke_width=2)
            self.scene.play(Create(cx), run_time=0.5)
            gasto += 0.5
        if nota:
            n = Text(nota, font_size=22, color=NOTA).next_to(eq, RIGHT, buff=0.5)
            # se a nota lateral vazaria da tela, coloca abaixo da linha
            if n.get_right()[0] > 6.6:
                n.next_to(eq, DOWN, buff=0.2).align_to(eq, LEFT).shift(RIGHT * 0.3)
            self.scene.play(FadeIn(n, shift=LEFT * 0.15), run_time=0.5)
            gasto += 0.5
            self._pausa(fala, gasto)
            self.scene.play(FadeOut(n), *( [FadeOut(cx)] if destaque else [] ),
                            run_time=0.4)
        else:
            self._pausa(fala, gasto)
            if destaque:
                self.scene.play(FadeOut(cx), run_time=0.4)
        return eq

    def transformar(self, latex, operacao=None, fala=None, run_time=1.5):
        ref = self.linhas[-1]
        op = None
        if operacao:
            op = Text(operacao, font_size=24, color=APOIO).next_to(ref, RIGHT, buff=0.5)
            self.scene.play(FadeIn(op, shift=LEFT * 0.15), run_time=0.5)
        eq = self.escrever(latex, fala=fala, run_time=run_time)
        if op:
            self.scene.play(FadeOut(op), run_time=0.3)
        return eq

    def resposta(self, latex, alternativa, fala=None, run_time=1.7):
        eq = self.escrever(latex, fala=max(2.0, (fala or 0) * 0.4), run_time=run_time)
        rot = Text(f"Alternativa  [{alternativa}]", font_size=38, color=DESTAQUE)
        # sempre ABAIXO da equação, alinhada à esquerda. A versão anterior jogava a
        # caixa para a direita quando não cabia embaixo — e aí ela vazava da tela.
        rot.next_to(eq, DOWN, buff=0.5).align_to(eq, LEFT)
        # se não couber embaixo, sobe o conteúdo já escrito para abrir espaço
        falta = BASE_TRABALHO + 0.25 - (rot.get_bottom()[1] - 0.3)
        if falta > 0:
            self.scene.play(self.linhas.animate.shift(UP * falta), run_time=0.6)
            rot.shift(UP * falta)
        # trava nas bordas laterais: nunca sai da tela
        if rot.get_right()[0] > 6.4:
            rot.shift(LEFT * (rot.get_right()[0] - 6.4))
        if rot.get_left()[0] < -6.4:
            rot.shift(RIGHT * (-6.4 - rot.get_left()[0]))
        caixa = SurroundingRectangle(rot, color=DESTAQUE, buff=0.3, stroke_width=2.5)
        self.scene.play(Write(rot), run_time=1.1)
        self.scene.play(Create(caixa), run_time=0.7)
        self._pausa(max(fala or 0, 2.5), 1.8)
