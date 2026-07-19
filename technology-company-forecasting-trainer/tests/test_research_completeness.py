import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
SKILL=ROOT/'skills/technology-company-forecasting-trainer'

class ResearchCompletenessTest(unittest.TestCase):
    def _write_csv(self,path,headers,rows):
        with path.open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.writer(f);w.writerow(headers);w.writerows(rows)

    def test_thin_summary_pack_fails(self):
        with tempfile.TemporaryDirectory() as td:
            w=Path(td)
            (w/'source_docs').mkdir()
            manifest={
                'run_id':'run://thin','entity':'THIN','security':'THIN','as_of':'2026-07-18T23:59:59Z',
                'purpose':'full model','fiscal_calendar':'calendar','currency':'USD','accounting_basis':'GAAP',
                'horizons':{'annual_years':3},'selected_mechanisms':['unit-volume-price-mix-cost','cycle-state-regime'],
                'readiness_target':'screen-grade','readiness_result':'screen-grade','phase_status':{},
                'research_completeness_required':True
            }
            (w/'run_manifest.json').write_text(json.dumps(manifest))
            sources=[]
            for i in range(9):
                p=w/'source_docs'/f's{i}.md';p.write_text('short summary fact ' * 20)
                sources.append({'source_id':f'S{i}','source_type':'filing' if i<3 else ('earnings' if i==3 else 'official-product'),
                    'publisher':'Publisher','published_at':'2026-01-01T00:00:00Z','retrieved_at':'2026-07-18T00:00:00Z',
                    'period_scope':f'FY{i}' if i<3 else 'current','evidence_tier':'E0' if i<3 else 'E1',
                    'content_hash':f'sha256:{i}','location':str(p),'claim_or_fact':'summary','allowed_use':'base',
                    'limitations':'','decision_status':'accepted'})
            (w/'source_manifest.json').write_text(json.dumps({'as_of':manifest['as_of'],'sources':sources}))
            (w/'forecast_snapshot.json').write_text(json.dumps({'horizon_contracts':{'FY+1':'point','FY+2':'point','FY+3':'point'}}))
            # Required files exist but remain thin/incomplete, so the validator must inspect content rather than presence alone.
            for name in ['research_coverage_matrix.csv','company_quality_moat_register.csv','technology_commercialization_register.csv','product_customer_driver_schedule.csv','material_assumption_support.csv']:
                (w/name).write_text('placeholder\n')
            (w/'report.md').write_text('# Report\n## Base forecast\n')
            r=subprocess.run([sys.executable,str(SKILL/'scripts/validate_research_completeness.py'),
                              '--workspace',str(w),'--strict'],capture_output=True,text=True)
            self.assertNotEqual(r.returncode,0,r.stdout+r.stderr)
            self.assertIn('accepted research corpus',r.stdout+r.stderr)
            self.assertIn('source depth metadata missing',r.stdout+r.stderr)

    def test_substantive_workspace_passes(self):
        with tempfile.TemporaryDirectory() as td:
            w=Path(td)
            (w/'source_docs').mkdir()
            manifest={
                'run_id':'run://test','entity':'TEST','security':'TEST','as_of':'2026-07-18T23:59:59Z',
                'purpose':'full model','fiscal_calendar':'calendar','currency':'USD','accounting_basis':'GAAP',
                'horizons':{'annual_years':3},'selected_mechanisms':['unit-volume-price-mix-cost'],
                'readiness_target':'screen-grade','readiness_result':'screen-grade',
                'phase_status':{'research_completeness':'complete'},'research_completeness_required':True
            }
            (w/'run_manifest.json').write_text(json.dumps(manifest))
            sources=[]
            topics=['historical_financials_and_vintage','current_quarter_and_guidance','business_segments_products_revenue_units',
                    'customers_channels_and_demand','competitors_and_market_structure','supply_capacity_delivery_inventory_cost',
                    'technology_roadmap_and_product_stages','papers_standards_patents_failure_boundaries',
                    'management_governance_capital_allocation','company_quality_and_moat','balance_sheet_cash_and_economic_capital']
            for i in range(10):
                text=('substantial source evidence product customer technology management accounting cash ' * 180)
                p=w/'source_docs'/f's{i}.md';p.write_text(text)
                stype='filing' if i<3 else ('earnings-call-transcript' if i==3 else ('official-product' if i<6 else 'industry-research'))
                period=f'FY{2023+i}' if i<3 else 'current'
                sources.append({'source_id':f'S{i}','source_type':stype,'publisher':'Publisher','published_at':'2026-01-01T00:00:00Z',
                    'retrieved_at':'2026-07-18T00:00:00Z','period_scope':period,'evidence_tier':'E0' if i<3 else 'E1',
                    'content_hash':f'sha256:{i}','location':str(p),'claim_or_fact':'substantial fact','allowed_use':'base',
                    'limitations':'','decision_status':'accepted','document_depth':'full_document','word_count':1440,
                    'anchor_count':8,'coverage_topics':topics,'original_source_available':True,'page_or_section_anchors':['p1','p2']})
            (w/'source_manifest.json').write_text(json.dumps({'as_of':manifest['as_of'],'sources':sources}))
            (w/'forecast_snapshot.json').write_text(json.dumps({'horizon_contracts':{'FY+1':'point-and-interval','FY+2':'point-and-interval','FY+3':'distribution-only'}}))
            coverage=[]
            required=['historical_financials_and_vintage','current_quarter_and_guidance','business_segments_products_revenue_units',
                'customers_channels_and_demand','competitors_and_market_structure','supply_capacity_delivery_inventory_cost',
                'technology_roadmap_and_product_stages','papers_standards_patents_failure_boundaries',
                'management_governance_capital_allocation','company_quality_and_moat','balance_sheet_cash_and_economic_capital',
                'industry_policy_and_macro','news_and_event_timeline','valuation_and_reverse_implied']
            for t in required:
                coverage.append([t,'critical' if t in required[:6] else 'high','accepted','S0;S1','','C1;C2','substantial','none',f'model:{t}','screen-grade','reviewer'])
            self._write_csv(w/'research_coverage_matrix.csv',['topic','materiality','status','accepted_source_ids','rejected_source_ids','evidence_clusters','depth','unresolved_questions','model_link','readiness_cap','reviewer'],coverage)
            dims=['management_execution','governance_and_incentives','capital_allocation_and_mna','rd_productivity_and_cadence',
                  'technology_ip_and_standards','customer_stickiness_switching_costs','channel_distribution_advantage_and_risk',
                  'cost_scale_manufacturing_or_data_advantage','competitive_response_and_substitution','balance_sheet_and_counterparty_resilience']
            self._write_csv(w/'company_quality_moat_register.csv',['dimension','status','evidence_source_ids','independent_clusters','claim','forecast_permission','downside_or_falsification','confidence','reviewer'],
                            [[d,'accepted','S0;S4','2','evidence claim','margin/share persistence','failure evidence','medium','reviewer'] for d in dims])
            self._write_csv(w/'technology_commercialization_register.csv',['technology_or_product','materiality','current_stage','paper_source_ids','patent_source_ids','standard_source_ids','benchmark_or_prototype','customer_evaluation_or_qualification','production_evidence','revenue_evidence','competitor_route','technical_bottleneck','allowed_model_use','confidence','reviewer'],
                            [['Core','critical','production','S6','S5','S4','benchmark','qualified','production','revenue','alternative','cost','base','medium','reviewer'],
                             ['Next','high','qualification','S6','S5','S4','prototype','evaluation','pilot','none','alternative','yield','scenario','low','reviewer']])
            self._write_csv(w/'product_customer_driver_schedule.csv',['segment_or_product','materiality','revenue_unit','payer_or_customer','end_user','volume_usage_or_deployment_driver','price_arpu_or_asp','mix_share_or_attach','cost_and_capacity_constraint','program_stage','evidence_source_ids','confidence','schedule_status','consolidation_link','human_required'],
                            [['Core','critical','units','enterprise customers','operators','installed units','ASP','mix/share','capacity/cost','production','S0;S4','medium','modeled','total revenue','false']])
            self._write_csv(w/'material_assumption_support.csv',['assumption_id','metric','horizon','scenario','materiality_weight','sensitivity_to_output','support_status','evidence_cluster_count','source_ids','allowed_horizon','falsification_trigger','notes'],
                            [['A1','volume','FY+1','Base',0.35,'high','hard_anchor',2,'S0;S4','FY+1','actual volume',''],
                             ['A2','price','FY+2','Base',0.25,'high','corroborated',2,'S1;S5','FY+2','price',''],
                             ['A3','mix','FY+2','Base',0.20,'medium','corroborated',2,'S4;S6','FY+2','mix',''],
                             ['A4','cost','FY+3','Base',0.20,'medium','single_source',1,'S2','FY+3','cost','']])
            (w/'report.md').write_text('# Report\n## Technology, IP and roadmap\n## Company quality and moat\n## Management and capital allocation\n')
            r=subprocess.run([sys.executable,str(SKILL/'scripts/validate_research_completeness.py'),
                              '--workspace',str(w),'--strict'],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            result=json.loads((w/'research_completeness.json').read_text())
            self.assertTrue(result['passed'])

if __name__=='__main__':
    unittest.main()
