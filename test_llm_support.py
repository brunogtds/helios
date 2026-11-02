import ast
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from llm_support import build_claude, message_text, CLAUDE_DEFAULT_MODEL
from ranking_agent import rank_hypotheses

class ClaudeTests(unittest.TestCase):
    def test_key_precedence_and_options(self):
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'environment-key'}):
            model = build_claude(CLAUDE_DEFAULT_MODEL, ' ui-key ', timeout=None, max_retries=2)
            self.assertEqual(model.anthropic_api_key.get_secret_value(), 'ui-key')
            self.assertEqual(model.max_tokens, 8192)
            self.assertIsNone(model.temperature)
            model = build_claude('claude-haiku-4-5-20251001', '')
            self.assertEqual(model.anthropic_api_key.get_secret_value(), 'environment-key')

    def test_missing_key(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(ValueError, 'ANTHROPIC_API_KEY'):
            build_claude('', '')

    def test_only_text_blocks_are_extracted(self):
        blocks = [{'type': 'thinking', 'thinking': 'private'}, {'type': 'text', 'text': 'Hello'}, {'type': 'tool_use', 'text': 'ignore'}, ' world']
        self.assertEqual(message_text(SimpleNamespace(content=blocks)), 'Hello world')
        self.assertEqual(message_text(SimpleNamespace(content='Hello')), 'Hello')
        self.assertEqual(message_text(SimpleNamespace(content=[])), '')

    def test_ranking_reads_claude_blocks(self):
        payload = dict(summary='Relevant', unanswered_aspects=[], decisions=[dict(id=0, accepted=True, score=9, rank=1, reason='Addresses query')])
        llm = SimpleNamespace(invoke=lambda messages: SimpleNamespace(content=[{'type': 'thinking', 'thinking': 'ignore'}, {'type': 'text', 'text': json.dumps(payload)}]))
        accepted, report = rank_hypotheses(llm, 'query', 'target', [{}])
        self.assertEqual(accepted, [{}])
        self.assertEqual(report['status'], 'completed')

    def test_backend_dispatch_and_provider_listing(self):
        source = ast.parse(Path(__file__).with_name('main.py').read_text(encoding='utf-8'))
        functions = [node for node in source.body if isinstance(node, ast.FunctionDef) and node.name in ('build_llm', 'available_llm_providers')]
        for node in functions: node.decorator_list = []
        dispatch = unittest.mock.Mock(return_value='claude')
        namespace = dict(os=os, build_claude=dispatch, CLAUDE_DEFAULT_MODEL=CLAUDE_DEFAULT_MODEL)
        exec(compile(ast.Module(body=functions, type_ignores=[]), '<provider functions>', 'exec'), namespace)
        for provider in ('Anthropic', 'Claude'):
            self.assertEqual(namespace['build_llm'](provider, 'model', 0.2, 'key', timeout=None), 'claude')
        dispatch.assert_called_with('model', 'key', timeout=None)
        self.assertEqual(namespace['available_llm_providers']()['Anthropic']['default_model'], CLAUDE_DEFAULT_MODEL)

if __name__ == '__main__': unittest.main()
