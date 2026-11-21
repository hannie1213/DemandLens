"""M3 chronological source-specific split and unknown-day exclusion."""
from datetime import timedelta
from ..data.quality import parse_day,day_range,EVENTS

def unknown_days_from_calendar(rows):
    """Return category-specific unknown dates; observed zero is not unknown."""
    unknown={}
    for row in rows:
        if any(row.get(column) in ('',None) for column in EVENTS):
            parse_day(row['date'])
            unknown.setdefault(str(row['category_id']),set()).add(row['date'])
    return unknown

def split_by_time(meta,config,unknown_days=None):
    """Return row positions in train/validation/test/excluded for ONE source.

    Pass that source's split configuration, not a mixed multi-source config.
    Unknown dates invalidate both historical inputs and future labels; they
    never cause category reselection, date-grid shifts or implicit zero filling.
    """
    if 'm3' in config and 'sources' in config.get('m3',{}):
        raise ValueError('Pass one source-specific split; do not mix store calendars')
    cfg=config.get('split',config)
    keys=['val_origin_start','test_origin_start','test_origin_end','data_end']
    if not all(cfg.get(k) for k in keys):raise ValueError('Split placeholders require actual data and M1 confirmation')
    val,test,end,data_end=[parse_day(cfg[k]) for k in keys]
    if not val<test<=end<=data_end:raise ValueError('Invalid chronological origin boundaries')
    horizon=cfg.get('horizon_days',7);step=cfg.get('eval_step_days',7)
    if type(horizon)!=int or type(step)!=int or horizon<1 or step<horizon:
        raise ValueError('Evaluation step must be an integer at least as large as horizon')
    records=meta.to_dict('records') if hasattr(meta,'to_dict') else list(meta)
    missing={str(cid):{parse_day(day) for day in days} for cid,days in (unknown_days or {}).items()}
    result={'train':[],'validation':[],'test':[],'excluded':[]};seen=set()
    for i,row in enumerate(records):
        if cfg.get('require_dataset_metadata') and row.get('dataset')!=cfg.get('dataset'):
            raise ValueError('Dataset mismatch: metadata.dataset must match the source-specific split.dataset')
        def dt(key):return parse_day(row.get(key+'_date',row.get(key,'')))
        a,b,c,d=[dt(key) for key in ['input_start','input_end','target_start','target_end']]
        if not a<=b<c<=d or c!=b+timedelta(days=1) or (d-c).days+1!=horizon:
            raise ValueError('Invalid or leaking input/target interval')
        if not row.get('category_id'):raise ValueError('Missing category_id')
        cid=str(row['category_id']);key=(cid,b)
        if key in seen:raise ValueError('Duplicate category prediction origin')
        seen.add(key)
        if any(a<=day<=d for day in missing.get(cid,set())):part='excluded'
        elif d>data_end:part='excluded'
        elif b<val and d<val:part='train'
        elif val<=b<test and d<test and (b-val).days%step==0:part='validation'
        elif test<=b<=end and (b-test).days%step==0:part='test'
        else:part='excluded'
        result[part].append(i)
    return result

def audit_split_feasibility(ids,start,end,config,unknown_days=None,lookbacks=(7,14,28)):
    """Calendar-only M3 audit; no M4 features or purchase-label values are built."""
    first,last=parse_day(start),parse_day(end);horizon=int(config.get('horizon_days',7))
    result=[]
    for lookback in lookbacks:
        meta=[]
        for cid in map(str,ids):
            for day in day_range(start,end):
                origin=parse_day(day)
                if origin-timedelta(days=lookback-1)<first or origin+timedelta(days=horizon)>last:continue
                meta.append(dict(dataset=config.get('dataset'),category_id=cid,input_start_date=str(origin-timedelta(days=lookback-1)),input_end_date=str(origin),target_start_date=str(origin+timedelta(days=1)),target_end_date=str(origin+timedelta(days=horizon))))
        parts=split_by_time(meta,config,unknown_days)
        one=[r for r in meta if r['category_id']==str(ids[0])]
        theoretical=split_by_time(one,config)
        per=[]
        for cid in map(str,ids):
            per.append(dict(category_id=cid,**{key:sum(meta[i]['category_id']==cid for i in indices) for key,indices in parts.items()}))
        result.append(dict(lookback_days=lookback,
          train_per_complete_category=len(theoretical['train']),validation_per_complete_category=len(theoretical['validation']),test_per_complete_category=len(theoretical['test']),
          usable_train_windows=len(parts['train']),usable_validation_windows=len(parts['validation']),usable_test_windows=len(parts['test']),
          excluded_windows=len(parts['excluded']),per_category=per,
          status='blocked_no_training_windows' if not parts['train'] else ('source_gaps_excluded' if unknown_days else 'calendar_feasible_not_model_experiment')))
    return result
