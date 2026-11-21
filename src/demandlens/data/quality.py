"""M3 daily-table validation and audit. Standard library only."""
import csv
import re
from collections import Counter,defaultdict
from datetime import date,timedelta
from statistics import median
from pathlib import Path

FIELDS=['date','category_id','category_code','views','cart','purchase']
EVENTS=FIELDS[3:]
UINT=re.compile(r'0|[1-9][0-9]*\Z')

def parse_day(value):
    if not isinstance(value,str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}',value):
        raise ValueError('Expected YYYY-MM-DD UTC calendar date')
    return date.fromisoformat(value)

def day_range(start,end):
    a,b=parse_day(start),parse_day(end)
    if a>b:raise ValueError('Calendar start must not exceed end')
    while a<=b:
        yield a.isoformat();a+=timedelta(days=1)

def read_daily(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        missing=set(FIELDS)-set(reader.fieldnames or [])
        if missing:raise ValueError('Missing daily columns: '+','.join(sorted(missing)))
        return list(reader)

def write_csv(path,rows,fields):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore')
        writer.writeheader();writer.writerows(rows)

def validate(rows):
    """Strict contract; do not coerce invalid counts into zeros or deduplicate."""
    issues=[];keys=set()
    for line,r in enumerate(rows,2):
        def flag(kind,column):issues.append(dict(csv_line=line,issue=kind,column=column))
        for col in FIELDS:
            if col not in r:flag('missing_column',col)
        try:parse_day(r.get('date'))
        except (ValueError,TypeError):flag('invalid_date','date')
        cid=r.get('category_id')
        if not isinstance(cid,str) or not UINT.fullmatch(cid):flag('invalid_category_id','category_id')
        key=(r.get('date'),cid)
        if key in keys:flag('duplicate_date_category','date/category_id')
        keys.add(key)
        for col in EVENTS:
            value=r.get(col)
            if not isinstance(value,(str,int)) or isinstance(value,bool) or not UINT.fullmatch(str(value)):
                flag('invalid_count',col)
    return issues

def audit(rows,expected_start=None,expected_end=None):
    metrics=[];issues=validate(rows)
    def add(metric,value,status='measured'):metrics.append(dict(metric=metric,value=value,status=status))
    add('rows',len(rows));add('invalid_issues',len(issues))
    counts=Counter(x['issue'] for x in issues)
    for kind in ['invalid_date','invalid_category_id','duplicate_date_category','invalid_count','missing_column']:
        add(kind,counts[kind])
    for col in FIELDS:add('missing_'+col,sum(r.get(col) in (None,'') for r in rows))
    add('raw_duplicates_and_event_types','PENDING_M2_RAW_AUDIT','pending_m2')
    if not rows or issues:
        add('derived_metrics','not computed for empty or invalid daily table','blocked')
        return metrics,issues,[]
    observed_start=min(r['date'] for r in rows);observed_end=max(r['date'] for r in rows)
    if bool(expected_start)!=bool(expected_end):raise ValueError('Provide both expected calendar endpoints or neither')
    start,end=expected_start or observed_start,expected_end or observed_end
    calendar=list(day_range(start,end));scope=set(calendar)
    x=[r for r in rows if r['date'] in scope]
    add('observed_start',observed_start);add('observed_end',observed_end)
    add('audit_start',start);add('audit_end',end);add('calendar_days',len(calendar))
    add('rows_outside_audit_range',len(rows)-len(x))
    ids={r['category_id'] for r in x};codes=defaultdict(set);reverse=defaultdict(set);site=Counter();per=defaultdict(list)
    details=[]
    for r in x:
        cid=r['category_id'];code=r.get('category_code') or ''
        if code:
            for token in filter(None,code.split('|')):
                codes[cid].add(token);reverse[token].add(cid)
        site[r['date']]+=sum(int(r[c]) for c in EVENTS)
        per[cid].append((r['date'],int(r['purchase'])))
    add('distinct_category_ids',len(ids));add('category_ids_without_code',sum(not codes[c] for c in ids))
    add('ids_with_multiple_codes',sum(len(v)>1 for v in codes.values()))
    add('codes_with_multiple_ids',sum(len(v)>1 for v in reverse.values()))
    add('category_code_depths',';'.join(map(str,sorted({len(c.split('.')) for c in reverse}))))
    for cid in sorted(ids,key=int):
        if not codes[cid]:details.append(dict(kind='missing_code',category_id=cid,date='',detail='Anonymous ID retained'))
        if len(codes[cid])>1:details.append(dict(kind='multiple_codes',category_id=cid,date='',detail=';'.join(sorted(codes[cid]))))
    for code,identifiers in sorted(reverse.items()):
        if len(identifiers)>1:details.append(dict(kind='code_multiple_ids',category_id=';'.join(sorted(identifiers,key=int)),date='',detail=code))
    missing_site=sorted(scope-set(site));add('missing_all_site_days',len(missing_site))
    for d in missing_site:details.append(dict(kind='missing_all_site_day',category_id='',date=d,detail='Unknown until M2 source verification'))
    add('missing_category_days',len(ids)*len(calendar)-len(x))
    add('zero_purchase_observed_days',sum(int(r['purchase'])==0 for r in x))
    add('zero_purchase_observed_pct',100*sum(int(r['purchase'])==0 for r in x)/len(x) if x else '')
    for c in EVENTS:add('total_'+c,sum(int(r[c]) for r in x))
    def threshold(values):
        m=median(values);mad=median(abs(v-m) for v in values)
        return m+10*mad if mad else 5*m
    site_threshold=threshold(list(site.values())) if site else 0
    add('site_peak_threshold',site_threshold)
    for d,v in sorted(site.items()):
        if v>site_threshold:details.append(dict(kind='site_peak',category_id='',date=d,detail=str(v)))
    for cid,sequence in per.items():
        t=threshold([v for _,v in sequence])
        for d,v in sequence:
            if v>t:details.append(dict(kind='category_purchase_peak',category_id=cid,date=d,detail=f'purchase={v};threshold={t}'))
    add('site_peak_flags',sum(r['kind']=='site_peak' for r in details))
    add('category_purchase_peak_flags',sum(r['kind']=='category_purchase_peak' for r in details))
    add('gap_classification','PENDING_M2_SOURCE_EVIDENCE','pending_m2')
    return metrics,issues,details


from decimal import Decimal

def reconcile_project(root,config,dataset=None):
    root=Path(root)
    table=root/config['paths']['reports_tables_dir']/'aggregation_check.csv'
    with table.open(encoding='utf-8-sig',newline='') as stream:checks=list(csv.DictReader(stream))
    results=[];discrepancies=[]
    months={'01':'Jan','02':'Feb','03':'Mar','04':'Apr','05':'May','06':'Jun','07':'Jul','08':'Aug','09':'Sep','10':'Oct','11':'Nov','12':'Dec'}
    for source_id,source in config['datasets'].items():
        if dataset is not None and source_id!=dataset:continue
        path=root/config['paths']['processed_dir']/source['output']
        if not path.exists():continue
        rows=read_daily(path);totals=defaultdict(lambda:dict(views=0,cart=0,purchase=0))
        for row in rows:
            for column in ['views','cart','purchase']:totals[row['date'][:7]][column]+=int(row[column])
        for month,values in sorted(totals.items()):
            label=month[:4]+'-'+months[month[5:7]]
            for event,column in [('view','views'),('cart','cart'),('purchase','purchase')]:
                matches=[r for r in checks if r['dataset']==source_id and r['month']==label and r['check']=='count:'+event]
                if len(matches)!=1:raise ValueError(f'Missing or duplicate M2 counter: {source_id}/{label}/{event}')
                item=matches[0];matched=Decimal(item['raw_value'])==Decimal(item['aggregated_value'])==values[column]
                results.append(dict(dataset=source_id,month=label,event=event,upstream_valid_raw=item['raw_value'],upstream_aggregate=item['aggregated_value'],delivered_aggregate=values[column],status='MATCH' if matched else 'MISMATCH',evidence_scope='M2 raw counter plus M3 delivered CSV recomputation'))
        for item in checks:
            if item['dataset']==source_id and item['month']=='ALL' and item['check']=='combined:rows':
                reported=item['aggregated_value'];actual=len(rows)
                if Decimal(reported)!=actual:
                    discrepancies.append(dict(dataset=source_id,metric='combined:rows',m2_reported=reported,m3_observed=actual,status='M2_VALUE_RETAINED_UNCHANGED',note='Read-only discrepancy; no source table or upstream report was corrected'))
    return results,discrepancies,checks


def normalize_integral_counts(rows):
    """Normalize M2 monthly decimal text in memory; never truncate fractions or edit inputs."""
    from decimal import InvalidOperation
    output=[]
    for row in rows:
        item=dict(row)
        for column in EVENTS:
            try:value=Decimal(str(item[column]))
            except (InvalidOperation,KeyError,TypeError) as error:raise ValueError('Invalid monthly event count') from error
            if not value.is_finite() or value<0 or value!=value.to_integral_value():
                raise ValueError('Monthly event counts must be finite nonnegative integers')
            item[column]=str(int(value))
        output.append(item)
    return output


def read_candidate_daily(root, candidate):
    """Read a published candidate table or fail clearly before path construction."""
    path=candidate.get('output_file')
    if not path or candidate.get('unresolved_gaps',0):
        raise ValueError('Daily candidate unavailable: unresolved dates prevent integer-contract export')
    rows=read_daily(Path(root)/path)
    issues=validate(rows)
    if issues:raise ValueError('Published candidate violates the daily contract')
    return rows
