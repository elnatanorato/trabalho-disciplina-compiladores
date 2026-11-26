import copy
import io
import subprocess
import sys
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from tempfile import TemporaryDirectory

from compilador.main import main
from compilador.packages import load_project
from compilador.reports import render_report
from compilador.semantic_errors import (
    ISSUE_CATALOG, PatternFinding, PatternKind, SemanticCheck, SemanticIssue,
    analyze_semantics, check_genset_flags,
)


class SemanticErrorTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory(prefix='compilador-semantic-')
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)

    def source(self, code, name='model.tonto'):
        path = self.folder / name
        path.write_text(code, encoding='utf-8')
        return path

    def genset(self, stereotype='phase', flag='', parent='Pessoa'):
        return (f'package Modelo\nkind Pessoa\n'
                f'{stereotype} Primeiro specializes {parent}\n'
                f'{stereotype} Segundo specializes {parent}\n'
                f'{flag} genset Grupo {{ general Pessoa specifics Primeiro, Segundo }}')

    def load(self, code):
        return load_project(self.source(code))

    def test_missing_disjoint_in_phases_and_subkinds(self):
        for stereotype in ['phase', 'subkind']:
            with self.subTest(stereotype=stereotype):
                project = self.load(self.genset(stereotype))
                result = analyze_semantics(project)
                diagnostic, = result.diagnostics
                self.assertEqual(diagnostic['code'], 'genset_missing_disjoint')
                self.assertEqual(diagnostic['stage'], 'semantic')
                self.assertEqual((diagnostic['line'], diagnostic['column']), (5, 9))
                self.assertEqual(diagnostic['file'], str((self.folder / 'model.tonto').resolve()))
                self.assertTrue(diagnostic['suggestion'])

    def test_role_disjoint_uses_task_specific_rule(self):
        result = analyze_semantics(self.load(self.genset('role', 'disjoint')))
        self.assertEqual([d['code'] for d in result.diagnostics], ['role_genset_disjoint'])

    def test_complete_marker_is_optional(self):
        for stereotype, flag in [('phase', 'disjoint'), ('subkind', 'disjoint'), ('role', '')]:
            for complete in ['', ' complete']:
                with self.subTest(stereotype=stereotype, complete=complete):
                    result = analyze_semantics(self.load(self.genset(stereotype, flag + complete)))
                    self.assertEqual(result.diagnostics, [])

    def test_no_pattern_is_certified_by_flag_checks(self):
        result = analyze_semantics(self.load(self.genset('phase', 'disjoint')))
        self.assertEqual(result.final.patterns, ())
        self.assertFalse(result.recognizer_used)
        self.assertIn('COBERTURA PARCIAL', render_report(result.project, semantic=result))

    def test_coercion_changes_copy_then_revalidates(self):
        project = self.load(self.genset())
        original = project.table.lookup('Grupo', 'Modelo')[0]
        result = analyze_semantics(project, coerce=True)
        self.assertFalse(original.node.is_disjoint)
        self.assertTrue(result.project.table.lookup('Grupo', 'Modelo')[0].node.is_disjoint)
        self.assertEqual(len(result.initial.diagnostics), 1)
        self.assertEqual(result.diagnostics, [])
        correction, = result.corrections
        self.assertEqual((correction.field, correction.before, correction.after), ('is_disjoint', False, True))

    def test_coercion_can_remove_role_disjoint(self):
        result = analyze_semantics(self.load(self.genset('role', 'disjoint')), coerce=True)
        correction, = result.corrections
        self.assertEqual((correction.before, correction.after), (True, False))
        self.assertFalse(result.project.table.lookup('Grupo', 'Modelo')[0].node.is_disjoint)

    def test_coercion_preserves_files_ast_symbols_and_diagnostics(self):
        path = self.source(self.genset())
        contents = path.read_bytes()
        project = load_project(path)
        trees = copy.deepcopy(project.asts)
        diagnostics = copy.deepcopy(project.diagnostics)
        keys = set(project.symbols)
        analyze_semantics(project, coerce=True)
        self.assertEqual(path.read_bytes(), contents)
        self.assertEqual(project.diagnostics, diagnostics)
        self.assertEqual(set(project.symbols), keys)
        for filename in trees:
            self.assertEqual(project.asts[filename].instructions, trees[filename].instructions)

    def test_copy_preserves_links_between_ast_symbols_and_references(self):
        result = analyze_semantics(self.load(self.genset()), coerce=True)
        symbol = result.project.table.lookup('Grupo', 'Modelo')[0]
        tree, = result.project.asts.values()
        self.assertIs(symbol.node, tree.instructions[-1])
        references = [r for r in result.project.references if r.source is symbol]
        self.assertEqual(len(references), 3)
        self.assertTrue(all(result.project.symbols[r.target.key] is r.target for r in references))

    def test_repeated_analysis_does_not_duplicate_diagnostics(self):
        project = self.load(self.genset())
        first = analyze_semantics(project)
        second = analyze_semantics(project)
        self.assertEqual(first.diagnostics, second.diagnostics)
        self.assertEqual(project.diagnostics, [])

    def test_coercion_is_idempotent_on_corrected_copy(self):
        first = analyze_semantics(self.load(self.genset()), coerce=True)
        second = analyze_semantics(first.project, coerce=True)
        self.assertEqual(second.corrections, ())
        self.assertEqual(second.diagnostics, [])

    def test_errors_in_earlier_stages_block_local_coercion(self):
        for suffix in ['\nkind Broken { name string }', '\nkind Broken { car : Unknown }', '\n$']:
            with self.subTest(suffix=suffix):
                result = analyze_semantics(self.load(self.genset() + suffix), coerce=True)
                self.assertTrue(result.project.diagnostics)
                self.assertTrue(result.final.blocked)
                self.assertEqual(result.corrections, ())
                self.assertEqual(result.diagnostics, [])

    def test_unknown_parent_is_not_repaired_or_reported_twice(self):
        result = analyze_semantics(self.load(self.genset(parent='Unknown')), coerce=True)
        self.assertEqual(result.corrections, ())
        self.assertEqual(result.diagnostics, [])
        self.assertEqual({d['code'] for d in result.project.diagnostics}, {'unresolved_reference'})

    def test_unrelated_or_mixed_specifics_are_not_coerced(self):
        code = self.genset().replace('phase Segundo specializes Pessoa', 'role Segundo specializes Pessoa')
        result = analyze_semantics(self.load(code), coerce=True)
        self.assertEqual(result.corrections, ())
        self.assertTrue(result.final.blocked)

    def test_wrong_genset_general_is_not_coerced(self):
        code = self.genset().replace('general Pessoa', 'general Outro') + '\nkind Outro'
        result = analyze_semantics(self.load(code), coerce=True)
        self.assertEqual(result.project.diagnostics, [])
        self.assertEqual(result.corrections, ())

    def test_single_specific_is_not_treated_as_complete_pattern(self):
        code = self.genset().replace('specifics Primeiro, Segundo', 'specifics Primeiro')
        result = analyze_semantics(self.load(code), coerce=True)
        self.assertEqual(result.corrections, ())
        self.assertTrue(result.final.blocked)

    def test_same_names_in_different_packages_do_not_share_context(self):
        first = self.source(self.genset(), 'first.tonto')
        second = self.source(self.genset('role', '').replace('package Modelo', 'package Outro'), 'second.tonto')
        project = load_project([first, second])
        result = analyze_semantics(project, coerce=True)
        self.assertEqual(len(result.corrections), 1)
        self.assertTrue(result.project.table.lookup('Grupo', 'Modelo')[0].node.is_disjoint)
        self.assertFalse(result.project.table.lookup('Grupo', 'Outro')[0].node.is_disjoint)

    def test_imported_general_and_specifics_use_resolved_references(self):
        first = self.source('package Tipos\nkind Pessoa\nphase Primeiro specializes Pessoa\nphase Segundo specializes Pessoa', 'types.tonto')
        second = self.source('package Modelo\nimport Tipos\ngenset Grupo { general Pessoa specifics Primeiro, Segundo }', 'model.tonto')
        result = analyze_semantics(load_project([first, second]), coerce=True)
        self.assertEqual(result.project.diagnostics, [])
        self.assertEqual(len(result.corrections), 1)

    def test_catalog_keeps_existing_diagnostic_contract(self):
        project = self.load('kind Person')
        subject = project.table.lookup('Person', '<default>')[0]
        for code in ISSUE_CATALOG:
            with self.subTest(code=code):
                diagnostic = SemanticIssue(code, subject, 'Detalhe fornecido pelo reconhecedor.').diagnostic()
                self.assertEqual(set(diagnostic), {'stage', 'code', 'file', 'line', 'column', 'message', 'suggestion'})
                self.assertIn('Detalhe fornecido', diagnostic['message'])

    def test_unknown_error_code_is_rejected(self):
        subject = self.load('kind Person').table.lookup('Person', '<default>')[0]
        with self.assertRaises(ValueError):
            SemanticIssue('unknown', subject)

    def test_recognizer_results_and_overload_variants_are_reported(self):
        def recognizer(project):
            subject = project.table.lookup('Person', '<default>')[0]
            missing = SemanticIssue('phase_missing_sibling', subject)
            return SemanticCheck(patterns=(
                PatternFinding(PatternKind.PHASE, subject, (missing,), variant='alternativa incompleta'),
                PatternFinding(PatternKind.SUBKIND, subject, variant='resultado completo de teste'),
                PatternFinding(PatternKind.ROLE, subject, blocked='Referência ainda não resolvida.'),
            ), coverage=('Reconhecedor simulado no teste, não uma implementação dos padrões',))
        result = analyze_semantics(self.load('kind Person'), recognizer=recognizer)
        self.assertTrue(result.recognizer_used)
        self.assertEqual([d['code'] for d in result.diagnostics], ['phase_missing_sibling'])
        report = render_report(result.project, semantic=result)
        for text in ['PADRÕES COMPLETOS', 'CANDIDATOS INCOMPLETOS', 'CANDIDATOS BLOQUEADOS',
                     'alternativa incompleta', 'resultado completo de teste', 'Semântico / phase_missing_sibling']:
            self.assertIn(text, report)

    def test_same_issue_in_general_and_overloaded_results_is_deduplicated(self):
        subject = self.load('kind Person').table.lookup('Person', '<default>')[0]
        issue = SemanticIssue('phase_missing_kind', subject)
        check = SemanticCheck(issues=(issue,), patterns=(PatternFinding(PatternKind.PHASE, subject, (issue,)),))
        self.assertEqual(len(check.diagnostics), 1)

    def test_blocked_candidate_does_not_generate_cascaded_semantic_error(self):
        subject = self.load('kind Person').table.lookup('Person', '<default>')[0]
        issue = SemanticIssue('phase_missing_kind', subject)
        finding = PatternFinding(PatternKind.PHASE, subject, (issue,), blocked='Herança inconclusiva.')
        self.assertEqual(SemanticCheck(patterns=(finding,)).diagnostics, [])
        self.assertEqual(finding.status, 'bloqueado')

    def test_coercion_does_not_fabricate_missing_conceptual_dependencies(self):
        def recognizer(project):
            subject = project.table.lookup('Contract', '<default>')[0]
            return SemanticCheck(issues=(SemanticIssue('relator_missing_material', subject),))
        result = analyze_semantics(self.load('relator Contract'), coerce=True, recognizer=recognizer)
        self.assertEqual(result.corrections, ())
        self.assertEqual([d['code'] for d in result.diagnostics], ['relator_missing_material'])
        self.assertEqual(len(result.project.symbols), 2)

    def test_external_recognizer_is_called_again_after_coercion(self):
        calls = []
        def recognizer(project):
            calls.append(project.table.lookup('Grupo', 'Modelo')[0].node.is_disjoint)
            return SemanticCheck()
        result = analyze_semantics(self.load(self.genset()), coerce=True, recognizer=recognizer)
        self.assertEqual(calls, [False, True])
        self.assertEqual(result.diagnostics, [])

    def test_invalid_recognizer_contract_is_rejected(self):
        with self.assertRaises(TypeError):
            analyze_semantics(self.load('kind Person'), recognizer=lambda project: [])

    def test_report_distinguishes_correction_from_pending_errors(self):
        result = analyze_semantics(self.load(self.genset()), coerce=True)
        report = render_report(result.project, semantic=result)
        self.assertIn('Corrigido em memória', report)
        self.assertIn('False → True', report)
        self.assertIn('arquivo original continua inalterado', report)
        self.assertIn('Nenhum erro pendente nas verificações executadas.', report)
        self.assertNotIn('[Semântico / genset_missing_disjoint]', report)

    def test_cli_semantic_error_returns_one(self):
        path = self.source(self.genset())
        output = io.StringIO()
        with redirect_stdout(output), self.assertRaises(SystemExit) as raised:
            main(['--semantic', str(path)])
        self.assertEqual(raised.exception.code, 1)
        self.assertIn('genset_missing_disjoint', output.getvalue())

    def test_cli_coercion_returns_success_without_editing_source(self):
        path = self.source(self.genset())
        contents = path.read_bytes()
        with redirect_stdout(io.StringIO()):
            self.assertIsNone(main(['--semantic', '--coerce', str(path)]))
        self.assertEqual(path.read_bytes(), contents)

    def test_coerce_requires_explicit_semantic_mode(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            main(['--coerce', str(self.source('kind Person'))])
        self.assertEqual(raised.exception.code, 2)

    def test_syntax_only_cli_is_not_changed(self):
        with redirect_stdout(io.StringIO()):
            self.assertIsNone(main([str(self.source(self.genset()))]))

    def test_versioned_semantic_examples(self):
        folder = Path(__file__).resolve().parents[1] / 'exemplos' / 'semantica'
        bad = load_project(folder / 'gensets_com_erros.tonto')
        good = load_project(folder / 'gensets_validos.tonto')
        self.assertEqual(bad.diagnostics, [])
        result = analyze_semantics(bad, coerce=True)
        self.assertEqual(len(result.initial.diagnostics), 3)
        self.assertEqual(len(result.corrections), 3)
        self.assertEqual(result.diagnostics, [])
        self.assertEqual(analyze_semantics(good).diagnostics, [])

    def test_cli_subprocess_returns_one_for_semantic_errors(self):
        path = self.source(self.genset())
        result = subprocess.run([sys.executable, '-m', 'compilador.main', '--semantic', str(path)],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('[Semântico / genset_missing_disjoint]', result.stdout)

    def test_cli_subprocess_coerces_without_editing_source(self):
        path = self.source(self.genset())
        contents = path.read_bytes()
        result = subprocess.run([sys.executable, '-m', 'compilador.main', '--semantic', '--coerce', str(path)],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Corrigido em memória', result.stdout)
        self.assertEqual(path.read_bytes(), contents)

    def test_rolemixin_genset_is_not_confused_with_role_genset(self):
        project = self.load('''kind Pessoa
kind Empresa
role Aluno specializes Pessoa
role Escola specializes Empresa
roleMixin Cliente
disjoint genset Clientes { general Cliente specifics Aluno, Escola }''')
        self.assertEqual(project.diagnostics, [])
        result = analyze_semantics(project, coerce=True)
        self.assertEqual(result.corrections, ())
        self.assertEqual(result.diagnostics, [])
        self.assertTrue(result.final.blocked)


if __name__ == '__main__':
    unittest.main()
