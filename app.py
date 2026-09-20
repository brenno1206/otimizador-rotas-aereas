"""
Aplicativo Tkinter para consultar a malha aérea (grafo direcionado).

Abas:
    - Rotas: menor custo (km) e menos conexões entre duas cidades, lado a lado.
    - Árvore geradora mínima: conjunto de rotas de menor distância total que liga todos os aeroportos.

Dependências: pandas, openpyxl, networkx, matplotlib
Uso: python app.py [caminho_do_excel] ou python app.py (usa aeroportos_brasil.xlsx como default)
"""
import sys
import tkinter as tk
from functools import partial
from tkinter import filedialog, messagebox, ttk

import networkx as nx
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from grafos import Grafo

COR_CUSTO = "#1f77b4"
COR_CONEXOES = "#d62728"
COR_ARVORE = "#2ca02c"


def formatar_km(valor):
    """Formata a distância no padrão brasileiro: 1234.5 -> '1.235 km'."""
    return f"{valor:,.0f} km".replace(",", ".")


def formatar_trechos(quantidade):
    return f"{quantidade} trecho" + ("" if quantidade == 1 else "s")


def construir_digrafo(grafo):
    """Converte a classe Grafo em um DiGraph do networkx (usado só para desenhar)."""
    G = nx.DiGraph()
    G.add_nodes_from(grafo.vertices)
    for origem, vizinhos in grafo.adjacencias.items():
        for destino, peso in vizinhos:
            G.add_edge(origem, destino, peso=float(peso))
    return G


def distancia_do_caminho(G, caminho):
    return sum(G[u][v]["peso"] for u, v in zip(caminho, caminho[1:]))


def desenhar_grafo(ax, G, pos, arestas, rotulos, titulo, cor, tamanho=500):
    """
    Desenha o grafo inteiro em cinza ao fundo e destaca `arestas` (lista de (origem, destino)) com setas.
    Só os vértices que participam das arestas destacadas recebem rótulo.
    """
    destacados = {no for aresta in arestas for no in aresta}

    ax.set_axis_off()
    ax.set_title(titulo, fontsize=11)

    # fundo: malha completa, discreta
    nx.draw_networkx_edges(G, pos, ax=ax, arrows=False, edge_color="#dddddd", width=0.4)
    nx.draw_networkx_nodes(G, pos, ax=ax, node_size=15, node_color="#bbbbbb")

    # destaque: vértices e arestas direcionadas
    nx.draw_networkx_nodes(G, pos, nodelist=list(destacados), ax=ax, node_size=tamanho, node_color=cor)
    nx.draw_networkx_edges(
        G, pos, edgelist=arestas, ax=ax, edge_color=cor, width=2,
        arrows=True, arrowstyle="-|>", arrowsize=16, node_size=tamanho,
    )

    # rótulos levemente acima dos vértices, para não cobrir a cor
    pos_rotulos = {no: (x, y + 0.09) for no, (x, y) in pos.items()}
    nx.draw_networkx_labels(
        G, pos_rotulos, labels={no: rotulos[no] for no in destacados}, ax=ax, font_size=7,
        bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.8),
    )

    # distância sobre cada aresta, apenas quando são poucas
    if len(arestas) <= 15:
        nx.draw_networkx_edge_labels(
            G, pos, ax=ax, font_size=7, rotate=False,
            edge_labels={(u, v): formatar_km(G[u][v]["peso"]) for u, v in arestas},
        )


class PainelGrafico(ttk.Frame):
    """Frame com uma figura matplotlib (e barra de zoom/pan) que pode ter vários quadros lado a lado."""

    def __init__(self, mestre):
        super().__init__(mestre)
        self.figura = Figure(figsize=(10, 6), layout="tight")
        self.canvas = FigureCanvasTkAgg(self.figura, master=self)
        NavigationToolbar2Tk(self.canvas, self).update()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def desenhar(self, *quadros):
        """Cada quadro é um callable que recebe um `ax` e desenha nele."""
        self.limpar()
        for i, quadro in enumerate(quadros, start=1):
            quadro(self.figura.add_subplot(1, len(quadros), i))
        self.canvas.draw_idle()

    def limpar(self):
        self.figura.clear()
        self.canvas.draw_idle()


