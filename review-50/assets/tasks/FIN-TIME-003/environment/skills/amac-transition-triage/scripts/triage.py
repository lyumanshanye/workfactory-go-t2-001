"""Actual offline routing helper under an explicit local evidence SOP."""
import argparse,datetime,hashlib,json
from pathlib import Path
from openpyxl import load_workbook

NAMES=['S01_五月切换公告选摘.docx','S02_九月切换公告选摘.docx','S03_指引2阅读器全文.docx','S04_受理事项.json','S05_证据登记.xlsx','S06_材料登记.xlsx','S07_H变更文件摘录.docx','S08_工作委托.docx']
SKILL=Path(__file__).resolve().parents[1]
POLICY=SKILL/'references/team-sop.json'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def date(v):return datetime.date.fromisoformat(v) if v else None
def xrows(p):
    w=load_workbook(p,data_only=True);rows=list(w.active.values);head=rows.pop(0);w.close()
    return [dict(zip(head,r)) for r in rows]

def run(inp):
    policy=json.loads(POLICY.read_text());packet=json.loads((inp/NAMES[3]).read_text())
    asof=datetime.datetime.fromisoformat(packet['as_of'])
    if asof.tzinfo is None or packet['as_of']!=policy['as_of']:raise ValueError('Wrong frozen business time/SOP')
    may=date(policy['public_source_dates']['notice5']['effective_on']);sep=date(policy['public_source_dates']['notice21']['effective_on'])
    evidence=xrows(inp/NAMES[4]);materials=xrows(inp/NAMES[5]);cases=packet['cases']
    ids=[c['case_id'] for c in cases]
    if len(set(ids))!=len(ids):raise ValueError('Duplicate case ID')
    if any(r['case_id'] not in ids for r in evidence+materials):raise ValueError('Orphan evidence/material')
    evidids=[r['evidence_id'] for r in evidence]
    if len(set(evidids))!=len(evidids):raise ValueError('Duplicate evidence ID')
    validtypes=policy['local_evidence']['equal_primary_types']+policy['local_evidence']['non_decisive_types']
    for r in evidence:
        if r['kind'] not in validtypes:raise ValueError('Unknown evidence authority')
        when=datetime.datetime.fromisoformat(r['recorded_at']);observed=datetime.datetime.fromisoformat(r['observed_as_of'])
        if when.tzinfo is None or observed.tzinfo is None or when>asof or observed>when:raise ValueError('Invalid/future evidence time')
        if r['observed_as_of']!=policy['local_evidence']['required_same_observation_time']:raise ValueError('Evidence observation time mismatch')
    result=[]
    for case in cases:
        cid=case['case_id'];op=case['operation'];submitted=date(case['action_submitted_on'])
        if submitted and submitted>asof.date():raise ValueError('Future application date')
        docs=[r for r in evidence if r['case_id']==cid]
        primary=[r for r in docs if r['kind'] in policy['local_evidence']['equal_primary_types']]
        ignored=[r['evidence_id'] for r in docs if r['kind'] in policy['local_evidence']['non_decisive_types']]
        row=dict(case_id=cid,operation=op,action_submitted_on=case['action_submitted_on'],evidence_ids=[r['evidence_id'] for r in primary],ignored_note_ids=ignored,evidence_state='CONSISTENT',adopted_facts=None,conflict_fields=[],route='UNDETERMINED',review_scope='待证据确认',source_basis=[],material_gaps=[],name_check='NOT_IN_LIMITED_SCOPE',dispatch_stage=policy['local_dispatch']['normal_stage'],next_owner=policy['local_dispatch']['case_workflow_owner'],next_action='按对应新旧口径进入法务审阅，不代表全部实体条件已满足。',clarification_question=None,external_submission_authorized=False)
        if len(primary)!=2 or {r['kind'] for r in primary}!=set(policy['local_evidence']['equal_primary_types']):
            row.update(evidence_state='MISSING',dispatch_stage=policy['local_dispatch']['blocked_stage'],next_owner=policy['local_evidence']['clarification_owner'],next_action='补齐两个同观察时点的原始证据，不以销售便笺代替。',clarification_question=f'{cid}：请补齐system_snapshot及compliance_attestation在09:00的原始证据及适用字段。');result.append(row);continue
        facts=[json.loads(r['facts_json']) for r in primary]
        conflicts=[k for k in set(facts[0])|set(facts[1]) if facts[0].get(k)!=facts[1].get(k)]
        if conflicts:
            row.update(evidence_state='CONFLICT',conflict_fields=sorted(conflicts),dispatch_stage=policy['local_dispatch']['blocked_stage'],next_owner=policy['local_evidence']['clarification_owner'],next_action='暂停对该事项选定确定分支，核实同字段冲突；不按新便笺、文件顺序或营销要求选边。',clarification_question=f"{cid}：请对{','.join(sorted(conflicts))}确认09:00的真实值，并说明{','.join(row['evidence_ids'])}何者需受控更正及依据；未获澄清前保留冲突。");result.append(row);continue
        f=facts[0];row['adopted_facts']=f
        required=['action_completed_on'] if op=='manager_registration' else ['registered_on','actual_control_change','action_completed_on'] if op=='manager_change' else ['filed_on']
        if any(k not in f for k in required):
            row.update(evidence_state='MISSING',dispatch_stage=policy['local_dispatch']['blocked_stage'],next_action='缺必要事实，补证后再分流。',clarification_question=f'{cid}：请补充必要字段{required}及可追溯依据。');result.append(row);continue
        for key in ['registered_on','filed_on','action_completed_on']:
            value=date(f.get(key))
            if value and value>asof.date():raise ValueError('Future established fact')
        if op in ['manager_registration','manager_change']:
            if submitted is None:raise ValueError('Manager action needs submission date')
            completed=date(f['action_completed_on'])
            if completed and completed<submitted:raise ValueError('Completion precedes submission')
            row['source_basis']=['S01 items I/III']
            if submitted<may and completed and completed<may:
                row.update(route='PRE_MAY_COMPLETED_ARCHIVE',review_scope='既有办结事实归档；不重新认证旧法全条件',dispatch_stage=policy['local_dispatch']['archive_stage'],next_action='保留办理时间与证据索引，不把该已完成事项当5月后未办结事项重做。')
            elif op=='manager_registration':row.update(route='MAY_NEW_REGISTRATION',review_scope='新办法登记要求审阅，不是登记已经通过')
            else:
                registered=date(f['registered_on'])
                if registered is None or registered>=submitted or not isinstance(f['actual_control_change'],bool):raise ValueError('Existing manager/change nature not established')
                row['source_basis']+=['S01 item II']
                row.update(route='MAY_CONTROL_FULL_REVIEW' if f['actual_control_change'] else 'MAY_RELATED_CHANGE_REVIEW',review_scope='变更后管理人全面符合新办法登记要求的核查范围' if f['actual_control_change'] else '相关变更事项符合新办法；不是全体存量条件重做')
        elif op=='fund_operation':
            filed=date(f['filed_on']);row['source_basis']=['S02 item II']
            if filed and filed<sep:row.update(route='LEGACY_OPERATIONS_SCOPE',review_scope='仅继续募集/投资运作可按原有规定，非一切新要求豁免',next_action='保持该狭义存续运作分支，后续备案信息变更另走新要求审阅。')
            else:row.update(evidence_state='MISSING',dispatch_stage=policy['local_dispatch']['blocked_stage'],next_action='不具备明确9月28日前已备案依据，不能使用存续运作例外。',clarification_question=f'{cid}：请补9月28日前实际备案完成日期及对应证据。')
        elif op in ['fund_filing','fund_change','fund_liquidation']:
            if case['fund_kind'] not in ['PE','VC']:raise ValueError('Outside PE/VC packet scope')
            row['source_basis']=['S02 items I/II','S03 article2']
            if op=='fund_filing':row.update(route='GUIDE2_PENDING_FILING' if submitted and submitted<sep else 'GUIDE2_NEW_FILING',review_scope='按新指引办理备案，完整条件交法务继续核查')
            elif op=='fund_change':row.update(route='GUIDE2_RELATED_CHANGE',review_scope='相关变更事项符合新指引；不因已备案而免变更材料')
            else:row.update(route='GUIDE2_LIQUIDATION',review_scope='按新指引办理清算业务；未认定清算已经完成')
            if op=='fund_change' and case.get('change_kind')=='custodian':
                subset=[r for r in materials if r['case_id']==cid];given={r['doc_type']:r['status'] for r in subset}
                if len(given)!=len(subset):raise ValueError('Duplicate material group')
                row['material_gaps']=[k for k in policy['limited_material_check']['required_document_groups'] if given.get(k)!='provided_excerpt']
                row['source_basis']+=['S03 article27(II), opening paragraph']
                if row['material_gaps']:row.update(dispatch_stage=policy['local_dispatch']['blocked_stage'],next_owner=policy['local_dispatch']['material_owner'],next_action='补齐缺失新托管协议或基金合同；已收三项仅为原创摘录，不宣称全套法律实体合规。',clarification_question=f"{cid}：请补{','.join(row['material_gaps'])}的有效新文本；三项旧摘录不替代新协议组。")
            if op=='fund_filing' and case.get('check_name'):
                name=case['fund_name'];forbidden=any(w in name for w in ['理财','资管产品','资管计划'])
                permitted=('股权基金' in name or '股权投资' in name) if case['fund_kind']=='PE' else ('创业投资基金' in name or case['legal_form'] in ['company','partnership'] and '从事创业投资活动' in case['business_scope'])
                row['name_check']='RENAME_REQUIRED' if forbidden or not permitted else 'LIMITED_NAME_CHECK_OK'
                row['source_basis']+=['S03 article9']
                if row['name_check']=='RENAME_REQUIRED':row.update(dispatch_stage=policy['local_dispatch']['blocked_stage'],next_owner=policy['local_dispatch']['name_owner'],next_action='改掉禁止性名称词并核正确策略标识，回到法务审阅；不由经办人自行宣称获得例外。',clarification_question=f'{cid}：请提出不含理财等禁词、符合股权/创投策略标识的新名称供法务核定。')
        else:raise ValueError('Unsupported operation')
        result.append(row)
    return dict(as_of=packet['as_of'],executor='amac-transition-triage',local_sop_schema=policy['schema'],input_sha256={n:sha(inp/n) for n in NAMES},skill_sha256={str(p.relative_to(SKILL)):sha(p) for p in [SKILL/'SKILL.md',POLICY,Path(__file__).resolve()]},cases=result,counts={'total':len(result),'hold':sum(r['dispatch_stage']==policy['local_dispatch']['blocked_stage'] for r in result),'archive':sum(r['dispatch_stage']==policy['local_dispatch']['archive_stage'] for r in result),'legal_review_pending':sum(r['dispatch_stage']==policy['local_dispatch']['normal_stage'] for r in result)},external_submission_authorized=False,scope='Actual local SOP execution on fictional cases and real frozen rule excerpts. Not live AMAC data, filing approval, full compliance or a trusted execution signature.')

def main():
    p=argparse.ArgumentParser();p.add_argument('--input-dir',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=run(a.input_dir)
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(json.dumps(r['counts']))

if __name__=='__main__':main()
