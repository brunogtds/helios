import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
import pandas as pd
from eda_execution import execute_python, execute_sql


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame({'island': ['Dream', 'Dream', 'Other', 'Other'], 'mass': [1., 3., 5., 7.]})

    def test_sql_cte_window_function_and_all_rows(self):
        result = execute_sql(self.df, 'mass', 'WITH ranked AS (SELECT *, ROW_NUMBER() OVER (ORDER BY mass DESC) AS rank FROM dataset) SELECT island, mass, rank FROM ranked')
        self.assertEqual(len(result['rows']), 4)
        self.assertEqual(result['rows'][0], ['Other', 7., 1])

    def test_sql_multiple_statements_and_changes_do_not_persist(self):
        result = execute_sql(self.df, 'mass', "CREATE TABLE derived AS SELECT * FROM dataset WHERE island='Dream'; UPDATE derived SET mass=mass*2; SELECT SUM(mass) FROM derived;")
        self.assertEqual(result['rows'], [[8.]])
        self.assertEqual(execute_sql(self.df, 'mass', 'SELECT SUM(mass) FROM dataset')['rows'], [[16.]])
        self.assertEqual(self.df.mass.sum(), 16.)

    def test_sql_literal_semicolons_and_output_limits(self):
        result = execute_sql(self.df, 'mass', "SELECT ';' AS literal, mass FROM dataset;", max_rows=2)
        self.assertEqual(result['rows'][0], [';', 1.])
        self.assertTrue(result['truncated'])

    def test_sql_external_access_is_denied(self):
        for sql in ("ATTACH DATABASE '/tmp/other.db' AS external", "SELECT load_extension('external')", "VACUUM INTO '/tmp/other.db'"):
            with self.assertRaises(Exception):
                execute_sql(self.df, 'mass', sql)

    def test_sql_runaway_query_times_out(self):
        with self.assertRaisesRegex(Exception, 'interrupted'):
            execute_sql(self.df, 'mass', 'WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM n) SELECT SUM(x) FROM n', timeout=.01)

    def run_worker(self, code):
        # Trusted fixed test code only. Production code always uses Docker.
        request = json.dumps({'dataframe': self.df.to_json(orient='table'), 'target': 'mass', 'code': code})
        output = subprocess.run([sys.executable, str(Path(__file__).with_name('eda_python_worker.py'))],
                                input=request, text=True, capture_output=True, timeout=30, check=True)
        return json.loads(output.stdout)

    def test_worker_custom_function_and_statistics(self):
        result = self.run_worker("def difference(df):\n    return df.loc[df.island=='Other',target].mean()-df.loc[df.island=='Dream',target].mean()\nprint('analysis executed')\nresult={'difference':difference(df), 'test':stats.ttest_ind(df.mass[:2],df.mass[2:],equal_var=False).pvalue}")
        self.assertEqual(result['result']['difference'], 4.)
        self.assertIn('test', result['result'])
        self.assertIn('analysis executed', result['stdout'])

    def test_worker_last_expression_and_error_feedback(self):
        self.assertEqual(self.run_worker('df.mass.mean()')['result'], 4.)
        self.assertIn('ZeroDivisionError', self.run_worker('1/0')['error'])
        self.assertEqual(self.run_worker("print('x'*50000)")['stdout'], 'x' * 20000)

    def test_docker_command_is_isolated_and_gets_full_dataset(self):
        def run(command, payload, name, timeout):
            self.assertIn('--network=none', command)
            self.assertIn('--read-only', command)
            self.assertIn('--cap-drop=ALL', command)
            self.assertNotIn('-v', command)
            self.assertNotIn('--env', command)
            sent = json.loads(payload)
            loaded = pd.read_json(io.StringIO(sent['dataframe']), orient='table')
            pd.testing.assert_frame_equal(loaded, self.df)
            return 0, '{"result":4}', ''
        with patch('eda_execution.shutil.which', return_value='docker'), patch('eda_execution._run_container', side_effect=run):
            self.assertEqual(execute_python(self.df, 'mass', 'df.mass.mean()')['result'], 4)


if __name__ == '__main__':
    unittest.main()
