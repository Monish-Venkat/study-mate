"""Validate and summarize real research measurements; never invent missing scores."""
import argparse
import json
from pathlib import Path
from statistics import mean

TARGETS={'content_accuracy':(.85,'min'),'faithfulness':(.85,'min'),'answer_relevance':(.80,'min'),
'context_relevance':(.75,'min'),'persona_consistency':(.78,'min'),'tam_usefulness':(4.0,'min'),
'tam_ease':(4.0,'min'),'latency_seconds':(5.0,'max_strict'),'pyq_accuracy':(.80,'min'),
'mock_compliance':(.90,'min'),'asr_wer':(.15,'max')}

def report(data):
    metrics={}
    for name,(target,rule) in TARGETS.items():
        values=data.get(name,[])
        maximum=5 if name.startswith('tam_') else float('inf') if name=='latency_seconds' else 1
        if not isinstance(values,list) or any(type(v) not in (int,float) or not 0<=v<=maximum for v in values):
            raise ValueError(f'{name}: provide finite numeric measurements in the valid range')
        if not values:metrics[name]={'status':'missing','target':target};continue
        value=mean(values)
        passed=value>=target if rule=='min' else value<target if rule=='max_strict' else value<=target
        metrics[name]={'status':'meets_threshold' if passed else 'below_threshold','mean':value,'n':len(values),'target':target}
    protocol={'faculty_benchmark_100':data.get('faculty_vetted_questions',0)>=100,
              'student_cohort_30':data.get('respondents',0)>=30,
              'exposure_14_days':data.get('minimum_exposure_days',0)>=14,
              'independent_style_judge':data.get('independent_style_judge') is True}
    return {'metrics':metrics,'protocol':protocol,'complete':all(p for p in protocol.values()) and all(m['status']=='meets_threshold' for m in metrics.values()),
            'note':'Imported measurements only. This report does not independently verify faculty labels, run RAGAS, or prove learning gains.'}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('measurements',type=Path)
    parser.add_argument('--output',type=Path,default=Path('evaluation/report.json'))
    args=parser.parse_args()
    result=report(json.loads(args.measurements.read_text(encoding='utf-8')))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(args.output)
