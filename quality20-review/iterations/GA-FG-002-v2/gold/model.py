"""Original closed planning model, independent implementation for revision 2.

Integer shipment arithmetic; no external engine claims or baked-in optimum.
This file also serves as the reference deliverable model.py.
"""
import argparse,hashlib,itertools,json
from pathlib import Path

def route_metrics(route,rate,n,policy,stress=False):
    distance=sum(abs(a-b) for a,b in zip(route['from'],route['to']))
    t=route['age_periods']+(policy['stress_age_periods'] if stress else 0)
    cycle=route['cycle_days']+(policy['stress_cycle_days'] if stress else 0)
    demand=route['demand']*(policy['stress_demand_percent'] if stress else 100)//100
    factor=max(31,255-max(0,t-rate['days1'])-max(0,t-rate['days1']-rate['days2']))
    delivered=min(demand,n*(policy['year_days']//cycle)*route['capacity'])
    numerator=rate['base']*distance*factor
    full,tail=divmod(delivered,route['capacity'])
    revenue=full*(numerator*route['capacity']//(2**21))+numerator*tail//(2**21)
    capex=n*route['capex'];running=n*route['annual_running']
    return dict(distance=distance,age_periods=t,time_factor=factor,cycle_days=cycle,available_trips=n*(policy['year_days']//cycle),demand=demand,delivered=delivered,revenue=revenue,capex=capex,annual_running=running,first_year_net=revenue-capex-running)

def solve_case(routes,rates,policy,budget):
    options={r['id']:[dict(vehicles=n,base=route_metrics(r,rates[r['cargo']],n,policy),stress=route_metrics(r,rates[r['cargo']],n,policy,True)) for n in range(policy['max_per_option']+1)] for r in routes}
    feasible=[]
    for vector in itertools.product(range(policy['max_per_option']+1),repeat=len(routes)):
        if sum(vector)>policy['fleet_limit']:continue
        groups=[r['exclusive_group'] for r,n in zip(routes,vector) if n]
        if len(groups)!=len(set(groups)):continue
        selected=[options[r['id']][n] for r,n in zip(routes,vector)]
        capex=sum(s['base']['capex'] for s in selected)
        stress=sum(s['stress']['first_year_net'] for s in selected)
        if capex>budget or stress<policy['minimum_stress_net']:continue
        feasible.append(dict(fleet=dict(zip([r['id'] for r in routes],vector)),capex=capex,base_net=sum(s['base']['first_year_net'] for s in selected),stress_net=stress,vehicles=sum(vector)))
    feasible.sort(key=lambda s:(-s['stress_net'],-s['base_net'],s['capex'],tuple(s['fleet'][r['id']] for r in routes)))
    return dict(budget=budget,feasible_count=len(feasible),best=feasible[0] if feasible else None,alternatives=feasible[1:4],options=options)

def solve(inputs):
    routes=json.loads((inputs/'routes.json').read_text());rates=json.loads((inputs/'cargo-rates.json').read_text());policy=json.loads((inputs/'planning_policy.json').read_text())
    cases={c['id']:solve_case(routes,rates,policy,c['budget']) for c in policy['budget_cases']}
    first,second=[cases[c['id']] for c in policy['budget_cases'][:2]]
    comparison=None
    if first['best'] and second['best']:
        a,b=first['best'],second['best']
        comparison=dict(capex_saved=a['capex']-b['capex'],stress_net_forgone=a['stress_net']-b['stress_net'],stress_net_retained_fraction=b['stress_net']/a['stress_net'])
    return dict(currency='GBP',scope='fictional closed planning model; not an OpenTTD engine execution',cases=cases,budget_comparison=comparison,input_sha256={n:hashlib.sha256((inputs/n).read_bytes()).hexdigest() for n in ['routes.json','cargo-rates.json','planning_policy.json']})

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--inputs',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    result=solve(args.inputs);args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'plan.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+'\n')

if __name__=='__main__':main()
