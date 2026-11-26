# Tratamento de erros semânticos, coerção e integração

- catálogo de erros semânticos e sugestões, com a localização dos símbolos;
- apresentação de padrões completos, candidatos incompletos e bloqueados;
- verificação local, parcial, dos marcadores de gensets;
- coerção opcional desses marcadores numa cópia em memória, seguida de revalidação;
- interface de terminal, exemplos e testes.



## 3. Arquivos adicionados e alterados

| Arquivo | Mudança |
| --- | --- |
| `src/compilador/semantic_errors.py` | Contratos, catálogo, verificação parcial e coerção |
| `src/compilador/reports.py` | Cobertura, resultados semânticos, coerções e erros pendentes |
| `src/compilador/main.py` | Opções explícitas `--semantic` e `--coerce` |
| `tests/test_semantic_errors.py` | Testes da nova camada e execução real da CLI |
| `exemplos/semantica/gensets_com_erros.tonto` | Três divergências de marcadores |
| `exemplos/semantica/gensets_validos.tonto` | Contraparte sem essas divergências |
| `README.md` | Instruções de execução e indicação de cobertura parcial |


### `SemanticIssue`

Contém `code`, `subject` (um `Symbol` do projeto analisado) e `details` opcional.
`diagnostic()` retorna o mesmo contrato de sete campos já utilizado pelo projeto:

```python
{
    "stage": "semantic",
    "code": "phase_missing_sibling",
    "file": "modelo.tonto",
    "line": 8,
    "column": 7,
    "message": "...",
    "suggestion": "..."
}
```

Os códigos incluem:

| Regra | Código |
| --- | --- |
| Subkind sem kind | `subkind_missing_kind` |
| Role sem kind | `role_missing_kind` |
| Phase sem kind | `phase_missing_kind` |
| Phase sem irmã | `phase_missing_sibling` |
| Relator sem mediações suficientes | `relator_missing_mediations` |
| Relator sem material correspondente | `relator_missing_material` |
| Mode sem characterization | `mode_missing_characterization` |
| Mode sem externalDependence | `mode_missing_external_dependence` |
| RoleMixin sem roles suficientes | `rolemixin_missing_roles` |
| RoleMixin sem kinds distintos | `rolemixin_same_kind` |
| Falta de disjoint | `genset_missing_disjoint` |
| Disjoint em genset de roles, segundo o PDF | `role_genset_disjoint` |



### `PatternFinding`

Representa um candidato/resultado entregue pelo reconhecedor:

- `pattern`: `PatternKind` (`subkind`, `role`, `phase`, `relator`, `mode`, `roleMixin`);
- `subject`: símbolo que ancora o padrão;
- `missing`: tupla de violações confirmadas;
- `variant`: nome da alternativa/sobrecarga avaliada;
- `blocked`: motivo pelo qual o contexto ainda é inconclusivo.

Com `blocked` preenchido, o candidato fica **bloqueado**. Sem bloqueio e com
pendências, fica **incompleto**. Sem bloqueio nem pendências, fica **completo
segundo o reconhecedor que o forneceu**. Esta camada não certifica sua lógica.

### `SemanticCheck`

Agrega tuplas `issues`, `patterns`, `coverage` e `blocked`. As violações das
alternativas não bloqueadas entram automaticamente nos diagnósticos. Uma mesma
violação em várias listas é deduplicada por código, chave do símbolo e detalhes.

O reconhecedor deve selecionar os resultados relevantes antes de retorná-los:
hipóteses descartadas durante a busca de uma sobrecarga não devem ser enviadas
como violações confirmadas. Esta camada não decide entre alternativas e não
deve transformar uma alternativa rejeitada em erro de uma entrada válida.

Um candidato bloqueado não emite artificialmente erros de dependências ausentes:
uma referência não resolvida pode tornar impossível saber se a dependência
realmente falta. Essa distinção evita mensagens em cascata.

### Como conectar um reconhecedor

O contrato esperado é:

```python
def reconhecer_padroes(project) -> SemanticCheck:
    # Retornar os resultados reais; não modificar project nem imprimir.
    ...
```

Depois da implementação desse reconhecedor:

```python
from compilador.packages import load_project
from compilador.reports import render_report
from compilador.semantic_errors import analyze_semantics

project = load_project("pasta_da_ontologia")
analysis = analyze_semantics(
    project,
    recognizer=reconhecer_padroes,
    coerce=False,
)
print(render_report(analysis.project, semantic=analysis))
```

`reconhecer_padroes` A CLI atual só conecta a verificação local. Quando o
reconhecedor estiver disponível, deve ser passado na chamada de
`analyze_semantics()` em `main.py`.

O callback recebe a cópia de trabalho, não o projeto original. Seus resultados
devem usar símbolos **dessa cópia**. Ele é chamado novamente após coerções
efetivamente aplicadas e deve produzir resultados novos, sem manter estado
obsoleto ou modificar o projeto.

## 5. Interpretação de sobrecarga

O enunciado menciona “padrões incompletos identificados por sobrecarregamento”,
sem definir seu mecanismo. Por isso, não foi criada uma regra de seleção
arbitrária, nem um método que apenas se chama “sobrecarga”.

