# Partes Únicos: API.py
# Copyright (C) 2026 Caio Gustavo Rodrigues Grizosto
# SPDX-License-Identifier: LGPL-3.0-only
# Este arquivo é software livre, sob a GNU Lesser General Public License, versão 3 (veja COPYING.LESSER e COPYING). Sem nenhuma garantia.
"""Módulo de API do jogo, incluindo funções para consultar o ranking e gerenciar a desistência do jogador.

Este módulo define a base comum a todos os jogos da série "Únicas" (Números, Palavras ,e Letras): as classes Tema, Jogo e Rodada. 
Cada jogo específico (carrega_numeros.py,
carrega_palavras.py, ...) herda dessas três classes e sobrescreve os métodos que fazem sentido
mudar (config(), carrega(), verifica() etc.), mas reaproveita os atributos e o fluxo geral
descritos abaixo. A ideia é que, ao criar um novo jogo, baste criar um carrega_jogo.py
seguindo o mesmo contrato — sem precisar reinventar o carregamento de tema, o salvamento de
progresso ou a checagem de vitória.
"""
import dvcs, json, menus, os, ranking, sys, time
from datetime import datetime

# Progressão no fácil: sobe de nível ao terminar a janela inteira da partida em poucas rodadas.
RODADAS_PARA_SUBIR = {1: 1, 2: 1, 3: 2}  # nível -> máximo de rodadas jogadas na sessão
JANELA_MAXIMA = 20  # a janela exigida é nivel * 10, mas nunca mais que isso (o F3 sobe com 20)

def dir_troca():
    """Muda para a pasta do programa (assim dic, rankings e saves ficam sempre ao lado dele) e devolve o caminho do programa: o .exe ou o .py."""
    if getattr(sys, 'frozen', False): caminho_completo = sys.executable
    else: caminho_completo = os.path.abspath(sys.argv[0])
    os.chdir(os.path.dirname(caminho_completo))
    return caminho_completo

def configuraDosvox(caminho):
    """Registra o programa no Dosvox.ini, só na versão compilada e se o Jogo10 estiver livre: a interpretada (de teste) não mexe na instalação."""
    if not getattr(sys, 'frozen', False): return
    # Jogo10: o Dosvox oficial vai só até o Jogo7 nos educativos (do Jogo21 em diante são menus de outros jogos), e o Jogo10 de progjogos também é de sistema
    if not dvcs.sintAmbiente("JOGOSEDUCATIVOS", "Jogo10"):
        dvcs.sintGravaAmbiente("JOGOSEDUCATIVOS", "Jogo10", f"p,{caminho},-jopartes,Sistema de jogos - Partes Únicas")

def menu_ajuda():
    dvcs.sintWriteln("Bakspace - Reinicia a rodada.")
    dvcs.sintWriteln("Esk desiste da rodada e do jogo.")
    dvcs.sintWriteln("Tab vai para o próximo menu.")
    dvcs.sintWriteln("Enter seleciona a opção atual.")
    print()
    dvcs.sintWriteln("Aperte enter.")
    dvcs.sintReadKey()


