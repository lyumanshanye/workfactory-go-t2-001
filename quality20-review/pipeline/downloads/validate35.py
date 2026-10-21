"""35 parallel occupation-specific prompt trials. Design drafts, NOT delivered packages."""
import concurrent.futures,datetime,hashlib,json,sys,threading,traceback
from pathlib import Path
MODULE=Path(__file__).resolve().parent
sys.path.insert(0,str(MODULE.parent))
import pipeline as p

ROOT=MODULE/'validation35_v1_20261021'
BRIEFS={
 'biostatisticians':('生物统计师','用虚构随访研究的失访和用药依从记录，给研究团队制作可审计的数据分析及偏倚说明；不是心血管样本量题，不编造临床疗效结论。'),
 'bookkeeping_accounting_and_auditing_clerks':('记账与审计文员','核对原创会展服务项目的客户预付款、完工验收与应收明细，为财务准备项目结算包；不做银行月末结账或税表映射。'),
 'civil_engineers':('土木工程师','依据虚构园区雨水沟修复测量、施工窗口和内部计价规则，比较分区修复方案并交工程量与现场交接；不做桥梁题。'),
 'computer_and_information_research_scientists':('计算机研究科学家','分析原创检索系统试验日志，检验两个候选算法的质量、延迟与资源取舍，交可复现分析与下一轮试验建议。'),
 'computer_and_information_systems_managers':('信息系统经理','根据虚构机构的软件席位使用与续费台账，制定满足服务连续性和内部预算的许可证整合方案与实施交接。'),
 'computer_user_support_specialists':('计算机用户支持专员','分析原创会议终端故障工单和设备清单，制作一线排查决策表与升级包；不伪造已修复或用户确认。'),
 'court_clerks':('法院文书','在虚构法院内部会务规则和工作日历下，准备公开听证的场次、材料登记和通知交接；不编造真实司法程序或法定期限。'),
 'customer_service_representatives':('客户服务代表','按虚构家电租赁公司的完整服务政策和工单记录，处理预约改期、争议费用与升级事项，形成可执行处理清单和回复稿。'),
 'data_entry_keyers':('数据录入员','依据原创馆藏移交单和明确字段词典，生成可导入登记表与待核对清单，处理重号、缺值和数量不一致。'),
 'financial_managers_branch_or_department':('部门财务经理','分析原创区域服务站的月度现金安排与维修承诺，在内部资金限制下制定分期支付方案和流动性预警。'),
 'human_resources_specialists':('人力资源专员','依据虚构组织的岗位说明、候选人授权材料和公开给定的内部评价规则，制作岗位匹配与面试交接，不推断敏感属性。'),
 'lawyers':('律师','审阅虚构双方的设备维护合同草案与已给定商业谈判底线，形成条款风险表和红线修改建议；不借未提供法律编造强制结论。'),
 'licensing_examiners_and_inspectors':('许可审查与检查员','依据明确标为虚构的社区设施内部准入标准和申请档案，制作材料缺口、现场核查安排与建议；不冒充政府许可。'),
 'management_analysts':('管理分析师','分析原创共享服务中心的受理、排队与返工记录，为负责人提出流程调整及可量化试点验收方案。'),
 'mechanical_engineering_technicians':('机械工程技术员','依据虚构装配线的测量数据、图纸参数摘录和内部公差表，制作异常分组、复测顺序与工程师交接，不声称真实认证。'),
 'mechanical_engineers':('机械工程师','依据虚构风机平台的负载、安装约束及供应商规格，比较改造选件并交接口核对和试装验证计划；不假称已做有限元验证。'),
 'medical_and_health_services_managers':('医疗卫生服务经理','分析原创非临床服务台的预约、人员和房间安排，制定保持窗口覆盖的服务改进排程，不涉及诊断和真实患者资料。'),
 'medical_secretaries':('医疗秘书','根据虚构门诊的匿名改期请求、人员可用性和明确排程规则，整理通知清单与日程交接，不作临床优先级判断。'),
 'online_merchants':('线上商户运营','分析原创店铺商品、退货和库存记录，制定有资金与履约约束的促销组合和客服交接，不编造平台政策。'),
 'personal_financial_advisors':('个人财务顾问','基于虚构家庭提供的收支和确定的储蓄目标，整理预算与应急储备情景，披露缺失信息；不推荐真实金融产品或保证收益。'),
 'petroleum_engineers':('石油工程师','分析虚构井组的生产、停机和内部运行限制，比较维护窗口与产量影响并给出数据缺口，不宣称真实储量评估或安全批准。'),
 'police_fire_and_ambulance_dispatchers':('警消急救调度员','依据虚构演练脚本、资源状态和完整给定的训练调度规则，制作事件分派时间线与复盘；不得用于真实应急或编造当地法规。'),
 'producers':('制作人','依据虚构播客季的人员、录音资源、审稿依赖和预算，制作可执行制作日程与变更取舍，不使用影片拍摄示范情节。'),
 'purchasing_agents_except_wholesale_retail_and_farm_products':('采购代理','根据虚构实验室的仪器校准服务报价、停机窗口和内部采购限制，制作授标比较与交接，不沿用MRO采购示范材料。'),
 'reporters_and_correspondents':('记者与通讯员','依据原创访谈摘录、公开声明模拟稿和事实时间线，制作社区设施报道稿及事实核验表，区分证实事实与待核实说法。'),
 'sales_agents_securities_and_commodities':('证券与商品销售代理','依据虚构机构的完整内部沟通限制、客户需求与模拟产品条款，制作信息适配核对和客户说明稿；不推荐真实产品或冒称合规批准。'),
 'sales_representatives_wholesale_and_manufacturing_technical_and_scientific_products':('技术产品销售代表','依据原创客户实验流程、仪器参数和报价授权，制作技术适配与商务提案，明确不满足条件及待验证接口。'),
 'secretaries_and_administrative_assistants_except_legal_medical_and_executive':('行政秘书与助理','依据虚构委员会的日程、材料提交与保密规则，制作一次跨部门评审会的议程、材料登记和行动交接。'),
 'social_science_research_assistants':('社会科学研究助理','依据原创社区服务访谈、编码手册和样本登记，制作可追溯主题编码与研究简报，保留反例和资料局限。'),
 'sociology_teachers_postsecondary':('高校社会学教师','依据原创课程目标、学生作业节选和课时约束，设计一次研讨课、反馈样例与评估说明，不把唯一政治观点当评分答案。'),
 'statisticians':('统计师','分析原创物流抽样检验记录，比较班组差异与抽样不确定性，制作可复核工作簿和谨慎的运营建议。'),
 'supply_chain_managers':('供应链经理','依据原创备件需求、运输班次、仓库容量与供应承诺，制定跨仓补货安排与短缺应对，量化服务和费用取舍。'),
 'technical_writers':('技术文档作者','依据虚构离线设备管理工具的接口、用户记录和版本行为，制作首次上手与故障恢复手册及可执行核对示例。'),
 'training_and_development_specialists':('培训与发展专员','依据原创服务人员能力观察、可用时间与业务覆盖要求，设计实操训练及课后行为评估，不沿用制造业培训情节。'),
 'web_administrators':('网站管理员','依据虚构知识库的发布记录、备份目录和服务窗口，制作可回滚迁移计划、配置核对和验收脚本说明；不运行真实基础设施变更。'),
}
EXTRA='''
本次是few-shot提示效果验证：为指定职业生成一道全新原创任务的完整设计规格，不要完成JobBench示范题，不复用示范事实。
不联网获取真实规则。案例机构、业务记录和内部规则须明确为原创虚构；真实法规、强制标准、外部单位价格若未给来源不得杜撰。
本次没有外部source，因此selected_sources=[]，source_decisions说明这一点。inputs每项除filename/purpose/content_plan外，还须给content字符串：完整、紧凑、可直接保存的CSV/JSON/TXT/MD文本，不能只提供计划、占位符或省略号。至少两份相互关联的材料，至少8条有效业务记录；不要为了条数制造无意义数据。
交付要求保留2到4份实际工作成果的目标定义，可用原生Office；本轮不生成二进制成果，不声称题包已物化。
额外返回reference_solution：基于你生成的完整输入，给出可复核的关键数值/事实、推导或证据链，以及合理替代解和限制；这是私有参考草稿，不冒充经过验证的实际Gold。
rubrics仍遵循原管线要求：至少20个不重复的实质评分项，权重只能3/7/10/-3/-7/-10，至少两个+10、至少一项负项、至少两个五档Gradient。每项包含criterion、具体evidence、acceptable_alternatives、failure_examples；Binary写anchors{0,1}，Gradient写levels五档。公有要求不能只藏在reference_solution或rubric。
只返回一次完整规格JSON。所有内容是待复核设计，不伪造执行、渲染、专业批准或难度校准。
'''
REVIEW=p.BASE+'''
你是新上下文中的设计审阅者，只审查实际提供的完整设计。不要生成新题或修复覆盖原题。审查rubric具体证据、0/1或五档锚点、输入数值与参考解是否自洽、评分是否有公开依据、等价解是否受尊重、根因重复扣分、专业安全和材料是否足以完成。每个数值判断给你实际复算的依据；未复算部分写not_verified，不能因为字段齐全就判优秀。
输出JSON：verdict=needs_revision或candidate_reviewed；findings列表{id,severity=blocking/major/minor,rubric_ids,problem,evidence,fix}；dimensions对象{evidence_specificity,anchor_quality,public_grounding,non_duplication,reference_consistency}每项{verdict=pass/needs_revision/not_verified,reason,example_rubric_ids}；recomputed_checks列表{claim,calculation,conclusion}；limitations列表。不要宣称专家审核、真实文件制作或判官校准完成。不要输出分数，不必附整份规格。
'''
LOCK=threading.Lock()

