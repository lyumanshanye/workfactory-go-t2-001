"""Offline administrative rehearsal only. No clinical eligibility or live action."""
import argparse,datetime as dt,json
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]

def iso(value,field):
    if not isinstance(value,str):raise ValueError(field+' must be ISO date')
    date=dt.date.fromisoformat(value)
    if date.isoformat()!=value:raise ValueError(field+' must be YYYY-MM-DD')
    return date

def route(records,policy=None):
    policy=policy or json.loads((BASE/'references/policy.json').read_text())
    if not isinstance(records,list) or not records:raise ValueError('nonempty case list required')
    seen=set();validated=[]
    for row in records:
        if not isinstance(row,dict):raise ValueError('case must be object')
        required={'id','as_of','birth_date','sex','prior_doses','full_course_reported','special_health','current_health_question'}
        if not required<=row.keys():raise ValueError('missing required field')
        cid=row['id']
        if not isinstance(cid,str) or not cid or cid in seen:raise ValueError('missing/duplicate case ID')
        seen.add(cid);day=iso(row['as_of'],'as_of')
        birth=iso(row['birth_date'],'birth_date') if row['birth_date'] is not None else None
        if birth and birth>day:raise ValueError('birth date later than rehearsal date')
        if row['sex'] not in ['female','male',None]:raise ValueError('unsupported sex value')
        prior=row['prior_doses']
        if prior is not None and (type(prior) is not int or prior<0):raise ValueError('invalid prior dose count')
        for field in ['full_course_reported','special_health','current_health_question']:
            if row[field] is not None and type(row[field]) is not bool:raise ValueError('invalid tri-state flag')
        validated.append((row,day,birth))
    results=[]
    for row,day,birth in validated:
        age=day.year-birth.year-((day.month,day.day)<(birth.month,birth.day)) if birth else None
        prior=row['prior_doses'];complete=row['full_course_reported']
        source=['S01首段','S02一（一）/二']
        if day>iso(policy['snapshot_date'],'snapshot'):
            status,reason='POLICY_REVIEW','超出历史技能冻结时点，先取得适用版本；不是政策已失效。'
        elif day<iso(policy['implementation_date'],'implementation'):
            status,reason='PRELAUNCH','全国项目尚未实施；不能以公开日或落款日提前承诺免费接种。'
        elif birth is None or row['sex'] is None or any(row[k] is None for k in ['prior_doses','full_course_reported','special_health','current_health_question']) or (complete and prior==0):
            status,reason='DATA_REVIEW','必要人口/接种史字段缺失或内部不一致，先核实，不将未知当零剂。'
        elif birth==iso(policy['cohort_boundary_date'],'cohort'):
            status,reason='POLICY_CLARIFICATION','恰处原文日期边界；依R2本地约定请政策负责人核实，不自行补国家解释。'
        elif row['sex']!='female' or birth<iso(policy['cohort_boundary_date'],'cohort'):
            status,reason='PROGRAM_SCOPE_REVIEW','不符合此国家项目文字范围，另请接种单位核实其他政策/服务；非一概禁止HPV疫苗。'
        elif age<13 or age>=18:
            status,reason='AGE_REVIEW','未到常规年龄或超出所引未满18岁补种范围，不能直接确认项目服务。'
        elif row['special_health'] or row['current_health_question']:
            status,reason='CLINICIAN_REVIEW','特殊健康状态或本次健康问题需医护判断；行政人员不确定剂次或接种许可。'
        elif complete:
            status,reason='COURSE_RECORD_REVIEW','核实已完成全程记录；S02二（三）1说明完成全程者无需再接种，不能自动重启。'
        elif prior>0:
            status,reason='PRIOR_HISTORY_REVIEW','核实既往剂次/厂家与知情告知条件；不得自动重启或无条件替换厂家。'
        else:
            status,reason='SERVICE_REVIEW','可转接种单位核对常规项目服务，仍需医护评估与服务可用性确认。'
        results.append(dict(id=row['id'],as_of=row['as_of'],age=age,route=status,reason=reason,source_refs=source,clinical_clearance=False,appointment_confirmed=False))
    return dict(schema='hpv-service-routing/1',status='draft_rehearsal_not_approved',policy_snapshot=policy['snapshot_date'],cases=results)

def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
    if a.cases.resolve()==a.out.resolve():p.error('input and output must differ')
    result=route(json.loads(a.cases.read_text()))
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'cases':len(result['cases'])}))

if __name__=='__main__':main()