class Tema:
    """Representa o TEMA escolhido: o conteúdo bruto (vindo de um arquivo .pal) e as regras
    de dificuldade/nível que definem como esse conteúdo vira o material de uma partida.

    Um Tema é criado, configurado (dificuldade + nível) e carregado UMA vez, antes da partida
    começar. Ele não muda durante o jogo — quem muda é o Jogo/Rodada, que consomem cópias de
    self.partes e comparam o que o jogador formou com self.base.

    Atributos definidos aqui (comuns a todo jogo):
        dificuldade (str | None): "f", "m" ou "d" — definida por dif(), geralmente chamada
            dentro do config() de cada jogo específico. Cada subclasse decide o que cada
            dificuldade significa (ex.: em Números Únicos muda a operação matemática usada;
            em Palavras Únicas muda o quanto a ordem de montagem é exigida).
        nivel (int | None): limite numérico livre para cada jogo interpretar como quiser —
            em Números Únicos é o maior número que pode ser formado; em Palavras Únicas é
            quantas frases/itens do tema entram na partida (até 20). Definido em config().
        temas (dict[str, list[str]]): TODOS os temas encontrados no arquivo carregado, no
            formato {nome_do_tema: [linha1, linha2, ...]}. Preenchido por carrega() ao ler
            o arquivo .pal: cada bloco iniciado por "*nome" vira uma entrada nesse dicionário,
            e cada linha seguinte (ou cada item separado por vírgula) vira um elemento da lista.
        escolhido (str): a CHAVE de `temas` que foi selecionada para esta partida — escolhida
            interativamente por escolhe(), ou já vinda pronta no construtor.
        partes (list): o "pool" de peças que o jogador poderá selecionar durante o jogo,
            já processado a partir de temas[escolhido] pelo carrega() de cada subclasse.
            Em Números Únicos: os fatores/primos disponíveis. Em Palavras Únicas: as palavras
            (sem repetição) de todas as frases do tema. É a partir de uma CÓPIA deste atributo
            que o Jogo monta seu próprio self.partes (a "cópia de trabalho" que vai sendo consumida).
        base (list): o "gabarito" — o que o jogador precisa formar para vencer. Jogo.vitoria()
            compara sorted(Jogo.formados) com sorted(Tema.base): quando as duas listas baterem,
            o jogo termina. Em Números Únicos, cada item é um número-alvo; em Palavras Únicas,
            cada item é uma string "chave: frase completa".
    """
    def __init__(self, escolhido=""):
        self.dificuldade = None  # "f", "m" ou "d" — ver dif(). Cada jogo interpreta como quiser.
        self.nivel = None  # Limite numérico livre — significado depende do jogo (ver acima).
        self.cancelado = False  # True se o jogador apertou ESC durante dif()/config().
        self.temas = {}  # {nome_do_tema: [linhas cruas do arquivo]}, preenchido por carrega().
        self.escolhido = escolhido  # Nome do tema selecionado, chave de self.temas.
        self.jogador = None  # Quem joga, guardado por config(): o menu de temas usa para mostrar só os temas que ele ainda não concluiu.
        self.jogo = None  # Chave do jogo ("letras", "palavras"...): é a pasta dos saves e a chave do jogo no perfil.
        self.ranking_path = None  # Arquivo do ranking do jogo; se o jogo não definir, "<jogo>.json".
        self.segue_perfil = False  # True quando a partida segue o perfil do jogador (e por isso pode fazê-lo progredir); False no jogo livre.
        self.partes = []  # Pool de peças selecionáveis, montado por carrega() de cada subclasse.
        self.base = []  # Gabarito de vitória: o que Jogo.formados precisa igualar.

    def config(self, jogador=None, jogo=None, dificuldade=None, livre=False):
        """Configura dificuldade e nível. Se `jogador` já tiver um perfil salvo (progressão de sessões anteriores), oferece mantê-lo, sem perguntar
        de novo — é isso que faz o nível/dificuldade subirem sozinhos entre uma sessão
        e outra. Sem perfil (primeira vez), ou se o jogador preferir escolher novos, pergunta normalmente e grava a escolha como o novo perfil.
        `dificuldade` ("f", "m" ou "d") é para jogos que só têm uma: ela vale no lugar do perfil e a pergunta não é feita.
        `livre`: antes de tudo pergunta se o jogador segue o perfil (P) ou joga livre (L); o jogo livre não lê nem grava o perfil."""
        if jogador: self.jogador, self.jogo = jogador, jogo
        self.segue_perfil = bool(jogador and jogo)
        if self.segue_perfil and livre:
            self.segue_perfil = self._segue_perfil()
            if self.cancelado: return self
        if self.segue_perfil:
            perfil = self.cria_perfil(jogador)
            dados = perfil.get(jogo, {})
            if dados:
                dvcs.sintWriteln("Tecle Enter para manter a dificuldade e nível salvos do seu perfil, ou outra tecla para escolher novos.")
                if dvcs.dvcsLeTecla() == dvcs.ENTER:
                    self.dificuldade = dificuldade or dados["dificuldade"]
                    self.nivel = dados["nivel"]
                    self.do_perfil(dados)
                    return self
        self.dif(dificuldade)
        if self.cancelado: return self
        dvcs.sintWriteln("Escolha o nível de 1 a 3.")
        while True:
            tecla = dvcs.dvcsLeTecla()
            if tecla == dvcs.ESC:
                self.cancelado = True
                return self
            try:
                self.nivel = int(tecla)
                if 0 < self.nivel <= 3:
                    break
                else:
                    dvcs.sintWriteln("O nível deve ser 1, 2 ou 3.")
            except ValueError:
                dvcs.sintWriteln("Entrada inválida. Digite 1, 2 ou 3.")
        if self.segue_perfil:  # a escolha nova vira o perfil
            perfil[jogo] = {**perfil.novo(self.dificuldade, self.nivel), **self.para_perfil()}
            perfil.salva()
        return self
    def do_perfil(self, dados):
        """Um jogo com campos próprios no perfil (além de dificuldade e nível) os lê daqui, quando o jogador mantém o perfil."""
    def para_perfil(self):
        """Os campos próprios do jogo que vão para o perfil junto com a dificuldade e o nível escolhidos."""
        return {}
    def cria_perfil(self, jogador):
        """O perfil do jogador. Um jogo com regras próprias de perfil (níveis, campos) sobrescreve para devolver a sua subclasse de Perfil."""
        return Perfil(jogador)
    def _segue_perfil(self):
        """Pergunta p (seguir o perfil) ou l (jogar livre). ESC cancela."""
        dvcs.sintWriteln("Tecle P para seguir o seu perfil ou L para jogar livre.")
        while True:
            tecla = dvcs.dvcsLeTecla()
            if tecla == dvcs.ESC:
                self.cancelado = True
                return False
            if tecla.decode("latin-1").lower() in ("p", "l"): return tecla.decode("latin-1").lower() == "p"

    def escolhe(self):
        """Exibe um menu para o usuário escolher um tema, retornando o tema selecionado.

        Chamado automaticamente por carrega() depois que o arquivo é lido — não precisa ser
        chamado manualmente. Usa menus.menu(), que é o menu de escolha simples do Dosvox
        (diferente da classe Menus de menus.py, que é a tela de duas colunas do jogo em si).
        Só aparecem os temas que enchem a janela do nível (_temas_do_nivel). Se o jogador é conhecido e já concluiu alguns temas,
        a última opção do menu alterna entre todos os temas e só os que ele ainda não concluiu."""
        dvcs.clrscr()
        temas, concluidos, so_novos = self._temas_do_nivel(), self._concluidos(), False
        while True:
            lista = [t for t in temas if t not in concluidos] if so_novos else temas
            alterna = []
            if any(t in concluidos for t in temas) and any(t not in concluidos for t in temas):
                alterna = ["Mostrar todos os temas" if so_novos else "Mostrar só os temas que ainda não concluí"]
            i = menus.menu(lista + alterna, "escolha um tema") - 1
            if i == -1: return ""
            if i < len(lista): return lista[i]
            so_novos = not so_novos

    # --- filtros do menu de temas ---
    def _temas_do_nivel(self):
        """Os temas com palavras (ou itens) suficientes para o nível: pelo menos nivel*10 - 10, como no Scriptvox (no nível 3, 20 ou mais).
        O fácil, que usa janela de 10, e o jogo sem nível mostram todos; se nenhum serve, também todos."""
        if not isinstance(self.nivel, int) or self.dificuldade == "f": return list(self.temas)
        servem = [tema for tema, itens in self.temas.items() if len(itens) >= self.nivel * 10 - 10]
        return servem or list(self.temas)
    def _concluidos(self):
        """Os temas que o jogador concluiu: já jogou (tem recorde no ranking do jogo) e o save tem todos os itens do tema formados
        (como Jogo.carrega, que não retoma um tema completo; veja _completo). Vazio se o jogador ou o jogo não são conhecidos."""
        if not (self.jogador and self.jogo): return []
        jogados = ranking.Ranking(None, self.ranking_path or f"{self.jogo}.json").ranking.get(self.jogador, {})
        try:
            with open(f"{os.path.join(self.jogo, self.jogador)}.json", "r", encoding="utf-8") as f: salvos = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError): salvos = {}
        return [tema for tema in jogados if tema in self.temas and self._completo(tema, salvos.get(tema, {}).get("formados", []))]
    def _completo(self, tema, formados):
        """O save tem o tema todo formado? Por padrão, tantos formados quantos itens o tema tem. Cada jogo pode refinar (o Números compara com a base)."""
        return len(formados) >= len(self.temas[tema])

    def dif(self, dificuldade=None):
        """Pergunta ao jogador a dificuldade (F/M/D) e grava em self.dificuldade.
        Chamada normalmente dentro do config() de cada jogo específico, antes de perguntar
        o nível. Se o jogador apertar ESC, self.dificuldade fica como estava (None na primeira vez).
        Com `dificuldade` ("f", "m" ou "d") não pergunta nada: grava o valor recebido."""
        if dificuldade in ["f", "m", "d"]:
            self.dificuldade = dificuldade
            return self
        dvcs.sintWriteln("Tecle F para fácil, M para médio ou D para difícil.")
        dificuldade = dvcs.dvcsLeTecla()
        if dificuldade == dvcs.ESC:
            self.cancelado = True
            return self
        self.dificuldade = dificuldade.decode().lower()
        if self.dificuldade not in ["f", "m", "d"]:
            opcoes = ["f- Fácil", "m- Médio", "d- Difícil", "ESC- voltar"]
            opcao = menus.menu(opcoes, "Escolha a dificuldade do jogo")
            if opcao == 1: self.dificuldade = "f"
            elif opcao == 2: self.dificuldade = "m"
            elif opcao == 3: self.dificuldade = "d"
            else: self.cancelado = True  # ESC no menu: não deixa a tecla inválida como dificuldade

    def carrega(self, arquivo=None, tema_atual=None) -> dict:
        """Lê um arquivo de temas (.pal) e monta um dicionário com os dados encontrados.
        Retorna o dicionário de temas.

        Formato esperado do arquivo.pal (texto em latin-1):
            *nome do tema
            item1
            item2, item3, item4
        Uma linha começando com "*" abre um novo tema (a chave de self.temas). Linhas seguintes
        viram itens desse tema — se a linha tiver vírgulas, cada pedaço vira um item separado;
        senão, a linha inteira vira um item.

        IMPORTANTE para quem estende esta classe: normalmente você NÃO chama isto sozinho.
        As subclasses  sobrescrevem carrega() para primeiro chamar super().carrega(arquivo) — o que preenche self.temas
        e self.escolhido — e DEPOIS processar self.temas[self.escolhido] no formato específico
        daquele jogo, preenchendo self.partes e self.base na sequência.
        """
        try:
            with open(arquivo, "r", encoding="latin-1") as a:
                if tema_atual: 
                    self.escolhido = tema_atual
                    self.temas[self.escolhido] = []
                for linha in a:
                    conteudo = linha.strip()
                    if not conteudo: continue
                    if conteudo[0] == "*":
                        tema_atual = conteudo.lstrip("* ")
                        self.temas[tema_atual] = []
                        continue
                    if ";" in conteudo:
                        self.temas[tema_atual] += [item.strip() for item in conteudo.split(";") if item.strip()]
                    elif "," in conteudo:
                        self.temas[tema_atual] += [item.strip() for item in conteudo.split(",") if item.strip()]
                    else: self.temas[tema_atual].append(conteudo)
        except FileNotFoundError:
                    raise FileNotFoundError(f"Não foi possível encontrar o arquivo {arquivo} para carregamento dos temas do jogo.")
        else:
            if not self.escolhido: self.escolhido = self.escolhe()


