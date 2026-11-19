# Partes Únicos: livre.py
# Copyright (C) 2026 Caio Gustavo Rodrigues Grizosto
# SPDX-License-Identifier: LGPL-3.0-only
# Este arquivo é software livre, sob a GNU Lesser General Public License, versão 3 (veja COPYING.LESSER e COPYING). Sem nenhuma garantia.
"""Tema Livre do Letras Únicas: rodada única, em que as letras teclas levam a um conjunto de letras do dicionário do Dosvox.

O jogador tecla letras do alfabeto. A cada letra, ficam só as palavras que a têm, e o banco encolhe para as letras que ainda
aparecem nelas (nenhuma letra esvazia a lista). A partida acaba quando o banco esvazia: todas as palavras que têm as letras
teclas têm só elas. Essas palavras (uma ou mais, como ajoelhareis e ajoelháreis) formam o conjunto final.
O objetivo é um conjunto com muitas letras únicas, e cada dificuldade tem o seu mínimo para valer no ranking.
O ranking é o do Letras (letras.json), com um tema só, "Tema Livre": vale o melhor tempo por letra única do conjunto feito,
como nos outros temas. O conjunto de cada rodada é guardado só no save, para não valer duas vezes.
"""
import dvcs, API, dvdic, carrega_letras, json, os
from string import ascii_lowercase
from menus import Menus, menu

MINIMO_UNICAS = {"f": 0, "m": 10, "d": 14}  # objetivo de cada dificuldade: letras únicas mínimas do conjunto final, para valer no ranking
LISTA_MAXIMA = 50  # com até tantas palavras, o painel da direita as mostra; com mais, só se diz quantas são
_dicionario = None

# --- jogo e rodada ---
def menu_limpo(lista, titulo):
    """Um menu de escolha sozinho na tela: limpa antes, para não sobrar o menu do jogo à esquerda."""
    dvcs.clrScr()
    return menu(lista, titulo)
def dicionario():
    """O dicionário, carregado na primeira vez (leva cerca de 1 segundo)."""
    global _dicionario
    if _dicionario is None: _dicionario = dvdic.Dicionario()
    return _dicionario

class Jogo(carrega_letras.Jogo):
    """A partida do tema livre: uma rodada só, vencida quando as letras formam um conjunto final.
    O save guarda só os conjuntos que o jogador já fez ({"livre": {"conjuntos": [...]}} em "letras/<jogador>.json"), cada um pela palavra mais curta, como no ranking: o mesmo conjunto não vale duas vezes."""
    conta_erros = False
    def vitoria(self): return bool(self.formados)
    def carrega(self, jogo="letras"): return self
    def salva(self, jogo="letras"): pass
    def arquivo(self): return f"{os.path.join('letras', self.jogador)}.json"
    def le(self):
        """O save do jogador inteiro (os outros temas ficam como estão), ou {} se não há."""
        try:
            with open(self.arquivo(), "r", encoding="utf-8") as f: return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError): return {}
    def conjuntos(self): return self.le().get("livre", {}).get("conjuntos", [])
    def registra(self, chave):
        """Guarda o conjunto (a palavra mais curta dele) no save do jogador."""
        dados = self.le()
        dados.setdefault("livre", {}).setdefault("conjuntos", []).append(chave)
        os.makedirs("letras", exist_ok=True)
        with open(self.arquivo(), "w", encoding="utf-8") as f: json.dump(dados, f, indent=4, ensure_ascii=False)

