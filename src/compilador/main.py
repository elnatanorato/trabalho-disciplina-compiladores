from compilador.lex import tokenize


def main():
    tokens = tokenize("package Teste")
    for token in tokens:
        print(token)


if __name__ == "__main__":
    main()
