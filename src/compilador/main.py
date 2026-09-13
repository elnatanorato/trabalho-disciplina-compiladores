import sys
from compilador.lex import tokenize, find_column, reserved, relation

META_ATRIBUTOS = {"ORDERED_META", "CONST_META", "DERIVED_META", "SUBSETS_META", "REDEFINES_META"}
PALAVRAS_RESERVADAS = set(reserved.values()) - META_ATRIBUTOS

def gerar_relatorio(codigo_fonte):
    tokens, erros = tokenize(codigo_fonte)


    print("\n" + "="*70)
    print(" VISÃO ANALÍTICA DOS TOKENS ".center(70))
    print("="*70)
    print(f"{'Token':<25} | {'Lexema':<20} | {'Linha':<6} | {'Coluna'}")
    print("-" * 70)
    
    for t in tokens:
        col = find_column(codigo_fonte, t)
        print(f"{t.type:<25} | {str(t.value):<20} | {t.lineno:<6} | {col}")

    contadores = {
        "Classes": 0,
        "Relações": 0,
        "Palavras-chave / Estereótipos": 0,
        "Indivíduos (Instâncias)": 0,
        "Meta-atributos": 0,
        "Outros (Símbolos, Números, Tipos)": 0
    }

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

    print("\n" + "="*70)
    print(" TABELA DE SÍNTESE ".center(70))
    print("="*70)
    for categoria, quantidade in contadores.items():
        print(f"{categoria:<40} : {quantidade}")

    
    print("\n" + "="*70)
    print(" RELATÓRIO DE ERROS ".center(70))
    print("="*70)
    
    if not erros:
        print("-> Nenhum erro léxico foi encontrado no código fonte analisado.")
    else:
        for err in erros:
            print(f"[Erro Léxico] Linha {err['line']}, Coluna {err['column']}: {err['message']}")
            print(f"   ↳ Sugestão de Tratamento: {err['suggestion']}\n")

def main():
    codigo_teste = """
    package TesteOntologia
    
    category Pessoa
    kind Estudante subsets Pessoa
    
    Estudante123
    
    // Testando relações e meta atributos
    @material
    ordered const
    
    # erro_aqui
    """
    
    gerar_relatorio(codigo_teste)

if __name__ == "__main__":
    main()