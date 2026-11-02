import json
import unittest
from types import SimpleNamespace
from ranking_agent import rank_hypotheses

class FakeLLM:
    def __init__(self, decisions): self.decisions = decisions
    def invoke(self, messages):
        self.messages = messages
        return SimpleNamespace(content=json.dumps(dict(summary="Critical assessment", unanswered_aspects=["Causality"], decisions=self.decisions)))

def decision(idx, score=8, rank=1, accepted=True):
    return dict(id=idx, score=score, rank=rank, accepted=accepted, reason="Relevance and score justification")

class RankingTests(unittest.TestCase):
    def test_ranking_filter_and_audit(self):
        hypotheses = [{"target_metric": "A"}, {"target_metric": "B"}, {"target_metric": "C"}]
        llm = FakeLLM([decision(0, 7, 2), decision(1, 0, 3, False), decision(2, 9.5, 1)])
        accepted, report = rank_hypotheses(llm, "Compare A", "target", hypotheses)
        self.assertIn('You are the Ranking Agent', llm.messages[0].content)
        self.assertIn('Write all generated report text in English', llm.messages[0].content)
        self.assertEqual(accepted, [hypotheses[2], hypotheses[0]])
        self.assertIs(accepted[0], hypotheses[2])
        self.assertEqual([d['id'] for d in report['ranked_hypotheses']], [2, 0, 1])
        self.assertEqual(report['decisions'][1]['hypothesis'], hypotheses[1])
        self.assertEqual(report['rejected_count'], 1)

    def test_ties_follow_agent_rank(self):
        _, report = rank_hypotheses(FakeLLM([decision(0, 8, 2), decision(1, 8, 1)]), 'query', 'target', [{}, {}])
        self.assertEqual([d['id'] for d in report['ranked_hypotheses']], [1, 0])

    def test_all_rejected(self):
        accepted, report = rank_hypotheses(FakeLLM([decision(0, 0, 1, False)]), "query", "target", [{}])
        self.assertEqual(accepted, [])
        self.assertEqual(report['accepted_count'], 0)
        self.assertEqual(len(report['ranked_hypotheses']), 1)

    def test_score_boundaries_and_decimals(self):
        for score in (0, 0.1, 9.5, 10):
            with self.subTest(score=score):
                _, report = rank_hypotheses(FakeLLM([decision(0, score)]), 'query', 'target', [{}])
                self.assertEqual(report['ranked_hypotheses'][0]['score'], score)

    def test_invalid_score(self):
        for score in (None, True, 'invalid', -1, 10.1, 100, float('nan'), float('inf')):
            with self.subTest(score=score), self.assertRaises(ValueError):
                rank_hypotheses(FakeLLM([decision(0, score)]), 'query', 'target', [{}])

    def test_rank_normalization(self):
        for rank in (None, True, '1', 0, 2, 1.5):
            with self.subTest(rank=rank):
                _, report = rank_hypotheses(FakeLLM([decision(0, rank=rank)]), 'query', 'target', [{}])
                self.assertEqual(report['ranked_hypotheses'][0]['rank'], 1)
        _, report = rank_hypotheses(FakeLLM([decision(0, 5, 1), decision(1, 9, 1)]), 'query', 'target', [{}, {}])
        self.assertEqual([d['id'] for d in report['ranked_hypotheses']], [1, 0])
        self.assertTrue(report['normalizations'])

    def test_numeric_score_strings(self):
        _, report = rank_hypotheses(FakeLLM([decision(0, '8.5')]), 'query', 'target', [{}])
        self.assertEqual(report['ranked_hypotheses'][0]['score'], 8.5)
        self.assertTrue(report['normalizations'])

    def test_invalid_score_repaired_without_regenerating(self):
        class RepairLLM(FakeLLM):
            def __init__(self): self.calls = 0
            def invoke(self, messages):
                self.calls += 1
                self.decisions = [decision(0, 85 if self.calls == 1 else 8.5)]
                return super().invoke(messages)
        llm = RepairLLM()
        _, report = rank_hypotheses(llm, 'query', 'target', [{}])
        self.assertEqual(llm.calls, 2)
        self.assertEqual(len(report['repair_attempts']), 1)
        self.assertIn('score=85', report['repair_attempts'][0]['error'])
        self.assertEqual(report['ranked_hypotheses'][0]['score'], 8.5)

    def test_repair_is_bounded(self):
        llm = FakeLLM([decision(0, 85)])
        with self.assertRaisesRegex(ValueError, 'after 3 attempts.*id=0.*85'):
            rank_hypotheses(llm, 'query', 'target', [{}])

    def test_invalid_decisions(self):
        for decisions in ([], [decision(1)], [decision(0, accepted='false')], [{**decision(0), 'reason': ''}]):
            with self.subTest(decisions=decisions), self.assertRaises(ValueError):
                rank_hypotheses(FakeLLM(decisions), 'query', 'target', [{}])
        with self.assertRaises(ValueError):
            rank_hypotheses(FakeLLM([decision(0, rank=1), decision(0, rank=2)]), 'query', 'target', [{}, {}])

    def test_empty_query_or_list_skips(self):
        for query, hypotheses in (("", [{}]), ("query", [])):
            accepted, report = rank_hypotheses(None, query, 'target', hypotheses)
            self.assertEqual(report['status'], 'skipped')
            self.assertEqual(report['ranked_hypotheses'], [])
            self.assertEqual(accepted, hypotheses)

if __name__ == '__main__': unittest.main()
