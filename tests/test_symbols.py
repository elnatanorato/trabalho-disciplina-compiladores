import copy
import unittest
from itertools import permutations

from compilador import ast
from compilador.symbols import BASIC_TYPES, SymbolTable


def class_node(name, *, attributes=None, relations=None, specializes=None):
    return ast.DeclClass(
        ast.Stereotype.KIND, name, specializes, attributes or [], relations or []
    )


def relation_type(name=None):
    operator = ast.RelationOperator.MINUS_MINUS
    if name is None:
        return ast.RelationType1(operator)
    return ast.RelationType2(operator, name, operator)


def internal_relation(target, name=None):
    return ast.RelationIn(
        None, ast.Cardinality(1, None), relation_type(name),
        ast.Cardinality(0, '*'), target,
    )


def external_relation(source, target, name=None):
    return ast.RelationOut(
        None, source, ast.Cardinality(1, None), relation_type(name),
        ast.Cardinality(1, None), target,
    )


class SymbolTableTests(unittest.TestCase):
    def setUp(self):
        self.table = SymbolTable()

    def register(self, *nodes, package='School', file='school.tonto'):
        return self.table.register_ast([ast.Package(package), *nodes], file)

    def test_registers_top_level_declarations_and_keeps_original_nodes(self):
        nodes = [
            class_node('Person'), ast.DeclType('Address', None, []),
            ast.DeclEnum('Status', ['Active1', 'Inactive2']),
            ast.DeclGenset(True, False, 'Roles', 'Person', ['Person']),
        ]
        package = self.register(*nodes)
        self.assertEqual(package.category, 'package')
        self.assertIs(self.table.packages['School'], package)
        expected = {'Person': 'class', 'Address': 'datatype', 'Status': 'enum', 'Roles': 'genset'}
        for node in nodes:
            symbol, = self.table.lookup(node.name, 'School', category=expected[node.name])
            self.assertIs(symbol.node, node)
            self.assertEqual(symbol.key, ('School', None, expected[node.name], node.name))
            self.assertEqual(symbol.file, 'school.tonto')
        self.assertEqual(len(self.table.symbols), 7)
        self.assertEqual(self.table.diagnostics, [])

    def test_registers_attributes_in_classes_and_datatypes(self):
        age = ast.Attribute('age', 'number', ast.Cardinality(1, None), [ast.Meta.CONST])
        street = ast.Attribute('street', 'string', None, None)
        self.register(class_node('Person', attributes=[age]), ast.DeclType('Address', None, [street]))
        self.table.resolve()
        self.assertEqual(self.table.diagnostics, [])
        person_age, = self.table.members('School', 'Person', 'attribute')
        address_street, = self.table.members('School', 'Address', 'attribute')
        self.assertIs(person_age.node, age)
        self.assertEqual(person_age.node.metas, [ast.Meta.CONST])
        self.assertEqual(person_age.node.cardinality.start, 1)
        self.assertIs(address_street.node, street)
        self.assertEqual([r.basic_type for r in self.table.references], ['number', 'string'])

    def test_named_relations_keep_owners_and_resolve_both_external_ends(self):
        internal = internal_relation('Car', 'owns')
        external = external_relation('Person', 'Car', 'rents')
        self.register(class_node('Person', relations=[internal]), class_node('Car'), external)
        self.table.resolve()
        self.assertEqual(self.table.diagnostics, [])
        inside, = self.table.relations('School', external=False)
        outside, = self.table.relations('School', external=True)
        self.assertEqual((inside.name, inside.owner), ('owns', 'Person'))
        self.assertIs(inside.node, internal)
        self.assertEqual((outside.name, outside.owner), ('rents', None))
        targets = {(r.source.name, r.field): r.target.name for r in self.table.references}
        self.assertEqual(targets, {('owns', 'target'): 'Car', ('rents', 'source'): 'Person', ('rents', 'target'): 'Car'})

    def test_lookup_filters_name_package_owner_and_category(self):
        self.register(class_node('Person', attributes=[ast.Attribute('name', 'string', None, None)]))
        self.register(class_node('Person'), package='Other', file='other.tonto')
        self.assertEqual(len(self.table.lookup('Person', 'School', category='class')), 1)
        self.assertEqual(self.table.lookup('Person', 'School', category='enum'), [])
        self.assertEqual(self.table.lookup('Person', 'Missing'), [])
        self.assertEqual(self.table.lookup('name', 'School'), [])
        attribute, = self.table.lookup('name', 'School', owner='Person', category='attribute')
        self.assertEqual(attribute.owner, 'Person')
        self.assertEqual([s.name for s in self.table.symbols_in_package('Other', 'class')], ['Person'])

    def test_members_excludes_other_owners_and_package_declarations(self):
        self.register(
            class_node('Person', attributes=[ast.Attribute('age', 'number', None, None)], relations=[internal_relation('Car', 'owns')]),
            class_node('Car', attributes=[ast.Attribute('model', 'string', None, None)]),
            external_relation('Person', 'Car', 'rents'),
        )
        self.assertEqual({s.name for s in self.table.members('School', 'Person')}, {'age', 'owns'})
        self.assertEqual([s.name for s in self.table.members('School', 'Person', 'relation')], ['owns'])
        self.assertEqual(self.table.members('School', 'Unknown'), [])

    def test_same_type_name_in_distinct_packages_is_allowed(self):
        first = class_node('Person')
        second = class_node('Person')
        self.register(first, package='A', file='a.tonto')
        self.register(second, package='B', file='b.tonto')
        self.assertEqual(self.table.diagnostics, [])
        self.assertIs(self.table.lookup('Person', 'A')[0].node, first)
        self.assertIs(self.table.lookup('Person', 'B')[0].node, second)
        self.assertEqual(len(self.table.symbols), 4)

    def test_duplicate_class_keeps_first_declaration_and_its_members(self):
        first = class_node('Person', attributes=[ast.Attribute('age', 'number', None, None)])
        duplicate = class_node('Person', attributes=[ast.Attribute('other', 'Missing', None, None)])
        self.register(first, duplicate)
        self.table.resolve()
        self.assertIs(self.table.lookup('Person', 'School')[0].node, first)
        self.assertEqual([s.name for s in self.table.members('School', 'Person')], ['age'])
        self.assertEqual([d['code'] for d in self.table.diagnostics], ['duplicate_declaration'])

    def test_duplicate_members_and_attribute_relation_conflicts_are_detected(self):
        self.register(
            class_node('Person', attributes=[ast.Attribute('owns', 'string', None, None), ast.Attribute('owns', 'number', None, None)], relations=[internal_relation('Car', 'owns')]),
            class_node('Car'),
        )
        self.assertEqual([s.category for s in self.table.members('School', 'Person')], ['attribute'])
        self.assertEqual([d['code'] for d in self.table.diagnostics], ['duplicate_declaration'] * 2)

    def test_classes_enums_and_datatypes_share_namespace_in_every_order(self):
        nodes = [class_node('Value'), ast.DeclEnum('Value', ['One1', 'Two2']), ast.DeclType('Value', None, [])]
        for first, second in permutations(nodes, 2):
            with self.subTest(first=type(first).__name__, second=type(second).__name__):
                table = SymbolTable()
                table.register_ast([ast.Package('A'), first, second], 'a.tonto')
                self.assertEqual(len(table.lookup('Value', 'A')), 1)
                self.assertIs(table.lookup('Value', 'A')[0].node, first)
                self.assertEqual([d['code'] for d in table.diagnostics], ['duplicate_declaration'])

    def test_same_member_name_in_distinct_owners_is_allowed(self):
        self.register(*[class_node(name, attributes=[ast.Attribute('name', 'string', None, None)]) for name in ('Person', 'Car')])
        self.assertEqual(self.table.diagnostics, [])
        self.assertEqual({s.owner for s in self.table.symbols_in_package('School', 'attribute')}, {'Person', 'Car'})

    def test_unnamed_relations_receive_distinct_internal_ids(self):
        self.register(class_node('Person', relations=[internal_relation('Car'), internal_relation('Car')]), class_node('Car'), external_relation('Person', 'Car'), external_relation('Person', 'Car'))
        self.table.resolve()
        relations = self.table.relations()
        self.assertEqual(len(relations), 4)
        self.assertEqual(len({s.key for s in relations}), 4)
        self.assertTrue(all(s.anonymous and s.name.startswith('<relation:') for s in relations))
        self.assertEqual(len(self.table.relations(external=False)), 2)
        self.assertEqual(len(self.table.relations(external=True)), 2)
        self.assertEqual(self.table.diagnostics, [])
        self.assertEqual([r.target.name for r in self.table.references], ['Car', 'Car', 'Person', 'Car', 'Person', 'Car'])

    def test_enum_values_are_scoped_and_duplicates_are_reported(self):
        self.register(ast.DeclEnum('First', ['One1', 'One1']), ast.DeclEnum('Second', ['One1', 'Two2']))
        self.assertEqual([s.name for s in self.table.members('School', 'First')], ['One1'])
        self.assertEqual([s.name for s in self.table.members('School', 'Second')], ['One1', 'Two2'])
        self.assertEqual([d['code'] for d in self.table.diagnostics], ['duplicate_declaration'])

    def test_all_six_basic_types_resolve_without_declarations(self):
        attributes = [ast.Attribute(f'value_{name}', name, None, None) for name in sorted(BASIC_TYPES)]
        self.register(class_node('Record', attributes=attributes))
        self.table.resolve()
        self.assertEqual({r.basic_type for r in self.table.references}, BASIC_TYPES)
        self.assertTrue(all(r.target is None for r in self.table.references))
        self.assertEqual(self.table.symbols_in_package('School', 'datatype'), [])
        self.assertEqual(self.table.diagnostics, [])

    def test_forward_local_attribute_references_accept_classes_enums_and_datatypes(self):
        self.register(
            class_node('Person', attributes=[ast.Attribute('address', 'Address', None, None), ast.Attribute('status', 'Status', None, None), ast.Attribute('car', 'Car', None, None)]),
            ast.DeclType('Address', None, []), ast.DeclEnum('Status', ['One1', 'Two2']), class_node('Car'),
        )
        self.table.resolve()
        self.assertEqual([(r.name, r.target.category) for r in self.table.references], [('Address', 'datatype'), ('Status', 'enum'), ('Car', 'class')])
        self.assertEqual(self.table.diagnostics, [])

    def test_class_specialization_and_genset_references_resolve_to_classes(self):
        genset = ast.DeclGenset(True, True, 'Roles', 'Person', ['Student', 'Teacher'])
        self.register(genset, class_node('Student', specializes='Person'), class_node('Teacher', specializes='Person'), class_node('Person'))
        self.table.resolve()
        self.assertEqual(self.table.diagnostics, [])
        refs = [r for r in self.table.references if r.source.name == 'Roles']
        self.assertEqual([(r.field, r.target.name) for r in refs], [('general', 'Person'), ('specifics[0]', 'Student'), ('specifics[1]', 'Teacher')])
        self.assertTrue(all(r.target.category == 'class' for r in self.table.references))
        self.assertIs(self.table.lookup('Roles', 'School')[0].node, genset)
        self.assertTrue(genset.is_disjoint and genset.is_complete)

    def test_datatype_bases_resolve_basic_and_declared_types(self):
        self.register(ast.DeclType('Money', 'number', []), ast.DeclType('Price', 'Money', []))
        self.table.resolve()
        basic, declared = self.table.references
        self.assertEqual(basic.basic_type, 'number')
        self.assertIs(declared.target, self.table.lookup('Money', 'School')[0])
        self.assertEqual(self.table.diagnostics, [])

    def test_incompatible_relation_and_specialization_targets_are_rejected(self):
        self.register(ast.DeclEnum('Status', ['One1', 'Two2']), class_node('Person', specializes='Status', relations=[internal_relation('Status')]))
        self.table.resolve()
        self.assertEqual([d['code'] for d in self.table.diagnostics], ['incompatible_category'] * 2)
        self.assertTrue(all(r.target is None for r in self.table.references))

    def test_basic_type_cannot_be_used_as_class(self):
        symbol = self.table.add_symbol('Person', 'class', 'School')
        reference = self.table.add_reference(symbol, 'number', 'specializes', {'class'})
        self.table.resolve()
        self.assertIsNone(reference.target)
        self.assertIsNone(reference.basic_type)
        self.assertEqual(self.table.diagnostics[0]['code'], 'incompatible_category')

    def test_diagnostics_keep_actual_file_line_column_message_and_suggestion(self):
        attribute = ast.Attribute('missing', 'Unknown', None, None)
        attribute.line, attribute.column = 8, 5
        self.register(class_node('Person', attributes=[attribute]), file='actual.tonto')
        self.table.resolve()
        symbol, = self.table.members('School', 'Person')
        self.assertEqual((symbol.file, symbol.line, symbol.column), ('actual.tonto', 8, 5))
        diagnostic, = self.table.diagnostics
        self.assertEqual(set(diagnostic), {'stage', 'code', 'file', 'line', 'column', 'message', 'suggestion'})
        self.assertEqual((diagnostic['stage'], diagnostic['code'], diagnostic['file'], diagnostic['line'], diagnostic['column']), ('resolution', 'unresolved_reference', 'actual.tonto', 8, 5))
        self.assertIn('Unknown', diagnostic['message'])
        self.assertTrue(diagnostic['suggestion'])

    def test_duplicate_diagnostic_uses_the_duplicate_location(self):
        first = class_node('Person')
        duplicate = class_node('Person')
        first.lineno, first.column = 2, 6
        duplicate.lineno, duplicate.column = 7, 6
        self.register(first, duplicate)
        symbol, = self.table.lookup('Person', 'School')
        self.assertEqual((symbol.line, symbol.column), (2, 6))
        self.assertEqual((self.table.diagnostics[0]['line'], self.table.diagnostics[0]['column']), (7, 6))

    def test_missing_ast_positions_remain_none(self):
        self.register(class_node('Person', attributes=[ast.Attribute('value', 'Unknown', None, None)]))
        self.table.resolve()
        self.assertTrue(all(s.line is None and s.column is None for s in self.table.symbols.values()))
        self.assertEqual((self.table.diagnostics[0]['line'], self.table.diagnostics[0]['column']), (None, None))

    def test_reresolution_clears_stale_errors_and_preserves_registration_errors(self):
        self.register(class_node('Person', attributes=[ast.Attribute('car', 'Car', None, None)]), class_node('Person'))
        self.table.resolve()
        self.assertEqual([d['code'] for d in self.table.diagnostics], ['duplicate_declaration', 'unresolved_reference'])
        car = self.table.add_symbol('Car', 'class', 'School', class_node('Car'))
        self.table.resolve()
        self.table.resolve()
        self.assertIs(self.table.references[0].target, car)
        self.assertEqual([d['code'] for d in self.table.diagnostics], ['duplicate_declaration'])

    def test_registration_and_resolution_do_not_mutate_ast(self):
        nodes = [ast.Package('School'), class_node('Person', attributes=[ast.Attribute('age', 'number', None, None)]), external_relation('Person', 'Person')]
        original = copy.deepcopy(nodes)
        self.table.register_ast(nodes, 'school.tonto')
        self.table.resolve()
        self.assertEqual(nodes, original)
        self.assertIs(self.table.lookup('Person', 'School')[0].node, nodes[1])

    def test_accepts_actual_listinstructions_container(self):
        tree = ast.ListInstructions(ast.Package('School'))
        node = class_node('Person')
        tree + node
        self.table.register_ast(tree, 'school.tonto')
        self.assertIs(self.table.lookup('Person', 'School')[0].node, node)

    def test_multiple_package_declarations_reject_file_without_mixing_scopes(self):
        result = self.table.register_ast([ast.Package('A'), class_node('Person'), ast.Package('B')], 'mixed.tonto')
        self.assertIsNone(result)
        self.assertEqual(self.table.symbols, {})
        self.assertEqual(self.table.diagnostics[0]['code'], 'multiple_packages')


if __name__ == '__main__':
    unittest.main()