Esta camada **recebe e apresenta alternativas** identificadas por `variant`,
com suas pendências. A escolha das assinaturas, a identificação dos candidatos
e eventual resolução de ambiguidades pertencem ao reconhecedor. Apresentar
alternativas não equivale a implementar esse mecanismo. O grupo deve confirmar
a interpretação esperada com o professor antes de concluir esse requisito.

## 6. Verificação parcial implementada

`check_genset_flags()` considera um genset somente se:

1. Não há diagnósticos das etapas anteriores no projeto.
2. A referência ao geral está resolvida para uma classe `kind`.
3. Há pelo menos duas específicas, distintas e resolvidas.
4. Todas têm o mesmo estereótipo e especializam diretamente aquele mesmo geral.
5. A resolução utiliza a identidade dos símbolos, não a igualdade textual dos nomes.

Nesse contexto:

- phases e subkinds precisam de `disjoint`, conforme os exemplos do PDF;
- gensets de roles não usam `disjoint`, segundo a orientação específica do PDF;
- `complete` continua opcional e não é alterado.

Gensets mistos, RoleMixin, hierarquias indiretas ou contextos incompletos ficam
fora do escopo local, com indicação explícita no relatório. Não são
automaticamente considerados inválidos. A verificação também não detecta
classes sem genset ou sem irmã; essas regras continuam para os reconhecedores.

A restrição de disjoint em roles é um **critério desta tarefa**, não uma afirmação
universal sobre todos os modelos OntoUML. Confirmar a aplicação com o professor.

## 7. Coerção: política, execução e limites

Na TONTO declarativa não se trata de promover números para outro tipo como em
uma expressão aritmética. A interpretação implementada é uma **normalização
contextual da representação semântica** para atender aos marcadores canônicos.
O professor deve confirmar que essa interpretação atende à técnica solicitada.

O modo padrão apenas diagnostica. A opção explícita `--coerce` autoriza:

| Problema confirmado | Transformação |
| --- | --- |
| Phase/subkind sem disjoint | `is_disjoint: False → True` |
| Role com disjoint | `is_disjoint: True → False` |

Adicionar ou retirar disjoint muda uma restrição do modelo; não é inferência
segura da intenção do autor. A autorização é explícita e a mudança é exibida.

`analyze_semantics()` faz `deepcopy` do projeto inteiro, preservando na cópia
as ligações entre AST, símbolos e referências. Guarda a avaliação inicial,
aplica somente as duas transformações locais e reavalia. O objeto original,
sua lista de diagnósticos e os arquivos permanecem inalterados.

O registro `AppliedCoercion` contém chave do símbolo, campo alterado, valores
anterior/posterior e o diagnóstico original. Problemas corrigidos aparecem
separados dos erros ainda pendentes. Aplicar o processo de novo sobre a cópia
já corrigida não repete a transformação.

Não existe mecanismo de execução de ações arbitrárias retornadas pelo callback.
O analisador **não inventa kinds, phases irmãs, participantes, mediações ou
relações materiais**. Não troca estereótipos nem altera heranças para esconder
violações. Esses casos recebem orientações quando o reconhecedor os reporta.

Erros léxicos, sintáticos, de leitura ou de resolução bloqueiam globalmente a
verificação local e sua coerção. É uma política conservadora inicial: os colegas
podem posteriormente trabalhar no bloqueio por dependência/arquivo, preservando
o cuidado com ASTs parciais.

## 8. Execução e interpretação da saída

```bash
# Diagnostica três problemas de marcadores; retorna 1.
poetry run python -m compilador.main --semantic exemplos/semantica/gensets_com_erros.tonto

# Aplica três coerções em memória, revalida e retorna 0 neste exemplo.
poetry run python -m compilador.main --semantic --coerce exemplos/semantica/gensets_com_erros.tonto

# Nenhuma divergência nos marcadores locais; retorna 0.
poetry run python -m compilador.main --semantic exemplos/semantica/gensets_validos.tonto
```

As formas `poetry run compilador ...` continuam disponíveis. Sem `--semantic`,
a execução anterior permanece igual. `--coerce` sem `--semantic` retorna erro
de uso (código 2).

A saída informa a cobertura executada e que o reconhecedor dos seis ODPs ainda
não está conectado. Seções de padrões completos/incompletos/bloqueados estão
prontas para receber seus resultados, mas não apresentam resultados fictícios.

Código 0 significa **nenhum erro pendente nas verificações executadas**, e não
“todos os padrões estão corretos”. Com coerção, vale para a cópia em memória:
é necessário ajustar a fonte para persistir as correções. Ao executar novamente
o modo de diagnóstico sobre a fonte original, os problemas reaparecem.

O retorno `analysis.diagnostics` fica separado de `project.diagnostics` para não
alterar o trabalho da resolução. `render_report(..., semantic=analysis)` combina
as duas listas apenas para apresentação e usa a cópia analisada na síntese.
Consumidores programáticos também precisam considerar ambas as listas.

## 9. Testes

```bash
poetry run python -m unittest discover -s tests
git diff --check
```


