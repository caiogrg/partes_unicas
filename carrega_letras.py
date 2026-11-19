# Partes Únicos: carrega_letras.py
# Copyright (C) 2026 Caio Gustavo Rodrigues Grizosto
# SPDX-License-Identifier: LGPL-3.0-only
# Este arquivo é software livre, sob a GNU Lesser General Public License, versão 3 (veja COPYING.LESSER e COPYING). Sem nenhuma garantia.
"""Módulo de carregamento do jogo Letras Únicas: classe Tema com normalização."""
import re, unicodedata, dvcs, menus, API
from copy import deepcopy
from collections import Counter

MAX_LETRAS = 20  # teto de letras (partes) por rodada
POUCAS_PALAVRAS = 10  # "faltam poucas palavras": a janela da partida ou o tema está acabando


def desacentuar(texto):
    """Remove acentos e maiúsculas de uma palavra."""
    nfkd_form = unicodedata.normalize('NFKD', texto)
    return "".join([c.lower() for c in nfkd_form if not unicodedata.combining(c)])

def extrair_caracteres_unicos(palavra):
    """Extrai caracteres alfabéticos únicos e desacentuados de uma palavra."""
    palavra_desacentuada = desacentuar(palavra) 
    letras_apenas = re.sub(r'[^a-z]', '', palavra_desacentuada)
    return set(letras_apenas)

class Palavra:
    """Representa uma palavra do jogo, seu estado de progresso e dica."""
    @property
    def formacao(self):
        """Retorna a palavra em formação como uma string."""
        return ''.join(self.palavra_em_formacao)
    @property
    def iniciada(self):
        """Indica se a palavra já teve alguma letra revelada."""
        return self.letras_reveladas > 0
    @property
    def completa(self):
        """Verifica se a palavra está completa (sem letras faltantes)."""
        return not self.letras_faltantes
    
    def __init__(self, palavra, posicao):
        self.posicao = posicao
        palavra_completa = palavra
        dica = palavra  # Inicialmente, a dica é a própria palavra
        if any(c in palavra for c in ":="):
            partes_palavra = re.split(r"[:=]+", palavra, maxsplit=1)  # Separa a palavra e a dica, se houver
            if len(partes_palavra) > 1: palavra_completa, dica = (p.strip() for p in partes_palavra)
        self.palavra_completa = palavra_completa
        self.dica = dica
        letras_originais_desacentuadas = extrair_caracteres_unicos(palavra_completa)
        self.letras_unicas = letras_originais_desacentuadas
        self.palavra_em_formacao = []
        for char_original in palavra_completa:
            if char_original.isalpha():
                self.palavra_em_formacao.append('_')
            else:
                self.palavra_em_formacao.append(char_original)
        self.letras_faltantes = set(letras_originais_desacentuadas)
        self.letras_reveladas = 0

    def aplicar_letra(self, letra_jogada, repete=True):
        """Aplica a letra na palavra se ela existir e atualiza o progresso,
        respeitando os acentos da palavra original.
        Retorna True se a letra foi aplicada, False caso contrário (já usada ou não existe).
        """
        # Se a letra jogada não está nas letras únicas da palavra, não pode ser aplicada.
        if letra_jogada not in self.letras_unicas: return False
        # Verifica se todas as ocorrências desta letra já foram reveladas na palavra.
        todas_ocorrencias_reveladas = True
        for i, char_original in enumerate(self.palavra_completa):
            if desacentuar(char_original) == letra_jogada:
                if self.palavra_em_formacao[i] == '_': # Se ainda há um '_' para essa letra
                    todas_ocorrencias_reveladas = False
                    break
        if todas_ocorrencias_reveladas:
            return False # A letra já está toda revelada nesta palavra.
        letra_aplicada_com_sucesso = False

        # Percorre a palavra completa e aplica a letra onde for correspondente e ainda não revelado.
        for i, char_original in enumerate(self.palavra_completa):
            if desacentuar(char_original) == letra_jogada:
                if self.palavra_em_formacao[i] == '_':
                    self.palavra_em_formacao[i] = char_original
                    self.letras_reveladas += 1
                    letra_aplicada_com_sucesso = True
                    if not repete: break  # Se não deve repetir, para após a primeira aplicação
        if letra_aplicada_com_sucesso:
            # Se a letra foi aplicada, remove ela das letras faltantes da palavra, a menos que ainda reste uma ocorrência a revelar (repete=False).
            if not any(desacentuar(c) == letra_jogada and self.palavra_em_formacao[i] == '_' for i, c in enumerate(self.palavra_completa)):
                self.letras_faltantes.discard(letra_jogada)
            return True
        else:
            return False

    def retira_letra(self, letra, todas=False):
        """Inversa de aplicar_letra: tira da palavra a primeira ocorrência revelada da letra (todas, com todas=True)
        e a devolve às faltantes. Retorna True se havia algo a tirar, False se a letra não estava revelada nesta palavra."""
        retirada = False
        for i, char_original in enumerate(self.palavra_completa):
            if desacentuar(char_original) == letra and self.palavra_em_formacao[i] != '_':
                self.palavra_em_formacao[i] = '_'
                self.letras_reveladas -= 1
                retirada = True
                if not todas: break
        if retirada: self.letras_faltantes.add(letra)
        return retirada


