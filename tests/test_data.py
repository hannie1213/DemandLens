import unittest
from demandlens.data.quality import audit,validate
from demandlens.data.select_categories import select_categories
from demandlens.data.select_categories import complete_calendar

def row(d='2020-01-01',cid='1',purchase='1',code='a.b'):
    return dict(date=d,category_id=cid,category_code=code,views='5',cart='2',purchase=purchase)

class DailyContractTests(unittest.TestCase):
    def test_invalid_dates_rejected(self):
        for d in ['2020-02-30','2020-1-01','20200101','2020-01-01T00:00:00Z','']:
            with self.subTest(d=d):self.assertTrue(validate([row(d=d)]))

    def test_invalid_counts_rejected(self):
        for value in ['-1','1.5','nan','1e3','',True,1.5]:
            with self.subTest(value=value):self.assertTrue(validate([row(purchase=value)]))

    def test_duplicate_keys_and_missing_columns(self):
        self.assertTrue(validate([row(),row()]))
        r=row();del r['cart'];self.assertTrue(validate([r]))

    def test_large_ids_kept_exact(self):
        cid='9223372036854775807';r=row(cid=cid)
        self.assertFalse(validate([r]));self.assertEqual(r['category_id'],cid)
        self.assertTrue(validate([row(cid='9.223372036854776e18')]))

    def test_missing_names_counted(self):
        metrics,issues,_=audit([row(code='')])
        self.assertFalse(issues)
        self.assertEqual({r['metric']:r['value'] for r in metrics}['category_ids_without_code'],1)

    def test_expected_calendar_detects_endpoint_gaps(self):
        metrics,_,details=audit([row(d='2020-01-02')],'2020-01-01','2020-01-03')
        m={r['metric']:r['value'] for r in metrics}
        self.assertEqual(m['missing_all_site_days'],2);self.assertEqual(m['missing_category_days'],2)
        self.assertEqual(len([d for d in details if d['kind']=='missing_all_site_day']),2)

    def test_invalid_data_blocks_derived_statistics(self):
        metrics,issues,_=audit([row(purchase='bad')])
        self.assertTrue(issues)
        self.assertFalse(any(r['metric']=='total_purchase' for r in metrics))

class CategoryTests(unittest.TestCase):
    def test_test_activity_cannot_change_selection(self):
        base=[row(cid='1'),row(cid='2',purchase='2')]
        a=select_categories(base,'2020-01-01','2020-01-01',1)
        b=select_categories(base+[row(d='2021-01-01',purchase='999999')],'2020-01-01','2020-01-01',1)
        self.assertEqual(a,b);self.assertEqual(a[0]['category_id'],'2')

    def test_unknowns_not_zero_and_spans_not_continuity(self):
        rows=[row(d='2020-01-01',purchase='0'),row(d='2020-01-03')]
        r=select_categories(rows,'2020-01-01','2020-01-03',1,min_coverage=.5)[0]
        self.assertEqual(r['missing_days'],1)
        self.assertEqual(r['zero_purchase_day_pct_observed'],50)
        self.assertEqual(r['effective_history_days'],3)
        self.assertEqual(r['longest_consecutive_observed_days'],1)

    def test_conflicting_codes_excluded_anonymous_allowed(self):
        x=[row(d='2020-01-01',code='a'),row(d='2020-01-02',code='b'),row(d='2020-01-01',cid='2',code=''),row(d='2020-01-02',cid='2',code='')]
        r=select_categories(x,'2020-01-01','2020-01-02',10)
        byid={v['category_id']:v for v in r}
        self.assertFalse(byid['1']['selected']);self.assertTrue(byid['2']['selected'])

    def test_share_uses_all_development_purchases(self):
        r=select_categories([row(cid='1',purchase='3'),row(cid='2',purchase='1')],'2020-01-01','2020-01-01',1)
        self.assertEqual(r[0]['selected_set_coverage_pct'],75)

