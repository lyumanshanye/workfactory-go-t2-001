"""A prompt fragment, not another model stage or grader."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
MARKER='JOBBENCH_RUBRIC_FEWSHOT_V1'
# These are our explicit analogy defaults, NOT official occupational mappings.
DEFAULTS={
    'FIN':'financial_managers_branch_or_department',
    'DA':'statisticians',
    'LAW':'lawyers',
    'MED':'medical_and_health_services_managers',
    'GO':'management_analysts',
    'DE':'technical_writers',
    'GA':'producers',
}

def prompt(card):
    explicit=card.get('rubric_example_occupation') or card.get('occupation')
    index=json.loads((ROOT/'reference/index.json').read_text())
    known={r['occupation'] for r in index['occupations']}
    if explicit:
        if explicit not in known:
            raise ValueError('No exact JobBench example; explicitly set rubric_example_occupation to a suitable analogy')
        occupation=explicit
        selection='Explicit example selection; a deliberate analogy when occupations differ'
    else:
        occupation=DEFAULTS[card['domain']]
        selection='Our broad-domain analogy default, NOT an exact or official occupational mapping'
    example=json.loads((ROOT/'examples'/f'{occupation}.json').read_text())
    demonstration={k:example[k] for k in ('occupation','task_id','prompt','reference_files','rubrics','source_url')}
    return '\n\n'+MARKER+'\n'+(ROOT/'fewshot_instructions.txt').read_text()+'\n示范选择：'+selection+'\n<jobbench_example>\n'+json.dumps(demonstration,ensure_ascii=False,indent=2)+'\n</jobbench_example>\n示范到此结束。请为用户消息中的当前新任务返回完整规格；上述细化要求适用于其中的rubrics。不要回答示范题。\n'

