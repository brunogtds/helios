"""Opt-in real container tests: set HELIOS_TEST_DOCKER=1 before running."""
import os
import unittest
import pandas as pd
from eda_execution import execute_python


@unittest.skipUnless(os.getenv('HELIOS_TEST_DOCKER') == '1', 'Requires the built EDA Docker image')
class DockerExecutionTests(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame({'island': ['Dream', 'Dream', 'Other', 'Other'], 'mass': [1., 3., 5., 7.]})

    def test_real_python_sees_every_row_and_runs_statistics(self):
        result = execute_python(self.df, 'mass', "result={'rows':len(df),'mean':df[target].mean(),'p':stats.ttest_ind(df.mass[:2],df.mass[2:],equal_var=False).pvalue}")
        self.assertNotIn('error', result, result)
        self.assertEqual(result['result']['rows'], 4)
        self.assertEqual(result['result']['mean'], 4.)
        self.assertIsInstance(result['result']['p'], float)

    def test_container_is_unprivileged_without_network_or_credentials(self):
        result = execute_python(self.df, 'mass', "import os\nfrom pathlib import Path\nresult={'uid':os.getuid(),'provider_key_present':'OPENAI_API_KEY' in os.environ,'routes':Path('/proc/net/route').read_text().splitlines()}")
        self.assertEqual(result['result']['uid'], 65534)
        self.assertFalse(result['result']['provider_key_present'])
        self.assertEqual(len(result['result']['routes']), 1)

    def test_python_errors_are_returned_to_agent(self):
        result = execute_python(self.df, 'mass', 'result = missing_variable')
        self.assertIn('NameError', result['error'])

    def test_infinite_loop_times_out(self):
        with self.assertRaisesRegex(RuntimeError, 'exceeded'):
            execute_python(self.df, 'mass', 'while True: pass', timeout=4)

    def test_low_level_output_flood_is_bounded(self):
        with self.assertRaisesRegex(RuntimeError, 'output limit'):
            execute_python(self.df, 'mass', "import os\nwhile True: os.write(1, b'x'*65536)", timeout=20)


if __name__ == '__main__':
    unittest.main()
