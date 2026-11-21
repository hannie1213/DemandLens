"""Development-only category candidates. No test-period ranking information."""
from collections import defaultdict
from .quality import day_range,parse_day,validate

SELECTION_FIELDS=['rank','category_id','category_code_values','purchase_total','purchase_share_dev_pct',
 'observed_days','missing_days','effective_history_days','longest_consecutive_observed_days',
 'zero_purchase_day_pct_observed','calendar_coverage_pct','code_stable','eligible','selection_reason',
 'selected','requested_count','selected_set_coverage_pct']

def select_categories(rows,dev_start,dev_end,count=10,min_coverage=.8,min_purchase=1):
    if isinstance(count,bool) or count<1 or not 0<=min_coverage<=1 or min_purchase<1:
        raise ValueError('Invalid selection thresholds')
    calendar=list(day_range(dev_start,dev_end))
    # Ignore out-of-development rows before computing any candidate statistic.
    x=[r for r in rows if dev_start<=r.get('date','')<=dev_end]
    if validate(x):raise ValueError('Resolve development-table validation issues before selection')
    groups=defaultdict(list)
    for r in x:groups[r['category_id']].append(r)
    total=sum(int(r['purchase']) for r in x);result=[]
    for cid,seq in groups.items():
        p=sum(int(r['purchase']) for r in seq);n=len(seq);codes=sorted({token for r in seq for token in (r['category_code'] or '').split('|') if token})
        observed=sorted(r['date'] for r in seq);coverage=n/len(calendar)
        longest=run=1
        for a,b in zip(observed,observed[1:]):
            run=run+1 if (parse_day(b)-parse_day(a)).days==1 else 1;longest=max(longest,run)
        reasons=[]
        if coverage<min_coverage:reasons.append('insufficient_coverage')
        if p<min_purchase:reasons.append('insufficient_purchases')
        if len(codes)>1:reasons.append('conflicting_codes')
        result.append(dict(category_id=cid,category_code_values=';'.join(codes),purchase_total=p,
          purchase_share_dev_pct=100*p/total if total else '',observed_days=n,missing_days=len(calendar)-n,
          effective_history_days=(parse_day(observed[-1])-parse_day(observed[0])).days+1,
          longest_consecutive_observed_days=longest,zero_purchase_day_pct_observed=100*sum(int(r['purchase'])==0 for r in seq)/n,
          calendar_coverage_pct=100*coverage,code_stable=len(codes)==1,eligible=not reasons,
          selection_reason=';'.join(reasons) if reasons else ('eligible_anonymous_id' if not codes else 'eligible')))
    result.sort(key=lambda r:(not r['eligible'],-r['purchase_total'],-r['calendar_coverage_pct'],int(r['category_id'])))
    for rank,r in enumerate(result,1):r.update(rank=rank,selected=bool(r['eligible'] and rank<=count),requested_count=count)
    covered=sum(r['purchase_total'] for r in result if r['selected'])
    for r in result:r['selected_set_coverage_pct']=100*covered/total if total else ''
    return result


def stratified_categories(rows,dev_start,dev_end,count=10,min_coverage=1.0,min_purchase=7):
    """A development-only 60/30/10 high/middle/low activity quota proposal.

    Activity strata are equal-count thirds of eligible development categories,
    ordered by purchase volume and numeric ID. A quota may include tied activity
    at a stratum boundary; numeric ID resolves ties reproducibly. Thresholds and
    quotas are proposals, not validated optimal hyperparameters.
    """
    if count not in (10,20):raise ValueError('Stratified candidates support count 10 or 20')
    ranked=select_categories(rows,dev_start,dev_end,count,min_coverage,min_purchase)
    eligible=[r for r in ranked if r['eligible']]
    n=len(eligible);a=n//3;b=2*n//3
    groups={'high':eligible[:a],'middle':eligible[a:b],'low':eligible[b:]}
    quotas={'high':count*6//10,'middle':count*3//10,'low':count//10}
    selected=set();stratum={}
    for group,candidates in groups.items():
        stratum.update({r['category_id']:group for r in candidates})
        selected.update(r['category_id'] for r in candidates[:quotas[group]])
    total=sum(r['purchase_total'] for r in ranked)
    selected_total=sum(r['purchase_total'] for r in ranked if r['category_id'] in selected)
    for r in ranked:
        r.update(activity_stratum=stratum.get(r['category_id'],'ineligible'),selected=r['category_id'] in selected,
          requested_count=count,selected_set_coverage_pct=100*selected_total/total if total else '',
          selection_strategy='development_activity_stratified_60_30_10')
    return ranked


from .quality import FIELDS,EVENTS

EVIDENCE_FIELDS=['date','category_id','decision','evidence_ref','approved_by']
GAP_FIELDS=['date','category_id','status','evidence_ref','approved_by']

def complete_calendar(rows,ids,start,end,evidence):
    if validate(rows):raise ValueError('Invalid daily contract')
    ids=list(map(str,ids))
    if not ids or len(set(ids))!=len(ids):raise ValueError('Selected IDs must be nonempty and unique')
    index={(r['date'],r['category_id']):r for r in rows};proofs={};result=[];log=[]
    for e in evidence:
        if not set(EVIDENCE_FIELDS)<=set(e):raise ValueError('Missing gap evidence fields')
        parse_day(e['date']);key=(e['date'],str(e['category_id']))
        if key in proofs:raise ValueError('Duplicate gap evidence')
        if e['decision'] not in ['confirmed_zero','unresolved_gap','collection_gap']:
            raise ValueError('Invalid gap decision')
        proofs[key]=e
    for cid in ids:
        for d in day_range(start,end):
            if (d,cid) in index:
                result.append(index[(d,cid)].copy());continue
            e=proofs.get((d,cid),{})
            confirmed=e.get('decision')=='confirmed_zero' and bool(str(e.get('evidence_ref','')).strip()) and bool(str(e.get('approved_by','')).strip())
            r=dict.fromkeys(FIELDS,'');r.update(date=d,category_id=cid)
            if confirmed:r.update({c:0 for c in EVENTS})
            result.append(r)
            log.append(dict(date=d,category_id=cid,status='confirmed_zero' if confirmed else 'unresolved_gap',
              evidence_ref=e.get('evidence_ref',''),approved_by=e.get('approved_by','')))
    return result,log
