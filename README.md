# Analisador Léxico para TONTO (Textual Ontology Language)

Projeto desenvolvido como requisito de avaliação para a disciplina de Compiladores.

O objetivo deste software é realizar a análise léxica de arquivos contendo ontologias especificadas na linguagem TONTO, identificando seus componentes, validando a corretude dos caracteres e gerando relatórios de síntese.

## Funcionalidades

- Leitura de código-fonte a partir de arquivos `.tonto`.
- Classificação de tokens de acordo com as especificações da linguagem (estereótipos de classes, relações, meta-atributos, tipos de dados e palavras reservadas).
- Visão analítica dos tokens, detalhando linha, coluna, lexema e classificação de cada elemento encontrado.
- Geração de tabela de síntese com o quantitativo de instâncias, classes, relações e palavras-chave.
- Sistema de tratamento de erros léxicos que identifica a localização exata de caracteres inválidos e fornece sugestões de correção, permitindo que a análise prossiga sem interrupções bruscas.

## Tecnologias e Pré-requisitos

- Python
- Biblioteca PLY (Python Lex-Yacc) para a construção do analisador léxico.
- Gerenciador de dependências [Poetry](https://python-poetry.org/).

## Instalação

Clone este repositório em sua máquina local. Na raiz do projeto, execute o comando abaixo para instalar as dependências necessárias através do Poetry:

```bash
poetry install
```
## Para Executar

Para realizar a análise léxica de um arquivo, utilize o comando abaixo informando o caminho do arquivo .tonto como argumento:

```bash
poetry run compilador {input.tonto}
```

## Execução dos Testes

Para executar a suíte de testes rode:

```bash
poetry run test
```
