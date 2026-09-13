import unittest

from compilador.lex import tokenize


class TokenizePositionTests(unittest.TestCase):
    def test_tokenizes_basic_example_with_line_and_column(self):
        source = "kind Person {\n    name : string\n}"

        result = [
            (
                token.type,
                token.value,
                token.lineno,
                getattr(token, "column", None)
            )
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


if __name__ == "__main__":
    unittest.main()