class Cripto(str):
    """Uma letra que o menu mostra como número (o criptograma): o str() é o número, e a letra também acha o item na busca."""
    def __new__(cls, letra, numero):
        item = super().__new__(cls, letra)
        item.numero, item.outras_chaves = numero, (letra,)
        return item
    def __str__(self): return str(self.numero)


class Tema(API.Tema):
    """Gerencia o tema do jogo: a lista de palavras normalizadas (base), as letras únicas
    necessárias pra formar todas elas (partes), e a dica opcional de cada palavra."""
    def __init__(self, escolhido =""):
        super().__init__(escolhido)
        self.livre = False
        self.cripto = False  # criptograma: o menu mostra números no lugar das letras; a dificuldade (f/m/d) diz como numerar
    tem_cripto = True  # o Monta, que herda este Tema, não tem criptograma
    def dif(self, dificuldade=None):
        """Pergunta F, M ou D (ou C, criptograma: aí pergunta a dificuldade do criptograma). Com `dificuldade`, não pergunta."""
        self.cripto = False
        if dificuldade in ["f", "m", "d"] or not self.tem_cripto: return super().dif(dificuldade)
        dvcs.sintWriteln("Tecle F para fácil, M para médio, D para difícil ou C para criptograma.")
        tecla = dvcs.dvcsLeTecla()
        if tecla == dvcs.ESC:
            self.cancelado = True
            return self
        tecla = tecla.decode("latin-1").lower()
        if tecla not in ("f", "m", "d", "c"):
            opcao = menus.menu(["f- Fácil", "m- Médio", "d- Difícil", "c- Criptograma", "ESC- voltar"], "Escolha a dificuldade do jogo")
            tecla = "fmdc"[opcao - 1] if 0 < opcao < 5 else ""
            if not tecla:
                self.cancelado = True
                return self
        if tecla != "c":
            self.dificuldade = tecla
            return self
        self.cripto = True
        dvcs.sintWriteln("Criptograma.")
        return super().dif()
    def do_perfil(self, dados):
        """O perfil lembra se o jogador joga o criptograma."""
        self.cripto = bool(dados.get("cripto"))
    def para_perfil(self): return {"cripto": True} if self.cripto else {}
    def carrega(self, arquivo="letras.pal"):
        """Carrega o tema, normaliza as palavras (removendo acentos e caracteres especiais),
                separa as dicas e monta o pool de letras únicas (partes) e a base do jogo."""
        # Se self.livre for True, não há arquivo de tema: as palavras vêm do dicionário do Dosvox (livre.py) e as partes são o alfabeto.
        # Define self.temas e self.escolhido.
        if self.livre:
            from string import ascii_lowercase
            self.escolhido, self.temas, self.palavras, self.partes = "livre", {"livre": []}, [], set(ascii_lowercase)
            return
        super().carrega(arquivo)
        if not self.escolhido or self.escolhido not in self.temas: return
        self.palavras = [Palavra(item.strip(), indice) for indice, item in enumerate(self.temas[self.escolhido]) if item.strip()]
        partes = set()
        for palavra in self.palavras:
            self.base.append(palavra.palavra_completa)
            partes.update(palavra.letras_unicas)
        self.partes = sorted(partes)


