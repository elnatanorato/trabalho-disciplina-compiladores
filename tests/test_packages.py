import importlib
import unittest
from collections import Counter
from functools import partial
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from compilador import ast, packages
from compilador.packages import load_project
from compilador.symbols import DEFAULT_PACKAGE


def setUpModule():
    import ply.yacc as yacc

    # Usa as regras reais, sem gravar tabelas ou logs nos arquivos dos colegas.
    with patch.object(yacc, 'yacc', partial(yacc.yacc, debug=False, write_tables=False)):
        importlib.import_module('compilador.syntax')


class ProjectFilesTestCase(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory(prefix='compilador-tests-')
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)

    def source(self, name, code):
        path = self.directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(code, encoding='utf-8')
        return path

    def reference(self, project, package, source_name, field):
        matches = [r for r in project.references if r.source.package == package and r.source.name == source_name and r.field == field]
        self.assertEqual(len(matches), 1)
        return matches[0]

    def assert_codes(self, project, expected):
        self.assertEqual([d['code'] for d in project.diagnostics], expected)


class PackageTests(ProjectFilesTestCase):
    def test_loads_single_file_and_keeps_ast_and_provenance(self):
        path = self.source('person.tonto', 'package School\nkind Person { age : number }')
        project = load_project(path)
        self.assert_codes(project, [])
        self.assertEqual(set(project.packages), {'School'})
        self.assertEqual(set(project.asts), {str(path.resolve())})
        self.assertIsInstance(project.asts[str(path.resolve())], ast.ListInstructions)
        person, = project.table.lookup('Person', 'School', category='class')
        self.assertEqual(person.file, str(path.resolve()))
        self.assertIs(person.node, project.asts[str(path.resolve())].instructions[1])
        self.assertEqual([s.name for s in project.table.members('School', 'Person')], ['age'])
        self.assertEqual(self.reference(project, 'School', 'age', 'type').basic_type, 'number')

    def test_folder_loads_only_direct_tonto_files(self):
        first = self.source('a.tonto', 'package A\nkind Alpha')
        second = self.source('b.tonto', 'package B\nkind Beta')
        self.source('ignored.txt', 'package Ignored')
        self.source('nested/c.tonto', 'package C\nkind Gamma')
        project = load_project(str(self.directory))
        self.assert_codes(project, [])
        self.assertEqual(set(project.packages), {'A', 'B'})
        self.assertEqual(set(project.asts), {str(first.resolve()), str(second.resolve())})
        self.assertEqual(len(project.symbols), 4)

    def test_import_uses_declared_package_instead_of_filename(self):
        first = self.source('consumer.tonto', 'import Models\npackage App\nkind User { car : Car }')
        second = self.source('different_filename.tonto', 'package Models\nkind Car')
        project = load_project([first, second])
        self.assert_codes(project, [])
        dependency, = project.imports['App']
        self.assertIs(dependency.target, project.packages['Models'])
        reference = self.reference(project, 'App', 'car', 'type')
        self.assertIs(reference.target, project.table.lookup('Car', 'Models')[0])
        self.assertEqual(dependency.file, str(first.resolve()))

    def test_mutual_imports_resolve_forward_references_in_both_directions(self):
        first = self.source('a.tonto', 'import B\npackage A\nkind Alpha { peer : Beta }')
        second = self.source('b.tonto', 'import A\npackage B\nkind Beta { peer : Alpha }')
        project = load_project([first, second])
        self.assert_codes(project, [])
        self.assertEqual(len(project.asts), 2)
        self.assertIs(project.imports['A'][0].target, project.packages['B'])
        self.assertIs(project.imports['B'][0].target, project.packages['A'])
        self.assertEqual(self.reference(project, 'A', 'peer', 'type').target.package, 'B')
        self.assertEqual(self.reference(project, 'B', 'peer', 'type').target.package, 'A')
        self.assertEqual(len(project.symbols), 6)

    def test_local_declaration_takes_precedence_over_import(self):
        first = self.source('a.tonto', 'package A\nimport B\nkind Person\nrole Child specializes Person')
        second = self.source('b.tonto', 'package B\nkind Person')
        project = load_project([first, second])
        self.assert_codes(project, [])
        reference = self.reference(project, 'A', 'Child', 'specializes')
        self.assertIs(reference.target, project.table.lookup('Person', 'A')[0])
        self.assertIsNot(reference.target, project.table.lookup('Person', 'B')[0])

    def test_incompatible_local_type_does_not_fall_back_to_import(self):
        first = self.source('a.tonto', 'package A\nimport B\nenum Person { One1, Two2 }\nrole Child specializes Person')
        second = self.source('b.tonto', 'package B\nkind Person')
        project = load_project([first, second])
        self.assert_codes(project, ['incompatible_category'])
        self.assertIsNone(self.reference(project, 'A', 'Child', 'specializes').target)

    def test_ambiguous_imported_declarations_produce_no_target(self):
        first = self.source('a.tonto', 'package A\nimport B\nimport C\nrole Child specializes Person')
        second = self.source('b.tonto', 'package B\nkind Person')
        third = self.source('c.tonto', 'package C\nkind Person')
        project = load_project([first, second, third])
        self.assert_codes(project, ['ambiguous_reference'])
        self.assertIsNone(self.reference(project, 'A', 'Child', 'specializes').target)
        diagnostic, = project.diagnostics
        self.assertIn('B, C', diagnostic['message'])
        self.assertEqual(diagnostic['file'], str(first.resolve()))

    def test_only_compatible_imported_candidate_is_selected(self):
        first = self.source('a.tonto', 'package A\nimport B\nimport C\nrole Child specializes Person')
        second = self.source('b.tonto', 'package B\nenum Person { One1, Two2 }')
        third = self.source('c.tonto', 'package C\nkind Person')
        project = load_project([first, second, third])
        self.assert_codes(project, [])
        reference = self.reference(project, 'A', 'Child', 'specializes')
        self.assertEqual((reference.target.package, reference.target.category), ('C', 'class'))

    def test_missing_import_has_file_and_suggestion(self):
        path = self.source('a.tonto', 'package A\nimport Missing\nkind Alpha')
        project = load_project(path)
        self.assert_codes(project, ['missing_import'])
        self.assertIsNone(project.imports['A'][0].target)
        diagnostic, = project.diagnostics
        self.assertEqual(diagnostic['file'], str(path.resolve()))
        self.assertEqual((diagnostic['line'], diagnostic['column']), (2, 8))
        self.assertIn('Missing', diagnostic['message'])
        self.assertTrue(diagnostic['suggestion'])

    def test_unknown_reference_is_reported(self):
        path = self.source('a.tonto', 'package A\nkind Person { car : Unknown }')
        project = load_project(path)
        self.assert_codes(project, ['unresolved_reference'])
        self.assertIsNone(self.reference(project, 'A', 'car', 'type').target)
        self.assertIn('Unknown', project.diagnostics[0]['message'])

    def test_relation_endpoint_must_be_a_class(self):
        path = self.source('a.tonto', 'package A\nkind Person\nenum Status { One1, Two2 }\nrelation Person [1] -- [1] Status')
        project = load_project(path)
        self.assert_codes(project, ['incompatible_category'])
        relation, = project.table.relations(external=True)
        self.assertEqual(self.reference(project, 'A', relation.name, 'source').target.name, 'Person')
        self.assertIsNone(self.reference(project, 'A', relation.name, 'target').target)

    def test_repeated_paths_and_folder_overlap_parse_each_file_once(self):
        first = self.source('a.tonto', 'package A\nkind Alpha')
        second = self.source('b.tonto', 'package B\nkind Beta')
        with patch.object(packages, '_parse_source', wraps=packages._parse_source) as parse:
            project = load_project([first, first.resolve(), self.directory, second])
        self.assertEqual(parse.call_count, 2)
        self.assertEqual(set(project.asts), {str(first.resolve()), str(second.resolve())})
        self.assertEqual(len(project.symbols), 4)
        self.assert_codes(project, [])

    def test_file_without_package_uses_default_scope(self):
        path = self.source('plain.tonto', 'kind Person { name : string }')
        project = load_project(path)
        self.assert_codes(project, [])
        self.assertEqual(set(project.packages), {DEFAULT_PACKAGE})
        self.assertIsNone(project.packages[DEFAULT_PACKAGE].node)
        person, = project.table.lookup('Person', DEFAULT_PACKAGE, category='class')
        self.assertEqual(person.file, str(path.resolve()))
        self.assertEqual(self.reference(project, DEFAULT_PACKAGE, 'name', 'type').basic_type, 'string')

    def test_files_without_package_share_default_scope_and_keep_own_files(self):
        first = self.source('one.tonto', 'kind Person { car : Car }')
        second = self.source('two.tonto', 'kind Car')
        project = load_project([first, second])
        self.assert_codes(project, [])
        self.assertEqual(len(project.packages), 1)
        target = self.reference(project, DEFAULT_PACKAGE, 'car', 'type').target
        self.assertEqual(target.file, str(second.resolve()))
        self.assertEqual(len(project.symbols), 4)

    def test_unimported_package_is_not_globally_visible(self):
        first = self.source('a.tonto', 'package A\nkind Person { car : Car }')
        second = self.source('b.tonto', 'package B\nkind Car')
        project = load_project([first, second])
        self.assert_codes(project, ['unresolved_reference'])
        self.assertIsNone(self.reference(project, 'A', 'car', 'type').target)

    def test_transitive_import_does_not_expose_third_package(self):
        first = self.source('a.tonto', 'package A\nimport B\nkind Alpha { value : Gamma }')
        second = self.source('b.tonto', 'package B\nimport C\nkind Beta')
        third = self.source('c.tonto', 'package C\nkind Gamma')
        project = load_project([first, second, third])
        self.assert_codes(project, ['unresolved_reference'])
        self.assertIsNone(self.reference(project, 'A', 'value', 'type').target)
        self.assertIs(project.imports['B'][0].target, project.packages['C'])

    def test_repeated_import_does_not_create_false_ambiguity(self):
        first = self.source('a.tonto', 'package A\nimport B\nimport B\nkind Alpha { value : Beta }')
        second = self.source('b.tonto', 'package B\nkind Beta')
        project = load_project([first, second])
        self.assert_codes(project, [])
        self.assertEqual(len(project.imports['A']), 2)
        self.assertEqual(self.reference(project, 'A', 'value', 'type').target.package, 'B')

    def test_self_import_terminates_and_resolves_local_references(self):
        path = self.source('a.tonto', 'import A\npackage A\nkind Person { friend : Person }')
        project = load_project(path)
        self.assert_codes(project, [])
        self.assertIs(project.imports['A'][0].target, project.packages['A'])
        self.assertIs(self.reference(project, 'A', 'friend', 'type').target, project.table.lookup('Person', 'A')[0])

    def test_missing_file_produces_read_diagnostic(self):
        missing = self.directory / 'missing.tonto'
        project = load_project(missing)
        self.assert_codes(project, ['file_read_error'])
        self.assertEqual(project.symbols, {})
        self.assertEqual(project.asts, {str(missing.resolve()): None})

    def test_invalid_utf8_produces_read_diagnostic(self):
        path = self.directory / 'invalid.tonto'
        path.write_bytes(b'\xff\xfe\xff')
        project = load_project(path)
        self.assert_codes(project, ['file_read_error'])
        self.assertEqual(project.symbols, {})

    def test_explicit_non_tonto_file_is_rejected(self):
        path = self.source('wrong.txt', 'package A')
        project = load_project(path)
        self.assert_codes(project, ['invalid_extension'])
        self.assertEqual(project.asts, {})

    def test_empty_source_directory_is_reported(self):
        project = load_project(self.directory)
        self.assert_codes(project, ['no_source_files'])
        self.assertEqual(project.diagnostics[0]['file'], str(self.directory.resolve()))
        self.assertEqual(project.symbols, {})

    def test_unreadable_source_directory_is_reported(self):
        with patch('os.scandir', side_effect=PermissionError('directory access denied')):
            project = load_project(self.directory)
        self.assert_codes(project, ['invalid_path'])
        self.assertEqual(project.diagnostics[0]['file'], str(self.directory.resolve()))
        self.assertEqual(project.asts, {})

    def test_lexical_errors_keep_each_file_and_reset_line_numbers(self):
        first = self.source('a.tonto', '\n\n$ package A\nkind Alpha')
        second = self.source('b.tonto', 'package B\n? kind Beta')
        project = load_project([first, second])
        self.assert_codes(project, ['lexical_error', 'lexical_error'])
        self.assertEqual([(d['file'], d['line'], d['column']) for d in project.diagnostics], [(str(first.resolve()), 3, 1), (str(second.resolve()), 2, 1)])
        self.assertEqual(set(project.packages), {'A', 'B'})
        self.assertEqual(len(project.table.symbols_in_package('B', 'class')), 1)

    def test_multiple_packages_in_one_file_are_rejected(self):
        path = self.source('mixed.tonto', 'package A\nkind Alpha\npackage B\nkind Beta')
        project = load_project(path)
        self.assert_codes(project, ['multiple_packages'])
        self.assertEqual(project.packages, {})
        self.assertEqual(project.symbols, {})

    def test_duplicate_package_files_are_not_silently_merged(self):
        first = self.source('a.tonto', 'package A\nkind Alpha')
        second = self.source('b.tonto', 'package A\nkind Beta')
        project = load_project([first, second])
        self.assert_codes(project, ['duplicate_package'])
        self.assertEqual(project.packages['A'].file, str(first.resolve()))
        self.assertEqual(project.table.lookup('Beta', 'A'), [])
        self.assertEqual(project.diagnostics[0]['file'], str(second.resolve()))
        self.assertEqual(len(project.asts), 2)

    def test_unavailable_ast_has_diagnostic_instead_of_success(self):
        path = self.source('invalid.tonto', 'kind')
        project = load_project(path)
        self.assert_codes(project, ['unexpected_eof'])
        self.assertEqual(project.asts, {str(path.resolve()): None})
        self.assertEqual(project.symbols, {})

    def test_all_basic_type_tokens_reach_the_table(self):
        code = 'package A\nkind Record { n : number s : string b : boolean d : date t : time dt : datetime }'
        project = load_project(self.source('a.tonto', code))
        self.assert_codes(project, [])
        self.assertEqual({r.basic_type for r in project.references}, {'number', 'string', 'boolean', 'date', 'time', 'datetime'})
        self.assertEqual(len(project.table.members('A', 'Record')), 6)

    def test_table_provides_summary_counts_members_relationships_and_metadata(self):
        code = '''package School
kind Person {
    age : number [1] {ordered}
    @material [1] -- owns -- [0..*] Car
}
kind Car
subkind Student specializes Person
datatype Address { street : string [1] }
enum Status { Active1, Inactive2 }
disjoint complete genset Roles where Student specializes Person
relation Person [1] -- [1] Car
'''
        project = load_project(self.source('school.tonto', code))
        self.assert_codes(project, [])
        self.assertEqual(Counter(s.category for s in project.symbols.values()), {'package': 1, 'class': 3, 'datatype': 1, 'attribute': 2, 'enum': 1, 'enum_value': 2, 'genset': 1, 'relation': 2})
        self.assertIs(project.symbols, project.table.symbols)
        self.assertIs(project.packages, project.table.packages)
        self.assertIs(project.imports, project.table.imports)
        self.assertIs(project.references, project.table.references)
        self.assertIs(project.diagnostics, project.table.diagnostics)
        self.assertEqual({s.name for s in project.table.symbols_in_package('School', 'class')}, {'Person', 'Car', 'Student'})
        self.assertEqual({s.name for s in project.table.members('School', 'Person')}, {'age', 'owns'})
        age, = project.table.members('School', 'Person', 'attribute')
        self.assertEqual(age.node.metas, [ast.Meta.ORDERED])
        self.assertEqual((age.node.cardinality.start, age.node.cardinality.end), (1, None))
        internal, = project.table.relations('School', external=False)
        self.assertEqual(internal.node.at, ast.AtRelation.MATERIAL)
        self.assertEqual((internal.node.cardinality2.start, internal.node.cardinality2.end), (0, '*'))
        self.assertEqual(self.reference(project, 'School', 'owns', 'target').target.name, 'Car')
        external, = project.table.relations('School', external=True)
        self.assertTrue(external.anonymous)
        self.assertEqual(self.reference(project, 'School', external.name, 'source').target.name, 'Person')
        self.assertEqual(self.reference(project, 'School', external.name, 'target').target.name, 'Car')
        genset, = project.table.lookup('Roles', 'School', category='genset')
        self.assertTrue(genset.node.is_disjoint and genset.node.is_complete)
        positioned = [s for s in project.symbols.values() if s.category != 'enum_value']
        self.assertTrue(all(s.line is not None and s.column is not None for s in positioned))
        self.assertTrue(all(r.target is not None or r.basic_type is not None for r in project.references))


class ParserRegressionTests(ProjectFilesTestCase):
    def test_relation_after_attribute_without_cardinality_is_preserved(self):
        # Regressão: a cardinalidade inicial da relação não pertence ao atributo.
        code = '''package School
kind Car
kind Person {
    age : number
    [1] -- owns -- [1] Car
}
'''
        path = self.source('regression.tonto', code)
        project = load_project(path)
        tree = project.asts[str(path.resolve())]
        self.assertIsNotNone(tree)
        classes = {n.name: n for n in tree.instructions if isinstance(n, ast.DeclClass)}
        self.assertIn('Person', classes, 'Bloqueio no parser: a AST perdeu Person antes do registro na tabela.')
        self.assertEqual([r.type.name for r in classes['Person'].relations], ['owns'], 'Bloqueio no parser: a AST perdeu a relação owns antes do registro na tabela.')
        self.assertEqual({s.name for s in project.table.members('School', 'Person')}, {'age', 'owns'})
        self.assertEqual(self.reference(project, 'School', 'owns', 'target').target.name, 'Car')
        self.assert_codes(project, [])


if __name__ == '__main__':
    unittest.main()
