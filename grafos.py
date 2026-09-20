from builtins import sorted
import os
import pandas as pd
import heapq

class Grafo:
    """
    Representa um grafo nao firecionado de rotas aereas.

    Os vertices sao aeroportos identificados pelo codigo IATA, e as arestas
    representam as conexoes entre eles, tendo a distancia em km como peso.
    """
    def __init__(self, path):
        """
        Inicializa o grafo de aeroportos e carrega os dados do arquivo Excel
        Args:
            path (str):  Caminho para arquivo Excel contendo as rotas
        """
        self.vertices = {}
        """
        dict: mapeia o codigo IATA (str) para uma tupla contendo:
        (nome do aeroporto, nome da cidade, uf)
        """

        self.adjacencias = {}
        """
        dict: mapeia a origem (IATA) para uma lista de tuplas de adjacencia:
        [(destino, peso), ...]
        """
        self._carregar_dados_excel(path)

    def _carregar_dados_excel(self, path):
        """
        Le o arquivo Excel e popula os vertices e arestas do grafo
        Args:
            path (str): Caminho para o arquivo Excel
        Raises:
            FileNorFoundError: Se o arquivo especificado em `path` nao for encontrado
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"Arquivo {path} nao encontrado.")
        df = pd.read_excel(path)

        for _, row in df.iterrows():
            origem_iata = row["origem_iata"]
            origem_aeroporto = row["origem_aeroporto"]
            origem_cidade = row["origem_cidade"]
            origem_uf = row["origem_uf"]

            destino_iata = row["destino_iata"]
            destino_aeroporto = row["destino_aeroporto"]
            destino_cidade = row["destino_cidade"]
            destino_uf = row["destino_uf"]

            distancia_km = row["distancia_km"]

            self._adicionar_vertice(origem_iata, origem_aeroporto, origem_cidade, origem_uf)
            self._adicionar_vertice(destino_iata, destino_aeroporto, destino_cidade, destino_uf)

            self._adicionar_aresta(origem_iata, destino_iata, distancia_km)
    
    def _adicionar_vertice(self, IATA, aeroporto,cidade, uf):
        """
        Adiciona um novo aerorporto (vertice) ao grafo, caso ainda nao exista.
        Args:
            IATA (str): Codigo IATA do aeroporto.
            aeroporto (str): Nome completo do aeroporto.
            cidade (str): Cidade ondeo aeroporto esta localizado.
            uf (str): Unidade Federativa do aeroporto.
        """
        if IATA not in self.vertices:
            self.vertices[IATA] = (aeroporto, cidade, uf)

    def _adicionar_aresta(self, origem, destino, peso):
        """
        Adiciona uma rota (aresta bidirecional) entre dois aeroportos.
        Args:
            origem(str): Codigo IATA do aeroporto de origem.
            destino(str): Codigo IATA do aeroporto de destino.
            peso (float/int): Distancia em km entre dois aeroportos
        """
        # inicializa a lista de adjacencias dos vertices, caso ainda nao exista
        self.adjacencias.setdefault(origem, [])
        self.adjacencias.setdefault(destino, [])

        # aresta direcionada: so existe no sentido origem -> destino
        if (destino, peso) not in self.adjacencias[origem]:
            self.adjacencias[origem].append((destino, peso))

    def _obter_vizinhos(self, IATA):
        """
        Retorna os aeroportos conectados diretamentamente a um aeroporto especifico.
        Args:
            IATA (str): codigo IATA do aeroporto.
        Returns:
            list? Lista de tuplas (destino, peso) reprensentando os vizinhos e as distancias
        """
        return self.adjacencias.get(IATA, [])

    def obter_arv_minima(self):
        """
        Retorna uma tupla contendo:
        [0] -> vetor com os vertices
        [1] -> vetor com as arestas da arvore geradora minima (Kruskal)
        """
        vertices = list(self.adjacencias.keys())

        # ordena todas as arestas pelo peso em ordem crescente
        arestas = sorted(
            (
                (origem, destino, float(peso))
                for origem, vizinhos in self.adjacencias.items()
                for destino, peso in vizinhos
            ),
            key=lambda aresta : aresta[2],
        )

        # estrutura Union-Find: inicialmente, cada aeroporto eh a raiz do proprio conjunto
        pai = {v : v for v in vertices}

        def find(v):
            """
            Raiz do conjunto de `v`, com compressao de caminho (iterativa)
            """
            while pai[v] != v:
                pai[v] = pai[pai[v]]
                v = pai[v]
            return v

        def union(u, v):
            """
            Une os conjuntos de `u` e `v`.
            Returns:
                bool: True se foram unidos com sucesso, False se ja pertenciam ao mesmo conjunto (evita ciclo)
            """
            raiz_u, raiz_v = find(u), find(v)
            if(raiz_u == raiz_v):
                return False
            pai[raiz_u] = raiz_v
            return True

        arestas_mst = []
        # Kruskal: Aceita a aresta de ela nao formar um ciclo
        for origem, destino, peso in arestas:
            if union(origem, destino):
                arestas_mst.append((origem, destino, peso))

        return vertices, arestas_mst

    def _dijkstra(self, origem, destino, custo_aresta):
        """
        Encontra o caminho otimo entre dois aeroportos usando o Algoritmo de Dijkstra

        Args:
            origem (str): Codigo IATA do aeroporto de origem.
            destino (str): Codigo IATA do aeroporto de destino.
            custo_aresta (callable): Funcao que recebe o peso da aresta e retorna o custo matematico a ser considerado.
        Returns: 
            tuple: (caminho_lista, custo_total) ou None se nao houver caminho possivel
        Raises:
            ValueError: Se a origem ou o destino nao existirem na estrutura do grafo.
        """
        if origem not in self.adjacencias or destino not in self.adjacencias:
            raise ValueError("Aeroporto inexistente no grafo.")

        dist = {origem: 0}
        anterior = {}
        # Fila de prioridade armazena tuplas no formato (custo_acumulado, vertice)
        fila = [(0, origem)]

        while fila:
            d, u = heapq.heappop(fila)
            # se o vertice extraido eh o destino, finaliza a busca
            if u == destino:
                break
            # ignora entradas obsoletas que ficarem presas na fila de prioridade
            if d > dist[u]:
                continue
            for v, peso in self._obter_vizinhos(u):
                # calcula o novo custa usando uma funcao fornecida (distnacia em km ou salto unitario)
                nova = d + custo_aresta(peso)
                # se encontrou um caminho mais "barato" para o vizinho 'v', atualiza as distancias e o caminho anterior
                if nova < dist.get(v, float("inf")):
                    dist[v] = nova
                    anterior[v] = u
                    heapq.heappush(fila, (nova, v))

        # Se o destino nunca foi mapeado nas distâncias, eles estão em componentes isoladas
        if destino not in dist:
            return None

        caminho = [destino]
        # Reconstrói o caminho de trás para frente a partir do destino
        while caminho[-1] != origem:
            caminho.append(anterior[caminho[-1]])
        return caminho[::-1], dist[destino]
    
    def caminho_menor_custo(self, origem, destino):
        """
        Encontra a menor distancia total (km) entre dois aeroportos
        Args:
            origem (str): Codigo IATA de origem.
            destino (str): Codigo IATA de destino.
        Returns:
            tuple: Lista com a sequencia de codigos IATA do caminho e distancia acumulada em km.
        """
        return self._dijkstra(origem, destino, lambda peso: peso)

    def caminho_menos_conexoes(self, origem, destino):
        """
        Encontra a rota com o menor numero de trechos (conexoes) entre dois aeroportos.
        Args:
            origem (str): Codigo IATA de origem.
            destino (str): Codigo IATA de destino.
        Returns:
            tuple: Lista com a sequencia de codigos IATA do caminho e a quantidade total de trachos voados.
        """
        return self._dijkstra(origem, destino, lambda _ : 1)