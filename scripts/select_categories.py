"""M3-only preparation for independently enabled primary and cosmetics sources."""
from pathlib import Path
import argparse,csv,hashlib,json,sys
import yaml
PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT/'src'))
from demandlens.data.quality import read_daily,audit,write_csv,reconcile_project,normalize_integral_counts,FIELDS
from demandlens.data.select_categories import select_categories,stratified_categories,complete_calendar
from demandlens.evaluation.splits import unknown_days_from_calendar,audit_split_feasibility

def resolve_path(root,value):
    path=Path(value);return path if path.is_absolute() else Path(root)/path

def load_config(project_root=None,config_path=None):
    root=Path(project_root or PROJECT).resolve()
    path=Path(config_path).resolve() if config_path else root/'config/config.yaml'
    with path.open(encoding='utf-8-sig') as stream:cfg=yaml.safe_load(stream)
    if not isinstance(cfg,dict) or not {'paths','datasets'}<=set(cfg):
        raise ValueError('Configuration requires paths and datasets')
    if not isinstance(cfg.get('m3'),dict) or not isinstance(cfg['m3'].get('sources'),dict):
        raise ValueError('Missing M3 preparation profiles. Preserve m3.sources when freezing the shared config, or pass --config PATH to a complete preparation config. Source dates and candidate IDs cannot be inferred safely.')
    cfg.setdefault('approval',{'frozen':False,'approved_by':None,'approved_at':None,'version':None})
    if not isinstance(cfg['m3'].get('sources'),dict):raise ValueError('Source profiles required')
    return cfg,root


