# Partes Únicos: ranking.py
# Copyright (C) 2026 Caio Gustavo Rodrigues Grizosto
# SPDX-License-Identifier: LGPL-3.0-only
# Este arquivo é software livre, sob a GNU Lesser General Public License, versão 3 (veja COPYING.LESSER e COPYING). Sem nenhuma garantia.
"""Módulo de Ranking do jogo."""
import dvcs, json, unicodedata
from typing import Dict
def desacentuar(texto): return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))

class Ranking:
    """Classe para gerenciar o ranking do jogo, incluindo verificação de recordes e exibição de resultados."""
    def verifica_record(self) -> bool:
        """Verifica se a partida atual bateu algum recorde no ranking."""
        partida = self.partida
        jogador = partida.jogador
        tema = partida.tema.escolhido
        if jogador not in self.ranking:
            return True
        if tema not in self.ranking[jogador]:
            return True
        record = self.ranking[jogador][tema]
        if partida.tempo_por_numero < record["tempo_por_numero"]:
            return True
        if (partida.tempo_por_numero == record["tempo_por_numero"] and
                record["tempo_total"] and partida.tempo_total < record["tempo_total"]):
            return True
        return False

    def __init__(self, partida=None, path="ranking.json"):
        """Inicializa o ranking, carregando os dados do arquivo especificado e verificando se a partida atual bateu algum recorde."""
        self.path = path
        self.partida = partida
        self.record = False
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self.ranking: dict[str, dict[str, dict]] = json.load(f)
        except FileNotFoundError:
            self.ranking = {}
        except json.JSONDecodeError:
            self.ranking = {}
        self.record = self.verifica_record() if partida else False
        if self.record: 
            jogador = partida.jogador
            tema = partida.tema.escolhido
            self.ranking.setdefault(jogador, {})[tema] = {
                "tempo_total": partida.tempo_total,
                "tempo_por_numero": partida.tempo_por_numero,
                "data": partida.data
           }
            self._save()
    def _save(self):
        """Salva o ranking atualizado no arquivo especificado."""
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.ranking, f, indent=4, ensure_ascii=False)

    def exibe_por_tema(self, tema):
        """retorna lista de (jogador, record) ordenada por tempo_total asc, depois tempo_por_numero asc"""
        resultados = []
        for jogador, temas in self.ranking.items():
            if tema in temas:
                r = temas[tema]
                resultados.append((jogador, r))
        resultados.sort(key=lambda x: (x[1]["tempo_por_numero"], x[1]["tempo_total"] or 0))  # "" nos registros importados
        return resultados

    def lista_por_tema(self, tema):
        """retorna lista de dicionários com os dados necessários para exibir no menu"""
        return [
            {
                "nome": jogador,
                "tema": tema,
                "data": record.get("data", ""),
                "tempo_total": record.get("tempo_total"),
                "tempo_por_numero": record.get("tempo_por_numero"),
            }
            for jogador, record in self.exibe_por_tema(tema)
        ]
    def linhas_por_tema(self, tema):
        """retorna lista de strings prontas para exibir em um menu ou seleção"""
        return [
            f"{item['tempo_por_numero']} - {item['nome']} - {item['tema']} - {item['data']} - {item['tempo_total']}"
            for item in self.lista_por_tema(tema)
        ]

    def linhas_por_nome(self, nome, tema=None):
        """retorna lista de strings prontas para exibir em um menu ou seleção, ordenada por tempo_por_numero asc, depois tempo_total asc.
        O nome não diferencia maiúsculas; com tema, só os registros desse tema."""
        resultados = []
        for jogador, temas in self.ranking.items():
            if jogador.lower() == nome.lower():
                for t, record in temas.items():
                    if tema is None or t == tema: resultados.append((t, record))
        resultados.sort(key=lambda x: (x[1]["tempo_por_numero"], x[1]["tempo_total"] or 0))
        return [
            f"{item[1]['tempo_por_numero']} - {item[0]} - {item[1]['data']} - {item[1]['tempo_total']}"
            for item in resultados
                    ]        
    
    def melhor_record(self, ranking_jogador=None, ranking_tema=None):
        """Compara os rankings do jogador e do tema, retornando o ranking com o melhor recorde."""
        if not ranking_jogador: ranking_jogador = self.linhas_por_nome(self.partida.jogador)
        if not ranking_tema : ranking_tema = self.linhas_por_tema(self.partida.tema.escolhido)
        if not ranking_jogador or len(ranking_jogador) == 1:
            return ranking_tema, "tema"
        if not ranking_tema or len(ranking_tema) == 1:
            return ranking_jogador, "nome"
        linha_jogador = f"{self.partida.tempo_por_numero} - {self.partida.tema.escolhido} - {self.partida.data} - {self.partida.tempo_total}"
        linha_tema = f"{self.partida.tempo_por_numero} - {self.partida.jogador} - {self.partida.tema.escolhido} - {self.partida.data} - {self.partida.tempo_total}"
        if linha_jogador not in ranking_jogador or linha_tema not in ranking_tema:
            return ranking_tema, "tema"
        pos_jogador = ranking_jogador.index(linha_jogador)
        pos_tema = ranking_tema.index(linha_tema)
        return (ranking_jogador, "nome") if pos_jogador < pos_tema else (ranking_tema, "tema")

    def exibe_ranking(self, ranking=None, tipo=None):
        """Exibe o ranking no menu, com base no tipo especificado (nome ou tema)."""
        if ranking == None and tipo == None: ranking, tipo = self.melhor_record()
        dvcs.clrScr()
        if not ranking: return dvcs.sintWriteln("Ainda não há registros para esta consulta.")
        dvcs.sintWriteln("Ranking por " + tipo + ":")
        dvcs.popupMenuCria(3, 1, 40, len(ranking) + 2, 0)
        for linha in ranking:
            dvcs.popupMenuAdiciona("", linha)
        dvcs.popupMenuSeleciona()

