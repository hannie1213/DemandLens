import unittest
from datetime import date,timedelta
from demandlens.evaluation.splits import split_by_time

class SplitTests(unittest.TestCase):
    def setUp(self):
        self.cfg=dict(val_origin_start='2020-02-01',test_origin_start='2020-02-22',test_origin_end='2020-03-07',data_end='2020-03-31',horizon_days=7,eval_step_days=7)
        self.rows=[]
        for cid in ['1','2']:
            for k in range(75):
                b=date(2020,1,1)+timedelta(days=k)
                self.rows.append(dict(category_id=cid,input_start_date=str(b-timedelta(days=13)),input_end_date=str(b),target_start_date=str(b+timedelta(days=1)),target_end_date=str(b+timedelta(days=7))))

    def test_strict_boundary_purge(self):
        s=split_by_time(self.rows,self.cfg)
        for i in s['train']:self.assertLess(self.rows[i]['target_end_date'],self.cfg['val_origin_start'])
        for i in s['validation']:self.assertLess(self.rows[i]['target_end_date'],self.cfg['test_origin_start'])
        self.assertEqual(max(self.rows[i]['input_end_date'] for i in s['train']),'2020-01-24')
        self.assertEqual(len(s['validation']),4);self.assertEqual(len(s['test']),6)

    def test_shared_grid_even_when_one_category_missing(self):
        x=[r for r in self.rows if not(r['category_id']=='1' and r['input_end_date']=='2020-02-01')]
        s=split_by_time(x,self.cfg)
        origins={x[i]['input_end_date'] for i in s['validation']}
        self.assertEqual(origins,{'2020-02-01','2020-02-08'})
        self.assertFalse(any(x[i]['input_end_date']=='2020-02-02' for i in s['validation']))

    def test_all_positions_assigned_once(self):
        s=split_by_time(self.rows,self.cfg);positions=sum(s.values(),[])
        self.assertEqual(len(positions),len(self.rows));self.assertEqual(len(set(positions)),len(self.rows))

    def test_target_beyond_real_end_excluded(self):
        self.cfg.update(test_origin_end='2020-03-07',data_end='2020-03-10')
        s=split_by_time(self.rows,self.cfg)
        self.assertEqual(len(s['test']),4)

    def test_input_target_overlap_and_duplicate_origin_rejected(self):
        with self.assertRaises(ValueError):split_by_time(self.rows+[self.rows[0]],self.cfg)
        self.rows[0]['input_end_date']=self.rows[0]['target_start_date']
        with self.assertRaises(ValueError):split_by_time(self.rows,self.cfg)

    def test_missing_boundaries_and_overlapping_grid_rejected(self):
        with self.assertRaises(ValueError):split_by_time(self.rows,{})
        self.cfg['eval_step_days']=1
        with self.assertRaises(ValueError):split_by_time(self.rows,self.cfg)

    def test_legacy_date_column_aliases(self):
        x=[{(k[:-5] if k.endswith('_date') else k):v for k,v in r.items()} for r in self.rows]
        self.assertEqual(split_by_time(x,self.cfg),split_by_time(self.rows,self.cfg))


class SourceSpecificLeakageTests(unittest.TestCase):
    def setUp(self):
        self.cosmetics=dict(val_origin_start='2019-11-30',test_origin_start='2019-12-31',test_origin_end='2020-02-18',data_end='2020-02-29',horizon_days=7,eval_step_days=7)
        self.primary=dict(val_origin_start='2019-10-31',test_origin_start='2019-11-14',test_origin_end='2019-11-21',data_end='2019-11-30',horizon_days=7,eval_step_days=7)
        self.meta=[dict(category_id='1',input_start_date='2019-11-03',input_end_date='2019-11-30',target_start_date='2019-12-01',target_end_date='2019-12-07')]

    def test_cosmetics_28_day_training_is_calendar_feasible(self):
        from demandlens.evaluation.splits import audit_split_feasibility
        result=audit_split_feasibility(['1'],'2019-10-01','2020-02-29',self.cosmetics)
        self.assertEqual([r['train_per_complete_category'] for r in result],[47,40,26])
        self.assertTrue(all(r['validation_per_complete_category']==4 and r['test_per_complete_category']==8 for r in result))

    def test_primary_28_day_training_limit_is_not_hidden_by_external_history(self):
        from demandlens.evaluation.splits import audit_split_feasibility
        result=audit_split_feasibility(['1'],'2019-10-01','2019-11-30',self.primary)
        self.assertEqual(result[2]['usable_train_windows'],0)

    def test_unknown_target_day_excludes_window(self):
        self.assertEqual(split_by_time(self.meta,self.cosmetics)['validation'],[0])
        result=split_by_time(self.meta,self.cosmetics,{'1':{'2019-12-01'}})
        self.assertEqual(result['validation'],[]);self.assertEqual(result['excluded'],[0])

    def test_unknown_input_day_also_excludes_window(self):
        result=split_by_time(self.meta,self.cosmetics,{'1':{'2019-11-25'}})
        self.assertEqual(result['excluded'],[0])

    def test_other_category_missing_day_does_not_move_or_exclude_this_window(self):
        result=split_by_time(self.meta,self.cosmetics,{'2':{'2019-12-01'}})
        self.assertEqual(result['validation'],[0])

    def test_source_calendars_are_applied_independently_even_for_same_identifier(self):
        meta=[dict(category_id='1',input_start_date='2019-10-25',input_end_date='2019-11-07',target_start_date='2019-11-08',target_end_date='2019-11-14')]
        self.assertEqual(split_by_time(meta,self.primary)['excluded'],[0])
        self.assertEqual(split_by_time(meta,self.cosmetics)['train'],[0])

    def test_mixed_source_root_is_rejected(self):
        with self.assertRaises(ValueError):
            split_by_time(self.meta,{'m3':{'sources':{'multi_store':{},'cosmetics':{}}}})

if __name__=='__main__':unittest.main()



class SourceIdentityTests(unittest.TestCase):
    def test_wrong_or_missing_source_is_rejected(self):
        cfg=dict(dataset='multi_store',require_dataset_metadata=True,val_origin_start='2020-02-01',test_origin_start='2020-02-22',test_origin_end='2020-03-07',data_end='2020-03-31')
        row=dict(category_id='1',input_start_date='2020-01-01',input_end_date='2020-01-14',target_start_date='2020-01-15',target_end_date='2020-01-21')
        for source in [None,'cosmetics']:
            with self.subTest(source=source),self.assertRaisesRegex(ValueError,'Dataset mismatch'):
                split_by_time([dict(row,dataset=source)],cfg)
        self.assertEqual(split_by_time([dict(row,dataset='multi_store')],cfg)['train'],[0])