def prepare_source(root,cfg,source_id):
    c=cfg['m3']['sources'][source_id]
    if not c.get('enabled'):raise ValueError(f'Source not enabled: {source_id}')
    if c['development_end']>=c['split']['test_origin_start']:raise ValueError('Development selection reaches test origin')
    if c['strategy'] not in ['development_activity_stratified_60_30_10','purchase_rank']:raise ValueError('Unsupported selection strategy')
    tables=root/cfg['paths']['reports_tables_dir'];tables.mkdir(parents=True,exist_ok=True)
    processed=root/cfg['paths']['processed_dir'];processed.mkdir(parents=True,exist_ok=True)
    source=processed/cfg['datasets'][source_id]['output'];rows=read_daily(source)
    metrics,issues,details=audit(rows,c['calendar_start'],c['calendar_end'])
    if issues:raise ValueError(f'{source_id}: invalid daily contract: {issues[:10]}')
    reconciliation,discrepancies,checks=reconcile_project(root,cfg,dataset=source_id)
    if not reconciliation or any(r['status']!='MATCH' for r in reconciliation):raise ValueError(f'{source_id}: missing or mismatched source counters')
    metrics=[r for r in metrics if r['metric']!='raw_duplicates_and_event_types']
    for item in checks:
        if item['dataset']==source_id and item['check'].startswith(('invalid:','excluded:','duplicate:','missing:')):
            metrics.append(dict(metric=f"m2_raw_evidence:{item['month']}:{item['check']}",value=item['raw_value'],status='reported_by_m2_not_independently_raw_rescanned'))
    metrics.append(dict(metric='m3_recomputed_month_event_matches',value=len(reconciliation),status='delivered_aggregate_verified_not_raw_rescanned'))
    metrics.append(dict(metric='site_peak_dates',value=';'.join(sorted(r['date'] for r in details if r['kind']=='site_peak')),status='flags_only_not_deleted'))
    dev=[]
    for path in c['development_sources']:
        monthly=read_daily(resolve_path(root,path))
        dev+=normalize_integral_counts([r for r in monthly if c['development_start']<=r['date']<=c['development_end']])
    index={(r['date'],r['category_id']):r for r in rows}
    for row in dev:
        key=(row['date'],row['category_id'])
        if key not in index or any(int(row[col])!=int(index[key][col]) for col in ['views','cart','purchase']):raise ValueError('Development monthly keys/counts differ from delivered source')
    proposals={};comparison=[]
    for n in c['candidate_counts']:
        ranked=select_categories(dev,c['development_start'],c['development_end'],n,c['minimum_observed_coverage'],c['minimum_development_purchases'])
        balanced=stratified_categories(dev,c['development_start'],c['development_end'],n,c['minimum_observed_coverage'],c['minimum_development_purchases'])
        for strategy,items in [('purchase_rank',ranked),('activity_stratified',balanced)]:
            selected=[r for r in items if r['selected']]
            comparison.append(dict(strategy=strategy,requested_count=n,selected_count=len(selected),development_purchase_coverage_pct=selected[0]['selected_set_coverage_pct'] if selected else None))
        proposals[n]=balanced if c['strategy']=='development_activity_stratified_60_30_10' else ranked
    evidence=[]
    if c.get('gap_evidence'):
        with resolve_path(root,c['gap_evidence']).open(encoding='utf-8-sig',newline='') as stream:evidence=list(csv.DictReader(stream))
    variants={}
    for n in c['candidate_counts']:
        selected=[r for r in proposals[n] if r['selected']];ids=[r['category_id'] for r in selected]
        if len(ids)!=n:raise ValueError('Insufficient categories for fixed quotas')
        if ids!=c['variants'][str(n)]['selected_ids']:raise ValueError('Configured candidate IDs differ from development selection')
        suffix=('' if source_id=='multi_store' else '_'+source_id)+('_top20' if n==20 else '')
        write_csv(tables/f'category_selection{suffix}.csv',selected,list(selected[0]))
        completed,gaps=complete_calendar(rows,ids,c['calendar_start'],c['calendar_end'],evidence)
        missing=unknown_days_from_calendar(completed)
        final=processed/c['variants'][str(n)]['output']
        if missing:
            if final.exists():final.unlink()
            output=None;status='withheld_unresolved_gaps_no_daily_contract_output'
        else:
            write_csv(final,completed,FIELDS);output=final;status='complete_observed_candidate_not_final_selection'
        gap_path=tables/f'gap_review{suffix}.csv'
        if n==20 and gaps and {cid:sorted(days) for cid,days in missing.items()}==variants.get('10',{}).get('unknown_days'):
            gap_path=tables/('gap_review'+('' if source_id=='multi_store' else '_'+source_id)+'.csv')
        elif gaps:write_csv(gap_path,gaps,['date','category_id','status','evidence_ref','approved_by'])
        elif gap_path.exists():gap_path.unlink()
        feasibility=audit_split_feasibility(ids,c['calendar_start'],c['calendar_end'],c['split'],missing)
        variants[str(n)]=dict(candidate_count=n,release_status=status,output_file=output.relative_to(root).as_posix() if output else None,
            selected_ids=ids,expected_calendar_rows=len(completed),observed_selected_rows=len(completed)-sum(len(v) for v in missing.values())-sum(r['status']=='confirmed_zero' for r in gaps),
            unresolved_gaps=sum(len(v) for v in missing.values()),filled_zero_rows=sum(r['status']=='confirmed_zero' for r in gaps),
            unknown_days={cid:sorted(days) for cid,days in missing.items()},split_feasibility=feasibility,
            development_purchase_coverage_pct=selected[0]['selected_set_coverage_pct'])
        metrics.extend([dict(metric=f'candidate_{n}_categories',value=n,status='M1_confirmed_comparison_not_final_selection'),
            dict(metric=f'candidate_{n}_expected_calendar_rows',value=len(completed),status='calendar_audit'),
            dict(metric=f'candidate_{n}_unresolved_category_days',value=sum(len(v) for v in missing.values()),status='never_implicitly_zero'),
            dict(metric=f'candidate_{n}_observed_selected_rows',value=variants[str(n)]['observed_selected_rows'],status='measured'),
            dict(metric=f'candidate_{n}_purchase_coverage_pct',value=selected[0]['selected_set_coverage_pct'],status='development_only')])
    # Default view is only a convenience alias. Both candidate records are authoritative.
    view=variants[str(c['default_count'])]
    metadata=dict(dataset=source_id,role=c['role'],enabled=True,default_count=c['default_count'],final_count=None,
        input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),input_rows=len(rows),
        calendar_start=c['calendar_start'],calendar_end=c['calendar_end'],development_start=c['development_start'],development_end=c['development_end'],
        category_strategy_comparison=comparison,split=c['split'],raw_events_reprocessed=False,variants=variants,**view)

    return [dict(dataset=source_id,**r) for r in metrics],metadata

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root',type=Path,default=PROJECT)
    parser.add_argument('--config',type=Path,default=None)
    parser.add_argument('--dataset',choices=['all','multi_store','cosmetics'],default='all')
    parser.add_argument('--require-approved',action='store_true')
    parser.add_argument('--require-ready',action='store_true',help='Fail if any selected source has unknown calendar counts')
    args=parser.parse_args();cfg,root=load_config(args.project_root,args.config)
    approval=cfg['approval']
    if args.require_approved and not (approval.get('frozen') and approval.get('approved_by') and approval.get('approved_at') and approval.get('version')):raise SystemExit('PENDING_M1: final source-specific protocol approval required')
    enabled=[key for key,value in cfg['m3']['sources'].items() if value.get('enabled')]
    requested=enabled if args.dataset=='all' else [args.dataset]
    tables=root/cfg['paths']['reports_tables_dir'];reports=tables.parent;reports.mkdir(parents=True,exist_ok=True)
    manifest_path=reports/'m3_run_manifest.json';quality_path=tables/'quality_report.csv'
    previous={}
    if manifest_path.exists():previous=json.loads(manifest_path.read_text(encoding='utf-8')).get('datasets',{})
    quality=[]
    if quality_path.exists():
        with quality_path.open(encoding='utf-8-sig',newline='') as stream:quality=[r for r in csv.DictReader(stream) if r.get('dataset') and r['dataset'] not in requested]
    for source_id in requested:
        metrics,metadata=prepare_source(root,cfg,source_id);quality+=metrics;previous[source_id]=metadata
    write_csv(quality_path,quality,['dataset','metric','value','status'])
    manifest=dict(release_status='M3_preparation_not_final_model_evaluation',enabled_datasets=enabled,approval=approval,comparison_decision=cfg['m3']['comparison_decision'],datasets=previous,full_original_experiment_completed=False,limitations=['M1 protocol approval pending','Primary 28-day lookback remains infeasible under its current split','Cosmetics unknown category-days require M2 evidence or exclusion of every affected input/target window','External data preparation does not establish zero-shot cross-store model validity','Raw source completeness, true duplicates and licenses not independently verified','Actual M4 feature files and M5/M6 model results are outside M3 scope'])
    manifest_path.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps({key:{'status':previous[key]['release_status'],'output':previous[key]['output_file'],'rows':previous[key]['expected_calendar_rows'],'unknown_days':previous[key]['unresolved_gaps']} for key in requested},indent=2))
    if args.require_ready and any(v['unresolved_gaps'] for key in requested for v in previous[key]['variants'].values()):raise SystemExit('PENDING_M2_GAP_EVIDENCE: no final cosmetics daily table is claimed')

if __name__=='__main__':main()
