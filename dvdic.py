# Partes Únicos: dvdic.py
# Copyright (C) 2026 Caio Gustavo Rodrigues Grizosto
# SPDX-License-Identifier: LGPL-3.0-only
# Este arquivo é software livre, sob a GNU Lesser General Public License, versão 3 (veja COPYING.LESSER e COPYING). Sem nenhuma garantia.
"""Dicionário do Dosvox (dvdic: diciona.dic, .suf e .exc) para o Tema Livre.

O diciona.dic tem uma linha por prefixo, "prefixo grupo1 grupo2 ...", e o diciona.suf define cada grupo, "[grupo]" seguido dos
sufixos. A palavra é prefixo + sufixo ("=" no lugar do grupo é o próprio prefixo), como no dvdic.pas. O diciona.exc lista as
palavras que essa expansão gera mas não existem. Palavras com hífen ou apóstrofo ficam de fora, e os nomes próprios (.nom) também.
São milhões de formas e poucos conjuntos de letras: por isso o jogo trabalha com conjuntos, uma máscara de 26 bits (a=bit 0),
e só gera as palavras de verdade quando precisa mostrá-las.
"""
import collections, os, unicodedata

PASTA = "dic"  # onde estão diciona.dic, diciona.suf e diciona.exc
ALFABETO = (1 << 26) - 1

# --- leitura dos arquivos ---
def ruim(texto): return "-" in texto or "'" in texto
def le(caminho):
    """As linhas do arquivo (latin-1), sem espaços nas pontas, sem linhas vazias nem comentários (*)."""
    with open(caminho, encoding="latin-1") as f: return [l.strip() for l in f if l.strip() and l.strip()[0] != "*"]
def sufixos(caminho):
    """{grupo: [sufixos]} do diciona.suf."""
    grupos, atual = {}, None
    for linha in le(caminho):
        if linha[0] == "[": atual = grupos.setdefault(linha[1:].rstrip("]").strip(), [])
        elif atual is not None: atual.append(linha)
    return grupos

# --- letras ---
def desacentuar(texto): return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))
def mascara(palavra):
    """As letras a-z da palavra (sem acento, sem hífen), uma por bit."""
    m = 0
    for c in desacentuar(palavra.lower()):
        if "a" <= c <= "z": m |= 1 << (ord(c) - 97)
    return m
def bits(m): return bin(m).count("1")
def nomes(m): return [chr(97 + i) for i in range(26) if m >> i & 1]

# --- o dicionário ---
class Dicionario:
    """Os conjuntos de letras das palavras do dicionário e, sob pedido, as palavras de um conjunto."""
    def __init__(self, pasta=PASTA):
        grupos = sufixos(os.path.join(pasta, "diciona.suf"))
        self.grupos = {g: self._por_conjunto(lista) for g, lista in grupos.items()}  # grupo -> {letras do sufixo: [sufixos]}
        self.pares = []  # (prefixo, letras do prefixo, grupo)
        for linha in le(os.path.join(pasta, "diciona.dic")):
            partes = linha.split()
            if ruim(partes[0]): continue
            self.pares += [(partes[0], mascara(partes[0]), g) for g in partes[1:] or ["="]]
        self.excecoes = {p.lower() for p in le(os.path.join(pasta, "diciona.exc")) if not ruim(p)}
        self.conjuntos = self._conta()  # letras -> quantas formas do dicionário têm exatamente essas letras
        self._tira_excecoes()
        self.fora = frozenset()  # conjuntos descontados, como exceções (veja desconta)
    @staticmethod
    def _por_conjunto(lista):
        por = collections.defaultdict(list)
        for s in lista:
            if not ruim(s): por[mascara(s)].append(s)
        return por
    def _conta(self):
        conta = collections.Counter()
        for prefixo, pm, g in self.pares:
            if g == "=": conta[pm] += 1
            else:
                for sm, lista in self.grupos.get(g, {}).items(): conta[pm | sm] += len(lista)
        return conta
    def _tira_excecoes(self):
        """Desconta as exceções que a expansão realmente gera (um conjunto que só tinha exceções some)."""
        prefixos = collections.defaultdict(list)
        for prefixo, pm, g in self.pares: prefixos[prefixo.lower()].append(g)
        sufs = {g: {s.lower() for lista in por.values() for s in lista} for g, por in self.grupos.items()}
        for palavra in self.excecoes:
            m = mascara(palavra)
            if self.conjuntos[m] > 0 and self._gera(palavra, prefixos, sufs):
                self.conjuntos[m] -= 1
                if not self.conjuntos[m]: del self.conjuntos[m]
    @staticmethod
    def _gera(palavra, prefixos, sufs):
        """A expansão gera esta palavra? (prefixo + sufixo de algum grupo do prefixo)"""
        return any(g == "=" and i == len(palavra) or g != "=" and palavra[i:] in sufs.get(g, ())
                   for i in range(1, len(palavra) + 1) for g in prefixos.get(palavra[:i], ()))

    # --- consultas ---
    def desconta(self, palavras):
        """Tira do dicionário, como se fossem exceções, os conjuntos de letras das `palavras` (os que o jogador já fez). Vale até a próxima chamada; sem palavras, devolve tudo."""
        self.fora = frozenset(mascara(p) for p in palavras)
    def filtra(self, teclas):
        """Quantas formas têm todas as letras teclas, e o banco: as outras letras que elas ainda usam."""
        n = banco = 0
        for m, c in self.conjuntos.items():
            if m & teclas == teclas and m not in self.fora:
                n += c
                banco |= m
        return n, banco & ~teclas & ALFABETO
    def cabe(self, livres):
        """Alguma palavra do dicionário usa só as letras `livres` (uma máscara)?"""
        return any(m and m & ~livres == 0 and m not in self.fora for m in self.conjuntos)
    def procura(self, palavra):
        """A forma do dicionário que corresponde à palavra digitada (com ou sem acento), ou "" se ela não existe."""
        p = palavra.strip().lower()
        achadas = {w.lower(): w for w in self.palavras(mascara(p), exato=True)}
        if p in achadas: return achadas[p]
        return next((w for k, w in achadas.items() if desacentuar(k) == desacentuar(p)), "")
    def palavras(self, teclas, exato=False):
        """As palavras com todas as letras teclas (com exatamente elas, se exato), em ordem alfabética."""
        achadas = set()
        for prefixo, pm, g in self.pares:
            if g == "=":
                if pm not in self.fora and self._serve(pm, teclas, exato): achadas.add(prefixo)
            else:
                for sm, lista in self.grupos.get(g, {}).items():
                    if pm | sm not in self.fora and self._serve(pm | sm, teclas, exato): achadas.update(prefixo + s for s in lista)
        return sorted((p for p in achadas if p.lower() not in self.excecoes), key=lambda p: (desacentuar(p).lower(), p))
    @staticmethod
    def _serve(m, teclas, exato): return m == teclas if exato else m & teclas == teclas
