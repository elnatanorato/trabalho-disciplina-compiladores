import io
import unittest
from contextlib import redirect_stdout

from compilador import ast
from compilador.syntax import parse_code


class SyntaxDiagnosticsTests(unittest.TestCase):
    def classes(self, result):
        return {node.name: node for node in result.tree.instructions if isinstance(node, ast.DeclClass)}

    def test_valid_constructs_and_positions(self):
        result = parse_code('package A\nkind Person { age : number }\ndatatype DocumentDataType specializes string\nenum Status { Active1 }')
        self.assertEqual(result.diagnostics, [])
        person = self.classes(result)['Person']
        self.assertEqual((person.line, person.column), (2, 6))
        self.assertEqual((person.attributes[0].line, person.attributes[0].column), (2, 15))

    def test_empty_class_and_datatype_bodies(self):
        result = parse_code('kind Person {}\ndatatype Address {}')
        self.assertEqual(result.diagnostics, [])
        self.assertEqual(len(result.tree.instructions), 2)

    def test_missing_colon_has_file_location_and_suggestion_without_printing(self):
        output = io.StringIO()
        with redirect_stdout(output):
            result = parse_code('kind Person {\n name string\n}', 'person.tonto')
        self.assertEqual(output.getvalue(), '')
        diagnostic, = result.diagnostics
        self.assertEqual((diagnostic['stage'], diagnostic['code']), ('syntax', 'unexpected_token'))
        self.assertEqual((diagnostic['file'], diagnostic['line'], diagnostic['column']), ('person.tonto', 2, 7))
        self.assertIn("':'", diagnostic['suggestion'])

    def test_recovers_members_before_and_after_an_error(self):
        result = parse_code('kind Person { age : number bad string good : boolean }\nkind Car')
        self.assertEqual(len(result.diagnostics), 1)
        self.assertEqual(set(self.classes(result)), {'Person', 'Car'})
        self.assertEqual([a.name for a in self.classes(result)['Person'].attributes], ['age', 'good'])

    def test_multiple_independent_errors_in_same_block(self):
        result = parse_code('kind A { bad string good : number badAgain boolean last : date }')
        self.assertEqual(len(result.diagnostics), 2)
        self.assertEqual([a.name for a in self.classes(result)['A'].attributes], ['good', 'last'])

    def test_recovers_before_and_between_declarations(self):
        for code in ['garbage\nkind Good\nkind Other', 'kind Good\nwrong\nkind Other']:
            with self.subTest(code=code):
                result = parse_code(code)
                self.assertEqual(len(result.diagnostics), 1)
                self.assertEqual(set(self.classes(result)), {'Good', 'Other'})

    def test_missing_closing_brace_preserves_next_declaration(self):
        result = parse_code('kind Person { age : number\nkind Car')
        self.assertEqual(len(result.diagnostics), 1)
        self.assertIn("'}'", result.diagnostics[0]['suggestion'])
        self.assertEqual(set(self.classes(result)), {'Person', 'Car'})

    def test_eof_preserves_previously_completed_declarations(self):
        result = parse_code('package A\nkind Good\nkind Broken { age : number')
        self.assertEqual([d['code'] for d in result.diagnostics], ['unexpected_eof'])
        self.assertEqual(set(self.classes(result)), {'Good'})

    def test_incomplete_first_declaration_has_no_ast(self):
        result = parse_code('kind')
        self.assertIsNone(result.tree)
        self.assertEqual(result.diagnostics[0]['code'], 'unexpected_eof')
        self.assertEqual((result.diagnostics[0]['line'], result.diagnostics[0]['column']), (1, 5))

    def test_missing_bracket_recovers_next_class(self):
        result = parse_code('kind Person { age : number [1..* -- [1] Car }\nkind Car')
        self.assertTrue(result.diagnostics)
        self.assertIn("']'", result.diagnostics[0]['suggestion'])
        self.assertIn('Car', self.classes(result))

    def test_relation_after_attribute_has_its_own_cardinality(self):
        for separator in [' ', '\n', '\r\n', '\r', '\n// comentário\n']:
            with self.subTest(separator=repr(separator)):
                result = parse_code('kind Car\nkind Person { age : number' + separator + '[0..*] -- owns -- [1] Car }')
                self.assertEqual(result.diagnostics, [])
                person = self.classes(result)['Person']
                self.assertIsNone(person.attributes[0].cardinality)
                self.assertEqual(person.relations[0].cardinality1, ast.Cardinality(0, '*'))

    def test_attribute_cardinality_and_metadata_are_not_taken_by_relation(self):
        result = parse_code('kind Car\nkind Person { age : number [1] {ordered} [0..*] <>-- owns -- [1] Car }')
        self.assertEqual(result.diagnostics, [])
        person = self.classes(result)['Person']
        self.assertEqual(person.attributes[0].cardinality, ast.Cardinality(1, None))
        self.assertEqual(person.attributes[0].metas, [ast.Meta.ORDERED])
        self.assertEqual(person.relations[0].cardinality1, ast.Cardinality(0, '*'))

    def test_resets_diagnostics_and_positions_between_calls(self):
        first = parse_code('\n\nkind', 'first.tonto')
        second = parse_code('kind Person', 'second.tonto')
        self.assertEqual(first.diagnostics[0]['line'], 3)
        self.assertEqual(second.diagnostics, [])
        self.assertEqual(self.classes(second)['Person'].line, 1)

    def test_eof_position_handles_all_line_endings(self):
        for ending in ['\n', '\r\n', '\r']:
            with self.subTest(ending=repr(ending)):
                result = parse_code('kind Person' + ending + 'kind')
                self.assertEqual((result.diagnostics[0]['line'], result.diagnostics[0]['column']), (2, 5))


if __name__ == '__main__':
    unittest.main()