class Jogo(API.Jogo):
    """Gerencia o estado global da partida de Letras Únicas."""
    @property
    def partes(self):
        return sorted(self.letras)
    @partes.setter
    def partes(self, value):
        pass  # Mantém compatibilidade com a API, mas não permite definir partes diretamente; use self.letras.
    @property
    def proxima(self):
        return self.cursor
    @proxima.setter
    def proxima(self, valor):
        self.cursor = valor
    conta_erros = True  # o Letras conta e guarda os erros; os jogos que herdam (Monta, Tema Livre) desligam
    def __init__(self, nome, tema_selecionado=None):
        super().__init__(nome, tema_selecionado)
        self.perfil = self.tema.cria_perfil(self.jogador)  # o perfil do jogo (cada Tema diz qual classe)
        self.palavras = deepcopy(self.tema.palavras)
        self.letras = set(self.tema.partes)
        self.letras_total = 0
        self.erros = Counter()  # erros da sessão por tipo (dica, inválida, repetida, máximo)
        self.limite = self.tema.nivel * 10  # Limite de palavras por partida

    def vitoria(self):
        return super().vitoria() or set(self.base[self.inicio:self.limite]) <= set(self.formados)
    def numero_cripto(self, letra):
        """Criptograma médio: o número fixo da letra na partida, sua posição entre as letras das palavras da partida (em ordem).
        Uma letra de palavra que entrou além do limite ganha o próximo número, e o conserva."""
        if not hasattr(self, "cripto_letras"): self.cripto_letras = sorted({l for p in self.palavras[self.inicio:self.limite] for l in p.letras_unicas})
        if letra not in self.cripto_letras: self.cripto_letras.append(letra)
        return self.cripto_letras.index(letra) + 1

    def carrega(self, jogo="letras"):
        """Carrega o estado da partida a partir do save, se houver um save para o tema escolhido."""
        super().carrega(jogo)
        self.limite += self.inicio  # Ajusta o limite de palavras com base na posição inicial da partida
        if self.dados and "letras_total" in self.dados: self.letras_total = self.dados["letras_total"]
        if self.dados and "rodada_atual" in self.dados: self.erros.update(self.dados.get("erros", {}))  # sessão em andamento: os erros continuam (o save da sessão concluída é só registro)
        return self

    def salva(self, jogo="letras"):
        """Salva o estado atual da partida em "<jogador>.json", com os erros da sessão como registro (não entram no ranking nem na progressão)."""
        if self.conta_erros:
            if not self.jogos: self.jogos = {}
            self.jogos.setdefault(self.tema.escolhido, {})["erros"] = dict(self.erros)
        super().salva(jogo)