class Rodada(carrega_letras.Rodada):
    """A rodada do tema livre: o banco de letras, as letras já teclas (em teclas) e as palavras que ainda servem (só as poucas)."""
    auto_confirma = True
    def __init__(self, partida, valor_rodada=1):
        super().__init__(partida, valor_rodada)
        self.dic = dicionario()
        self.digitadas, self.teclas = [], 0
        self.dic.desconta(partida.conjuntos())  # os conjuntos que o jogador já fez não existem mais para ele
        self.total, banco = self.dic.filtra(0)
        self.letras = set(dvdic.nomes(banco))
        self.formados = []
    def exibe_formados(self): return self.formados
    def comandos(self, foco):
        """O menu interativo (F9) do tema livre."""
        return [("Enter", "Tecla a letra", dvcs.ENTER), ("Espaço", "Diz quantas palavras restam", b" "), ("F6", "Diz as letras teclas", dvcs.F6), ("F7", "Tira a última letra teclada", dvcs.F7),
            ("Backspace", "Recomeça", dvcs.BACKSPACE), ("Tab", "Alterna para a lista de palavras", dvcs.TAB), ("Esc", "Sai do tema livre", dvcs.ESC)]
    def numero(self, letra): return ord(letra) - 96  # no criptograma, a rodada é única e as letras são o alfabeto todo: o número é a posição nele, em qualquer dificuldade
    def tabela(self): return [f"{ord(letra) - 96}. {letra}" for letra in ascii_lowercase]
    def fim(self):
        """A rodada acaba quando o banco esvazia."""
        return bool(self.digitadas) and not self.letras
    def finais(self):
        """As palavras do conjunto final (só vale no fim da rodada)."""
        return self.dic.palavras(self.teclas, exato=True)
    def atualiza(self):
        """Recalcula o que resta a partir das letras teclas: total, banco e, se forem poucas, as palavras."""
        self.teclas = 0
        for l in self.digitadas: self.teclas |= dvdic.mascara(l)
        self.total, banco = self.dic.filtra(self.teclas)
        self.letras = set(dvdic.nomes(banco))
        self.formados = self.dic.palavras(self.teclas) if 0 < self.total <= LISTA_MAXIMA and self.letras else []
    def joga(self, letra):
        """Tecla a letra: ficam as palavras com ela e o banco só com as letras que elas ainda usam. Retorna (True, mensagem)."""
        self.digitadas.append(letra)
        self.atualiza()
        return True, f"{self.total} palavra{'s' if self.total > 1 else ''} com {letra}."
    def desfaz(self):
        """F7: tira a última letra teclada e volta ao conjunto anterior. Retorna (sucesso, mensagem)."""
        if not self.digitadas: return False, "Nenhuma letra teclada."
        letra = self.digitadas.pop()
        self.atualiza()
        return True, f"Tirou {letra}. {self.total} palavra{'s' if self.total > 1 else ''}."

class RodadaPalavras(Rodada):
    """A rodada do tema livre nos níveis 1 e 2: o jogador escreve palavras do dicionário, e as letras únicas de cada uma saem das partes (as letras que restam).
    Termina quando as letras acabam ou nenhuma palavra cabe nas que restam; Esc também encerra."""
    def __init__(self, partida, valor_rodada=1):
        carrega_letras.Rodada.__init__(self, partida, valor_rodada)
        self.dic = dicionario()
        self.dic.desconta([])  # o dicionário é um só para o jogo todo: aqui nenhum conjunto fica de fora
        self.letras, self.formados = set(ascii_lowercase), []
    @property
    def unicas(self): return 26 - len(self.letras)
    def livres(self): return dvdic.mascara("".join(self.letras))
    def fim(self): return bool(self.formados) and (not self.letras or not self.dic.cabe(self.livres()))
    def comandos(self, foco):
        """O menu interativo (F9) do tema livre com palavras."""
        if foco == "partes": primeiro = ("Enter", "Põe a letra na palavra e abre o campo para escrever", dvcs.ENTER)
        else: primeiro = ("Enter", "Abre o campo para escrever a palavra", dvcs.ENTER)
        return [primeiro, ("F2", "Escreve a palavra direto no campo", dvcs.F2), ("Espaço", "Diz quantas letras restam", b" "), ("F6", "Diz as palavras formadas", dvcs.F6), ("F7", "Tira a última palavra formada, devolvendo as letras", dvcs.F7),
            ("Backspace", "Apaga a palavra em formação ou, se não há, a última formada", dvcs.BACKSPACE), ("Tab", "Alterna para a lista de palavras", dvcs.TAB), ("Esc", "Encerra a partida", dvcs.ESC)]
    def limpa(self, texto):
        """Tira do texto o que não é letra e as letras que já saíram das partes (usadas em outra palavra). Retorna (texto, letras recusadas)."""
        texto = "".join(c for c in texto.lower() if c.isalpha())
        recusadas = sorted({dvdic.desacentuar(c) for c in texto if dvdic.desacentuar(c) not in self.letras})
        return "".join(c for c in texto if dvdic.desacentuar(c) in self.letras), recusadas
    def joga(self, texto):
        """Escreve uma palavra: ela precisa estar no dicionário e só ter letras ainda livres. Retorna (sucesso, mensagem)."""
        texto = texto.strip().lower()
        if not dvdic.desacentuar(texto).isalpha(): return False, "Escreva só letras, sem espaços nem hífen."
        usadas = [l for l in dvdic.nomes(dvdic.mascara(texto)) if l not in self.letras]
        if usadas: return False, f"A palavra usa letras que já foram usadas: {', '.join(usadas)}."
        palavra = self.dic.procura(texto)
        if not palavra: return False, f"A palavra {texto} não está no dicionário."
        self.letras -= set(dvdic.nomes(dvdic.mascara(palavra)))
        self.formados.append(palavra)
        return True, f"{palavra}. Restam {len(self.letras)} letras."
    def desfaz(self):
        """F7: tira a última palavra e devolve as letras dela. Retorna (sucesso, mensagem)."""
        if not self.formados: return False, "Nenhuma palavra escrita."
        palavra = self.formados.pop()
        self.letras = set(ascii_lowercase) - set(dvdic.nomes(dvdic.mascara("".join(self.formados))))
        return True, f"Tirou {palavra}. Restam {len(self.letras)} letras."

