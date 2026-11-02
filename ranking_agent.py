"""Post-generation relevance scoring, ranking and filtering."""
import json
import math
from llm_support import message_text
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage


def rank_hypotheses(llm, user_query, target, hypotheses):
    if not hypotheses or not str(user_query).strip():
        return hypotheses, {
            'status': 'skipped',
            'reason': 'No hypotheses or no User Query to evaluate.',
            'decisions': [],
            'ranked_hypotheses': [],
        }
    instructions = """You are the Ranking Agent, a specialist and critical reviewer of generated hypotheses.
Evaluate hypothesis relevance to the User Query after all generation has finished.
Assess every hypothesis, including target, subgroup conditions, comparison,
direction and aggregation. Reject unrelated hypotheses and explain the missing connection. Write all generated report text in English.
Also assign every hypothesis a relevance score from 0 to 10 and a unique rank.
Score how directly and specifically it addresses the User Query, considering
alignment with the target, subgroup, comparison, direction and aggregation.
Decimal scores are allowed. Use 0 for unrelated hypotheses, scores above 0 and below 4
for weak relevance, 4 to below 7 for partial relevance, 7 to below 9 for strong
relevance, and 9 to 10 for direct, comprehensive relevance.
The score measures query relevance, not statistical significance or probability.
Rank the complete list from highest to lowest score, starting at 1 with no gaps.
Break equal-score ties by specificity and usefulness to the query.
Explain the acceptance decision and score in each reason. Do not rewrite hypotheses.
Respond ONLY with a JSON object:
{"summary": "English critical assessment",
 "unanswered_aspects": ["English explanation"],
 "decisions": [{"id": 0, "accepted": true, "score": 9, "rank": 1, "reason": "English explanation"}]}
Return exactly one decision for every id. Scores must be JSON numbers between 0 and 10 inclusive, never percentages or scores out of 100. Ranks must be JSON integers. """
    messages = [
        SystemMessage(content=instructions),
        HumanMessage(content=json.dumps({
            'user_query': user_query, 'target': target,
            'hypotheses': [{'id': i, 'hypothesis': h} for i, h in enumerate(hypotheses)],
        }, ensure_ascii=False)),
    ]
    attempts = []
    for attempt in range(1, 4):
        response = llm.invoke(messages)
        raw = message_text(response).strip()
        try:
            report, by_id, ordered = _parse_ranking_report(raw, len(hypotheses))
            break
        except (ValueError, TypeError) as exc:
            attempts.append({'attempt': attempt, 'error': str(exc)})
            if attempt == 3:
                raise ValueError(f'Ranking Agent returned an invalid report after 3 attempts: {exc}') from exc
            messages.extend([
                AIMessage(content=raw),
                HumanMessage(content=(
                    f'Correct your JSON report. Validation error: {exc}. '
                    f'Return all {len(hypotheses)} decisions, one for every original id. '
                    'Use finite numeric scores from 0 to 10, never 0 to 100. '
                    'Use distinct integer ranks from 1 to the number of hypotheses, '
                    'ordered by descending score. Keep summary, unanswered_aspects, '
                    'accepted (JSON boolean), and a nonempty reason for every decision.'
                )),
            ])
    report['repair_attempts'] = attempts
    accepted = [hypotheses[d['id']] for d in ordered if d['accepted']]
    report.update(status='completed', user_query=user_query, generated_count=len(hypotheses),
                  accepted_count=len(accepted), rejected_count=len(hypotheses) - len(accepted))
    report['decisions'] = [{**by_id[i], 'hypothesis': h} for i, h in enumerate(hypotheses)]
    report['ranked_hypotheses'] = [{**d, 'hypothesis': hypotheses[d['id']]} for d in ordered]
    return accepted, report


def _parse_ranking_report(raw, count):
    if raw.startswith('```') and raw.endswith('```'):
        raw = raw.split('\n', 1)[1].rsplit('```', 1)[0].strip()
    report = json.loads(raw)
    if not isinstance(report, dict):
        raise ValueError('Report must be a JSON object')
    decisions = report.get('decisions')
    if (not isinstance(report.get('summary'), str) or not report['summary'].strip()
            or not isinstance(report.get('unanswered_aspects'), list)
            or not all(isinstance(x, str) for x in report['unanswered_aspects'])
            or not isinstance(decisions, list) or len(decisions) != count):
        raise ValueError(f'Report must include summary, unanswered_aspects and exactly {count} decisions')
    by_id = {}
    normalizations = []
    for decision in decisions:
        if not isinstance(decision, dict):
            raise ValueError('Every decision must be an object')
        idx = decision.get('id')
        if (type(idx) is not int or idx not in range(count) or idx in by_id
                or type(decision.get('accepted')) is not bool
                or not isinstance(decision.get('reason'), str) or not decision['reason'].strip()):
            raise ValueError(f'Invalid id, accepted or reason for decision id={idx!r}')
        original_score = decision.get('score')
        score = original_score
        if isinstance(score, str):
            try:
                score = float(score.strip())
            except ValueError:
                pass
        if type(score) not in (int, float) or not math.isfinite(score) or not 0 <= score <= 10:
            raise ValueError(f'Hypothesis id={idx}: score={original_score!r}; expected a number from 0 to 10')
        if isinstance(original_score, str):
            normalizations.append(f'id={idx}: numeric score string converted to number')
        decision['score'] = score
        rank = decision.get('rank')
        # Position is derived from scores, with model rank used only to resolve ties.
        if isinstance(rank, str):
            try:
                rank = float(rank.strip())
            except ValueError:
                pass
        valid_rank = type(rank) in (int, float) and math.isfinite(rank) and rank == int(rank) and 1 <= rank <= count
        decision['model_rank'] = decision.get('rank')
        decision['_tie_rank'] = int(rank) if valid_rank else count + 1
        by_id[idx] = decision
    ordered = sorted(by_id.values(), key=lambda d: (-d['score'], d['_tie_rank'], d['id']))
    for rank, decision in enumerate(ordered, 1):
        if type(decision.get('rank')) is not int or decision['rank'] != rank:
            normalizations.append(f"id={decision['id']}: rank normalized to {rank} using descending scores")
        decision['rank'] = rank
        del decision['_tie_rank']
    report['normalizations'] = normalizations
    return report, by_id, ordered