class Rodada(API.Rodada):
    """Gerencia a rodada atual: as palavras em jogo e as letras únicas disponíveis.
    A rodada é de LETRAS, não de palavras: ela termina quando as letras acabam (ou quando as
    palavras se formam), mas as palavras já liberadas continuam em jogo até serem formadas.
    Por isso o __init__ NÃO carrega palavras — só inicia() decide, no começo de cada rodada:
      - se ainda há palavras liberadas e incompletas (pendentes), elas continuam, com o
        progresso que tinham, e as letras são renovadas a partir do que falta nelas;
      - se não há pendentes, as palavras seguintes são carregadas do tema (_carrega_palavras).
    Pendentes não precisam de estado extra: são as palavras entre partida.inicio e
    partida.proxima que ainda não estão em partida.formados (a única fonte de certeza).
    """
    auto_confirma = True  # Se True, a busca incremental confirma automaticamente se só houver um item encontrado.

    # Atributos de instância (PROPRIEDADES):
    @property
    def partes(self):
         return sorted(self.letras)
    @partes.setter
    def partes(self, value):
        pass  # Mantém compatibilidade com a API, mas não permite definir partes diretamente; use self.letras.
    @property
    def limite_letras(self):
        """Letras que cada palavra pode revelar na rodada: sem limite no fácil e no médio nível 1 (o tamanho da maior palavra);
        a partir do médio nível 2 e no difícil, o valor da rodada (atual). Sem palavras em jogo, 0."""
        if not self.palavras: return 0
        tema = self.partida.tema
        if tema.dificuldade == "f" or (tema.dificuldade == "m" and tema.nivel == 1): return max(len(p.palavra_completa) for p in self.palavras)
        return self.atual
    @property
    def quantas_letras(self):
        """Máximo de letras que ainda podem ser aplicadas nas palavras em jogo: cada letra serve uma vez."""
        return self.aproveitamento(self.palavras, self.letras)
    @property
    def quantas_palavras(self):
        """Número de palavras em jogo que ainda podem receber letras (não estão completas)."""
        limite = self.limite_letras
        return len(self.palavras) if any(p.letras_reveladas < limite for p in self.palavras) else 0

    def aproveitamento(self, palavras, letras):
        """Máximo de letras que ainda podem ser aplicadas nessas palavras: cada letra serve uma vez
        e cada palavra aceita até (limite_letras - reveladas) letras. É um emparelhamento de letras
        com palavras (aumenta caminhos), e já conta letras raras e letras que completam várias
        palavras sem precisar de Counter nem de regras especiais.
        """
        limite = self.limite_letras
        vagas = [max(0, limite - p.letras_reveladas) for p in palavras]
        recebidas = [[] for _ in palavras]  # letras já encaixadas em cada palavra
        def encaixa(letra, vistas):
            for i, palavra in enumerate(palavras):
                if letra not in palavra.letras_faltantes or i in vistas: continue
                vistas.add(i)
                if len(recebidas[i]) < vagas[i]:
                    recebidas[i].append(letra)
                    return True
                for outra in recebidas[i]:  # palavra cheia: tenta realocar uma das letras dela
                    if encaixa(outra, vistas):
                        recebidas[i].remove(outra)
                        recebidas[i].append(letra)
                        return True
            return False
        return sum(encaixa(letra, set()) for letra in letras)

    def _estende_janela(self):
        """Faltando poucas palavras para o fim do tema, a janela da partida vai até o fim dele: as últimas palavras entram na mesma partida."""
        partida = self.partida
        if len(partida.palavras) - partida.proxima < POUCAS_PALAVRAS: partida.limite = len(partida.palavras)

    def acrescenta(self):
        """Médio e difícil: chamada no começo da rodada que veio depois de uma com letras sem uso;
        tenta liberar a próxima palavra do tema (uma por chamada). Ela entra se:
          - traz exatamente uma letra nova (a rodada cresce aos poucos), ou
          - as letras não passam das palavras e a janela da partida ou o tema está acabando
            (faltam POUCAS_PALAVRAS palavras ou menos).
        Não entra se não traz letra nova, nem se estourar as 20 letras da rodada."""
        partida = self.partida
        if partida.tema.dificuldade == "f": return
        self._estende_janela()
        formadas = set(partida.formados)
        while partida.proxima < min(partida.limite, len(partida.palavras)) and partida.palavras[partida.proxima].palavra_completa in formadas:
            partida.proxima += 1  # palavras já formadas: só avança
        if partida.proxima >= min(partida.limite, len(partida.palavras)): return
        palavra = partida.palavras[partida.proxima]
        novas_letras = palavra.letras_faltantes - self.letras
        if not novas_letras or len(self.letras | novas_letras) > MAX_LETRAS: return
        perto_do_fim = partida.limite - partida.proxima <= POUCAS_PALAVRAS or len(partida.palavras) - partida.proxima <= POUCAS_PALAVRAS
        if len(novas_letras) == 1 or (len(self.letras) <= len(self.palavras) and perto_do_fim):
            self.letras |= novas_letras
            self._entra(palavra)
            partida.letras_total += len(palavra.letras_unicas)
            partida.proxima += 1
            self.inicial.append(deepcopy(palavra)); self.letras_inicial |= novas_letras  # o melhor jogo possível passa a contar esta palavra
            self.sobra_minima = len(self.letras_inicial) - self.aproveitamento(self.inicial, self.letras_inicial)

    def repoe(self, indice):
        """F7: devolve uma palavra ao estado do início da rodada. As letras gastas nela voltam ao banco.
        Retorna True se algo mudou, False se a palavra já estava como no início."""
        atual = self.palavras[indice]
        original = next((p for p in self.inicial if p.posicao == atual.posicao), None)
        if original is None or atual.formacao == original.formacao: return False
        self.letras |= original.letras_faltantes - atual.letras_faltantes  # letras reveladas desde o início
        if atual.completa and atual.palavra_completa in self.partida.formados: self.partida.formados.remove(atual.palavra_completa)
        self.partida.palavras[original.posicao] = deepcopy(original)
        self.palavras[indice] = deepcopy(original)
        self.formados[indice] = original.formacao if original.iniciada else original.dica
        return True

    def desfaz(self):
        """Devolve a rodada ao estado do começo dela: palavras (inclusive as acrescentadas ou completas),
        menu e letras. Retorna True se houve algo a desfazer, False se já estava no estado inicial.
        """
        if [p.formacao for p in self.palavras] == [p.formacao for p in self.inicial] and self.letras == self.letras_inicial: return False
        for palavra in self.inicial:
            self.partida.palavras[palavra.posicao] = deepcopy(palavra)
            if palavra.palavra_completa in self.partida.formados: self.partida.formados.remove(palavra.palavra_completa)
        self.palavras, self.formados = [], []
        for palavra in self.inicial: self._entra(palavra)  # menu como no início da rodada
        self.letras = set(self.letras_inicial)  # e as mesmas letras (inclusive as de distração do fácil)
        return True

    def __init__(self, partida, valor_rodada=1):
        super().__init__(partida, valor_rodada)
        self.formados = []
        self.letras = set()
        self.palavras = []
        self.iniciada = False
        self.sobra_minima = 0  # letras que sobrariam mesmo jogando o melhor possível (calculada em inicia)
        self.inicial, self.letras_inicial = [], set()  # palavras e letras como estavam no começo da rodada (mais as acrescentadas)
        dados_perfil = partida.perfil.get("letras", {})
        self.max = min(dados_perfil.get("max_rodada", 0), MAX_LETRAS)

    def inicia(self):
        """Prepara palavras e letras desta rodada (uma vez só): continua as pendentes ou
        carrega o próximo lote."""
        if self.iniciada: return self
        self.iniciada = True
        pendentes = self.pendentes()
        if pendentes:
            for palavra in pendentes:
                self._entra(palavra)
                self.letras.update(palavra.letras_faltantes)  # letras de volta, só as que ainda faltam
        else:
            self._carrega_palavras()
        self.inicial, self.letras_inicial = deepcopy(self.palavras), set(self.letras)
        self.sobra_minima = len(self.letras) - self.aproveitamento(self.inicial, self.letras_inicial)
        return self

    def letra_comum(self):
        """A segunda letra mais comum entre as que faltam nas palavras do início da rodada (a "comum" do Scriptvox): o difícil pede para usá-la, além da mais comum.
        Retorna "" se não houver (todas as letras faltam no mesmo número de palavras)."""
        contagem = Counter(letra for palavra in self.inicial for letra in palavra.letras_faltantes)
        valores = sorted(set(contagem.values()), reverse=True)
        return min(l for l, n in contagem.items() if n == valores[1]) if len(valores) > 1 else ""

    def pendentes(self):
        """Palavras já liberadas (de partida.inicio até partida.proxima) e ainda não formadas."""
        formadas = set(self.partida.formados)
        return [p for p in self.partida.palavras[self.partida.inicio:self.partida.proxima]
                if p.palavra_completa not in formadas]

    def _entra(self, palavra):
        """Coloca uma cópia da palavra em jogo e a sua exibição no menu (dica, ou o que já foi formado)."""
        self.palavras.append(deepcopy(palavra))
        self.formados.append(palavra.formacao if palavra.iniciada else palavra.dica)  # com letra revelada, mostra a formação atual; senão, a dica

    def _carrega_palavras(self):
        """Carrega o lote de palavras e letras únicas, respeitando o limite máximo de letras."""
        # Carrega palavras do tema, respeitando o limite de letras únicas por rodada (self.max).
        partida = self.partida
        formadas = set(partida.formados)
        idx = partida.proxima
        self._estende_janela()
        janela = min(partida.limite, len(partida.palavras))
        n_letras_palavra1 = None  # letras únicas da 1ª palavra realmente carregada (só vale no fácil)
        for i in range(idx, janela):
            palavra = partida.palavras[i]
            if palavra.palavra_completa in formadas: continue  # Pula palavras já formadas
            if n_letras_palavra1 is None: n_letras_palavra1 = len(palavra.letras_unicas)
            if len(self.palavras) > len(self.letras): break
            letras_atuais = set(palavra.letras_faltantes)
            novas_letras = letras_atuais - self.letras
            todas_letras = self.letras | novas_letras
            limite = self.max + n_letras_palavra1 if partida.tema.dificuldade == "f" else MAX_LETRAS

            # Se o número de letras únicas exceder o limite, remove as letras excedentes do conjunto de novas letras.
            if len(todas_letras) > limite:
                excesso = len(todas_letras) - limite
                lista_letras = list(novas_letras)
                del lista_letras[-excesso:]  # Remove as letras excedentes do conjunto de novas letras
                novas_letras = set(lista_letras)
                self.letras.update(novas_letras)
                if partida.tema.dificuldade == "f":  # o max só mede o limite do fácil; no médio e no difícil o teto é MAX_LETRAS
                    self.max = min(self.max + 1, MAX_LETRAS)
                    partida.perfil.setdefault("letras", {})["max_rodada"] = self.max
                break
            # Se o número de letras únicas não exceder o limite, adiciona todas as novas letras ao conjunto de letras disponíveis.
            self.letras.update(novas_letras)
            self._entra(palavra)
            partida.letras_total += len(self.palavras[-1].letras_unicas)
            partida.proxima = i + 1

    def verifica(self, idx_p, idx_f):
        """Verifica se a letra selecionada (idx_p) forma a palavra selecionada (idx_f)."""
        if idx_p >= len(self.partes) or idx_f >= len(self.palavras):
            return False, "Índice fora do intervalo."
        letra_selecionada = self.partes[idx_p]
        palavra_selecionada = self.palavras[idx_f]
        limite = self.limite_letras
        if palavra_selecionada.letras_reveladas >= limite and len(self.letras) > 1:  # a última letra ignora o limite: pode completar uma palavra maior
            self.partida.erros["máximo"] += 1
            return False, f"Esta palavra já atingiu o limite de {limite} letras."
        if palavra_selecionada.aplicar_letra(letra_selecionada):
            palavra_formada = palavra_selecionada.formacao
            info = palavra_formada
            self.formados[idx_f] = palavra_formada  # Atualiza a palavra formada na lista de formados
            if len(self.letras_inicial) > 1: self.letras.discard(letra_selecionada)  # Remove a letra selecionada das partes disponíveis
            self.partida.palavras[palavra_selecionada.posicao] = palavra_selecionada  # Atualiza a palavra na lista de palavras da partida
            if palavra_selecionada.completa:
                if self.partida.tema.dificuldade == "f":
                    self.letras.update(palavra_selecionada.letras_unicas)  # Recoloca as letras da palavra formada de volta às partes
                    del self.palavras[idx_f]  # Remove a palavra formada da lista de palavras restantes
                    del self.formados[idx_f]  # Remove a palavra formada da lista de formados
                    info += " formada, letras devolvidas!"
                    if self.partida.tema.nivel == 1: 
                        self.letras = self.letras_uteis()  # Atualiza as letras úteis disponíveis
                else: info += " formada!"
                self.partida.formados.append(palavra_formada)  # Adiciona a palavra formada à lista de palavras formadas na partida
            return True, info
        elif letra_selecionada in palavra_selecionada.letras_unicas:  # a letra é da palavra e já foi toda revelada
            self.partida.erros["repetida"] += 1
            return False, "Esta letra já existe na palavra!"
        else:
            self.partida.erros["inválida"] += 1
            return False, "Esta letra não forma esta palavra!"
    def dica(self, idx):
        """F5: a palavra completa do tema; ver a dica conta como erro."""
        self.partida.erros["dica"] += 1
        return self.palavras[idx].palavra_completa

    # --- criptograma ---
    def numero(self, letra):
        """O número da letra no criptograma: fácil, a posição no alfabeto; médio, a posição entre as letras da partida; difícil, entre as letras da rodada."""
        dificuldade = self.partida.tema.dificuldade
        if dificuldade == "f": return ord(letra) - 96
        if dificuldade == "m": return self.partida.numero_cripto(letra)
        return sorted(self.letras_inicial | self.letras).index(letra) + 1
    def exibe_partes(self):
        """As letras do menu: no criptograma, cada uma aparece como o seu número (e a letra também a acha)."""
        return [Cripto(letra, self.numero(letra)) for letra in self.partes] if self.partida.tema.cripto else self.partes
    def comandos(self, foco):
        """O menu interativo (F9): os comandos do painel em foco, como (nome da tecla, o que faz, tecla)."""
        comuns = [("Enter", "Seleciona a opção", dvcs.ENTER), ("Backspace", "Reinicia a rodada", dvcs.BACKSPACE), ("Tab", "Alterna para o outro menu", dvcs.TAB), ("Esc", "Desiste do jogo", dvcs.ESC)]
        if foco == "partes": return comuns + ([("F5", "Informa a letra do número", dvcs.F5)] if self.partida.tema.cripto else [])
        return comuns + [("Espaço", "Informa o limite de letras por palavra", b" "), ("F2", "Explora a palavra letra a letra, com as setas", dvcs.F2), ("F5", "Informa a palavra a ser formada", dvcs.F5),
            ("F6", "Informa quantas letras a palavra já tem", dvcs.F6), ("F7", "Repõe a palavra como estava no início da rodada, devolvendo as letras", dvcs.F7)]
    def dica_letra(self, idx):
        """F5 no menu das letras, no criptograma: diz a letra que está atrás do número. Conta como erro de dica."""
        self.partida.erros["dica"] += 1
        letra = self.partes[idx]
        return f"{self.numero(letra)} é a letra {letra}."
    def tabela(self):
        """A tabela do criptograma, "número. letra" de cada letra da rodada, para o jogador ver antes de jogar."""
        return [f"{self.numero(letra)}. {letra}" for letra in sorted(self.letras_inicial | self.letras)]

    def letras_uteis(self, letras=None):
        """Retorna as letras que ainda podem ser aplicadas em alguma palavra restante."""
        if letras is None:
            letras = self.letras
        letras_uteis = set()
        limite = self.limite_letras if len(letras) > 1 else float("inf")  # com uma letra só, o limite não vale
        for palavra in self.palavras:
            if palavra.letras_reveladas < limite: letras_uteis.update(palavra.letras_faltantes)
        return letras_uteis & letras

    def salva(self):
        """Salva o estado da rodada atual na partida, incluindo a rodada atual, tempo total e palavras formadas."""
        self.partida.formados += [palavra.formacao for palavra in self.palavras if palavra.completa]
        if not self.partida.jogos:
            self.partida.jogos = {}
        self.partida.jogos[self.partida.tema.escolhido] = {
            "rodada_atual": self.atual,
            "letras_total": self.partida.letras_total,
            "tempo_total": self.partida.duracao()
        }