class Jogo:
    """Representa a PARTIDA de um jogador: nome, tempo, e o estado que evolui durante o jogo

    Um Jogo é criado uma vez por sessão (Jogo(nome, tema)) e pode ser recarregado de um save

    Principais métodos e responsabilidades:
    iniciar: inicia a contagem de tempo da partida;
    duracao: Calcula a duração da partida em segundos com base em self.tempo_inicio;
    vitoria: Verifica se a partida foi vencida;
    carrega: Carrega uma eventual partida salva.
    salva: Salva o estado atual da partida em "<jogador>.json.

    Atributos:
        jogos (dict): conteúdo bruto de "<jogador>.json", se existir — indexado por nome de tema (self.tema.escolhido).
        tema (Tema): o tema já configurado e carregado desta partida.
        partes (list): CÓPIA de tema.partes — o pool de peças ainda disponíveis para usar. 
        formados (list): o que o jogador já formou/completou até agora. 
        jogador (str): nome do jogador, também usado como nome do arquivo de save
        tempo_por_numero (float): tempo médio por peça formada.
        Nome legado de Números Únicos: calculado no fim da partida (tempo_total dividido pela quantidade de itens formados) — usado no ranking.
            Não foi renomeado porque é também a chave usada nos arquivos de ranking já salvos.
        tempo_total (float): duração total da partida em segundos, calculada por duracao()
        data (str): data de criação da partida ("dd/mm/aa"), usada pelo ranking.
        tempo_inicio (float): timestamp (time.time()) do momento em que iniciar() foi chamado.
        Inicio(int): índice referente ao início da partida, incluindo eventuais rodadas salvas.
        cursor(int): Índice do próximo item da base ainda não processado por jogos que trabalham com um limite de itens por partida.
    """
    def __init__(self, nome, tema_selecionado=None):
        """Recebe o nome do jogador e o tema selecionado, configurando as partes e base formada."""
        self.jogos = {}  # Conteúdo de "<jogador>.json" (saves anteriores), por tema.
        self.tema = tema_selecionado
        self.partes = self.tema.partes.copy() # Cópia de trabalho, consumida durante o jogo.
        self.formados = []  # O que o jogador já formou; comparado com tema.base em vitoria().
        self.base = self.tema.base.copy() # Base a ser comparada com vitória
        self.jogador = nome
        self.tempo_por_numero = 0  # Tempo médio por item formado. Nome legado (ver docstring da classe).
        self.tempo_total = 0  # Duração total da partida em segundos.
        self.data = datetime.now().strftime("%d/%m/%y")
        self.tempo_inicio = 0  # Timestamp de início, definido por iniciar().
        self.inicio = 0  # Índice que representa o início da partida
        self.cursor = 0 
        self.dados = None

    def iniciar(self):
            """Inicia a contagem de tempo da partida e guarda o tamanho da janela de itens a jogar
            (usado em fim_de_sessao, já que o jogo avança self.inicio antes de chamá-la)."""
            self.tempo_inicio = time.time()
            self.janela = min(getattr(self, "limite", 0), len(self.base)) - self.inicio

    def duracao(self):
        """Calcula a duração da partida em segundos."""
        return int(time.time() - self.tempo_inicio)

    def vitoria(self):
        """Verifica se a partida foi vencida, comparando a estrutura formada com a base do tema.

        Cada jogo específico só precisa garantir que, quando um item é completado corretamente,
        ele seja adicionado a self.formados NO MESMO FORMATO em que aparece em tema.base
        (ex.: em Palavras Únicas, a string "chave: frase completa" precisa ser idêntica nos dois).
        """
        if sorted(self.formados) == sorted(self.base):
            return True
        return False
    
    def carrega(self, jogo):
        """Carrega  partidas salvas do jogador a partir de "<jogador>.json", se houver, para self.jogos
        e tenta restaurar o estado da partida atual a partir do tema selecionado.

        Cada jogo específico deve sobrescrever este método, chamar super().carrega() para restaurar atributos internos conforme a estrutura definida para self.jogos, caso necessário.
        """
        try:
            with open(f"{os.path.join(jogo, self.jogador)}.json", "r", encoding="utf-8") as f:
                self.jogos = json.load(f)
        except FileNotFoundError:
            return self
        except json.JSONDecodeError:
            raise ValueError(f"Erro ao ler o arquivo {self.jogador}.json. O arquivo pode estar corrompido.")
        self.dados = self.jogos.get(self.tema.escolhido) if self.jogos else None
        if self.dados:
            self.inicio = self.dados.get("inicio", 0)
            if "formados" in self.dados and sorted(self.dados["formados"]) != sorted(self.tema.base): self.formados = self.dados["formados"]
            self.cursor = self.inicio
        return self

    def salva(self, jogo):
        """Salva o estado atual da partida em "<jogador>.json".

        Cada jogo específico deve sobrescrever este método, chamando super().salva() para garantir que os dados sejam gravados corretamente no formato esperado.
        """
        if not self.jogos: self.jogos = {}
        if not self.jogos.get(self.tema.escolhido): self.jogos[self.tema.escolhido] = {}
        jogo_atual = self.jogos[self.tema.escolhido]
        jogo_atual.update({
            "inicio": self.inicio,
            "formados": self.formados
        })
        os.makedirs(jogo, exist_ok=True)
        with open(f"{os.path.join(jogo, self.jogador)}.json", "w", encoding="utf-8") as f:
            json.dump(self.jogos, f, indent=4, ensure_ascii=False)


