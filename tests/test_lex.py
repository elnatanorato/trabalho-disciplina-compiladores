import unittest

from compilador.lex import analyze, tokenize


class TokenizePositionTests(unittest.TestCase):

    # Testa se o analisador consegue ler um bloco básico de código e identificar
    # corretamente os tipos de token, seus valores, linhas e colunas exatas.
    def test_tokenizes_basic_example_with_line_and_column(self):
        source = "kind Person {\n    name : string\n}"

        result = [
            (token.type, token.value, token.lineno, getattr(token, "column", None))
            for token in tokenize(source)
        ]

        expected = [
            ("KIND", "kind", 1, 1),
            ("ID_CLASS", "Person", 1, 6),
            ("L_BRACE", "{", 1, 13),
            ("ID_RELATION", "name", 2, 5),
            ("COLON", ":", 2, 10),
            ("STRING_TYPE", "string", 2, 12),
            ("R_BRACE", "}", 3, 1),
        ]

        self.assertEqual(result, expected)

    # Garante que, ao rodar a análise mais de uma vez em textos diferentes, o contador recomeça do 1.
    def test_resets_line_number_between_analyses(self):
        tokenize("kind Person {\n}\n")

        result = [
            (token.type, token.value, token.lineno, token.column)
            for token in tokenize("package Test")
        ]

        expected = [
            ("PACKAGE", "package", 1, 1),
            ("ID_CLASS", "Test", 1, 9),
        ]

        self.assertEqual(result, expected)

    # Verifica se o analisador lida bem com formatos diversos de texto.
    def test_handles_empty_lines_tabs_and_different_line_endings(self):
        source = "kind Person {\r\r\tname : string\r}"

        result = [
            (token.type, token.value, token.lineno, token.column)
            for token in tokenize(source)
        ]

        expected = [
            ("KIND", "kind", 1, 1),
            ("ID_CLASS", "Person", 1, 6),
            ("L_BRACE", "{", 1, 13),
            ("ID_RELATION", "name", 3, 2),
            ("COLON", ":", 3, 7),
            ("STRING_TYPE", "string", 3, 9),
            ("R_BRACE", "}", 4, 1),
        ]

        self.assertEqual(result, expected)

    # Testa se todos os símbolos especiais estão sendo capturados e classificados individualmente.
    def test_recognizes_simple_and_composite_symbols(self):
        source = "{ } ( ) [ ] .. <>-- --<> * @ :"

        result = [
            (token.type, token.value, token.lineno, token.column)
            for token in tokenize(source)
        ]

        expected = [
            ("L_BRACE", "{", 1, 1),
            ("R_BRACE", "}", 1, 3),
            ("L_PAREN", "(", 1, 5),
            ("R_PAREN", ")", 1, 7),
            ("L_BRACKET", "[", 1, 9),
            ("R_BRACKET", "]", 1, 11),
            ("DOT_DOT", "..", 1, 13),
            ("L_AGGREGATION", "<>--", 1, 16),
            ("R_AGGREGATION", "--<>", 1, 21),
            ("STAR", "*", 1, 26),
            ("AT", "@", 1, 28),
            ("COLON", ":", 1, 30),
        ]

        self.assertEqual(result, expected)

    # Confirma o requisito de que o símbolo '@' seja separado da relação
    def test_separates_at_sign_from_relation_stereotype(self):
        result = [
            (token.type, token.value, token.lineno, token.column)
            for token in tokenize("@material")
        ]

        expected = [
            ("AT", "@", 1, 1),
            ("RELATION", "material", 1, 2),
        ]

        self.assertEqual(result, expected)

    # Assegura que quebras de linha sejam contadas devidamente
    def test_counts_crlf_as_single_line_break(self):
        source = "kind Person {\r\n    name : string\r\n}"

        result = [
            (token.type, token.value, token.lineno, token.column)
            for token in tokenize(source)
        ]

        expected = [
            ("KIND", "kind", 1, 1),
            ("ID_CLASS", "Person", 1, 6),
            ("L_BRACE", "{", 1, 13),
            ("ID_RELATION", "name", 2, 5),
            ("COLON", ":", 2, 10),
            ("STRING_TYPE", "string", 2, 12),
            ("R_BRACE", "}", 3, 1),
        ]

        self.assertEqual(result, expected)

    # Testa se o analisador não quebra ao achar caracteres inválidos.
    def test_collects_multiple_errors_and_continues_analysis(self):
        source = "kind Person $ {\n    ? name : string\n}"

        analysis = analyze(source)

        token_types = [token.type for token in analysis["tokens"]]

        error_positions = [
            (error["lexeme"], error["line"], error["column"])
            for error in analysis["errors"]
        ]

        expected_token_types = [
            "KIND",
            "ID_CLASS",
            "L_BRACE",
            "ID_RELATION",
            "COLON",
            "STRING_TYPE",
            "R_BRACE",
        ]

        expected_error_positions = [
            ("$", 1, 13),
            ("?", 2, 5),
        ]

        self.assertEqual(token_types, expected_token_types)
        self.assertEqual(error_positions, expected_error_positions)

        # Garante que os erros vêm com as sugestões de tratamento preenchidas.
        for error in analysis["errors"]:
            self.assertTrue(error["message"])
            self.assertTrue(error["suggestion"])


    # Verifica se símbolos complexos colados uns nos outros sejam divididos.
    def test_recognizes_adjacent_composite_symbols(self):
        analysis = analyze("[1..*]<>----<>")

        result = [
            (token.type, token.value, token.lineno, token.column)
            for token in analysis["tokens"]
        ]

        expected = [
            ("L_BRACKET", "[", 1, 1),
            ("NUMBER", 1, 1, 2),
            ("DOT_DOT", "..", 1, 3),
            ("STAR", "*", 1, 5),
            ("R_BRACKET", "]", 1, 6),
            ("L_AGGREGATION", "<>--", 1, 7),
            ("R_AGGREGATION", "--<>", 1, 11),
        ]

        self.assertEqual(result, expected)
        self.assertEqual(analysis["errors"], [])

    # Confirma se a lista de erros é limpa a cada nova análise.
    def test_clears_errors_between_analyses(self):
        first_analysis = analyze("$")
        second_analysis = analyze("kind")

        self.assertEqual(len(first_analysis["errors"]), 1)
        self.assertEqual(second_analysis["errors"], [])

    # Testa se o analisador mantém a imagem original do token.
    def test_preserves_original_lexeme(self):
        analysis = analyze("[03]")

        result = [
            (token.type, token.value, token.lexeme) for token in analysis["tokens"]
        ]

        expected = [
            ("L_BRACKET", "[", "["),
            ("NUMBER", 3, "03"),
            ("R_BRACKET", "]", "]"),
        ]

        self.assertEqual(result, expected)

    # Garante que linhas começadas com '//' sejam completamente ignoradas
    def test_ignore_comment(self):
        analysis = analyze("// comment package\ncomment // package\ncomment package //")

        result = [
            (token.type, token.value, token.lineno) for token in analysis["tokens"]
        ]

        expected = [
            ("ID_RELATION", "comment", 2),
            ("ID_RELATION", "comment", 3),
            ("PACKAGE", "package", 3),
        ]

        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
