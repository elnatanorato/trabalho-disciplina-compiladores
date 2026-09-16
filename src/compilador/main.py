from compilador.lex import analyze, reserved
import sys


# Agrupa os tokens que representam meta-atributos na linguagem TONTO.
META_ATRIBUTOS = {
    "ORDERED_META",
    "CONST_META",
    "DERIVED_META",
    "SUBSETS_META",
    "REDEFINES_META",
}

# Cria um conjunto com todas as palavras reservadas (pegando os valores do dicionário 'reserved' do lex.py)
PALAVRAS_RESERVADAS = set(reserved.values()) - META_ATRIBUTOS


def gerar_relatorio(codigo_fonte):

    # Chama a função principal do analisador léxico que retorna dicionários de tokens e erros
    analysis = analyze(codigo_fonte)
    tokens = analysis["tokens"]
    erros = analysis["errors"]


    # Imprime um cabeçalho formatado para a tabela de tokens
    print("\n" + "=" * 70)
    print(" VISÃO ANALÍTICA DOS TOKENS ".center(70))
    print("=" * 70)
    print(f"{'Token':<25} | {'Lexema':<20} | {'Linha':<6} | {'Coluna'}")
    print("-" * 70)

    # Percorre a lista de tokens reconhecidos e imprime suas propriedades alinhadas
    for t in tokens:
        print(f"{t.type:<25} | {str(t.value):<20} | " f"{t.lineno:<6} | {t.column}")

    # Dicionário usado para armazenar a contagem de cada categoria de token encontrada
    contadores = {
        "Classes": 0,
        "Relações": 0,
        "Palavras-chave / Estereótipos": 0,
        "Indivíduos (Instâncias)": 0,
        "Meta-atributos": 0,
        "Outros (Símbolos, Números, Tipos)": 0,
    }


    # Analisa o tipo de cada token e incrementa o contador da categoria correspondente
    for t in tokens:
        if t.type == "ID_CLASS":
            contadores["Classes"] += 1
        elif t.type in ("ID_RELATION", "RELATION"):
            contadores["Relações"] += 1
        elif t.type == "ID_INSTANCE":
            contadores["Indivíduos (Instâncias)"] += 1
        elif t.type in META_ATRIBUTOS:
            contadores["Meta-atributos"] += 1
        elif t.type in PALAVRAS_RESERVADAS:
            contadores["Palavras-chave / Estereótipos"] += 1
        else:
            contadores["Outros (Símbolos, Números, Tipos)"] += 1


    # Imprime a tabela com os totais calculados
    print("\n" + "=" * 70)
    print(" TABELA DE SÍNTESE ".center(70))
    print("=" * 70)
    for categoria, quantidade in contadores.items():
        print(f"{categoria:<40} : {quantidade}")

    # Exibe a lista de erros léxicos capturados durante a análise
    print("\n" + "=" * 70)
    print(" RELATÓRIO DE ERROS ".center(70))
    print("=" * 70)


    # Se a lista estiver vazia, exibe uma mensagem de sucesso
    if not erros:
        print("-> Nenhum erro léxico foi encontrado no código fonte analisado.")
    else:
        # Percorre a lista de erros formatando a linha, coluna, mensagem e sugestão de correção
        for err in erros:
            print(
                f"[Erro Léxico] Linha {err['line']}, Coluna {err['column']}: {err['message']}"
            )
            print(f"   ↳ Sugestão de Tratamento: {err['suggestion']}\n")


def main():
    # Verifica se o usuário passa exatamente um argumento na linha de comando
    if len(sys.argv) != 2:
        print(f"Argumento invalido! Esperado {sys.argv[0]} {{input.tonto}}")
        return

    # Salva o caminho do arquivo passado via terminal
    file = sys.argv[1]

    # Tenta abrir e ler o conteúdo do arquivo
    try:
        with open(file) as f:
            codigo = f.read()
    except FileNotFoundError:
        # Trata o caso onde o arquivo especificado não existe no caminho informado
        print(f"Arquivo {file} não existe")
        return
    except:
        print(f"Problemas ao abrir arquivo {file}")

    # Aciona a função que fará a análise completa do texto lido
    gerar_relatorio(codigo)


if __name__ == "__main__":
    main()
