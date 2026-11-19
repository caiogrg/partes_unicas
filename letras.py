# Partes Únicos: letras.py
# Copyright (C) 2026 Caio Gustavo Rodrigues Grizosto
# SPDX-License-Identifier: LGPL-3.0-only
# Este arquivo é software livre, sob a GNU Lesser General Public License, versão 3 (veja COPYING.LESSER e COPYING). Sem nenhuma garantia.
"""Módulo principal do jogo Letras Únicas, incluindo funções auxiliares e o laço principal do programa."""
from carrega_letras import Tema, Jogo, Rodada
import dvcs, API, livre
from collections import Counter
from menus import Menus, menu

TOLERANCIA = 1  # difícil: sobra além do mínimo possível + tolerância reinicia a rodada
TOLERANCIA_RODADAS = {1: 1, 2: 0, 3: 0}  # difícil: rodadas além do mínimo que ainda contam como eficiente, por nível (o nível 2 tem letras e palavras compatíveis)


def instr():
    dvcs.sintWriteln ("O JOGO: Complete palavras do tema com as letras disponiveis.")
    dvcs.sintWriteln ("Dicas: numero, letras ou frase. Use 'setas' e 'Enter'.")
    dvcs.sintWriteln ("NIVEL FACIL: Escreva palavras de uma vez.")
    dvcs.sintWriteln ("Letras esgotadas? Rodada nova, letras de volta!")
    dvcs.sintWriteln ("NIVEL MEDIO: Uma letra por palavra por rodada.")
    dvcs.sintWriteln ("Sobra de letras nao afeta.")
    dvcs.sintWriteln ("NIVEL DIFICIL: Uma letra por palavra por rodada.")
    dvcs.sintWriteln ("Sobrar muitas letras? Rodada pode reiniciar!")
    dvcs.sintWriteln("Criptograma: as letras aparecem como números; digite o número ou a letra")
    dvcs.sintWriteln ("Tecle f9 nos menus de letras e palavras para opções interativas.")
    dvcs.sintWriteln ("Aperte Enter para continuar...")
    dvcs.sintReadKey()
    return API.menu_ajuda()


# --- progressão do difícil ---
def rodadas_minimas(palavras):
    """O menor número de rodadas que a janela admite: cada letra entra uma vez por rodada, então a mais comum precisa de uma rodada por palavra em que aparece."""
    return max(Counter(letra for p in palavras for letra in p.letras_unicas).values(), default=0)

def janela_eficiente(partida, rodadas):
    """Difícil: a janela da sessão fechou no mínimo de rodadas, mais a tolerância do nível. Usar a letra mais comum desde a primeira rodada é o que dá o mínimo."""
    janela = partida.palavras[partida.inicio:min(partida.limite, len(partida.palavras))]
    return rodadas <= rodadas_minimas(janela) + TOLERANCIA_RODADAS[partida.tema.nivel]

def zera_perfil(partida, nome):
    """Difícil 3 eficiente zera o jogo: o perfil do Letras é apagado, e na próxima partida o jogador escolhe dificuldade e nível."""
    partida.perfil.pop("letras", None)
    API.salva_perfil(nome, partida.perfil)