class Rodada:
    """Representa UMA RODADA de jogadas dentro da partida — a unidade que efetivamente lê e
    processa as jogadas do jogador (isso normalmente fica a cargo do método verifica(),
    definido em cada jogo específico, já que a lógica de "o que é uma jogada válida" muda
    de jogo para jogo).

    Uma Rodada trabalha sobre CÓPIAS de partida.formados/partida.partes (self.formados,
    self.partes), permitindo reiniciar a rodada (tecla Backspace) sem perder
    o progresso salvo da partida como um todo — só quando a rodada termina bem (ou o jogador
    sai) é que salva() grava o resultado de volta no save.

    Atributos:
        partida (Jogo): referência à partida em andamento — é através dela que a Rodada
    acessa partida.tema (para consultar dificuldade, base, partes originais etc.).
        atual (int): número da rodada, usado por jogos que têm o conceito de "avançar de
            rodada". 
        formados (list): cópia de partida.formados no início da rodada.
        partes (list): cópia de partida.partes no início da rodada — é aqui, e não em
            partida.partes diretamente, que verifica() deve remover peças usadas.
    """
    def __init__(self, partida, valor_rodada=1):
        self.partida = partida
        self.atual = valor_rodada  # Número da rodada 
        self.formados = partida.formados.copy()  # Cópia de trabalho, gravada de volta em salva().
        self.base = partida.base.copy() # Base para save e vitória.
        self.partes = partida.partes.copy()  # Cópia de trabalho, consumida por verifica().

    def carrega(self):
        """Restaura dados da rodada  a partir do save, se houver um save para o tema escolhido."""
        dados = self.partida.jogos.get(self.partida.tema.escolhido) if self.partida.jogos else None
        if dados: 
            self.atual = dados.get("rodada_atual", 1)
        return self

    def salva(self):
        """Grava o estado atual da rodada de volta no save da partida, para que possa ser
        retomada depois. 
        """
        if not self.partida.jogos:
            self.partida.jogos = {}
        self.partida.jogos[self.partida.tema.escolhido] = {
            "rodada_atual": self.atual,
            "formados": self.formados,
            "partes": self.partes,
            "base": self.base,
            "inicio": self.partida.inicio,
            "tempo_total": self.partida.tempo_total
        }
            
    def exibe_formados(self):
        """Retorna os elementos já formados para exibição no menu.

        Na implementação padrão, retorna diretamente o conteúdo de
        ``self.formados``. Subclasses podem sobrescrever este método para
        adaptar a apresentação dos dados sem alterar sua estrutura interna.

        Exemplos:
        - Letras Únicas: ``self.formados`` já contém uma lista de palavras,
        portanto o comportamento padrão é suficiente.
        - Palavras Únicas: ``self.formados`` contém dicionários no formato
        ``{chave: frase}``; o método é sobrescrito para exibir apenas a frase.
        - Números Únicos: na dificuldade fácil, o método pode exibir apenas
        os números ainda formáveis a partir dos fatores restantes, como
        recurso de auxílio ao jogador.

        Returns:
            list: Estrutura contendo os elementos a serem exibidos no menu.
        """
        return self.formados