# --- partida ---
def instr():
    dvcs.sintWriteln("TEMA LIVRE nos níveis 1 e 2: monte palavras do dicionário. Tecle Enter numa letra do menu para pô-la na palavra, e use o campo para digitar ou mudar letras. As letras de cada palavra saem das letras disponíveis, e cada letra só pode ser usada uma vez.")
    dvcs.sintWriteln("A partida acaba quando as letras acabam ou nenhuma palavra cabe nas que restam, ou quando você tecla Esc. Enter no campo confirma a palavra. Backspace apaga a palavra em formação ou, se não há, a última formada. F2 escreve a palavra direto, F7 tira a última formada e Espaço diz quantas letras restam.")
    dvcs.sintWriteln("TEMA LIVRE no nível 3: tecle letras do alfabeto. Só ficam as palavras que têm as letras teclas.")
    dvcs.sintWriteln("Procure um conjunto de letras com o maior número de letras únicas.")
    dvcs.sintWriteln("No fácil, qualquer conjunto vale para o ranking. No médio, o conjunto precisa ter 10 letras únicas ou mais, e no difícil, 14 ou mais.")
    dvcs.sintWriteln("A partida acaba quando todas as palavras que têm as letras teclas têm só elas.")
    dvcs.sintWriteln("Tecle espaço para saber quantas palavras restam, F6 para ouvir as letras teclas, F7 para tirar a última letra e Backspace para recomeçar.")
    dvcs.sintWriteln("Tecle F9 para o menu interativo, com os comandos do menu em que você está.")
    dvcs.sintWriteln("Para jogar com mais gente, informe o número de jogadores: eles se revezam, uma rodada cada, e quem atinge o objetivo soma as letras únicas do conjunto. Esc encerra a disputa.")
    dvcs.sintWriteln("No criptograma, as letras aparecem como números: digite o número ou a letra.")
    dvcs.sintWriteln("Aperte Enter para continuar...")
    dvcs.sintReadKey()
    return API.menu_ajuda()

def novo_menu(progresso):
    interface = Menus(progresso)
    interface.foco = "partes"
    return interface

def edita_palavra(interface, atual):
    """Abre o campo de edição com a palavra em formação, logo abaixo das mensagens. Retorna (texto, tecla que fechou o campo)."""
    y = interface.pos_mensagem + 1
    dvcs.goToXY(1, y)
    dvcs.write("Palavra: ")
    return dvcs.sintEdita(atual, 10, y, 40, True)