ARQUIVOS = {"n": "ranking.json", "p": "palavras.json", "l": "letras.json", "m": "monta.json"}  # ranking de cada jogo (no Letras, o Tema Livre e o criptograma entram no mesmo)

def escolhe_tema(meu_tema, qual):
    """Define o tema da consulta: no Números, pela dificuldade e limite; no Letras, "Tema Livre" ou o menu de temas; nos demais, pelo menu de temas.
    Retorna o nome do tema, ou "" se o jogador cancelar ou o arquivo não existir."""
    if qual == "l":
        dvcs.sintWriteln("Tecle l para o Tema Livre, ou outra tecla para os temas.")
        if dvcs.dvcsLeTecla().decode("latin-1").lower() == "l": return "Tema Livre"
    if qual == "n":
        meu_tema.config()
        if meu_tema.cancelado: return ""
    try: meu_tema.carrega()
    except FileNotFoundError:
        dvcs.sintWriteln("o arquivo do tema não foi encontrado.")
        return ""
    return meu_tema.escolhido

def consulta(meu_tema, qual="?"):
    """Consulta o ranking do jogo, permitindo ao usuário pesquisar por nome ou tema e exibir os resultados."""
    records = Ranking(None, ARQUIVOS[qual])
    dvcs.sintWriteln("Tecle n para pesquisar por nome ou t para pesquisar por tema.")
    tecla = dvcs.dvcsLeTecla().decode().lower()
    if tecla == "t":
        tema = escolhe_tema(meu_tema, qual)
        if tema: records.exibe_ranking(records.linhas_por_tema(tema), "tema")
    elif tecla == "n":
        dvcs.sintWriteln("Nome a procurar")
        nome = dvcs.sintReadln()
        dvcs.sintWriteln("Filtra por tema?")
        tema = escolhe_tema(meu_tema, qual) if dvcs.dvcsLeTecla().decode().lower() == "s" else None
        if tema != "": records.exibe_ranking(records.linhas_por_nome(nome, tema), "nome")

def importa(arquivo="Ranking.ini"):
    """Importa Ranking do programa em Scriptvox"""
    records = Ranking()
    # 1. Carregamos o que vem do arquivo em uma estrutura temporária que acumula tudo
    dados_do_txt = {}
    with open(arquivo, "r", encoding="latin-1") as a:
        for linha in a:
            partes = linha.strip().split("- ")
            if not partes[0]: continue
            nome = partes[1]
            tema = partes[2]
                        # Inicializa a estrutura se o nome não existir no temporário
            if nome not in dados_do_txt:
                dados_do_txt[nome] = {}
            dados_do_txt[nome][tema] = {
                "tempo_total": "",
                "tempo_por_numero": round(int(partes[0]) / 100, 2),
                "data": partes[4]
            }
     # 2. Agora processamos a mesclagem com o ranking atual (records)
    for nome, temas in dados_do_txt.items():
        # Se o nome não existe no ranking, criamos a estrutura toda
        if nome not in records.ranking:
            records.ranking[nome] = temas
        else:
            # Se já existe, comparamos tema por tema
            for tema, novo_dado in temas.items():
                if tema not in records.ranking[nome]:
                    records.ranking[nome][tema] = novo_dado
                else:
                    # Comparação de performance (mantém o menor tempo)
                    if novo_dado["tempo_por_numero"] < records.ranking[nome][tema]["tempo_por_numero"]:
                        records.ranking[nome][tema] = novo_dado
    records._save()