def desiste():
    """Pergunta se o jogador quer mesmo sair; se sim, encerra o programa (sys.exit())."""
    dvcs.sintWriteln("Quer mesmo sair do jogo?")
    resposta = dvcs.dvcsLeTecla().decode().lower()
    if resposta == "s":
        dvcs.sintWriteln("Foi muito bom jogar com você. Até a próxima!")
        dvcs.sintFim()
        sys.exit()


# --- Perfil de progressão do jogador ---
# Guarda a dificuldade/nível ATUAIS de cada jogo, por jogador — separado do save por tema
# (que fica em "<jogador>.json"). Um "<jogador>_perfil.json" só, reaproveitável por
# todos os jogos, cada um sob sua própria chave (ex.: perfil["palavras"] = {"dificuldade": "m", "nivel": 2, "max_rodada": 0}).

class Perfil(dict):
    """O perfil de um jogador: um dicionário {jogo: {"dificuldade", "nivel", "max_rodada"}} que sabe se guardar em arquivo,
    zerar um jogo e mostrar/editar os próprios dados num formulário. Por ser um dicionário, get, setdefault e pop continuam valendo."""
    DIFICULDADES = {"f": "fácil", "m": "médio", "d": "difícil"}
    NIVEIS = {"f": range(1, 4), "m": range(1, 4), "d": range(1, 4)}  # níveis válidos de cada dificuldade; um jogo com outra escala sobrescreve
    NOME_NIVEL = "Nível"  # como o formulário chama o nível
    NOME_RODADA = "Rodada máxima"  # como o formulário chama o max_rodada; None se o jogo não usa
    MAX_RODADA = 20  # teto do max_rodada, o mesmo das letras por rodada do fácil

    def __init__(self, jogador):
        super().__init__()
        self.jogador = jogador
        self.carrega()

    # --- arquivo ---
    @property
    def arquivo(self):
        return f"{self.jogador}_perfil.json"
    def carrega(self):
        """Lê "<jogador>_perfil.json". Sem arquivo (ou com o arquivo estragado), o perfil fica vazio."""
        self.clear()
        try:
            with open(self.arquivo, "r", encoding="utf-8") as f: self.update(json.load(f))
        except (FileNotFoundError, json.JSONDecodeError): pass
        return self
    def salva(self):
        """Grava o perfil inteiro (todos os jogos) de volta no arquivo."""
        with open(self.arquivo, "w", encoding="utf-8") as f: json.dump(self, f, indent=4, ensure_ascii=False)
        return self
    def zera(self, jogo):
        """Apaga o perfil de um jogo (o jogador escolhe dificuldade e nível de novo na próxima partida) e grava."""
        self.pop(jogo, None)
        return self.salva()

    # --- formulário ---
    def novo(self, dificuldade, nivel):
        """Os dados de um perfil novo."""
        return {"dificuldade": dificuldade, "nivel": nivel, **({"max_rodada": 0} if self.NOME_RODADA else {})}
    def _formulario(self, dados):
        """Monta o formulário com os campos do perfil de um jogo."""
        dvcs.formCria()
        dvcs.formCampo("", "Dificuldade", str(dados.get("dificuldade", "f")), 1)
        dvcs.formCampo("", self.NOME_NIVEL, str(dados.get("nivel", 1)), 3)
        if self.NOME_RODADA: dvcs.formCampo("", self.NOME_RODADA, str(dados.get("max_rodada", 0)), 2)
    def _valida(self, respostas):
        """Converte o que o jogador digitou. Retorna (dados do perfil, "") ou (None, mensagem de erro)."""
        dificuldade = respostas["Dificuldade"].strip().lower()
        if dificuldade not in self.DIFICULDADES: return None, "A dificuldade deve ser f, m ou d."
        niveis = self.NIVEIS[dificuldade]
        try: nivel, max_rodada = int(respostas[self.NOME_NIVEL]), int(respostas[self.NOME_RODADA]) if self.NOME_RODADA else 0
        except ValueError: return None, "Os valores precisam ser números."
        if nivel not in niveis: return None, f"Nesta dificuldade, {self.NOME_NIVEL.lower()} deve ir de {niveis[0]} a {niveis[-1]}" + (f", de {niveis.step} em {niveis.step}." if niveis.step > 1 else ".")
        if self.NOME_RODADA and not 0 <= max_rodada <= self.MAX_RODADA: return None, f"{self.NOME_RODADA} deve ir de 0 a {self.MAX_RODADA}."
        return {"dificuldade": dificuldade, "nivel": nivel, **({"max_rodada": max_rodada} if self.NOME_RODADA else {})}, ""
    def edita(self, jogo):
        """Deixa o jogador alterar o perfil do jogo até digitar valores válidos (grava) ou teclar ESC (descarta)."""
        dados = self[jogo]
        while True:
            self._formulario(dados)
            respostas, tecla = dvcs.formEdita(True)
            if tecla == dvcs.ESC: return
            novos, erro = self._valida(respostas)
            if erro:
                dvcs.sintWriteln(erro)
                continue
            self[jogo] = {**dados, **novos}  # o que o formulário não mostra fica como estava
            self.salva()
            dvcs.sintWriteln("Perfil salvo.")
            return
    def consulta(self, jogo):
        """Mostra o perfil do jogador no jogo (dificuldade, nível, rodada máxima) e, com a tecla e, permite alterá-lo."""
        if not self.get(jogo): return dvcs.sintWriteln("Você ainda não tem perfil neste jogo. Ele nasce quando você escolhe a dificuldade e o nível.")
        dados = self[jogo]
        dvcs.sintWriteln(f"Perfil de {self.jogador}: dificuldade {self.DIFICULDADES.get(dados.get('dificuldade'), '?')}{' (criptograma)' if dados.get('cripto') else ''}, {self.NOME_NIVEL.lower()} {dados.get('nivel')}.")
        self._formulario(dados)
        dvcs.formEdita(False)
        dvcs.sintWriteln("Tecle e para alterar, ou outra tecla para voltar.")
        if dvcs.dvcsLeTecla().decode("latin-1").lower() == "e": self.edita(jogo)

