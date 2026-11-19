# Partes Únicos: menus.py
# Copyright (C) 2026 Caio Gustavo Rodrigues Grizosto
# SPDX-License-Identifier: LGPL-3.0-only
# Este arquivo é software livre, sob a GNU Lesser General Public License, versão 3 (veja COPYING.LESSER e COPYING). Sem nenhuma garantia.
import time, dvcs

TELA = (80, 25)  # largura e altura da tela, se o dvcs não informar

def tamanho_tela():
    """Largura e altura da tela (dvcs.screenSize), ou TELA se o dvcs não informar."""
    try: largura, altura = dvcs.screenSize()
    except Exception: return TELA
    return largura, altura


class Menu:
    """Um painel de menu navegável por teclado (baseado no jogo Partes Únicas e nos menus do Dosvox).
    Busca incremental por tecla e fala do item focado.
    Se os itens não cabem na altura da tela, o menu continua em novas colunas e rola para o item focado.
    """
    def __init__(self, x: int= 0, y: int= 0, itens: None | list= None, linhas: None | int= None,
        autoconfirma: bool= False, por_posicao: bool= False):
        """Inicializa o menu, podendo inclusive adicionar as coordenadas x, y.
        Os itens também já podem ser informados caso já seja uma lista pronta.
        linhas: itens por coluna. Se omitido, é o que cabe da posição y até o fim da tela.
        autoconfirma: quando a busca incremental acha um item só, ele já é escolhido, como se desse Enter.
        por_posicao: numa lista sem números, os dígitos digitados escolhem o item pela posição (1, 2, ...)."""
        self.idx = 0
        self.busca = ""
        self.itens = []
        self.tempo_tecla = 0.0
        self.maior = 0  # tamanho do maior item
        self.topo = 0  # primeira coluna visível
        self.borda = None  # última coluna da tela que o menu pode usar (None: o fim da tela)
        self.confirma = False  # a busca resolveu sozinha: o menu devolve Enter (ver executa)
        self.max_linhas = linhas
        self.autoconfirma = autoconfirma
        self.por_posicao = por_posicao
        self.cria(x, y)
        if itens:
            for item in itens:
                self.adiciona(item)

    def cria(self, x, y):
        """Cria um menu na posição especificada."""
        self.x = x
        self.y = self.pos_y = y

    def adiciona(self, item):
        """Adiciona um item ao menu."""
        self.maior = max(self.maior, len(str(item)))
        self.itens.append(item)

    def define(self, itens):
        """Usa a lista informada como os itens do menu, sem copiá-la: o que mudar nela aparece no menu."""
        self.itens = itens
        self.mede()

    def mede(self):
        """Recalcula o tamanho do maior item (a lista pode ter mudado)."""
        self.maior = max((len(str(i)) for i in self.itens), default=0)

    # --- medidas ---
    @property
    def linhas(self):
        """Itens por coluna."""
        return self.max_linhas or max(1, tamanho_tela()[1] - self.y - 1)

    @property
    def colunas(self):
        """Quantas colunas o menu tem, aparecendo ou não."""
        return -(-len(self.itens) // self.linhas)

    @property
    def largura_coluna(self):
        """Largura de uma coluna: o maior item mais dois espaços."""
        return self.maior + 2

    @property
    def visiveis(self):
        """Quantas colunas aparecem: as que cabem da posição x até a borda (ao menos uma)."""
        limite = tamanho_tela()[0] if self.borda is None else self.borda
        cabem = (limite - self.x + 3) // self.largura_coluna
        return max(1, min(self.colunas, cabem))

    @property
    def tam_x(self):
        """Coluna onde termina a parte visível do menu."""
        return self.x + self.visiveis * self.largura_coluna - 2 if self.itens else self.x

    @property
    def tam_y(self):
        """Linha onde termina o menu."""
        return self.y + min(len(self.itens), self.linhas)

    # --- tela ---
    def posicao(self, i):
        """Coluna e linha da tela do item i, na parte que está visível."""
        return self.x + (i // self.linhas - self.topo) * self.largura_coluna, self.y + i % self.linhas

    def rola(self) -> bool:
        """Ajusta a primeira coluna visível para o item focado aparecer. Retorna True se ela mudou."""
        self.mede()
        antes, coluna = self.topo, self.idx // self.linhas
        if coluna < self.topo: self.topo = coluna
        elif coluna >= self.topo + self.visiveis: self.topo = coluna - self.visiveis + 1
        return self.topo != antes

    def mostra(self):
        """Desenha as colunas visíveis do painel. Os itens são completados com espaços, para a rolagem apagar o que havia antes."""
        self.rola()
        linhas = self.linhas
        self.tam_menu = ((self.x, self.y), (self.tam_x, self.tam_y))
        for col in range(self.topo, self.topo + self.visiveis):
            x = self.x + (col - self.topo) * self.largura_coluna
            for lin in range(min(len(self.itens), linhas)):
                i = col * linhas + lin
                dvcs.goToXY(x, self.y + lin)
                dvcs.write(str(self.itens[i]).ljust(self.maior) if i < len(self.itens) else " " * self.maior)
        self.pos_y = self.y + min(len(self.itens), linhas)

    def executa(self) -> tuple[bytes, str]:
        """Exibe o menu e aguarda a escolha do usuário.
        Retorna a tecla e o texto da opção escolhida.
        Com autoconfirma, o item único achado pela busca é devolvido com a tecla Enter.
        """
        self.mostra()
        while True:
            dvcs.goToXY(*self.posicao(self.idx))
            dvcs.sintetiza(str(self.itens[self.idx]))
            tecla = dvcs.dvcsLeTecla()
            if not self.navegar(tecla):
                return tecla, self.itens[self.idx]
            if self.confirma:
                self.confirma = False
                return dvcs.ENTER, self.itens[self.idx]
            if self.rola(): self.mostra()

    # --- navegação ---
    def navegar(self, tecla) -> bool:
        """Trata uma tecla: move o foco, ou alimenta a busca incremental."""
        n = len(self.itens)
        if n == 0:
            return False

        if tecla == dvcs.BAIXO:
            if self.idx < n - 1: self.idx += 1
            else: dvcs.sintBip()
        elif tecla == dvcs.CIMA:
            if self.idx > 0: self.idx -= 1
            else: dvcs.sintBip()
        elif tecla == dvcs.PAGEUP:
            self.idx = max(0, self.idx - 10)
        elif tecla == dvcs.PAGEDOWN:
            self.idx = min(n - 1, self.idx + 10)
        elif tecla == dvcs.ESQUERDA:
            self.idx = max(0, self.idx - self.linhas)  # uma coluna para a esquerda
        elif tecla == dvcs.DIREITA:
            self.idx = min(n - 1, self.idx + self.linhas)  # uma coluna para a direita
        elif tecla == dvcs.HOME:
            self.idx = 0
        elif tecla == dvcs.END:
            self.idx = n - 1
        else:
            return self._busca_incremental(tecla)
        return True

    def _busca_incremental(self, tecla):
        """Vai para o primeiro item que começa com o que foi digitado (letras e números, sem diferenciar maiúsculas e ignorando "_").
        As teclas seguidas em até um segundo formam a mesma busca. Bipa se não achar nada."""
        try:
            char = tecla.decode('ascii')
        except Exception:
            return False
        if not char.isalnum():
            return False

        agora = time.time()
        self.busca = char.lower() if (agora - self.tempo_tecla > 1.0) else self.busca + char.lower()
        self.tempo_tecla = agora
        por_posicao = self.por_posicao and self.busca.isdigit() and not any(c.isdigit() for v in self.itens for c in str(v))
        chaves = [[str(i + 1)] for i in range(len(self.itens))] if por_posicao else [[str(v).replace("_", "").lower(), *getattr(v, "outras_chaves", ())] for v in self.itens]  # um item pode ter outras chaves de busca além do que mostra
        achados = [i for i, ks in enumerate(chaves) if any(k.startswith(self.busca) for k in ks)]
        if not achados:
            dvcs.sintBip()
            return True  # letra digitável: sempre continua no menu, ache ou não
        self.idx = achados[0]
        if self.autoconfirma and len(achados) == 1:
            self.confirma = True
            self.busca, self.tempo_tecla = "", 0  # a próxima busca recomeça do zero (outro menu)
        return True


# --- teclas do sistema Dosvox ---
TECLAS_DO_SISTEMA = (("F8", "falaHora"), ("CONTROL_F8", "falaDia"))  # constante do dvcs -> função dele (o Ctrl+Alt+F9, do leitor de tela, o próprio dvcs já trata)
def tecla_do_sistema(tecla):
    """Se a tecla é de um recurso padrão dos programas do Dosvox (hora e dia), executa-o e devolve True."""
    for constante, funcao in TECLAS_DO_SISTEMA:
        if tecla == getattr(dvcs, constante, None) and hasattr(dvcs, funcao): getattr(dvcs, funcao)(); return True
    return False

# --- tela de duas listas dos jogos ---
LINHAS, TOPO = 20, 4  # linhas por coluna e primeira linha das listas
X_PARTES, X_FORMADOS, VAO = 5, 40, 3  # onde começam as listas (a dos formados anda para a direita se as partes precisarem) e o vão entre elas
LARGURA_TITULO = {"partes": 14, "formados": 16}  # "=== partes ===" e "=== FORMADOS ==="

class Menus:
    """A tela dos jogos: a lista das partes à esquerda e a dos formados à direita, cada uma um Menu.
    Os jogos usam os nomes partes, formados, idx_p, idx_f e foco, que aqui repassam para o painel certo."""
    def __init__(self, progresso):
        self.progresso = progresso
        self.rodada = progresso.atual
        auto = getattr(progresso, "auto_confirma", False)  # jogo pede confirmação automática da busca
        self.paineis = {lista: Menu(x, TOPO, linhas=LINHAS, autoconfirma=auto, por_posicao=True) for lista, x in (("partes", X_PARTES), ("formados", X_FORMADOS))}
        self.paineis["partes"].define(getattr(progresso, "exibe_partes", lambda: progresso.partes)())  # o jogo pode mostrar as partes de outro jeito (o criptograma, em números)
        self.paineis["formados"].define(progresso.exibe_formados())
        self.foco = "partes"
        t_p, t_f = len(self.partes), len(self.formados)
        # Define posição da mensagem de erro/sucesso para não sobrepor o menu
        self.pos_mensagem = 25 if t_p >= 20 or t_f >= 20 else max(t_p + 5, t_f + 5)

    # --- apelidos dos painéis ---
    @property
    def partes(self):
        return self.paineis["partes"].itens
    @partes.setter
    def partes(self, itens):
        self.paineis["partes"].define(itens)
    @property
    def formados(self):
        return self.paineis["formados"].itens
    @formados.setter
    def formados(self, itens):
        self.paineis["formados"].define(itens)
    @property
    def idx_p(self):
        return self.paineis["partes"].idx
    @idx_p.setter
    def idx_p(self, valor):
        self.paineis["partes"].idx = valor
    @property
    def idx_f(self):
        return self.paineis["formados"].idx
    @idx_f.setter
    def idx_f(self, valor):
        self.paineis["formados"].idx = valor

    # --- layout ---
    def _layout(self):
        """Posiciona os painéis. Cabendo tudo, as listas ficam inteiras (formados na coluna 40 ou logo depois das partes).
        Não cabendo, a que ocupa menos fica inteira, se couber em metade da tela, e a outra rola no que sobrar; senão, cada uma fica com metade.
        Cada lista tem ao menos a largura do seu título, para os títulos não se sobreporem."""
        largura_tela = tamanho_tela()[0]
        paineis = self.paineis
        for p in paineis.values(): p.mede()
        precisa = {k: max(p.colunas * p.largura_coluna, LARGURA_TITULO[k]) for k, p in paineis.items()}
        visiveis = {k: p.colunas for k, p in paineis.items()}
        espaco = largura_tela - X_PARTES + 1 - VAO
        if sum(precisa.values()) > espaco:
            metade = espaco // 2
            for k, outra in (("partes", "formados"), ("formados", "partes")):
                if precisa[k] <= metade: visiveis[outra] = max(1, (espaco - precisa[k]) // paineis[outra].largura_coluna)
                elif precisa[outra] > metade: visiveis[k] = max(1, metade // paineis[k].largura_coluna)
        partes, formados = paineis["partes"], paineis["formados"]
        x_minimo = X_PARTES + max(visiveis["partes"] * partes.largura_coluna, LARGURA_TITULO["partes"]) + VAO
        x_formados = max(X_FORMADOS, x_minimo)
        if x_formados + visiveis["formados"] * formados.largura_coluna - 1 > largura_tela:
            x_formados = max(x_minimo, largura_tela - visiveis["formados"] * formados.largura_coluna + 1)
        for k, x in (("partes", X_PARTES), ("formados", x_formados)):
            paineis[k].x = x
            paineis[k].borda = x + visiveis[k] * paineis[k].largura_coluna - 3  # a última coluna visível termina aqui

    # --- tela ---
    @property
    def painel(self):
        """O painel em foco. Qualquer foco que não seja "partes" vale como os formados (o Números usa outro nome, "FATORES", depois de uma jogada recusada)."""
        return self.paineis["partes" if self.foco == "partes" else "formados"]

    def posicionar_cursor(self):
        painel = self.painel
        if not painel.itens: return
        dvcs.goToXY(*painel.posicao(painel.idx))
        dvcs.sintetiza(str(painel.itens[painel.idx]))

    def mensagem(self, conteudo):
        dvcs.goToXY(1, self.pos_mensagem)
        dvcs.sintWriteln(conteudo)

    def mostrar(self):
        dvcs.clrScr()
        dvcs.goToXY(30, 1)
        dvcs.write(f"rodada {self.rodada}")  # Mostra rodada atual
        self._layout()
        largura_tela = tamanho_tela()[0]
        # --- DESENHO DAS DUAS LISTAS ---
        for titulo, lista in (("=== partes ===", "partes"), ("=== FORMADOS ===", "formados")):
            painel = self.paineis[lista]
            painel.mostra()
            dvcs.goToXY(painel.x, 2)
            dvcs.write(titulo[:largura_tela - painel.x + 1])
            if painel.colunas > painel.visiveis:  # lista rolando: diz quais itens aparecem
                primeira = painel.topo * LINHAS
                ultima = min(len(painel.itens), (painel.topo + painel.visiveis) * LINHAS)
                dvcs.goToXY(painel.x, 3)
                dvcs.write(f"{primeira + 1}-{ultima}/{len(painel.itens)}"[:largura_tela - painel.x + 1])
        self.posicionar_cursor()

    # --- teclas ---
    def navegar(self, tecla):
        if tecla == dvcs.TAB:
            self.foco = "formados" if self.foco == "partes" and self.formados else "partes"
            dvcs.sintetiza(self.foco)
        else: self.painel.navegar(tecla)

    def le_tecla(self):
        """Lê a próxima tecla; se a busca já escolheu sozinha o item, devolve ENTER no lugar."""
        painel = self.painel
        if painel.confirma:
            painel.confirma = False
            return dvcs.ENTER
        tecla = dvcs.dvcsLeTecla()
        while tecla_do_sistema(tecla): tecla = dvcs.dvcsLeTecla()  # F8 e Ctrl+F8 valem em qualquer jogo e não chegam a ele (o leitor de tela, Ctrl+Alt+F9, o próprio dvcs trata)
        return self.interativo() if tecla == getattr(dvcs, "F9", b"\x00C") else tecla

    def interativo(self):
        """F9: lista os comandos do painel em foco (o jogo os define em progresso.comandos) e devolve a tecla do escolhido,
        para o jogo tratá-la como se tivesse sido teclada. Sem comandos, ou com Esc, não devolve tecla nenhuma."""
        comandos = getattr(self.progresso, "comandos", lambda foco: [])(self.foco)
        if not comandos: return b""
        escolha = menu([f"{nome}: {o_que}" for nome, o_que, tecla in comandos], "Menu interativo")
        return comandos[escolha - 1][2] if escolha else b""


def menu_auto(opções, titulo="Menu", x=1, y=3):
    """Como menu(), mas com a busca incremental autoconfirmada: a letra que acha um item só já o escolhe. Devolve a posição (1...), ou 0 com Esc."""
    dvcs.clrScr()
    dvcs.sintWriteln(titulo)
    tecla, item = Menu(x, y, list(opções), autoconfirma=True).executa()
    return list(opções).index(item) + 1 if tecla == dvcs.ENTER else 0

def menu(opções, titulo="Menu", x=1, y=3):
    dvcs.popupMenuCria(x, y, x+40, len(opções)+2, 0)
    dvcs.sintWriteln(titulo)
    for op in opções:
        dvcs.popupMenuAdiciona("", op)
    return dvcs.popupMenuSeleciona()
