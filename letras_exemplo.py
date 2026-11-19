# Partes Únicos: letras_exemplo.py
# Copyright (C) 2026 Caio Gustavo Rodrigues Grizosto
# SPDX-License-Identifier: LGPL-3.0-only
# Este arquivo é software livre, sob a GNU Lesser General Public License, versão 3 (veja COPYING.LESSER e COPYING). Sem nenhuma garantia.
"""Letras Únicas sozinho, como exemplo de jogo construído sobre a API do Partes Únicos.
O programa completo (com Números, Palavras e Monta) tem o mesmo desenho: Tema, Partida, Rodada, Menus e Ranking."""
import dvcs, API, menus, letras, livre, ranking
def perfil():
    dvcs.sintWriteln("Qual o seu nome?")
    nome = dvcs.sintReadln()
    if nome: API.Perfil(nome).consulta("letras")
def jogo():
    dvcs.sintWriteln("Qual o seu nome?")
    nome = dvcs.sintReadln()
    if not nome: return
    while True:
        tema = letras.Tema()
        tema.config(nome, "letras", livre=True)
        if tema.cancelado: return
        dvcs.sintWriteln("Tecle l para tema livre ou outra tecla para escolher um tema.")
        if dvcs.dvcsLeTecla().decode().lower() == "l": tema.livre = True
        try: tema.carrega()
        except FileNotFoundError: return dvcs.sintWriteln("O arquivo do tema não foi encontrado.")
        if not tema.escolhido: return
        letras.jogar(tema, nome)
        dvcs.sintWriteln("Quer jogar novamente?")
        if dvcs.dvcsLeTecla().decode().lower() != "s": return
def ajuda():
    dvcs.sintWriteln("Tecle l para as instruções do tema livre, ou outra tecla para as do jogo.")
    if dvcs.dvcsLeTecla().decode("latin-1").lower() == "l": livre.instr()
    else: letras.instr()
def inicia():
    dvcs.setWindowTitle("Letras Únicas")
    while True:
        dvcs.sintWriteln("Qual sua opção? i instruções, c ranking, p perfil, j jogar, esc sair.")
        tecla = dvcs.dvcsLeTecla()
        if tecla == dvcs.ESC: return
        opcao = tecla.decode("latin-1").lower()
        if opcao == "i": ajuda()
        elif opcao == "c": ranking.consulta(letras.Tema(), "l")
        elif opcao == "p": perfil()
        elif opcao == "j": jogo()
dvcs.sintInic(0, "")
dvcs.sintWriteln("Letras Únicas, exemplo de jogo sobre a API do Partes Únicos.")
inicia()