# --- consulta do save ---
class Save:
    """O save do jogador num jogo ("<jogo>/<jogador>.json", um registro por tema), só para consulta: não se altera por aqui."""
    CAMPOS = {"inicio": "Início", "rodada_atual": "Rodada", "letras_total": "Letras colocadas", "tempo_total": "Tempo em segundos"}  # chave do save -> rótulo
    def __init__(self, jogador, jogo):
        self.jogador, self.jogo = jogador, jogo
        self.dados = self.carrega()
    def carrega(self):
        """Lê o save do jogador. Sem arquivo (ou estragado), vem vazio."""
        try:
            with open(f"{os.path.join(self.jogo, self.jogador)}.json", "r", encoding="utf-8") as f: return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError): return {}
    def linhas(self, tema):
        """Os campos do save do tema, como (rótulo, valor): os dados da partida, as palavras formadas e, se o jogo conta, os erros."""
        dados = self.dados[tema]
        linhas = [(rotulo, dados[chave]) for chave, rotulo in self.CAMPOS.items() if chave in dados]
        if "formados" in dados: linhas.append(("Formados", len(dados["formados"])))
        if "conjuntos" in dados: linhas += [("Conjuntos feitos", len(dados["conjuntos"])), ("Palavras dos conjuntos", ", ".join(dados["conjuntos"]))]  # o tema livre
        erros = dados.get("erros")
        if erros is not None:
            linhas += [(f"Erro {tipo}", erros.get(tipo, 0)) for tipo in ("inválida", "máximo", "repetida", "dica")]
            linhas.append(("Erro total", sum(erros.values())))
        return linhas
    def consulta(self):
        """Deixa escolher um tema salvo e mostra os dados do save dele (só leitura)."""
        if not self.dados: return dvcs.sintWriteln("Você ainda não tem jogo salvo neste jogo.")
        temas = list(self.dados)
        i = menus.menu(temas, "Escolha o tema do save") - 1
        if i == -1: return
        dvcs.sintWriteln(f"Save de {self.jogador}: {temas[i]}.")
        dvcs.formCria()
        for rotulo, valor in self.linhas(temas[i]): dvcs.formCampo("", rotulo, str(valor), max(len(str(valor)), 1))
        dvcs.formEdita(False)

