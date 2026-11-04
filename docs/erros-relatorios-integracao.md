# Erros, relatórios e integração — Colega 3

## Objetivo e escopo

Documento das mudanças implementadas na branch `feat/erros-relatorios-integracao`.
Esta entrega conecta o parser ao processamento de projetos, registra erros
sintáticos, recupera partes válidas e produz as duas visualizações exigidas.

A implementação reutiliza o trabalho de gramática/AST e de tabela de símbolos/
pacotes. Não substitui a tabela nem adiciona validações ontológicas completas.

## Estado anterior

- `main.py` apenas imprimia o resultado do parser.
- `p_error()` imprimia o token, sem retornar um diagnóstico ao projeto.
- Uma AST parcial podia existir mesmo com a lista de diagnósticos vazia.
- O relatório antigo contava ocorrências de tokens como se fossem declarações.
- Os nós produzidos pelo parser não propagavam linha e coluna.
- Havia uma regressão: uma relação após atributo sem cardinalidade era perdida.
- Resultado inicial: 68 testes aprovados e uma falha, entre 69 testes.

## Fluxo integrado

```text
main(paths)
  → load_project(paths)
      → selecionar arquivos sem repetir caminhos
      → ler UTF-8 / UTF-8 com BOM
      → parse_code(source)
          → análise léxica
          → adaptação de tokens para desambiguar cardinalidades
          → parser PLY com tracking e recuperação
          → ParseResult(tree, diagnostics)
      → incorporar diagnósticos com o caminho do arquivo
      → registrar as declarações recuperadas na tabela
      → resolver importações e referências após registrar todos os arquivos
  → render_report(project)
      → tabela de síntese
      → relatório unificado de erros
```

O carregamento continua não recursivo. Importações mútuas não exigem analisar
novamente um arquivo: todas as declarações são registradas antes da resolução.

## Contratos de programação

### Parser

```python
from compilador.syntax import parse_code

result = parse_code(codigo, filename="Pessoa.tonto")
tree = result.tree
diagnostics = result.diagnostics
```

`parse_code()` não imprime. A árvore pode ser completa, parcial ou `None`.
A presença de árvore não indica sucesso: é necessário verificar os diagnósticos.
A API anterior apenas imprimia a árvore; seus consumidores devem migrar para
`ParseResult`. Use essa função, não `parser.parse()` diretamente: o adaptador
de tokens e a inicialização de estado fazem parte do contrato da análise.

O parser e o lexer globais são reutilizados sequencialmente, com estado
reinicializado a cada chamada. A API não é segura para execução concorrente.

### Diagnósticos

Todos os diagnósticos mantêm o formato já utilizado pela tabela:

```python
{
    "stage": "syntax",
    "code": "unexpected_token",
    "file": "Pessoa.tonto",
    "line": 4,
    "column": 10,
    "message": "Token 'string' inesperado (STRING_TYPE).",
    "suggestion": "Verifique se falta ':' entre o nome e o tipo do atributo."
}
```

Etapas: `lexical`, `syntax`, `symbols`, `packages` e `resolution`.
Novos códigos: `unexpected_token` e `unexpected_eof`.
Erros léxicos continuam usando `lexical_error`.

Erros de fim de arquivo apontam para a posição após o último caractere, com
tratamento de LF, CRLF e CR. Erros de leitura não recebem posição inventada.
Quando não existe AST nem erro sintático específico, o carregador mantém o
diagnóstico de proteção `ast_unavailable`; não o duplica após um erro sintático.

### Posições na AST

O parser executa com `tracking=True`. Os nós de declaração, atributos e relações
recebem `line` e `column`, preservando seus construtores existentes. Nas
declarações nomeadas, a localização aponta para o identificador declarado; nos
atributos, para o nome; nas relações internas, para a cardinalidade inicial.

`SymbolTable` já consulta esses campos, portanto erros de duplicidade, imports
e referências passam a ter localização sem uma segunda busca textual.
Valores de enumeração ainda são strings e não têm posição individual; essa
limitação não foi escondida com coordenadas fictícias.

## Recuperação sintática

1. `p_error()` registra o problema e sugere tratamento conforme o estado do parser.
2. Produções com o símbolo especial `error` tentam retomar em atributos,
   relações e fechamentos de bloco, mantendo os membros já reduzidos.
3. A regra de recuperação entre instruções preserva instruções anteriores.
4. Se uma nova declaração aparece onde o estado aceita `}`, o adaptador pode
   devolver um fechamento sintético e reapresentar o token da nova declaração.
   A inserção é limitada a uma tentativa por posição, evitando repetição infinita.
5. Se o parser termina sem árvore, são preservadas as instruções completas já
   reduzidas naquela chamada; a declaração incompleta pode ser descartada.

O fechamento sintético não altera o arquivo nem converte a entrada em válida:
o diagnóstico permanece registrado e a CLI retorna erro. A recuperação é uma
heurística, não uma promessa de reconstruir toda entrada arbitrariamente
corrompida. Delimitadores aninhados malformados podem levar à perda de trechos.
Um erro também pode gerar diagnósticos de referência adicionais se a declaração
referenciada não puder ser recuperada.

Não se utiliza quebra de linha como terminador: construções multilinha são
permitidas. A supressão de mensagens em cascata continua seguindo a recuperação
do PLY; não se promete uma mensagem para cada caractere incorreto.

## Correções pontuais de integração com a gramática

