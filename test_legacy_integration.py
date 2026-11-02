import ast
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import pandas as pd
from fastapi.testclient import TestClient
import main

ROOT=Path(__file__).resolve().parent
LEGACY=ROOT.parent.parent/'helios_backup'/'snapshots_2026-10-02'/'before_comparison_reconstructed'
class FakeLLM:
    def __init__(self):self.calls=[]
    def invoke(self,messages):
        self.calls.append(list(messages))
        value=({'action':'query','operation':'sql','sql':'SELECT COUNT(*) AS n, AVG(mass) AS mean FROM dataset'} if len(self.calls)==1 else
               {'action':'finish','summary':'Three rows, mean mass 4.','execution_report':'Executed SQL count and mean on mass.','hypothesis_directions':['Compare species means.'],'limitations':['Small dataset.']})
        return SimpleNamespace(content=json.dumps(value))
class LegacyIntegrationTests(unittest.TestCase):
    def test_original_generation_functions_unchanged(self):
        def functions(path):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(path.read_text(encoding='utf-8')).body if isinstance(n,ast.FunctionDef)}
        before=functions(LEGACY/'main.py');after=functions(ROOT/'main.py')
        for name,value in before.items():
            if name not in ('build_data_context','build_eda_context','discover_with_ai_agent','generate_ai_async','build_llm','available_llm_providers','generate_statistical_advice','chat_with_ai'):
                self.assertEqual(after[name],value,name)
    def test_original_visual_assets_unchanged(self):
        for name in ('helios_core.js','tsne.js','image.png','imageindex.jpg'):
            self.assertEqual((ROOT/name).read_bytes(),(LEGACY/name).read_bytes(),name)
        self.assertEqual((ROOT/'helios.html').read_text(encoding='utf-8').replace('visualizationtools.js?v=eda-code-sunburst-5','visualizationtools.js'),(LEGACY/'helios.html').read_text(encoding='utf-8'))
        self.assertEqual((ROOT/'index.html').read_text(encoding='utf-8'),
                         (LEGACY/'index.html').read_text(encoding='utf-8').replace('http://localhost:8000',''))
        def without_context_renderer(path):
            text=path.read_text(encoding='utf-8')
            start=text.index('function renderSunburstCharts(hypotheses) {')
            end=text.index('\n}',start)+3
            text=text[:start]+text[end:]
            start=text.index('function renderGenerationContext(rawContext) {')
            end=text.index('\nfunction formatHypothesisBullets',start)
            return text[:start]+text[end:]
        self.assertEqual(without_context_renderer(ROOT/'visualizationtools.js'),without_context_renderer(LEGACY/'visualizationtools.js'))
    def test_eda_replaces_describe_even_if_legacy_toggle_is_false(self):
        llm=FakeLLM();df=pd.DataFrame({'species':['A','A','B'],'mass':[2,4,6]})
        with patch.object(main,'build_llm',return_value=llm),patch.object(main.utils,'describe_dataset_detailed',side_effect=AssertionError('Must not run')):
            context=json.loads(main.build_eda_context(df,'mass',{'eda_enabled':False}))
        initial=json.loads(llm.calls[0][1].content)
        self.assertEqual(set(initial),{'target','selected_test_type','user_intent'})
        self.assertNotIn('dataset',context)
        self.assertEqual(context['eda_agent']['evidence'][0]['result']['rows'],[[3,4.]])
        self.assertEqual(context['eda_agent']['status'],'completed')
    def test_eda_failure_propagates(self):
        with patch.object(main,'build_llm',side_effect=RuntimeError('Provider unavailable')):
            with self.assertRaisesRegex(RuntimeError,'Provider unavailable'):
                main.build_eda_context(pd.DataFrame({'mass':[2]}),'mass',{})
    def test_original_interface_and_login_served(self):
        client=TestClient(main.app)
        for path in ('/','/helios.html','/helios_core.js'):
            self.assertEqual(client.get(path).status_code,200)
        self.assertEqual(client.post('/login',json={'username':'admin','password':'password'}).status_code,200)
        self.assertEqual(client.get('/main.py').status_code,404)
    def test_backup_preserved(self):
        backup=ROOT.parent.parent/'helios_backup'
        for name,digest in json.loads((ROOT/'preserved_backup_manifest.json').read_text()).items():
            self.assertEqual(hashlib.sha256((backup/name).read_bytes()).hexdigest(),digest,name)
if __name__=='__main__':unittest.main()
