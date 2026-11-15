import re
import sys

# ESTRUTURAS DE DADOS

class Token:
    def __init__(self, tipo, atributo, lexema_original, linha):
        self.tipo = tipo                     # Ex: palavra chave, delimitador, identificador, operador e literal
        self.atributo = atributo             # Ex: #1, #2 para ID, ou o próprio lexema
        self.lexema_original = lexema_original  # O nome real da variável
        self.linha = linha

    def __repr__(self):
        return f"{self.atributo:<20} {self.tipo}"

class TabelaSimbolos:
    def __init__(self):
        self.simbolos = {}  # Mapeia: lexema -> id_posicao (ex: "nota1" -> "#1")
        self.ordem = []     # Mantém a ordem de inserção: (id_posicao, lexema)
        self.tipos = {}     # Guarda o tipo declarado para a Análise Semântica

    def obter_ou_inserir(self, lexema):
        # Insere apenas identificadores, uma entrada por nome
        if lexema not in self.simbolos:
            pos_id = f"#{len(self.simbolos) + 1}"
            self.simbolos[lexema] = pos_id
            self.ordem.append((pos_id, lexema))
            self.tipos[lexema] = "Indefinido"
        return self.simbolos[lexema]

    def definir_tipo(self, lexema, tipo_dado):
        if lexema in self.tipos:
            self.tipos[lexema] = tipo_dado

    def obter_tipo(self, lexema):
        return self.tipos.get(lexema, "Indefinido")

    def exibir(self):
        print("\nTabela de símbolos")
        print(f"{'Posição':<10} {'Lexema'}")
        print("-" * 30)
        for pos_id, lexema in self.ordem:
            print(f"{pos_id:<10} {lexema}")
        print("-" * 30)

class ASTNode:
    def __init__(self, rotulo, filhos=None):
        self.rotulo = rotulo
        self.filhos = filhos if filhos else []

    # Árvore visual
    def imprimir_visual(self, prefixo="", ultimo=True, raiz=True):
        if raiz:
            print(self.rotulo)
            proximo_prefixo = ""
        else:
            marcador = "└── " if ultimo else "├── "
            print(f"{prefixo}{marcador}{self.rotulo}")
            proximo_prefixo = prefixo + ("    " if ultimo else "│   ")
        
        for i, filho in enumerate(self.filhos):
            ultimo_filho = (i == len(self.filhos) - 1)
            filho.imprimir_visual(proximo_prefixo, ultimo_filho, False)

# 1. ANÁLISE LÉXICA

class Lexer:
    REGRAS = [
        ('PALAVRA_RESERVADA', r'\b(auto|break|case|char|const|continue|default|do|double|else|enum|extern|float|for|goto|if|inline|int|long|register|restrict|return|short|signed|sizeof|static|struct|switch|typedef|typeof|typeof_unqual|union|unsigned|void|volatile|while|alignas|alignof|bool|true|false|static_assert|thread_local|constexpr|nullptr)\b'),
        ('IDENTIFICADOR', r'[a-zA-Z_][a-zA-Z0-9_]*'),
        ('FLOAT_NUMBER', r'\d+\.\d+'),
        ('NUMBER', r'\d+'),
        ('STRING_LITERAL', r'"[^"]*"|\'[^\']*\''),
        ('OPERADOR', r'[<>]=?|==|!=|[+\-*/=]'),
        ('DELIMITADOR', r'[;,\(\)\{\}\.\[\]]'),
        ('WS', r'\s+'),
        ('MISMATCH', r'.'),
    ]

    def __init__(self, codigo, tabela_simbolos):
        self.codigo = codigo
        self.tabela_simbolos = tabela_simbolos
        self.tokens = []
        self.erros = []

    def analisar(self):
        linha_atual = 1
        padrao_regex = '|'.join(f'(?P<{nome}>{regex})' for nome, regex in self.REGRAS)
        
        for match in re.finditer(padrao_regex, self.codigo):
            tipo = match.lastgroup
            lexema = match.group(tipo)
            
            if tipo == 'WS':
                linha_atual += lexema.count('\n')
                continue
            elif tipo == 'MISMATCH':
                self.erros.append(f"[ERRO LÉXICO] Caractere inválido '{lexema}' na linha {linha_atual}")
                continue

            # se for identificador, o atributo vira o id da tabela
            if tipo == 'IDENTIFICADOR':
                atributo = self.tabela_simbolos.obter_ou_inserir(lexema)
            else:
                atributo = lexema

            token = Token(tipo, atributo, lexema, linha_atual)
            self.tokens.append(token)

        return self.tokens

    def exibir_tokens(self):
        print("\nLista de tokens")
        print(f"{'#':<5} {'Atributo':<20} {'Token'}")
        print("-" * 45)
        for idx, t in enumerate(self.tokens, 1):
            print(f"{idx:<5} {t.atributo:<20} {t.tipo}")
        print("-" * 45)

# 2 e 3. ANÁLISE SINTÁTICA E SEMÂNTICA