class CalendarTests(unittest.TestCase):
    def setUp(self):self.rows=[row(d='2020-01-01'),row(d='2020-01-03')]
    def test_unreviewed_gap_is_not_zero(self):
        out,log=complete_calendar(self.rows,['1'],'2020-01-01','2020-01-03',[])
        self.assertEqual(out[1]['purchase'],'');self.assertEqual(log[0]['status'],'unresolved_gap')
    def test_only_category_specific_review_allows_zero(self):
        e=dict(date='2020-01-02',category_id='2',decision='confirmed_zero',evidence_ref='test',approved_by='reviewer')
        out,_=complete_calendar(self.rows,['1'],'2020-01-01','2020-01-03',[e])
        self.assertEqual(out[1]['purchase'],'')
        e['category_id']='1'
        out,_=complete_calendar(self.rows,['1'],'2020-01-01','2020-01-03',[e])
        self.assertEqual(out[1]['purchase'],0);self.assertEqual(out[1]['category_code'],'')
    def test_empty_reference_cannot_approve_gap(self):
        e=dict(date='2020-01-02',category_id='1',decision='confirmed_zero',evidence_ref=' ',approved_by='reviewer')
        out,_=complete_calendar(self.rows,['1'],'2020-01-01','2020-01-03',[e])
        self.assertEqual(out[1]['purchase'],'')
    def test_duplicate_evidence_rejected(self):
        e=dict(date='2020-01-02',category_id='1',decision='unresolved_gap',evidence_ref='',approved_by='')
        with self.assertRaises(ValueError):complete_calendar(self.rows,['1'],'2020-01-01','2020-01-03',[e,e])


class AdditionalSourceQualityTests(unittest.TestCase):
    def test_integral_monthly_text_normalizes_without_editing_source_rows(self):
        from demandlens.data.quality import normalize_integral_counts
        rows=[dict(date='2019-10-01',category_id='1',category_code='',views='72.0',cart='0.00',purchase='7.0')]
        result=normalize_integral_counts(rows)
        self.assertEqual(result[0]['views'],'72')
        self.assertEqual(result[0]['cart'],'0')
        self.assertEqual(rows[0]['views'],'72.0')

    def test_fractional_or_nonfinite_monthly_values_are_not_truncated(self):
        from demandlens.data.quality import normalize_integral_counts
        for value in ['1.25','NaN','Infinity','-1']:
            with self.subTest(value=value):
                x=row();x['purchase']=value
                with self.assertRaises(ValueError):normalize_integral_counts([x])

    def test_external_anonymous_categories_remain_eligible(self):
        rows=[row(d='2019-10-01',cid=str(i),purchase=str(i+7),code='') for i in range(1,61)]
        from demandlens.data.select_categories import stratified_categories
        chosen=[r for r in stratified_categories(rows,'2019-10-01','2019-10-01',10) if r['selected']]
        self.assertEqual(len(chosen),10)
        self.assertTrue(all(not r['category_code_values'] for r in chosen))
        self.assertEqual({k:sum(r['activity_stratum']==k for r in chosen) for k in ['high','middle','low']},{'high':6,'middle':3,'low':1})

    def test_external_future_activity_or_missing_days_cannot_reselect_categories(self):
        from demandlens.data.select_categories import stratified_categories
        dev=[row(d='2019-10-01',cid=str(i),purchase=str(i+7),code='') for i in range(1,61)]
        baseline=stratified_categories(dev,'2019-10-01','2019-10-01',10)
        later=dev+[row(d='2020-01-01',cid='1',purchase='9999999',code='later.name')]
        # Most categories have no later rows, which cannot be used to replace them.
        self.assertEqual(baseline,stratified_categories(later,'2019-10-01','2019-10-01',10))

    def test_cosmetics_zero_counts_are_observed_not_unknown(self):
        from demandlens.evaluation.splits import unknown_days_from_calendar
        self.assertEqual(unknown_days_from_calendar([row(purchase='0')]),{})
        pending=row();pending['purchase']=''
        self.assertEqual(unknown_days_from_calendar([pending]),{'1':{'2020-01-01'}})

    def test_later_source_gap_stays_unknown_without_source_evidence(self):
        rows=[row(d='2019-11-30'),row(d='2019-12-02')]
        out,gaps=complete_calendar(rows,['1'],'2019-11-30','2019-12-02',[])
        self.assertEqual(out[1]['purchase'],'')
        self.assertEqual(gaps[0]['status'],'unresolved_gap')

if __name__=='__main__':unittest.main()



class CandidateReadinessTests(unittest.TestCase):
    def test_unpublished_candidate_has_clear_error(self):
        from demandlens.data.quality import read_candidate_daily
        with self.assertRaisesRegex(ValueError,'Daily candidate unavailable'):
            read_candidate_daily('.',dict(output_file=None,unresolved_gaps=71))
