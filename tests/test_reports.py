import copy
import io
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from tempfile import TemporaryDirectory

from compilador.main import main
from compilador.packages import load_project
from compilador.reports import build_summary, render_report


class ReportsTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory(prefix='compilador-reports-')
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)

    def source(self, name, code):
        path = self.directory / name
        path.write_text(code, encoding='utf-8')
        return path

    def test_summary_counts_declarations_not_identifier_occurrences(self):
        code = '\n'.join([
            'package A',
            'kind Person { age : number [1] [1] -- owns -- [0..*] Car }',
            'kind Car', 'subkind Student specializes Person',
            'datatype Money specializes number',
            'enum Status { Active1, Inactive2 }',
            'disjoint complete genset Roles where Student specializes Person',
            'relation Person [1] -- [1] Car',
        ])
        project = load_project(self.source('a.tonto', code))
        self.assertEqual(project.diagnostics, [])
        summary = build_summary(project)
        self.assertEqual(summary['counts'], {
            'package': 1, 'class': 3, 'attribute': 1, 'relation': 2,
            'datatype': 1, 'enum': 1, 'enum_value': 2, 'genset': 1,
            'internal_relation': 1, 'external_relation': 1,
        })
        self.assertFalse(summary['partial'])
        report = render_report(project)
        for expected in ['TABELA DE SÍNTESE', 'RELATÓRIO DE ERROS', 'Person.owns', 'Relação externa',
                         '(sem nome)', 'Active1, Inactive2', 'Geral: Person', 'disjoint: sim',
                         'complete: sim', 'Tipo-base: number', 'Nenhum erro encontrado.']:
            self.assertIn(expected, report)

    def test_reports_mutual_imports_and_groups_classes_by_package(self):
        self.source('a.tonto', 'package A\nimport B\nkind Alpha { peer : Beta }')
        self.source('b.tonto', 'package B\nimport A\nkind Beta { peer : Alpha }')
        project = load_project(self.directory)
        self.assertEqual(project.diagnostics, [])
        rows = build_summary(project)['rows']
        self.assertEqual({(row[0], row[2]) for row in rows if row[1] == 'Classe'}, {('A', 'Alpha'), ('B', 'Beta')})
        self.assertIn('importações: B', render_report(project))

    def test_syntax_error_marks_summary_partial_even_with_ast(self):
        path = self.source('a.tonto', 'package A\nkind Person { name string }\nkind Car')
        project = load_project(path)
        self.assertIsNotNone(project.asts[str(path.resolve())])
        report = render_report(project)
        self.assertIn('síntese pode estar incompleta', report)
        self.assertIn('Sintático / unexpected_token', report)
        self.assertIn(f'{path.resolve()}:2:', report)
        self.assertNotIn('Nenhum erro encontrado.', report)

    def test_duplicate_is_reported_but_not_counted_twice(self):
        project = load_project(self.source('a.tonto', 'kind Person\nkind Person'))
        self.assertEqual(build_summary(project)['counts']['class'], 1)
        self.assertIn('duplicate_declaration', render_report(project))

    def test_rendering_does_not_change_project(self):
        project = load_project(self.source('a.tonto', 'kind Person { age : number }'))
        diagnostics = copy.deepcopy(project.diagnostics)
        symbols = dict(project.symbols)
        first = render_report(project)
        self.assertEqual(first, render_report(project))
        self.assertEqual(project.diagnostics, diagnostics)
        self.assertEqual(project.symbols, symbols)

    def test_missing_file_has_suggestion_and_no_invented_position(self):
        report = render_report(load_project(self.directory / 'missing.tonto'))
        self.assertIn('file_read_error', report)
        self.assertIn('localização não disponível', report)
        self.assertIn('Sugestão:', report)

    def test_semantic_diagnostic_uses_ast_location(self):
        project = load_project(self.source('a.tonto', 'package A\nkind Person {\n car : Unknown\n}'))
        diagnostic, = project.diagnostics
        self.assertEqual((diagnostic['stage'], diagnostic['line'], diagnostic['column']), ('resolution', 3, 2))

    def test_diagnostics_from_different_files_do_not_leak(self):
        first = self.source('a.tonto', '\n\nkind')
        second = self.source('b.tonto', 'kind Person { age : Unknown }')
        project = load_project([first, second])
        self.assertEqual([(d['code'], d['file'], d['line']) for d in project.diagnostics], [
            ('unexpected_eof', str(first.resolve()), 3),
            ('unresolved_reference', str(second.resolve()), 1),
        ])

    def test_cli_accepts_directory_and_returns_success(self):
        self.source('a.tonto', 'kind Person')
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertIsNone(main([str(self.directory)]))
        self.assertIn('Nenhum erro encontrado.', output.getvalue())

    def test_cli_accepts_multiple_files(self):
        first = self.source('a.tonto', 'package A\nimport B\nkind Alpha')
        second = self.source('b.tonto', 'package B\nimport A\nkind Beta')
        with redirect_stdout(io.StringIO()):
            self.assertIsNone(main([str(first), str(second)]))

    def test_cli_invalid_ontology_returns_one(self):
        path = self.source('a.tonto', 'kind')
        output = io.StringIO()
        with redirect_stdout(output), self.assertRaises(SystemExit) as raised:
            main([str(path)])
        self.assertEqual(raised.exception.code, 1)
        self.assertIn('unexpected_eof', output.getvalue())

    def test_cli_missing_file_returns_one(self):
        with redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as raised:
            main([str(self.directory / 'missing.tonto')])
        self.assertEqual(raised.exception.code, 1)

    def test_cli_no_arguments_returns_usage_error(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            main([])
        self.assertEqual(raised.exception.code, 2)

    def test_versioned_valid_example_covers_all_basic_types(self):
        folder = Path(__file__).resolve().parents[1] / 'exemplos' / 'integracao'
        project = load_project(folder)
        self.assertEqual(project.diagnostics, [])
        self.assertEqual(set(project.packages), {'Pessoas', 'Bens'})
        self.assertEqual({r.basic_type for r in project.references if r.basic_type},
                         {'number', 'string', 'boolean', 'date', 'time', 'datetime'})
        self.assertEqual(build_summary(project)['counts']['class'], 4)

    def test_versioned_invalid_example_has_four_errors_and_keeps_valid_classes(self):
        path = Path(__file__).resolve().parents[1] / 'exemplos' / 'erros_sintaticos.tonto'
        project = load_project(path)
        self.assertEqual([d['code'] for d in project.diagnostics],
                         ['unexpected_token'] * 3 + ['unresolved_reference'])
        self.assertEqual(build_summary(project)['counts']['class'], 4)


if __name__ == '__main__':
    unittest.main()
