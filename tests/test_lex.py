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

if __name__ == "__main__":
    unittest.main()