def rodada_palavras(tema, nome, disputa=False):
    """O tema livre dos níveis 1 e 2. Retorna (partida, interface, finais, unicas, vale), ou None se o jogador encerrar sem nenhuma palavra.
    Vale (ranking ou pontos) se as letras únicas usadas atingiram o objetivo. Não guarda conjuntos no save: o que se repete aqui são palavras, e elas podem ser escritas de novo."""
    minimo = MINIMO_UNICAS.get(tema.dificuldade, 0)
    dvcs.sintWriteln("Tema livre. Escreva palavras do dicionário: cada letra só pode ser usada uma vez." + (f" Objetivo: pelo menos {minimo} letras únicas." if minimo else ""))
    partida = Jogo(nome, tema).carrega()
    progresso = RodadaPalavras(partida)
    interface = novo_menu(progresso)
    if tema.cripto: menu_limpo(progresso.tabela(), "Veja o número representado por cada letra e tecle Enter")
    partida.iniciar()
    atual, edita = "", False  # a palavra em formação: as letras do menu e as digitadas no campo
    interface.mensagem("Tecle Enter numa letra para pôr na palavra, ou F2 para escrever direto. Enter no campo confirma a palavra.")
    while True:
        interface.mostrar()
        tecla = interface.le_tecla()
        info = ""
        if tecla == dvcs.ESC:
            if not progresso.formados: return None
            break
        elif tecla == dvcs.BACKSPACE:
            if atual: atual, info = "", "Palavra apagada."
            elif progresso.formados: info = progresso.desfaz()[1]
            else: info = "Nada para apagar."
        elif tecla == dvcs.F7: info = progresso.desfaz()[1]
        elif tecla == b" ": info = f"Restam {len(progresso.letras)} letras."
        elif tecla == dvcs.F6: info = f"Palavras: {', '.join(progresso.formados) or 'nenhuma'}."
        elif tecla == dvcs.F2: edita = True
        elif tecla == dvcs.ENTER:
            if interface.foco == "partes" and progresso.partes: atual += progresso.partes[interface.idx_p]
            edita = True
        else: interface.navegar(tecla)
        if edita:
            edita = False
            texto, saida = edita_palavra(interface, atual)
            atual, recusadas = progresso.limpa(texto)
            if recusadas: info = f"Letra{'s' if len(recusadas) > 1 else ''} já usada{'s' if len(recusadas) > 1 else ''} em outra palavra: {', '.join(recusadas)}."
            elif saida == dvcs.ENTER and atual:
                sucesso, info = progresso.joga(atual)
                if sucesso: atual = ""
            elif atual: info = f"Palavra em formação: {atual}."
        if info:
            interface = novo_menu(progresso)  # as partes e os formados podem ter mudado
            interface.mensagem(info)
            if progresso.fim(): break
    finais, unicas = progresso.formados, progresso.unicas
    partida.formados = finais
    tema.chave = ", ".join(finais)  # na disputa, o que o jogador formou
    tema.escolhido = "Tema Livre"  # no ranking, é um tema só: vale o melhor tempo por letra única
    atingiu = unicas >= minimo
    interface = novo_menu(progresso)
    if len(finais) > 1:
        interface.mensagem(f"Você formou {len(finais)} palavras com {unicas} letras únicas! Veja quais foram as palavras e tecle Enter.")
        menu_limpo(finais, "Palavras formadas")
    else: interface.mensagem(f"Formou a palavra {finais[0]} com {unicas} letras únicas.")
    if not atingiu: interface.mensagem(f"O objetivo era {minimo} ou mais letras únicas. " + ("Sem pontos nesta rodada." if disputa else "Esta partida não entra no ranking."))
    return partida, interface, finais, unicas, atingiu

def rodada(tema, nome, disputa=False):
    """Joga uma rodada do tema livre até o banco de letras esvaziar. Retorna (partida, interface, finais, unicas, vale), ou None se o jogador sair com Esc.
    O conjunto vale (ranking ou pontos) se atingiu o objetivo e o jogador ainda não o tinha feito; um conjunto novo fica guardado no save.
    Nos níveis 1 e 2 o jogador escreve palavras (rodada_palavras); no nível 3, tecla letras."""
    if tema.nivel < 3: return rodada_palavras(tema, nome, disputa)
    minimo = MINIMO_UNICAS.get(tema.dificuldade, 0)
    dvcs.sintWriteln("Tema livre. Tecle letras até chegar a um conjunto com muitas letras únicas." + (f" Objetivo: pelo menos {minimo} letras únicas." if minimo else ""))
    partida = Jogo(nome, tema).carrega()
    progresso = Rodada(partida)
    interface = novo_menu(progresso)
    if tema.cripto: menu_limpo(progresso.tabela(), "Veja o número representado por cada letra e tecle Enter")  # antes de começar a contar o tempo
    partida.iniciar()
    while not progresso.fim():
        interface.mostrar()
        tecla = interface.le_tecla()
        if tecla == dvcs.ESC: return None
        elif tecla == dvcs.BACKSPACE:
            interface.mensagem("Recomeçando.")
            progresso = Rodada(partida)
            interface = novo_menu(progresso)
        elif tecla == b" ": interface.mensagem(f"{progresso.total} palavras restam.")
        elif tecla == dvcs.F7:
            sucesso, info = progresso.desfaz()
            interface = novo_menu(progresso)
            interface.mensagem(info)
        elif tecla == dvcs.F6: interface.mensagem(f"Letras teclas: {', '.join(progresso.digitadas) or 'nenhuma'}.")
        elif tecla == dvcs.ENTER and interface.foco == "partes":
            sucesso, info = progresso.joga(progresso.partes[interface.idx_p])
            interface = novo_menu(progresso)
            interface.mensagem(info)
        else: interface.navegar(tecla)
    finais = progresso.finais()
    unicas = dvdic.bits(progresso.teclas)
    partida.formados = finais
    tema.chave = min(finais, key=lambda p: (len(p), dvdic.desacentuar(p).lower(), p))  # o conjunto é guardado (já feitos) pela palavra mais curta
    tema.escolhido = "Tema Livre"  # no ranking, é um tema só: vale o melhor tempo por letra única
    atingiu = unicas >= minimo
    novo = tema.chave not in partida.conjuntos()
    if novo: partida.registra(tema.chave)
    interface = novo_menu(progresso)
    if len(finais) > 1:  # várias palavras com as mesmas letras: o jogador as vê num menu
        interface.mensagem(f"Você encontrou {len(finais)} palavras com as mesmas {unicas} letras únicas! Veja quais foram as palavras e tecle Enter.")
        menu_limpo(finais, "Palavras encontradas")
    else: interface.mensagem(f"Encontrou a palavra {finais[0]} com {unicas} letras únicas.")
    if not novo: interface.mensagem("Você já fez este conjunto, e ele não vale de novo.")
    elif not atingiu: interface.mensagem(f"O objetivo era {minimo} ou mais letras únicas. " + ("Sem pontos nesta rodada." if disputa else "Esta partida não entra no ranking."))
    return partida, interface, finais, unicas, atingiu and novo