def carrega_perfil(jogador):
    """Compatibilidade: devolve o Perfil do jogador (vazio se ainda não existe)."""
    return Perfil(jogador)

def salva_perfil(jogador, perfil):
    """Compatibilidade: grava o perfil. O Perfil já sabe o seu arquivo, então basta perfil.salva()."""
    perfil.salva()

def fim_de_sessao(interface, jogo, divisor, progride=True, ranking_path="ranking.json", aviso="", registra=True):
    """Fecha uma sessão vencida: progressão de dificuldade/nível (se `progride`), perfil, tempo,
    aplauso, mensagens e ranking. É o trecho que era repetido no fim de cada jogo.

    Cada jogo faz ANTES o que é só dele (avançar partida.inicio, descartar rodada salva, gravar
    a partida) e chama esta função em seguida.

    Parâmetros:
        interface: o Menus; dele saem a Rodada (interface.progresso) e a partida (progresso.partida),
            que tem o jogador (partida.jogador) e o perfil.
        jogo: "letras" ou "palavras" etc. — chave do jogo dentro do perfil.
        divisor: o que divide o tempo total pra dar partida.tempo_por_numero (letras sorteadas,
            números ou frases da sessão, conforme o jogo).
        progride: False em jogos sem progressão por perfil (Números Únicos).
            No fácil, o nível sobe (e o F3 vira médio 1) quando a janela inteira da partida (nivel*10 itens,
            no máximo JANELA_MAXIMA) termina em até RODADAS_PARA_SUBIR[nivel] rodadas.
        ranking_path: arquivo do ranking (o padrão, "ranking.json", é o do Números Únicos).
        aviso: mensagem do próprio jogo sobre o perfil (o Números, que cuida da sua progressão), dita depois do aplauso.
        registra: False numa partida que não vale para o ranking (o tema livre, quando as letras formam mais de uma palavra).
    """
    partida = interface.progresso.partida
    tema = partida.tema
    perfil_jogo = partida.perfil.setdefault(jogo, {}) if progride else {}
    dificuldade_antes = perfil_jogo.get("dificuldade", tema.dificuldade)  # o perfil guarda como a sessão começou, antes de o jogo ou esta função promoverem
    nivel_antes = perfil_jogo.get("nivel", tema.nivel)
    if progride:
        rodadas = interface.progresso.atual - 1  # o jogo já somou 1 à rodada ao terminá-la
        if tema.dificuldade == "f" and partida.janela >= min(tema.nivel * 10, JANELA_MAXIMA) and rodadas <= RODADAS_PARA_SUBIR[tema.nivel]:
            if tema.nivel < 3: tema.nivel += 1
            else: tema.dificuldade, tema.nivel = "m", 1
        perfil_jogo["dificuldade"], perfil_jogo["nivel"] = tema.dificuldade, tema.nivel
        partida.perfil.salva()
    partida.tempo_total = partida.duracao()
    partida.tempo_por_numero = round(partida.tempo_total / divisor, 2)
    dvcs.sintSom("Aplauso")
    if dvcs.keyPressed():
        dvcs.dvcsLeTecla()  # Limpa o buffer de teclas para a próxima tecla não ser capturada antes da mensagem de vitória ser lida.
        dvcs.sintPara()
    if tema.dificuldade != dificuldade_antes:
        nomes = {"f": "fácil", "m": "média", "d": "difícil"}
        interface.mensagem(f"Parabéns, você passou para a dificuldade {nomes[tema.dificuldade]}!")
    elif tema.nivel != nivel_antes:
        interface.mensagem(f"Parabéns, você passou para o nível {tema.nivel}!")
    if aviso: interface.mensagem(aviso)
    interface.mensagem(f"Parabéns {partida.jogador}! Você completou o jogo em {partida.tempo_total} segundos!")
    if not registra: return
    records = ranking.Ranking(partida, path=ranking_path)
    if records.record:
        dvcs.sintWriteln("Parabéns! Você bateu o seu recorde! Quer ver o ranking?")
    else:
        dvcs.sintWriteln("Que pena! Você não bateu o seu recorde. Quer ver o ranking mesmo assim?")
    if dvcs.dvcsLeTecla().decode().lower() == "s":
        records.exibe_ranking()