def structural(spec):
    problems=[]
    try:p.validate(spec)
    except Exception as exc:problems.append('legacy_spec_validation:'+type(exc).__name__)
    inputs=spec.get('inputs',[])
    if len(inputs)<2:problems.append('less_than_two_inputs')
    for item in inputs:
        try:p.safe(item['filename'])
        except Exception:problems.append('unsafe_input_filename')
        if not isinstance(item.get('content'),str) or len(item['content'])<30:problems.append('missing_actual_input_content:'+item.get('filename','?'))
    if not spec.get('reference_solution'):problems.append('missing_reference_solution')
    for row in spec.get('rubrics',[]):
        rid=row.get('id','?')
        for key in ('criterion','evidence','acceptable_alternatives','failure_examples'):
            if not row.get(key):problems.append(rid+':missing_'+key)
        if row.get('type')=='Binary' and set(row.get('anchors',{}))!={'0','1'}:problems.append(rid+':binary_anchors')
        if row.get('type')=='Gradient' and len(set(str(v) for v in row.get('levels',{}).values()))<5:problems.append(rid+':indistinct_gradient_anchors')
    return dict(passed=not problems,problems=problems,limitations='Field/format checks only; concrete grounding and scoring quality need actual review')

def one(index,occupation):
    tid=f'FS35-{index:02d}'
    chinese,brief=BRIEFS[occupation]
    state=dict(id=tid,occupation=occupation,occupation_zh=chinese,status='running',stage='generate',formal_accepted=False,materialized_package=False)
    dest=ROOT/'designs'/tid
    p.save(dest/'state.json',state)
    try:
        card=dict(id=tid,occupation=occupation,rubric_example_occupation=occupation,title=chinese+'原创工作任务',brief=brief,archetype='supplied_source')
        spec=p.call(tid,'fewshot_design_v1',p.design_prompt(card)+EXTRA,dict(card=card,sources=[]))
        p.save(dest/'spec.json',spec)
        checks=structural(spec)
        p.save(dest/'structure.json',checks)
        # Private review: no benchmark rubric, no previous review, no solver answer.
        state.update(stage='review',structure_pass=checks['passed'],rubric_count=len(spec.get('rubrics',[])))
        p.save(dest/'state.json',state)
        review=p.call(tid,'independent_review_v1',REVIEW,dict(spec=spec,structural_findings=checks['problems']))
        p.save(dest/'review.json',review)
        findings=review.get('findings',[])
        severe=[f for f in findings if f.get('severity') in ('major','blocking')]
        dimensions=review.get('dimensions',{})
        strong=all(dimensions.get(k,{}).get('verdict')=='pass' for k in ('evidence_specificity','anchor_quality','public_grounding','non_duplication','reference_consistency'))
        state.update(status='candidate_reviewed' if checks['passed'] and review.get('verdict')=='candidate_reviewed' and not severe and strong else 'needs_revision',stage='reviewed',major_findings=len(severe),review_verdict=review.get('verdict'),dimensions=dimensions)
    except Exception as exc:
        state.update(status='failed',error_type=type(exc).__name__,error=str(exc)[:700])
    state['finished_at']=p.now()
    p.save(dest/'state.json',state)
    return state

