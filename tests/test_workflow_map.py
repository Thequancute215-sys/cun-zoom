"""The CI map guard must detect real source/artifact drift across checkouts."""
import importlib.util
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('workflow_map', Path(__file__).resolve().parents[1] / 'scripts/workflow_map.py')
workflow_map = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workflow_map)


class WorkflowMapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        patcher = patch.object(workflow_map, 'ROOT', self.root)
        patcher.start()
        self.addCleanup(patcher.stop)
        (self.root / 'src').mkdir()
        (self.root / 'src/example.py').write_bytes(b'print("example")\n')
        (self.root / '.gitignore').write_text('.ua/intermediate/\n', encoding='utf-8')
        node = {'id': 'domain:example', 'type': 'domain', 'name': 'Example', 'summary': 'Fixture', 'tags': ['fixture'], 'complexity': 'simple'}
        domain = {'nodes': [node], 'edges': [], 'layers': [], 'tour': []}
        overview = {'nodes': [{**node, 'id': 'file:example', 'type': 'file', 'filePath': 'src/example.py', 'lineRange': [1, 1]}], 'edges': [], 'layers': [{'nodeIds': ['file:example']}], 'tour': []}
        for name in workflow_map.ARTIFACTS:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            if name.endswith('domain-graph.json'):
                workflow_map.write_json(name, domain)
            elif name.endswith('knowledge-graph.json'):
                workflow_map.write_json(name, overview)
            else:
                target.write_text('{}\n' if name.endswith('.json') else '# Fixture\n', encoding='utf-8')
        workflow_map.write_json(workflow_map.SNAPSHOT, {
            'sourceFiles': {n: workflow_map.digest(n) for n in workflow_map.source_files()},
            'artifacts': {n: workflow_map.digest(n) for n in workflow_map.ARTIFACTS}})

    def check(self):
        with redirect_stdout(io.StringIO()):
            workflow_map.check()

    def test_clean_source_and_cross_platform_line_endings(self):
        self.check()
        (self.root / 'src/example.py').write_bytes(b'print("example")\r\n')
        self.check()

    def test_changed_added_or_deleted_source_is_stale(self):
        source = self.root / 'src/example.py'
        original = source.read_bytes()
        source.write_bytes(original + b'# changed\n')
        with self.assertRaisesRegex(AssertionError, 'src/example.py'):
            self.check()
        source.write_bytes(original)
        added = self.root / 'src/new.py'
        added.write_text('pass\n')
        with self.assertRaisesRegex(AssertionError, 'src/new.py'):
            self.check()
        added.unlink()
        source.unlink()
        with self.assertRaisesRegex(AssertionError, 'src/example.py'):
            self.check()

    def test_changed_graph_or_generated_doc_is_stale(self):
        for name in ('.ua/domain-graph.json', 'docs/WORKFLOW.md'):
            target = self.root / name
            original = target.read_bytes()
            target.write_bytes(original + b' ')
            with self.assertRaisesRegex(AssertionError, 'stale'):
                self.check()
            target.write_bytes(original)

    def test_ignored_intermediate_is_not_source(self):
        scratch = self.root / '.ua/intermediate/context.json'
        scratch.parent.mkdir()
        scratch.write_text('{}')
        self.assertNotIn('.ua/intermediate/context.json', workflow_map.source_files())
        self.check()

    def test_path_escape_and_missing_line_are_rejected(self):
        graph = workflow_map.load('.ua/knowledge-graph.json')
        graph['nodes'][0]['filePath'] = '../private.py'
        with self.assertRaises(AssertionError):
            workflow_map.validate(graph)
        graph['nodes'][0]['filePath'] = 'src/example.py'
        graph['nodes'][0]['lineRange'] = [1, 99]
        with self.assertRaisesRegex(AssertionError, 'line range'):
            workflow_map.validate(graph)


if __name__ == '__main__':
    unittest.main()