### Atributo seguido de relação

A cardinalidade opcional de um atributo competia com a cardinalidade inicial
da relação seguinte. O adaptador identifica uma sequência de cardinalidade
fechada imediatamente seguida por operador de relação e muda somente seu token
inicial para `RELATION_L_BRACKET`, exclusivo do parser.

Comentários e espaços já foram removidos pelo lexer; não há dependência de
linhas. Cardinalidades de atributos continuam usando `L_BRACKET`. A regra
`relation_cardinality` consome a forma contextual e constrói a mesma AST.
O lexer público e seus testes permanecem inalterados. A segunda cardinalidade
da relação continua usando a produção normal.

### Outras correções

- `ID_TYPE` é aceito em nomes de datatypes e em referências de tipo.
- Enumerações aceitam um ou mais valores, em vez de exigir ao menos dois.
- Classes e datatypes aceitam blocos vazios sem produzir falso erro.
- A união `Instruction` inclui `RelationOut`.
- O parser não grava `parsetab.py` ou `parser.out` durante importação/execução.

## Tabela de símbolos como tabela de dispersão

A implementação existente em `symbols.py` usa o `dict` nativo do Python como
tabela de dispersão. Não se trata de uma tabela manual com vetor de buckets.
O cálculo de hash, tratamento de colisões e redimensionamento são realizados
pelo runtime do Python; não foram implementados novamente pelo grupo.

- `symbols`: chave `(pacote, proprietário, categoria, nome)` → `Symbol`.
- `_by_name`: chave `(pacote, proprietário, nome)` → lista de símbolos para
  consultas e verificação de conflitos entre categorias no mesmo namespace.
- `packages`: nome do pacote → símbolo do pacote.
- `imports`: nome do pacote → lista de referências de importação.

Atributos e relações internas têm o proprietário como escopo. Classes, enums
e datatypes compartilham o namespace de tipos; isso impede que a categoria
na chave esconda uma duplicidade. Relações anônimas recebem identificadores
internos distintos. Cada símbolo conserva o nó original, arquivo e posição.

Consultas diretas por chave têm custo médio esperado constante, sujeito ao
comportamento da tabela hash. Consultas de relatório como `members()`,
`relations()` e `symbols_in_package()` percorrem símbolos; não são O(1).
Caso o professor exija uma implementação manual de dispersão, esse requisito
precisa ser alinhado com o responsável pela tabela e não está resolvido por
uma mera troca de descrição na documentação.

## Síntese e relatório

`build_summary(project)` retorna contagens, linhas detalhadas e indicação de
resultado potencialmente parcial. `render_report(project)` retorna texto.
Essas funções não imprimem, não alteram a AST e não repetem a resolução.

As contagens usam símbolos registrados, não ocorrências de identificadores.
Duplicatas rejeitadas não são contadas duas vezes. O escopo implícito sem
declaração de pacote é mostrado como tal e entra em “Pacotes/escopos”.

Os detalhes incluem importações, classes por pacote, estereótipos,
especializações, atributos, tipos, metas, enumerações, generalizações e relações
com extremos e cardinalidades. Relações internas mostram sua classe
proprietária. Relações anônimas são exibidas como “sem nome”.

O relatório de erros ordena por arquivo e posição e identifica etapa, código,
mensagem e sugestão. Havendo qualquer diagnóstico, a síntese recebe aviso de
possível incompletude. A formatação é textual; não inclui exportação JSON/HTML.

## CLI e exemplos

```bash
poetry run compilador exemplos/integracao
poetry run compilador exemplos/integracao/Pessoas.tonto exemplos/integracao/Bens.tonto
poetry run compilador exemplos/erros_sintaticos.tonto
```

`main(argv=None)` aceita um ou mais arquivos/pastas. Códigos de saída: `0` sem
erros; `1` com diagnósticos; `2` com argumentos inválidos. A visualização léxica
antiga deixa de ser a saída principal; `lex.analyze()` e `lex.tokenize()` continuam
disponíveis para uso programático.

O exemplo de integração cobre os seis tipos básicos, tipo complexo,
enumeração, generalizações, relações internas/externas e importações mútuas.
O exemplo de erros demonstra dois atributos malformados, recuperação de `}`
ausente e uma referência não resolvida.

## Testes e validação

```bash
poetry run python -m unittest discover -s tests
poetry run test
git diff --check
```

Os testes existentes de pacotes foram atualizados somente onde mudou o
contrato: posições agora disponíveis e erro sintático específico em vez de
`ast_unavailable`. A regressão da relação foi mantida e passou.

`tests/test_syntax.py` cobre localização, ausência de impressão, erros múltiplos,
recuperação de membros e declarações, EOF, diferentes quebras de linha,
cardinalidades e reinicialização entre chamadas.

`tests/test_reports.py` cobre contagens, agrupamento por pacote, imports mútuos,
síntese parcial, duplicatas, apresentação, localização semântica, isolamento de
arquivos, exemplos versionados e códigos de saída da CLI.

Resultado final: **98 testes aprovados** (69 anteriores e 29 novos). Os exemplos
válido e inválido também foram executados pela CLI, com códigos de saída `0`
e `1`, respectivamente. Uma verificação adicional com 2.000 entradas aleatórias
determinísticas não encontrou exceções não tratadas. Isso é uma checagem de
robustez, não uma prova de correção da recuperação para qualquer entrada.