# --- jogo ---
def jogar(tema, nome):
    """Inicia o jogo com o tema e nome do jogador especificados, gerenciando o laço
    principal (rodada a rodada) e a interação com o usuário.
    """
    if tema.livre: return livre.jogar(tema, nome)
    avanca_fase = False  # Se True, avança a dificuldade/nivel do tema no fim da seção.
    p_escolhido = None  # a letra escolhida nas partes, à espera da palavra
    partida = Jogo(nome, tema).carrega(jogo="letras")
    dvcs.sintWriteln("Escreva as palavras do tema com as letras disponíveis.")
    progresso = Rodada(partida).carrega().inicia()
    interface = Menus(progresso)
    partida.iniciar()
    while not partida.vitoria():
        progresso.inicia()  # continua as palavras pendentes (letras renovadas) ou carrega o próximo lote
        dvcs.sintetiza(f"rodada {progresso.atual}")
        interface = Menus(progresso)  # Atualiza o menu a cada rodada, com o lote e palavras da vez.
        interface.mensagem(f"{progresso.quantas_letras} letras para {progresso.quantas_palavras} palavras.")
        if tema.cripto: menu(progresso.tabela(), "Veja o número representado por cada letra e tecle Enter")
        if tema.dificuldade in ["m", "d"]:
            limite_letras = progresso.limite_letras
            if tema.nivel > 1: dvcs.sintWriteln(f"{limite_letras} letras por palavra")
            else: 
                if progresso.atual == 1: dvcs.sintWriteln("Use letras em todas as palavras da rodada.")

        # Inicia a rodada
        while progresso.letras:
            interface.mostrar()
            tecla = interface.le_tecla()
            if tecla == dvcs.ESC:
                progresso.salva(); partida.salva(); API.salva_perfil(nome, partida.perfil)
                return
            elif tecla == dvcs.BACKSPACE:
                interface.mensagem("Rodada reiniciada." if progresso.desfaz() else "A rodada ainda está no início.")
                interface = Menus(progresso)  # menu e letras como no início da rodada
                p_escolhido = None
                continue
            if tecla == b" ": interface.mensagem(f"{len(progresso.letras)} letras para {progresso.quantas_palavras} palavras." + (f" {progresso.limite_letras} letras por palavra." if tema.dificuldade in ["m", "d"] and tema.nivel > 1 else ""))

            # Funções interativas para mostrar informações sobre a palavra selecionada
            if tecla == dvcs.F2: # permite explorar a palavra selecionada, letra por letra com as setas.
                if interface.foco != "formados": interface.mensagem("Selecione uma palavra para explorar.")
                else:
                    palavra_selecionada = interface.formados[interface.idx_f]
                    dvcs.sintEdita(palavra_selecionada, dvcs.whereX(), dvcs.whereY(), 255, False)
            elif tecla == dvcs.F5: # Mostra a palavra completa do tema.
                if interface.foco != "formados": interface.mensagem("Selecione uma palavra para mostrar.")
                else:
                    idx = interface.idx_f
                    interface.mensagem(progresso.dica(idx))
                continue
            elif tecla == dvcs.F6:  # Mostra o número de letras reveladas da palavra selecionada.
                if interface.foco != "formados": interface.mensagem("Selecione uma palavra para mostrar.")
                else:
                    idx = interface.idx_f
                    interface.mensagem(str(progresso.palavras[idx].letras_reveladas))
                continue
            elif tecla == dvcs.F7:  # repõe a palavra selecionada como estava no início da rodada
                if interface.foco != "formados": interface.mensagem("Selecione uma palavra para repor.")
                else:
                    idx = interface.idx_f
                    interface.mensagem("Palavra reposta, letras devolvidas!" if progresso.repoe(idx) else "A palavra ainda está como no início da rodada.")
                    interface = Menus(progresso)
                    interface.foco, interface.idx_f = "formados", min(idx, len(progresso.palavras) - 1)
                continue

            # Verifica se a palavra selecionada é formada com as letras disponíveis
            elif tecla == dvcs.ENTER:
                    if interface.foco == "partes": # Seleciona o fator do menu
                            p_escolhido = progresso.partes[interface.idx_p]
                            interface.foco = "formados" # Muda foco para o menu de formados.
                            continue
                    else:
                        if p_escolhido is None: info = "Selecione uma letra para formar a palavra."
                        else: sucesso, info = progresso.verifica(interface.idx_p, interface.idx_f)
                        interface.mensagem(info)
                        p_escolhido = None
                        interface.idx_p = 0
            else: 
                interface.navegar(tecla)
                if interface.foco == "partes": p_escolhido = None  # voltou às partes: a escolha anterior não vale mais
                continue

            # Verifica se há letras sobrando, permite avançar fas ee encerra a rodada se não houver letras úteis
            sobra = progresso.letras - progresso.letras_uteis()
            interface.mensagem(f"sobra {len(sobra)} e letras {len(progresso.letras)}")
            if sobra == progresso.letras: break  # Se não houver letras úteis, encerra a rodada
            interface = Menus(progresso)  # Atualiza o menu a cada rodada, com o lote e palavras da vez.
        # Fim da rodada
        excesso = len(progresso.letras) > progresso.sobra_minima + TOLERANCIA  # sobrou mais do que o inevitável (+ tolerância)
        sobrou = set()
        if tema.dificuldade == "d" and excesso and progresso.letras:  # difícil: a rodada recomeça, com as palavras como estavam no início dela
            interface.mensagem("Sobrou muitas letras. Vai ter que jogar esta rodada novamente!")
            progresso.desfaz()
            continue
        elif tema.dificuldade == "m": 
            if excesso: interface.mensagem("Cuidado com as sobras!")
            elif progresso.atual == 1: avanca_fase = True  # médio: se não sobrou nada na primeira rodada, avança para a próxima fase.
            elif tema.nivel == 1:
                todas_iniciadas = all(p.iniciada for p in progresso.palavras)
                if todas_iniciadas:
                    if progresso.atual == 1: avanca_fase = True  # médio: se não sobrou nada na primeira rodada, avança para a próxima fase.
                else: interface.mensagem("Use letras em todas as palavras.")
        if tema.dificuldade == "d" and tema.nivel < 3 and progresso.letra_comum() in progresso.letras: interface.mensagem("Use também as letras mais comuns!")  # sobrou a segunda mais comum: o difícil pede usá-la
        progresso.atual += 1
        partida.letras = progresso.letras_uteis(partida.letras)  # Atualiza as letras úteis disponíveis na partida
        sobrou = progresso.letras_inicial - partida.letras
        progresso = Rodada(partida, progresso.atual)  # Próxima rodada: quem decide o que entra é inicia()
        if sobrou: progresso.inicia().acrescenta()  # médio/difícil: letras sem uso na rodada anterior liberam a próxima palavra
                
    # Fim da sessão
    if tema.dificuldade == "d": avanca_fase = janela_eficiente(partida, progresso.atual - 1)  # antes de partida.inicio avançar: a janela é a que acabou de ser jogada
    if partida.limite < len(tema.base):
        partida.inicio = partida.limite  # Avança para o fim da janela concluída (não para proxima: o lote pode ter passado do limite).
    else: partida.inicio = 0  # Reinicia o início da próxima partida do tema, se todas as palavras já foram jogadas.
    (partida.jogos or {}).get(tema.escolhido, {}).pop("rodada_atual", None)  # a próxima janela recomeça na rodada 1
    partida.salva("letras")
    zerou = avanca_fase and tema.dificuldade == "d" and tema.nivel == 3  # difícil 3 eficiente: o jogo foi zerado
    if zerou:
        interface.mensagem("Parabéns! Você zerou o Letras Únicos! Na próxima partida, escolha a dificuldade e o nível que quiser.")
        zera_perfil(partida, nome)
    elif avanca_fase:
        if tema.dificuldade == "m": 
            if tema.nivel <= 2: tema.nivel += 1
            else: tema.dificuldade = "d"; tema.nivel = 1
        elif tema.dificuldade == "d": tema.nivel += 1
    erros = sum(partida.erros.values())
    API.fim_de_sessao(interface, "letras", partida.letras_total, progride=not zerou, ranking_path="letras.json", aviso=f"Você cometeu {erros} erro{'s' if erros != 1 else ''}." if erros else "Sem nenhum erro!")