class App(tk.Tk):
    def __init__(self, caminho=None):
        super().__init__()
        self.title("Malha aérea")
        self.geometry("1150x740")

        self.grafo = None
        self.G = None
        self.pos = {}
        self.codigos = {}    # "Cidade/UF (IATA)" -> IATA
        self.cidades = {}    # IATA -> "Cidade (IATA)"

        self._montar_interface()
        self.after(100, lambda: self.carregar(caminho) if caminho else self.abrir_arquivo())

    # ---------- interface ----------
    def _montar_interface(self):
        topo = ttk.Frame(self, padding=8)
        topo.pack(fill="x")

        ttk.Button(topo, text="Abrir Excel...", command=self.abrir_arquivo).pack(side="left")

        ttk.Label(topo, text="Origem:").pack(side="left", padx=(16, 4))
        self.cb_origem = ttk.Combobox(topo, state="readonly", width=34)
        self.cb_origem.pack(side="left")

        ttk.Label(topo, text="Destino:").pack(side="left", padx=(16, 4))
        self.cb_destino = ttk.Combobox(topo, state="readonly", width=34)
        self.cb_destino.pack(side="left")

        ttk.Button(topo, text="Buscar rotas", command=self.buscar_rotas).pack(side="left", padx=16)

        self.resultado = tk.StringVar(value="Abra o arquivo Excel com as rotas.")
        ttk.Label(self, textvariable=self.resultado, justify="left", padding=(8, 0)).pack(fill="x")

        abas = ttk.Notebook(self)
        abas.pack(fill="both", expand=True, padx=8, pady=8)
        self.painel_rotas = PainelGrafico(abas)
        self.painel_arvore = PainelGrafico(abas)
        abas.add(self.painel_rotas, text="Rotas")
        abas.add(self.painel_arvore, text="Árvore geradora mínima")

    # ---------- carregamento ----------
    def abrir_arquivo(self):
        caminho = filedialog.askopenfilename(
            parent=self, title="Selecione o Excel de rotas",
            filetypes=[("Excel", "*.xlsx *.xls"), ("Todos os arquivos", "*.*")],
        )
        if caminho:
            self.carregar(caminho)

    def carregar(self, caminho):
        try:
            grafo = Grafo(caminho)
        except Exception as erro:  # fronteira da interface: qualquer falha vira mensagem ao usuário
            messagebox.showerror("Erro ao carregar", str(erro), parent=self)
            return

        self.grafo = grafo
        self.G = construir_digrafo(grafo)
        self.pos = nx.spring_layout(self.G, seed=42)  # layout fixo: os desenhos ficam comparáveis
        self.cidades = {iata: f"{cidade} ({iata})" for iata, (_, cidade, _) in grafo.vertices.items()}
        self.codigos = {
            f"{cidade}/{uf} ({iata})": iata for iata, (_, cidade, uf) in grafo.vertices.items()
        }

        nomes = sorted(self.codigos)
        for combo in (self.cb_origem, self.cb_destino):
            combo.config(values=nomes)
            combo.set("")

        self.resultado.set(f"{len(grafo.vertices)} aeroportos carregados. Escolha origem e destino.")
        self.painel_rotas.limpar()
        self._desenhar_arvore()

    # ---------- ações ----------
    def buscar_rotas(self):
        if self.grafo is None:
            return

        origem = self.codigos.get(self.cb_origem.get())
        destino = self.codigos.get(self.cb_destino.get())
        if origem is None or destino is None:
            messagebox.showwarning("Rotas", "Selecione a origem e o destino.", parent=self)
            return
        if origem == destino:
            messagebox.showwarning("Rotas", "Origem e destino devem ser diferentes.", parent=self)
            return

        custo = self.grafo.caminho_menor_custo(origem, destino)
        if custo is None:  # se não há caminho por km, também não há por conexões
            self.painel_rotas.limpar()
            self.resultado.set(
                f"Não há rota de {self.cidades[origem]} para {self.cidades[destino]} "
                "(o grafo é direcionado: o sentido importa)."
            )
            return
        conexoes = self.grafo.caminho_menos_conexoes(origem, destino)

        caminho_km, km = custo
        caminho_con, trechos = conexoes
        km_con = distancia_do_caminho(self.G, caminho_con)

        seta = " → ".join
        self.resultado.set(
            f"Menor custo: {seta(self.cidades[i] for i in caminho_km)}  "
            f"[{formatar_km(km)}, {formatar_trechos(len(caminho_km) - 1)}]\n"
            f"Menos conexões: {seta(self.cidades[i] for i in caminho_con)}  "
            f"[{formatar_trechos(trechos)}, {formatar_km(km_con)}]"
        )

        rotulos = {iata: f"{cidade}\n({iata})" for iata, (_, cidade, _) in self.grafo.vertices.items()}
        quadro = partial(desenhar_grafo, G=self.G, pos=self.pos, rotulos=rotulos)
        self.painel_rotas.desenhar(
            partial(quadro, arestas=list(zip(caminho_km, caminho_km[1:])),
                    titulo=f"Menor custo: {formatar_km(km)}", cor=COR_CUSTO),
            partial(quadro, arestas=list(zip(caminho_con, caminho_con[1:])),
                    titulo=f"Menos conexões: {formatar_trechos(trechos)}", cor=COR_CONEXOES),
        )

    def _desenhar_arvore(self):
        vertices, arestas = self.grafo.obter_arv_minima()
        total = sum(peso for _, _, peso in arestas)
        componentes = len(vertices) - len(arestas)

        titulo = f"Árvore geradora mínima: {len(arestas)} rotas, {formatar_km(total)} no total"
        if componentes > 1:
            titulo += f" ({componentes} grupos de aeroportos desconectados entre si)"

        self.painel_arvore.desenhar(
            partial(
                desenhar_grafo, G=self.G, pos=self.pos,
                arestas=[(origem, destino) for origem, destino, _ in arestas],
                rotulos={v: v for v in vertices}, titulo=titulo, cor=COR_ARVORE, tamanho=140,
            )
        )


def main():
    caminho = sys.argv[1] if len(sys.argv) > 1 else "aeroportos_brasil.xlsx"
    App(caminho).mainloop()


if __name__ == "__main__":
    main()
