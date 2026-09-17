import os
import pandas as pd
class Grafo:
    def __init__(self, path):
        self.vertices = {}
        """
        dict com IATA : (nome do aeroporto, nome da idade, uf)
        """

        self.adjacencias = {}
        """
        dict com origem : (destino, peso)
        """
        self._carregar_dados_excel(path)

    def _carregar_dados_excel(self, path):
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
        if IATA not in self.vertices:
            self.vertices[IATA] = (aeroporto, cidade, uf)

    def _adicionar_aresta(self, origem, destino, peso):
        if origem not in self.adjacencias:
            self.adjacencias[origem] = []
        if destino not in self.adjacencias:
            self.adjacencias[destino] = []

        # verificar se aresta ja existe na origem se nao adicona
        if (destino, peso) not in self.adjacencias[origem]:
            self.adjacencias[origem].append((destino,peso))

        # verificar se aresta ja existe no destino se nao adicona
        if (origem, peso) not in self.adjacencias[destino]:
            self.adjacencias[destino].append((origem,peso))

    def _obter_vizinhos(self, IATA):
        return self.vertices.get(IATA, []);

    def obter_arv_minima(self):
        pass

    def caminho_menor_custo(self, origem, destino):
        pass

    def caminho_menos_conexoes(self, orgigem, destino):
        pass