def main():
    p.ROOT=ROOT
    occupations=[r['occupation'] for r in json.loads((MODULE/'reference/index.json').read_text())['occupations']]
    assert len(occupations)==35 and set(occupations)==set(BRIEFS)
    claim=ROOT/'batch-claim'
    claim.mkdir(parents=True,exist_ok=False)
    manifest=dict(started_at=p.now(),scope='35 occupation-specific original design+rubric trials; no delivered packages or grading calibration',occupations=occupations,workers=35,auto_retry=False,formal_accepted=False,parameters=p.PARAMS,script_sha256=p.digest(Path(__file__)),fewshot_instructions_sha256=p.digest(MODULE/'fewshot_instructions.txt'))
    p.save(ROOT/'manifest.json',manifest)
    results=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=35) as pool:
        pending={pool.submit(one,n,occ):occ for n,occ in enumerate(occupations,1)}
        for future in concurrent.futures.as_completed(pending):
            row=future.result();results.append(row)
            report=dict(at=p.now(),target=35,finished=len(results),status='complete' if len(results)==35 else 'running',counts={status:sum(r['status']==status for r in results) for status in ('candidate_reviewed','needs_revision','failed')},materialized_packages=0,formal_accepted=0,results=sorted(results,key=lambda r:r['id']))
            p.save(ROOT/'summary.json',report)
            print(json.dumps(dict(id=row['id'],occupation=row['occupation'],status=row['status'],finished=len(results)),ensure_ascii=False),flush=True)
    print('Finished all35 design trials; do not equate reviewed designs with accepted packages',flush=True)

if __name__=='__main__':main()
