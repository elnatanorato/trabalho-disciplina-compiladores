# Analisador sintático para TONTO

Projeto da disciplina de Compiladores, continuação do analisador léxico.
Reconhece declarações da linguagem TONTO, constrói uma AST, registra símbolos,
resolve referências entre pacotes e apresenta síntese e relatório de erros.

## Instalação

Requisitos: Python 3.14 ou superior e [Poetry](https://python-poetry.org/).

```bash
poetry install
```

## Execução

```bash
# Um arquivo
poetry run compilador exemplo.tonto

# Vários arquivos, incluindo os pacotes importados
poetry run compilador Pessoas.tonto Bens.tonto

# Todos os arquivos .tonto diretamente nesta pasta (sem recursão)
poetry run compilador exemplos/integracao

# Demonstração de erros e recuperação (retorna código 1)
poetry run compilador exemplos/erros_sintaticos.tonto
```

Alternativa: `poetry run python -m compilador.main exemplos/integracao`.
Importações são resolvidas pelos nomes declarados nos pacotes, não pelo nome
dos arquivos. Os arquivos importados precisam fazer parte da entrada; informar
um arquivo isolado não procura automaticamente suas dependências no disco.

**Saídas:** tabela de quantidades e detalhes por pacote (classes, atributos,
relações internas e externas, tipos complexos, enumerações e generalizações),
seguida dos erros com arquivo, localização disponível e sugestão de tratamento.
Havendo erros, a síntese é marcada como potencialmente incompleta.

Códigos de saída: `0` para análise sem diagnósticos; `1` para erros da análise
ou dos arquivos; `2` para uso incorreto da linha de comando.

## Testes

```bash
poetry run python -m unittest discover -s tests
# Ou, após instalar os scripts:
poetry run test
```

## Etapa semântica — implementação parcial

A camada de tratamento de erros já oferece diagnósticos semânticos, **O reconhecimento completo dos seis padrões ainda não está conectado.**

```bash
# Diagnóstico dos marcadores (exemplo com três erros; retorna 1)
poetry run compilador --semantic exemplos/semantica/gensets_com_erros.tonto

# Coerção e revalidação de uma cópia em memória (não modifica os arquivos)
poetry run compilador --semantic --coerce exemplos/semantica/gensets_com_erros.tonto

# Exemplo sem divergências nos marcadores locais
poetry run compilador --semantic exemplos/semantica/gensets_validos.tonto
```

Somente `disjoint` pode ser ajustado, em contextos restritos e conforme os
exemplos do PDF. Classes e relações ausentes não são inventadas. Código 0 nesse
modo significa ausência de erros pendentes **nas verificações executadas**,
não certificação dos seis ODPs; com coerção, refere-se à cópia analisada.
Sem as opções novas, a execução anterior permanece igual.

## Estrutura e documentação

| Arquivo | Responsabilidade |
| --- | --- |
| `src/compilador/lex.py` | Tokens, erros léxicos e localização |
| `src/compilador/syntax.py` | Parser PLY, construção da AST e recuperação |
| `src/compilador/ast.py` | Nós da árvore sintática |
| `src/compilador/symbols.py` | Tabela de símbolos, escopos e resolução |
| `src/compilador/packages.py` | Seleção e leitura de arquivos, registro em duas etapas |
| `src/compilador/reports.py` | Síntese e apresentação unificada de diagnósticos |
| `src/compilador/semantic_errors.py` | Tratamento semântico, contrato dos reconhecedores e coerções limitadas |
| `src/compilador/main.py` | Interface de linha de comando |

- [Gramática de referência](gramatica.md).
- [Documentação das mudanças de erros, relatórios e integração](docs/erros-relatorios-integracao.md): contratos, recuperação, tabela de dispersão, testes e limitações.
- [Erros semânticos e coerção](docs/erros-semanticos-coercao.md): mudanças desta etapa, exemplos, interpretações e integração pendente com os reconhecedores.