class Parser:
    def __init__(self, tokens, tabela_simbolos):
        self.tokens = tokens
        self.pos = 0
        self.tabela_simbolos = tabela_simbolos
        self.erros_semanticos = []
        self.ast_roots = []

    def token_atual(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def match(self, tipo_esperado, lexema_esperado=None):
        token = self.token_atual()
        if token and token.tipo == tipo_esperado:
            if lexema_esperado and token.lexema_original != lexema_esperado:
                return None
            self.pos += 1
            return token
        return None

    def analisar(self):
        while self.pos < len(self.tokens):
            token = self.token_atual()
            if token.tipo == 'PALAVRA_RESERVADA' and token.lexema_original in ['int', 'float', 'double', 'char']:
                stmt = self.parse_declaracao()
                if stmt: self.ast_roots.append(stmt)
            elif token.tipo == 'IDENTIFICADOR':
                stmt = self.parse_atribuicao()
                if stmt: self.ast_roots.append(stmt)
            else:
                self.pos += 1

    def parse_declaracao(self):
        tipo_token = self.match('PALAVRA_RESERVADA')
        id_token = self.match('IDENTIFICADOR')
        
        if tipo_token and id_token:
            # Atualiza o tipo na tabela de símbolos para a checagem semântica
            self.tabela_simbolos.definir_tipo(id_token.lexema_original, tipo_token.lexema_original)
            
            if self.match('DELIMITADOR', ';'):
                return ASTNode('Declaracao', [ASTNode(f"ID ({id_token.lexema_original})")])
        return None

    def parse_atribuicao(self):
        id_token = self.match('IDENTIFICADOR')
        op_token = self.match('OPERADOR', '=')
        
        if id_token and op_token:
            tipo_var = self.tabela_simbolos.obter_tipo(id_token.lexema_original)
            if tipo_var == "Indefinido":
                self.erros_semanticos.append(
                    f"[ERRO SEMÂNTICO] Variável '{id_token.lexema_original}' utilizada na linha {id_token.linha} não foi declarada previamente."
                )

            expr_node = self.parse_expressao()
            if self.match('DELIMITADOR', ';'):
                return ASTNode('Atribuicao', [
                    ASTNode(f"ID ({id_token.lexema_original})"),
                    ASTNode(f"OPERADOR ({op_token.lexema_original})"),
                    expr_node
                ])
        return None

    def parse_expressao(self):
        # Soma e Subtração
        no_esquerdo = self.parse_termo()
        
        token_atual = self.token_atual()
        while token_atual and token_atual.tipo == 'OPERADOR' and token_atual.lexema_original in ['+', '-']:
            op_token = self.match('OPERADOR')
            no_direito = self.parse_termo()
            no_esquerdo = ASTNode(f"Expressao ({op_token.lexema_original})", [no_esquerdo, no_direito])
            token_atual = self.token_atual()
            
        return no_esquerdo

    def parse_termo(self):
        # Multiplicação e Divisão (maior prioridade que soma/subtração)
        no_esquerdo = self.parse_fator()
        
        token_atual = self.token_atual()
        while token_atual and token_atual.tipo == 'OPERADOR' and token_atual.lexema_original in ['*', '/']:
            op_token = self.match('OPERADOR')
            no_direito = self.parse_fator()
            no_esquerdo = ASTNode(f"Termo ({op_token.lexema_original})", [no_esquerdo, no_direito])
            token_atual = self.token_atual()
            
        return no_esquerdo

    def parse_fator(self):
        # Valores básicos e Parênteses (prioridade máxima)
        token = self.token_atual()
        if token:
            if token.tipo == 'IDENTIFICADOR':
                self.match('IDENTIFICADOR')
                tipo_var = self.tabela_simbolos.obter_tipo(token.lexema_original)
                if tipo_var == "Indefinido":
                    self.erros_semanticos.append(
                        f"[ERRO SEMÂNTICO] Variável '{token.lexema_original}' utilizada na linha {token.linha} não foi declarada previamente."
                    )
                return ASTNode(f"ID ({token.lexema_original})")
            
            elif token.tipo == 'NUMBER':
                self.match('NUMBER')
                return ASTNode(f"NUMBER ({token.lexema_original})")
            
            elif token.tipo == 'FLOAT_NUMBER':
                self.match('FLOAT_NUMBER')
                return ASTNode(f"FLOAT_NUMBER ({token.lexema_original})")
            
            elif token.tipo == 'STRING_LITERAL':
                self.match('STRING_LITERAL')
                return ASTNode(f"STRING_LITERAL ({token.lexema_original})")
            
            elif token.tipo == 'DELIMITADOR' and token.lexema_original == '(':
                # Lida com expressões matemáticas dentro de parênteses
                self.match('DELIMITADOR', '(')
                no_interno = self.parse_expressao()
                self.match('DELIMITADOR', ')')
                return ASTNode("Agrupamento ()", [no_interno])
                
        return ASTNode("Erro_Sintatico")
    
# Teste com o código fonte
if __name__ == "__main__":
    nome_arquivo = "codigo_teste.c"
    print("--- INICIANDO COMPILADOR ---")
    
    try:
        with open(nome_arquivo, "r") as f:
            codigo = f.read()
    except FileNotFoundError:
        print(f"[ERRO] O arquivo '{nome_arquivo}' não foi encontrado.")
        sys.exit(1)

    tabela_simbolos = TabelaSimbolos()

    # 1. Fase Léxica
    lexer = Lexer(codigo, tabela_simbolos)
    tokens = lexer.analisar()
    
    lexer.exibir_tokens()
    tabela_simbolos.exibir()

    # 2 e 3. Fases Sintática e Semântica
    parser = Parser(tokens, tabela_simbolos)
    parser.analisar()
    
    print("\n--- ÁRVORE SINTÁTICA ABSTRATA ---")
    for ast in parser.ast_roots:
        # Imprime a árvore com os tracinhos no terminal
        ast.imprimir_visual()
        print("")
        
    print("\n--- VALIDAÇÃO SEMÂNTICA ---")
    if parser.erros_semanticos:
        for erro in parser.erros_semanticos:
            print(erro)
    else:
        print("[SUCESSO] Nenhuma inconsistência semântica encontrada.")