# --- disputa (vários jogadores) ---
def jogadores_da_disputa(nome, n):
    """Pergunta o nome dos outros jogadores. Retorna {nome: {"pontos": 0, "palavra": ""}}, na ordem de jogo."""
    jogadores = {nome: {"pontos": 0, "palavra": ""}}
    for i in range(2, n + 1):
        dvcs.sintWriteln(f"Nome do jogador {i}.")
        outro = dvcs.sintReadln().strip() or f"Jogador {i}"
        while outro in jogadores: outro += f" {i}"  # nomes repetidos não se misturam
        jogadores[outro] = {"pontos": 0, "palavra": ""}
    return jogadores

def classificacao(jogadores):
    """As linhas do ranking da disputa, "pontos nome- palavra", de quem tem mais pontos para quem tem menos."""
    ordem = sorted(jogadores.items(), key=lambda j: -j[1]["pontos"])
    return [f"{dados['pontos']} {nome}- {dados['palavra'] or 'sem palavra ainda'}" for nome, dados in ordem]

def vencedores(jogadores):
    """O fim da disputa: quem fez mais pontos (ou o empate)."""
    maior = max(d["pontos"] for d in jogadores.values())
    ganhou = [n for n, d in jogadores.items() if d["pontos"] == maior]
    return f"Venceu {ganhou[0]}, com {maior} pontos!" if len(ganhou) == 1 else f"Empate com {maior} pontos entre {', '.join(ganhou)}."

def disputa(tema, nome, n):
    """Os jogadores se revezam, uma rodada cada. Quem atinge o objetivo soma as letras únicas do conjunto. Sem fim fixo: Esc encerra.
    A disputa tem o seu ranking e não entra no ranking do Letras."""
    jogadores = jogadores_da_disputa(nome, n)
    nomes, vez = list(jogadores), 0
    while True:
        atual = nomes[vez % len(nomes)]
        dvcs.sintWriteln(f"{atual}, sua vez!")
        resultado = rodada(tema, atual, disputa=True)
        if resultado is None: break
        partida, interface, finais, unicas, atingiu = resultado
        jogadores[atual]["pontos"] += unicas if atingiu else 0
        jogadores[atual]["palavra"] = tema.chave
        if not menu_limpo(classificacao(jogadores), "Ranking da disputa. Enter continua e Esc encerra."): break
        vez += 1
    dvcs.sintWriteln("Fim da disputa. " + vencedores(jogadores))
    menu_limpo(classificacao(jogadores), "Ranking final da disputa")

# --- jogar ---
def jogar(tema, nome):
    """O Tema Livre sozinho (entra no ranking do Letras, se atingiu o objetivo) ou em disputa com vários jogadores."""
    dvcs.sintWriteln("Tecle Enter ou 1 para jogar sozinho, ou digite o número de jogadores.")
    texto = dvcs.sintReadln().strip()
    n = int(texto) if texto.isdigit() else 1
    if n > 1: return disputa(tema, nome, n)
    resultado = rodada(tema, nome)
    if resultado is None: return
    partida, interface, finais, unicas, atingiu = resultado
    API.fim_de_sessao(interface, "letras", unicas, progride=False, ranking_path="letras.json", registra=atingiu)  # conjunto rico e rápido vale mais; o ranking é o do Letras
