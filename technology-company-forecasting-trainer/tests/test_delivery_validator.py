import csv
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from contract_fixtures import valid_investment_snapshot, valid_model_graph

SKILL=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / 'scripts'))
from package_self_test import SMOKE_SHEETS, write_minimal_workbook

class DeliveryValidatorTest(unittest.TestCase):
    def test_scaffold_and_strict_validation(self):
        with tempfile.TemporaryDirectory() as td:
            workspace=Path(td)/'run'
            scaffold=[sys.executable,str(SKILL/'scripts/scaffold_delivery.py'),'--workspace',str(workspace),'--entity','TEST','--security','TEST','--as-of','2026-07-18']
            r=subprocess.run(scaffold,capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)

            manifest=json.loads((workspace/'run_manifest.json').read_text(encoding='utf-8'))
            manifest['fiscal_calendar']='calendar year'
            manifest['research_completeness_required']=False
            manifest['readiness_target']='screen-grade'
            manifest['readiness_result']='screen-grade'
            manifest['forward_evidence_min_signals']=3
            manifest['analysis_primitives']=['unit-volume-price-cost']
            manifest['accounting_basis']={
                'forecast_basis_id':'ACCT-US-2026','historical_basis_ids':['ACCT-US-2026'],
                'bases':[{'basis_id':'ACCT-US-2026','framework':'US_GAAP','jurisdiction':'US',
                    'version':'FASB ASC effective for fiscal years beginning 2026-01-01',
                    'effective_at':'2026-01-01T00:00:00Z','presentation_currency':'USD',
                    'major_policy_choices':[{'policy_id':'revenue-recognition',
                        'policy_area':'revenue_recognition','choice':'ASC 606 contract-specific recognition',
                        'source_ids':['SRC0']}]}],
                'comparability_bridges':[]}
            manifest['phase_status']={k:'complete' for k in manifest['phase_status']}
            (workspace/'run_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')

            source_profiles=[
                ('Example Corp',['Example Corp Filing Team'],'issuer-filings','regulatory_filings'),
                ('Example Corp',['Example Corp IR Team'],'issuer-dialogue','invoice_value_divided_by_accepted_units'),
                ('Independent Demand Data',['Demand Panel Team'],'demand-panel','sell_through_panel'),
                ('Independent Price Data',['Price Panel Team'],'price-panel','independent_transaction_price_panel'),
                ('Example Corp',['Example Corp Product Team'],'issuer-product','product_documentation'),
                ('Independent Research',['Independent Research Team'],'external-research','independent_research_synthesis'),
            ]
            source_roles=(
                'historical_fact','management_claim','leading_indicator',
                'leading_indicator','technical_boundary','assumption_support',
            )
            source_epistemic_classes=(
                'official_reported_fact','management_statement_or_plan',
                'independent_external_observation','independent_external_observation',
                'technical_evidence','expert_or_analyst_opinion',
            )
            source_origin_record_kinds=(
                'entity_primary_disclosure','entity_primary_disclosure',
                'original_measurement_observation','original_measurement_observation',
                'scholarly_or_engineering_record','expert_or_analyst_interpretation',
            )
            sources=[]
            for i in range(6):
                sources.append({
                    'source_id':f'SRC{i}','source_type':'filing' if i==0 else ('earnings' if i==1 else ('industry-research' if i==5 else 'official-product')),
                    'origin_record_kind':source_origin_record_kinds[i],
                    'epistemic_class':source_epistemic_classes[i],
                    'publisher':source_profiles[i][0],'authors':source_profiles[i][1],
                    'root_original_source_id':f'SRC{i}','derived_from_source_id':None,
                    'common_origin':False,'independence_cluster':source_profiles[i][2],
                    'measurement_method_id':source_profiles[i][3],
                    'published_at':f'2026-0{min(i+1,6)}-01T00:00:00Z','retrieved_at':'2026-07-18T00:00:00Z',
                    'period_scope':'FY2026','evidence_tier':'E0' if i==0 else 'E1','content_hash':f'unhashed:test-fixture-{i}',
                    'location':f'https://example.com/{i}','claim_or_fact':'official fact','allowed_use':'base anchor','limitations':''
                    ,'authority':'audited_filing' if i==0 else ('company' if i in {1,4} else 'third_party'),
                    'independence':'first_party' if i in {0,1,4} else 'independent',
                    'directness':'direct','role':source_roles[i],
                    'as_of_valid':True,'scope_match':{'entity':True,'product':True,'geography':True,'period':True,'unit':True}
                })
            source_manifest=json.loads((workspace/'source_manifest.json').read_text(encoding='utf-8'))
            source_manifest['sources']=sources
            (workspace/'source_manifest.json').write_text(json.dumps(source_manifest,indent=2),encoding='utf-8')
            (workspace/'internal_intangible_investment.json').write_text(json.dumps({
                'schema_version':'internal-intangible-investment/v1',
                'materiality_threshold_pct_revenue':1.0,
                'categories':[{
                    'category_id':'synthetic_internal_investment',
                    'status':'not_material_with_reason',
                    'reason':'Synthetic fixture provides a source-backed numeric immateriality test only.',
                    'source_ids':['SRC0'],
                    'materiality_test':{'amount':0.5,'revenue':100.0,'pct_revenue':0.5},
                }],
            },indent=2),encoding='utf-8')

            assumption_path=workspace/'assumption_register.csv'
            with assumption_path.open(encoding='utf-8-sig',newline='') as f:
                assumption_header=next(csv.reader(f))
            with assumption_path.open('a',encoding='utf-8-sig',newline='') as f:
                w=csv.DictWriter(f,fieldnames=assumption_header)
                w.writerow({'assumption_id':'A1','node_id':'ai_asp','entity':'TEST','segment':'AI',
                    'primitive':'unit-volume-price-cost','metric':'ASP','period':'FY2027','frequency':'quarterly',
                    'scenario':'central_operating_path','value':'50','unit':'USD/unit','input_type':'assumption',
                    'source_ids':'SRC0;SRC1','claim_ids':'C1','confidence':'medium','applies_to':'AI revenue',
                    'does_not_apply_to':'legacy revenue','test_delta':'ASP -10%','falsification_id':'asp_break',
                    'next_evidence':'next earnings','owner':'analyst','notes':''})

            signal_headers=['signal_id','case_id','source_id','claim_ids','publisher','published_at','source_family','evidence_tier','evidence_role','independence_cluster','method_transparency','specificity','causal_proximity','falsifiability','incentive_bias','direction','strength','horizon','allowed_use','model_driver','model_impact','source_url','limitations']
            signal_rows=[
                ['S1','TEST','SRC0','C1','Example Corp','2026-01-01','issuer-filing','E0','state_signal','issuer-filings','2','2','2','2','0','1','2','0-1y','base_driver','ai_asp','reported ASP anchors the named driver','https://example.com/s1','reported scope only'],
                ['S2','TEST','SRC5','','Independent Research','2026-05-01','industry-research','E3','timing_signal','external-research','2','2','2','2','0','-1','2','0-1y','monitor','inventory','monitor inventory pressure','https://example.com/s2','method recorded'],
                ['S3','TEST','SRC5','C2','Independent Research','2026-03-01','technical-paper-standard','E2','failure_boundary','external-research','2','2','1','2','0','1','1','2-5y','scenario_only','ai_asp','bounds ASP uplift in a rival state','https://example.com/s3','not commercial'],
                ['S4','TEST','SRC5','','Independent Research','2026-02-01','technical-paper-standard','E2','feasibility_bound','external-research','2','2','2','2','0','1','2','2-5y','monitor','ai_units','monitor ratification timing','https://example.com/s4','standard timing'],
            ]
            with (workspace/'forward_signal_cards.csv').open('w',encoding='utf-8-sig',newline='') as f:
                w=csv.writer(f);w.writerow(signal_headers);w.writerows(signal_rows)
            with (workspace/'historical_query_log.csv').open('w',encoding='utf-8-sig',newline='') as f:
                w=csv.writer(f);w.writerow(['query_id','case_id','searched_at','cutoff','query_text','domains','result_source_ids','future_outcome_terms_used','reviewer','notes'])
                for qid,qtext,doms in [('Q1', 'TEST 10-K annual report SEC EDGAR filing', 'sec.gov'), ('Q2', 'TEST Q3 earnings call transcript management guidance', 'seekingalpha.com'), ('Q3', 'TEST investor day CEO keynote fireside interview', 'ir.example.com'), ('Q4', 'TEST supplier customer value chain cross-company commentary', 'example.com'), ('Q5', 'TrendForce IDC industry shipment data unit forecast', 'trendforce.com'), ('Q6', 'sell-side broker research report analyst note initiation', 'example.com'), ('Q7', 'expert network channel check supply chain distributor', 'example.com'), ('Q8', 'arXiv IEEE ISSCC JEDEC standard patent roadmap paper', 'arxiv.org;jedec.org')]:
                    w.writerow([qid,'TEST','2026-07-18T12:00:00Z','2026-07-18T23:59:59Z',qtext,doms,'SIG1','false','reviewer','point-in-time'])
            with (workspace/'source_independence_map.csv').open('w',encoding='utf-8-sig',newline='') as f:
                w=csv.writer(f);w.writerow(['source_id','cluster_id','root_original_source_id','derived_from_source_id','relationship','common_origin','publisher','authors','measurement_method_id','independence_basis','notes'])
                for i,(publisher,authors,cluster,method) in enumerate(source_profiles):
                    w.writerow([f'SRC{i}',cluster,f'SRC{i}','','original','false',publisher,';'.join(authors),method,'root observation','independent source chain'])

            red='''# Red-team review\n\n| ID | Severity | Area | Finding | Evidence | Model impact | Required action | Status |\n|---|---|---|---|---|---|---|---|\n| RT-001 | P1 | double counting | Double-count capex and COGS test | SRC0 | FCF | reconcile | closed |\n| RT-002 | P1 | valuation | Normalization and terminal valuation challenge | SRC0 | value | stress | closed |\n| RT-003 | P1 | demand | Base demand share unsupported | SRC1 | revenue | cap share | closed |\n| RT-004 | P1 | supply | Capacity constraint omitted | SRC2 | revenue | add supply | closed |\n| RT-005 | P1 | accounting | GAAP cash bridge incomplete | SRC0 | profit | bridge | closed |\n| RT-006 | P1 | source independence | Repeated reports may share one original source cluster | SIG1/SIG2 | Base | map source chains | closed |\n'''
            (workspace/'red_team.md').write_text(red,encoding='utf-8')
            report=(SKILL/'assets/examples/sandisk_v73/Sandisk_SNDK_v7.3_模型报告.md').read_text(encoding='utf-8')
            report+='\n\n## Forward evidence and research synthesis\nInvestor dialogue, independent research, technical papers, source independence clusters, rejected signals and falsification triggers were reviewed.\n\n## 买入纪律\nRecommended buy price derives from Bear fair value with margin of safety.\n\n## 一致性检查\nArithmetic consistency: implied tax rate, segment sums, EPS x shares reconcile. FY+1 base revenue point 100,000.\n\n## 核心变量 (thesis carriers)\nThe call is carried by FY+2 AI unit ASP and FY+2 AI shipments.\n\n## 隐含指标 (implied diagnostics)\nImplied revenue yoy +10%; incremental margin (flow-through) 40%.\n\n## 线下项筛查\nTax rate normalized 21%, no valuation allowance exposure. Interest income modeled from cash; no material FX. No impairment or restructuring expected. Share count flat, no buyback.\n'
            (workspace/'report.md').write_text(report,encoding='utf-8')
            (workspace/'model').mkdir(exist_ok=True)
            write_minimal_workbook(workspace/'model/model.xlsx',SMOKE_SHEETS)

            snapshot=json.loads((workspace/'forecast_snapshot.json').read_text(encoding='utf-8'))
            snapshot['accounting_basis_id']='ACCT-US-2026'
            snapshot['source_pack_hash']='sha256:test'
            snapshot['scenario_probabilities']={'demand_contraction':0.2,'central_operating_path':0.55,'supply_tightness':0.2,'competitive_supply_break':0.05}
            snapshot.update(valid_investment_snapshot())
            # Only the reference valuation has an executable per-share identity in
            # this fixture.  Keep the three rival paths explicitly unvalued rather
            # than publishing invented scenario fair values or a buy action.
            snapshot['valuation_summary'].update({
                'reference_scenario_id':'central_operating_path',
                'fair_value_by_scenario_id':{'central_operating_path':9.10},
                'not_valued_scenario_ids':[
                    'competitive_supply_break','demand_contraction','supply_tightness'],
                'valuation_completeness':'reference_only_executable',
                'recommended_buy_price':None,
                'action':'watch',
            })
            authored_scenario_ids = [
                'demand_contraction', 'central_operating_path', 'supply_tightness'
            ]
            snapshot['persistence_analysis']['mean_reversion']['scenario_ids'] = authored_scenario_ids
            for cost_row in snapshot['persistence_analysis']['cost_behavior']:
                cost_row['scenario_ids'] = authored_scenario_ids
            # Canonical points reconcile to role=reference; interval sides name joint scenarios.
            snapshot['outputs']['year_1'].update({'period':'FY2027','low_scenario_id':'demand_contraction','high_scenario_id':'supply_tightness',
                'revenue_point':100000,'revenue_low':90000,'revenue_high':115000,
                'operating_profit_point':18000,'operating_profit_low':14000,'operating_profit_high':24000,
                'pretax_profit_point':17000,'pretax_profit_low':13000,'pretax_profit_high':23000,
                'tax_expense_point':5000,'tax_expense_low':4000,'tax_expense_high':5000,
                'noncontrolling_interest_net_income_point':0,'net_income_point':12000,
                'noncontrolling_interest_net_income_low':0,'noncontrolling_interest_net_income_high':0,
                'net_income_low':9000,'net_income_high':18000,
                'profit_point':12000,'profit_low':9000,'profit_high':18000,'eps_point':5.0})
            snapshot['outputs']['year_2'].update({'period':'FY2028','low_scenario_id':'demand_contraction','high_scenario_id':'supply_tightness',
                'revenue_point':110000,'revenue_low':90000,'revenue_high':130000,
                'operating_profit_point':19000,'operating_profit_low':14000,'operating_profit_high':25000,
                'pretax_profit_point':18000,'pretax_profit_low':13000,'pretax_profit_high':24000,
                'tax_expense_point':4500,'tax_expense_low':4000,'tax_expense_high':6000,
                'noncontrolling_interest_net_income_point':0,
                'noncontrolling_interest_net_income_low':0,'noncontrolling_interest_net_income_high':0,
                'net_income_point':13500,'net_income_low':9000,'net_income_high':18000,
                'profit_point':13500,'profit_low':9000,'profit_high':18000})
            snapshot['outputs']['year_3_distribution']={}
            snapshot['outputs']['year_3_distribution'].update({'period':'FY2029','low_scenario_id':'demand_contraction','high_scenario_id':'supply_tightness',
                'revenue_point':120000,'revenue_low':95000,'revenue_high':150000,
                'operating_profit_point':20000,'operating_profit_low':13000,'operating_profit_high':28000,
                'pretax_profit_point':19000,'pretax_profit_low':12000,'pretax_profit_high':27000,
                'tax_expense_point':4750,'tax_expense_low':4000,'tax_expense_high':6000,
                'noncontrolling_interest_net_income_point':0,
                'noncontrolling_interest_net_income_low':0,'noncontrolling_interest_net_income_high':0,
                'net_income_point':14250,'net_income_low':8000,'net_income_high':21000,
                'profit_point':14250,'profit_low':8000,'profit_high':21000,'point_evaluable':False})
            def integrated_period(period,revenue,operating,pretax,tax,attributable):
                consolidated=pretax-tax
                nci=consolidated-attributable
                return {'period':period,'income_statement':{
                    'revenue':revenue,'operating_costs_and_expenses':revenue-operating,
                    'operating_profit':operating,'nonoperating_income_expense_net':pretax-operating,
                    'pretax_profit':pretax,'tax_expense':tax,'tax':tax,'nopat':operating-tax,
                    'net_income':consolidated,
                    'net_income_attributable_to_noncontrolling_interests':nci,
                    'net_income_attributable':attributable},
                    'balance_sheet':{'cash':0,'assets':revenue,'liabilities':0,'equity':revenue},
                    'cash_flow_statement':{'net_income':consolidated,'cash_from_operations':consolidated,
                        'capex':0,'free_cash_flow':consolidated,'net_change_in_cash':0},
                    'roll_forwards':{
                        'cash':{'opening':0,'net_change':0,'closing':0},
                        'ppe':{'opening':0,'capex':0,'depreciation':0,'disposals':0,'closing':0},
                        'debt':{'opening':0,'borrowings':0,'repayments':0,'closing':0},
                        'working_capital':{'opening':0,'change':0,'closing':0}}}
            snapshot['integrated_model']['periods']=[
                integrated_period('FY2027',100000,18000,17000,5000,12000),
                integrated_period('FY2028',110000,19000,18000,4500,13500),
                integrated_period('FY2029',120000,20000,19000,4750,14250),
            ]
            # driver tree: segments must sum to year_1 revenue_point, main line declared
            snapshot['historical_base']={'trailing_organic_growth_pct':8.0,'base_period':'FY2026'}
            snapshot['error_budget']={h:{'expected_revenue_error_pct':e,'expected_margin_error_pp':m,
                'dominant_risk':'margin','why':'price/cost spread uncertainty'}
                for h,e,m in [('year_1',6,2),('year_2',11,4),('year_3_distribution',19,7)]}
            snapshot['growth_challenger_review']=[{
                'challenger':'trailing_organic_growth','horizon':'year_2','status':'accepted',
                'challenger_growth_pct':8.0,'driver_tree_growth_pct':10.0,
                'difference_direction':'acceleration','material_difference':True,
                'materiality_basis':'The two-point transition changes FY+2 revenue materially.',
                'transition_driver_node_ids':['ai_units'],'named_state_ids':['terminal_demand_up','capacity_available'],
                'bridge':[{'driver_node_id':'ai_units','delta_growth_pct':2.0}],
                'notes':'Named demand and supply states reconcile the transition.'},
                *[{'challenger':name,'horizon':'year_2','status':'not_available_with_reason',
                   'notes':'No point-in-time comparable series exists for this synthetic fixture.'}
                  for name in ('run_rate','company_guidance','consensus','reference_class')]]
            snapshot['driver_tree']={'main_line':'AI capacity ramp',
                'thesis_carriers':['FY+2 AI unit ASP ($/unit)','FY+2 AI shipments (k units)'],
                'partition':{'partition_id':'primary-revenue-segments','dimension':'analytical_segment',
                    'exhaustive':True,'mutually_exclusive':True,'declared_residual':0.0},
                'segments':[
                {'name':'Segment-Trad','basis':'volume_price','revenue_point':80000,'main_line':False},
                {'name':'Segment-AI','basis':'capacity_ramp','revenue_point':20000,'main_line':True,
                 'unit':'k units','capacity':500,'volume':400,'price':50.0,'unit_cost':30.0}],
                'cross_check_views':[]}
            (workspace/'forecast_snapshot.json').write_text(json.dumps(snapshot,indent=2),encoding='utf-8')
            graph=valid_model_graph()
            (workspace/'model_graph.json').write_text(json.dumps(graph,indent=2),encoding='utf-8')

            def write_scaffold_csv(name, rows):
                path=workspace/name
                with path.open(encoding='utf-8-sig',newline='') as f:
                    header=next(csv.reader(f))
                with path.open('w',encoding='utf-8-sig',newline='') as f:
                    writer=csv.DictWriter(f,fieldnames=header);writer.writeheader();writer.writerows(rows)

            product_common={'materiality':'critical','primary_tree_or_cross_check':'primary',
                'partition_id':'primary-revenue-segments','partition_dimension':'analytical_segment',
                'partition_exhaustive':'true','partition_mutually_exclusive':'true','revenue_unit':'USD',
                'payer_or_customer':'named customer groups','end_user':'end demand',
                'equation_primitive':'unit-volume-price-cost','volume_usage_or_deployment_driver':'ai_units',
                'price_arpu_or_asp':'ai_asp','cost_and_capacity_constraint':'cash_cost',
                'program_stage':'qualified production','evidence_source_ids':'SRC0;SRC1',
                'assumption_ids':'A1','confidence':'medium','schedule_status':'accepted',
                'consolidation_link':'ai_revenue','residual_or_ratio_carry':'false','human_required':'false'}
            write_scaffold_csv('product_customer_driver_schedule.csv',[
                {**product_common,'segment_or_product':'Segment-Trad','driver_node_ids':'ai_units;cash_cost'},
                {**product_common,'segment_or_product':'Segment-AI','driver_node_ids':'ai_units;ai_asp;cash_cost'}])

            series_common={'published_at':'2026-07-01T00:00:00Z','retrieved_at':'2026-07-18T00:00:00Z',
                'observation_value':'100','observation_type':'flow','available_at':'2026-07-15T00:00:00Z',
                'revision_of_series_id':'none','classification_version':'2026Q2-v1','input_series_ids':'none',
                'vintage_at':'2026-07-01T00:00:00Z','revision_at':'2026-07-01T00:00:00Z',
                'period_start':'2026-04-01','period_end':'2026-06-30',
                'frequency':'quarterly','unit':'unit','currency':'N/A','entity_scope':'market','product_scope':'AI device',
                'metric_construct_id':'accepted_end_customer_shipments_flow',
                'geography_scope':'global','population_coverage':'named panel with disclosed coverage',
                'transformation':'raw reported series','revision_policy':'retain each vintage','lag_days':'15',
                'allowed_model_use':'base_parameter','driver_node_ids':'ai_units','conclusion_critical':'true',
                'status':'accepted','notes':''}
            asp_series_common={**series_common,'unit':'USD/unit','driver_node_ids':'ai_asp',
                'product_scope':'AI device contract pricing','metric_construct_id':'matched_realized_net_asp'}
            write_scaffold_csv('data_series_register.csv',[
                {**series_common,'series_id':'D1','metric_name':'terminal demand','source_id':'SRC0',
                 'vintage_id':'D1-v1',
                 'original_source_id':'SRC0','independence_cluster':'issuer-filings','measurement_method_id':'regulatory_filings',
                 'metric_definition':'accepted end-customer units',
                 'known_bias':'small vendors excluded','cross_check_series_ids':'D2','cross_check_result':'reconciled within 3%'},
                {**series_common,'series_id':'D2','metric_name':'channel-adjusted shipments','source_id':'SRC2',
                 'vintage_id':'D2-v1','observation_value':'102',
                 'original_source_id':'SRC2','independence_cluster':'demand-panel','measurement_method_id':'sell_through_panel',
                 'metric_definition':'sell-through adjusted for channel inventory','known_bias':'survey non-response',
                 'cross_check_series_ids':'D1','cross_check_result':'reconciled within 3%'},
                {**asp_series_common,'series_id':'D3','metric_name':'realized contract ASP','source_id':'SRC1',
                 'vintage_id':'D3-v1','observation_value':'50',
                 'original_source_id':'SRC1','independence_cluster':'issuer-dialogue',
                 'measurement_method_id':'invoice_value_divided_by_accepted_units',
                 'metric_definition':'recognized revenue divided by matched accepted units',
                 'known_bias':'reported mix can differ from forecast mix',
                 'cross_check_series_ids':'D4','cross_check_result':'mix bridge reconciled within 2%'},
                {**asp_series_common,'series_id':'D4','metric_name':'independent market ASP','source_id':'SRC3',
                 'vintage_id':'D4-v1','observation_value':'51',
                 'original_source_id':'SRC3','independence_cluster':'price-panel',
                 'measurement_method_id':'independent_transaction_price_panel',
                 'metric_definition':'volume-weighted price for matched qualified products',
                 'known_bias':'panel excludes long-tail private contracts',
                 'cross_check_series_ids':'D3','cross_check_result':'mix bridge reconciled within 2%'},])
            write_scaffold_csv('financial_fact_ledger.csv',[{'fact_id':'F1','entity_id':'TEST','accounting_basis_id':'ACCT-US-2026','source_id':'SRC0',
                'accession_or_filing_id':'TEST-2026-10K','filed_at':'2026-03-01T00:00:00Z',
                'retrieved_at':'2026-07-18T00:00:00Z','as_of_cutoff':'2026-07-18T23:59:59Z','form':'10-K',
                'fiscal_year':'2025','fiscal_period':'FY','period_start':'2025-01-01','period_end':'2025-12-31',
                'fact_name':'Revenue','taxonomy':'us-gaap','tag':'Revenue','dimensions':'consolidated','unit':'USD',
                'decimals':'-6','scale':'1000000','sign':'positive','reported_value':'100','normalized_value':'100',
                'currency':'USD','statement_or_note_anchor':'income statement revenue',
                'extraction_method':'rendered filing checked','amendment_or_restatement':'original',
                'predecessor_fact_id':'','comparability_adjustment':'no adjustment','status':'accepted',
                'conflict_note':'no conflict'}])
            earnings=[]
            earnings_periods={
                'FY2027': [('revenue',100000,0,'ai_revenue'),('core_operating_profit',20000,-80000,'operating_profit'),
                    ('gaap_operating_profit',18000,-2000,'operating_profit'),('pretax_profit',17000,-1000,'pretax_profit'),
                    ('gaap_net_income_attributable',12000,-5000,'profit')],
                'FY2028': [('revenue',110000,0,'ai_revenue'),('core_operating_profit',21000,-89000,'operating_profit'),
                    ('gaap_operating_profit',19000,-2000,'operating_profit'),('pretax_profit',18000,-1000,'pretax_profit'),
                    ('gaap_net_income_attributable',13500,-4500,'profit')],
                'FY2029': [('revenue',120000,0,'ai_revenue'),('core_operating_profit',22000,-98000,'operating_profit'),
                    ('gaap_operating_profit',20000,-2000,'operating_profit'),('pretax_profit',19000,-1000,'pretax_profit'),
                    ('gaap_net_income_attributable',14250,-4750,'profit')],
            }
            tax_by_period={'FY2027':5000,'FY2028':4500,'FY2029':4750}
            for period,period_layers in earnings_periods.items():
              for layer,amount,bridge,node in period_layers:
                row={'period':period,'profit_layer':layer,'reported_amount':str(amount),
                    'bridge_from_prior_layer':str(bridge),'normalization_adjustment':'0',
                    'tax_expense':str(tax_by_period[period]) if layer=='gaap_net_income_attributable' else '',
                    'net_income_attributable_to_noncontrolling_interests':'0' if layer=='gaap_net_income_attributable' else '',
                    'normalized_amount':str(amount),'cash_support':str(amount),
                    'accrual_component':'0','investment_adjustment':'0','cycle_adjustment':'0',
                    'persistence_driver':'named operating equations','competitive_response':'qualified supply response',
                    'fade_target':str(amount),'fade_horizon':'3','source_ids':'SRC0;SRC1','driver_node_ids':node,
                    'status':'accepted','notes':'fixture'}
                if layer=='gaap_operating_profit':
                    operating_tax=amount*0.20
                    nopat=amount-operating_tax
                    row.update({'operating_tax_expense':str(operating_tax),'nopat':str(nopat),
                        'cash_support':str(nopat),'accrual_component':'0','noa_bridge_residual':'0'})
                earnings.append(row)
            write_scaffold_csv('earnings_power_bridge.csv',earnings)
            claim={'claim_id':'C1','text':'AI ASP is contractually supported','claim_type':'reported_fact',
                'proposition_scope':'reported_history',
                'source_ids':['SRC0'],'evidence_links':[
                    {'source_id':source_id,'relation':'support','evidence_function':'direct_anchor',
                     'authority_scope':'Named FY2026 ASP fact within the issuer reporting perimeter.',
                     'measurement_or_construct_basis':'Invoice value divided by accepted units for the named period.',
                     'incentive_conflict':'Issuer incentive disclosed and bounded to the reported proposition.',
                     'reconciliation_status':'not_applicable',
                     'permission_rationale':'The source observes the same ASP construct, unit, period, and entity scope.',
                     'observation_ids':[]}
                    for source_id in ('SRC0',)],
                'allowed_use':'base_parameter','driver_node_ids':['ai_asp'],
                'as_of':'2026-07-18T00:00:00Z','status':'accepted','limitations':[]}
            scenario_claim={
                'claim_id':'C2','text':'Independent research bounds the rival ASP state',
                'claim_type':'analyst_assumption','proposition_scope':'scenario_only',
                'source_ids':['SRC5'],'evidence_links':[{
                    'source_id':'SRC5','relation':'support','evidence_function':'direct_anchor',
                    'authority_scope':'Independent research interpretation within its stated sample.',
                    'measurement_or_construct_basis':'Named ASP construct and rival-state horizon.',
                    'incentive_conflict':'Research incentives disclosed for independent review.',
                    'reconciliation_status':'not_applicable',
                    'permission_rationale':'The source bounds only the named rival state.',
                    'observation_ids':[]}],
                'allowed_use':'scenario_only','driver_node_ids':['ai_asp'],
                'as_of':'2026-07-18T00:00:00Z','status':'accepted','limitations':[]}
            (workspace/'claim_ledger.jsonl').write_text(
                json.dumps(claim)+'\n'+json.dumps(scenario_claim)+'\n',encoding='utf-8')

            chain_fields=('revenue','operating_costs_and_expenses','operating_profit',
                'nonoperating_income_expense_net','pretax_profit','tax_expense','net_income',
                'net_income_attributable_to_noncontrolling_interests','net_income_attributable')
            chain_columns=dict(zip(chain_fields,'BCDEFGHIJ'))
            chain_rows={'demand_contraction':20,'central_operating_path':30,'supply_tightness':40,'competitive_supply_break':50}
            chain_period_offsets={'FY2027':0,'FY2028':1,'FY2029':2}
            def scenario_profit_period(scenario_id,period,revenue,operating,pretax,tax,nci,shock_node=None):
                consolidated=pretax-tax
                row_number=chain_rows[scenario_id]+chain_period_offsets[period]
                values={'revenue':revenue,'operating_costs_and_expenses':revenue-operating,
                    'operating_profit':operating,'nonoperating_income_expense_net':pretax-operating,
                    'pretax_profit':pretax,'tax_expense':tax,'net_income':consolidated,
                    'net_income_attributable_to_noncontrolling_interests':nci,
                    'net_income_attributable':consolidated-nci}
                return {'period':period,**values,
                    'model_cells':{field:f'Scenario_PnL!{chain_columns[field]}{row_number}' for field in chain_fields},
                    'applied_shock_node_ids':[shock_node] if shock_node else [],
                    'joint_state_id':f'{scenario_id}-joint-path'}
            scenario_paths={
                'demand_contraction':[
                    scenario_profit_period('demand_contraction','FY2027',90000,14000,13000,4000,0),
                    scenario_profit_period('demand_contraction','FY2028',90000,14000,13000,4000,0,'ai_asp'),
                    scenario_profit_period('demand_contraction','FY2029',95000,13000,12000,4000,0,'ai_asp')],
                'central_operating_path':[
                    scenario_profit_period('central_operating_path','FY2027',100000,18000,17000,5000,0),
                    scenario_profit_period('central_operating_path','FY2028',110000,19000,18000,4500,0),
                    scenario_profit_period('central_operating_path','FY2029',120000,20000,19000,4750,0)],
                'supply_tightness':[
                    scenario_profit_period('supply_tightness','FY2027',115000,24000,23000,5000,0),
                    scenario_profit_period('supply_tightness','FY2028',130000,25000,24000,6000,0,'ai_asp'),
                    scenario_profit_period('supply_tightness','FY2029',150000,28000,27000,6000,0,'ai_asp')],
                'competitive_supply_break':[
                    scenario_profit_period('competitive_supply_break','FY2027',95000,16000,15000,4000,0),
                    scenario_profit_period('competitive_supply_break','FY2028',100000,16000,15000,4000,0),
                    scenario_profit_period('competitive_supply_break','FY2029',105000,15000,14000,4000,0,'competitive_supply')],
            }
            scenarios={'schema_version':'2.0','scenarios':[
                {'id':'demand_contraction','role':'alternative','probability':0.2,'shocks':[{'node_id':'ai_asp','operation':'set','value':40,'unit':'USD/unit','model_cell_or_formula':'Scenarios!B12','effective_period':'FY2028','lag_periods':0}],'profit_chain_periods':scenario_paths['demand_contraction'],'narrative':'price pressure'},
                {'id':'central_operating_path','role':'reference','probability':0.55,'shocks':[],'profit_chain_periods':scenario_paths['central_operating_path'],'narrative':'central causal path'},
                {'id':'supply_tightness','role':'alternative','probability':0.2,'shocks':[{'node_id':'ai_asp','operation':'set','value':60,'unit':'USD/unit','model_cell_or_formula':'Scenarios!C12','effective_period':'FY2028','lag_periods':0}],'profit_chain_periods':scenario_paths['supply_tightness'],'narrative':'tight supply'},
                {'id':'competitive_supply_break','role':'alternative','probability':0.05,'shocks':[{'node_id':'competitive_supply','operation':'set','value':1,'unit':'dimensionless','model_cell_or_formula':'Scenarios!D12','effective_period':'FY2028','lag_periods':1}],'profit_chain_periods':scenario_paths['competitive_supply_break'],'narrative':'new supply'},
            ]}
            (workspace/'scenario_set.json').write_text(json.dumps(scenarios,indent=2),encoding='utf-8')
            (workspace/'model_checks.json').write_text(json.dumps({'schema_version':'2.0','checks':[
                {'id':'BS_CHECK','category':'balance_sheet',
                 'calculation':{'operation':'signed_sum','terms':[
                     {'name':'assets','coefficient':1.0,'model_cell':'Summary!B2'},
                     {'name':'liabilities','coefficient':-1.0,'model_cell':'Summary!B3'},
                     {'name':'equity','coefficient':-1.0,'model_cell':'Summary!B4'}]},
                 'value':0.0,'tolerance':0.0,'unit':'USD','status':'passed'}
            ]},indent=2),encoding='utf-8')
            with (workspace/'driver_monitoring.csv').open('w',encoding='utf-8-sig',newline='') as f:
                w=csv.writer(f);w.writerow(['driver_id','model_cell_or_formula','monitor_type','thesis_link','series','source_id','frequency','last_observed_at','next_expected_at','milestone_date','current_value','model_value','unit','trigger_operator','trigger_value','action_if_breached','owner','status'])
                w.writerow(['ai_asp','Drivers!F18','continuous','main line','contract ASP','SRC1','quarterly','2026-06-30','2026-09-30','','48','50','USD/unit','below','42','re-underwrite price path','analyst','active'])
                w.writerow(['asp_break','Tech_Gates!B12','milestone','falsification','contract ASP breach','SRC1','event_driven','2026-06-30','2026-08-15','2026-08-15','0','0','dimensionless','above','0','invalidate base case','analyst','active'])
            pool={'boundary_id':'AI_GLOBAL','period':'FY2027','geography':'global','product_scope':'AI devices',
                'currency':'USD','profit_measure':'operating_profit','capacity_or_supply':'500 units',
                'pricing_mechanism':'contract ASP','entry_exit_barrier':'qualification',
                'competitor_response':'qualified new supply','response_lead_time_days':'365','cycle_state':'balanced',
                'source_ids':'SRC0;SRC1','driver_node_ids':'ai_asp;competitive_supply','as_of':'2026-07-18',
                'data_vintage_at':'2026-07-01','status':'accepted','notes':''}
            write_scaffold_csv('industry_profit_pool.csv',[
                {**pool,'row_type':'total','value_chain_node':'industry total','revenue_pool':'100','profit_pool':'20',
                 'invested_capital':'75','company_revenue_share':'1','company_profit_share':'1'},
                {**pool,'row_type':'component','value_chain_node':'AI devices','revenue_pool':'100','profit_pool':'20',
                 'invested_capital':'75','company_revenue_share':'1','company_profit_share':'1'}])
            cycle=[]
            for i,family in enumerate(['end_demand','sell_through','sell_in_or_orders',
                    'channel_or_customer_inventory','company_inventory','backlog_and_cancellations',
                    'production_utilization_yield','installed_and_announced_capacity',
                    'spot_contract_realized_price','unit_cost_and_cash_conversion'],1):
                cycle.append({'branch_id':'AI','state_family':family,'metric_name':family.replace('_',' '),
                    'period':'FY2027Q2','frequency':'quarterly','value':str(100+i),'unit':'unit',
                    'ownership_or_location':'company or channel','lead_lag_days':'30','source_ids':'SRC0;SRC2',
                    'data_series_ids':'D1;D2','driver_node_ids':'ai_units','as_of':'2026-07-18',
                    'data_vintage_at':'2026-07-01','applicability':'material','status':'accepted','notes':'fixture'})
            cycle_check_common={'record_type':'equation_check','branch_id':'AI','state_family':'',
                'period':'FY2027Q2','frequency':'quarterly','source_ids':'SRC0;SRC2',
                'data_series_ids':'D1;D2','driver_node_ids':'ai_units','as_of':'2026-07-18',
                'data_vintage_at':'2026-07-01','applicability':'material','status':'accepted',
                'unit_conversion_factor':'1','check_tolerance':'0.001','check_residual':'0',
                'equation_status':'accepted','notes':'fixture recomputed equation'}
            cycle.extend([
                {**cycle_check_common,'equation_id':'AI-channel-roll','equation_type':'channel_inventory_roll',
                 'metric_name':'sell-in stock-flow','lhs_value':'410','rhs_1_value':'400','rhs_2_value':'10',
                 'lhs_unit':'unit','rhs_1_unit':'unit','rhs_2_unit':'unit','model_cell_or_formula':'Checks!B20'},
                {**cycle_check_common,'equation_id':'AI-company-roll','equation_type':'company_inventory_roll',
                 'metric_name':'shipment stock-flow','lhs_value':'400','rhs_1_value':'410','rhs_2_value':'20',
                 'rhs_3_value':'30','lhs_unit':'unit','rhs_1_unit':'unit','rhs_2_unit':'unit',
                 'rhs_3_unit':'unit','model_cell_or_formula':'Checks!B21'},
                {**cycle_check_common,'equation_id':'AI-revenue-check','equation_type':'revenue_recognition',
                 'metric_name':'accepted quantity times price','lhs_value':'20000','rhs_1_value':'400',
                 'rhs_2_value':'50','lhs_unit':'USD','rhs_1_unit':'unit','rhs_2_unit':'USD/unit',
                 'model_cell_or_formula':'Checks!B22'}])
            write_scaffold_csv('operating_cycle_register.csv',cycle)
            history=[]
            common={'currency':'USD','scope_basis':'continuing operations; consolidated attributable basis',
                'comparability_status':'comparable','data_status':'reported','latest_actual':'false',
                'perimeter_bridge':'none_no_change','accounting_bridge':'none_no_change',
                'source_ids':'SRC0','partition_id':'reported-segments',
                'partition_dimension':'reported_operating_segment','status':'accepted'}
            for year,revenue in [('FY2024',80.0),('FY2025',90.0),('FY2026',100.0)]:
                history.extend([
                    {**common,'period':year,'period_type':'annual','row_type':'consolidated',
                     'reported_segment':'Total','normalized_segment':'Total','actual_or_forecast':'actual',
                     'revenue':str(revenue),'cost':str(revenue*0.6),'gross_profit':str(revenue*0.4),
                     'operating_profit':str(revenue*0.2),'gaap_net_income_attributable':str(revenue*0.12),
                     'invested_capital':'75','partition_exhaustive':'true',
                     'partition_mutually_exclusive':'true','check_to_consolidated':'0',
                     'segment_reconciliation_status':'reconciled'},
                    {**common,'period':year,'period_type':'annual','row_type':'segment',
                     'reported_segment':'AI','normalized_segment':'AI','actual_or_forecast':'actual',
                     'revenue':str(revenue),'scope_basis':'continuing operations; reported segment basis'}])
            history.extend([
                {**common,'period':'H1-2027','period_type':'interim','row_type':'consolidated',
                 'reported_segment':'Total','normalized_segment':'Total','actual_or_forecast':'actual',
                 'revenue':'55','cost':'33','gross_profit':'22','operating_profit':'11',
                 'gaap_net_income_attributable':'6.6','invested_capital':'75','latest_actual':'true',
                 'partition_exhaustive':'true','partition_mutually_exclusive':'true',
                 'check_to_consolidated':'0','segment_reconciliation_status':'reconciled'},
                {**common,'period':'H1-2027','period_type':'interim','row_type':'segment',
                 'reported_segment':'AI','normalized_segment':'AI','actual_or_forecast':'actual','revenue':'55',
                 'scope_basis':'continuing operations; reported segment basis'},
                {**common,'period':'FY2027E','period_type':'first_forecast','row_type':'consolidated',
                 'reported_segment':'Total','normalized_segment':'Total','actual_or_forecast':'forecast',
                 'revenue':'115','cost':'69','gross_profit':'46','operating_profit':'23',
                 'gaap_net_income_attributable':'13.8','invested_capital':'75','data_status':'derived',
                 'source_ids':'SRC0;SRC1','segment_reconciliation_status':'not_applicable',
                 'bridge_from_period':'H1-2027','revenue_bridge_delta':'60','cost_bridge_delta':'36',
                 'gross_profit_bridge_delta':'24','operating_profit_bridge_delta':'12',
                 'gaap_net_income_attributable_bridge_delta':'7.2',
                 'forecast_bridge':'H2 units, ASP and cash cost bridge the latest interim',
                 'driver_node_ids':'ai_units;ai_asp;cash_cost'}])
            write_scaffold_csv('historical_segment_bridge.csv',history)

            frozen_names=('source_manifest.json','source_independence_map.csv','forward_signal_cards.csv','model_graph.json','scenario_set.json','data_series_register.csv','material_assumption_support.csv','claim_ledger.jsonl')
            frozen={name:'sha256:'+hashlib.sha256((workspace/name).read_bytes()).hexdigest() for name in frozen_names}
            (workspace/'research_quality_review.json').write_text(json.dumps({
                'schema_version':'research-quality-review/v1','review_id':'fixture-review',
                'reviewed_at':'2026-07-18T20:00:00Z','builder_id':'fixture-builder',
                'reviewer_id':'fixture-independent-reviewer','independent_of_builder':True,
                'orchestration_receipt':{
                    'assurance_boundary':'orchestration_receipt_only_not_cryptographic_identity',
                    'receipt_id':'orchestration-receipt://delivery-fixture',
                    'orchestrator':'delivery-validator-fixture',
                    'reviewer_session_id':'session:fixture-reviewer',
                    'reviewer_task_id':'task:fixture-research-review',
                    'builder_session_id':'session:fixture-builder',
                    'frozen_inputs_delivered_at':'2026-07-18T19:50:00Z',
                    'review_started_at':'2026-07-18T19:52:00Z',
                    'initial_conclusion_at':'2026-07-18T19:58:00Z',
                    'review_completed_at':'2026-07-18T20:00:00Z',
                    'receipt_issued_at':'2026-07-18T20:01:00Z',
                    'builder_rebuttal':{'status':'not_provided','provided_at':None}},
                'frozen_artifacts':frozen,
                'principal_contradiction':{
                    'carrier_node_ids':['ai_units','ai_asp'],'falsification_node_ids':['asp_break'],
                    'rival_hypothesis':'Qualified supply removes price persistence.',
                    'judgment':'adequate','reasoning':'Independent demand and price definitions bind the main line.',
                    'source_ids':['SRC0','SRC1']},
                'claim_authority_judgments':[{
                    'claim_id':'C2','reviewed_source_ids':['SRC5'],
                    'reviewed_source_epistemic_classes':{
                        'SRC5':'expert_or_analyst_opinion'},
                    'reviewed_source_origin_record_kinds':{
                        'SRC5':'expert_or_analyst_interpretation'},
                    'reviewed_observation_bindings':{},
                    'authority_sufficiency':'adequate','permitted_use':'scenario_only',
                    'rationale':'Independent reviewer accepts only the bounded rival-state use.'}],
                'material_judgments':[],
                'overall':{'research_sufficiency':'adequate','readiness_cap':'research-grade',
                    'rationale':'Synthetic validator fixture with frozen lineage.',
                    'unresolved_material_disagreements':[]}},indent=2),encoding='utf-8')

            validate=[sys.executable,str(SKILL/'scripts/validate_delivery.py'),'--workspace',str(workspace),'--strict']
            r=subprocess.run(validate,capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            result=json.loads((workspace/'delivery_validation.json').read_text(encoding='utf-8'))
            self.assertTrue(result['passed'])

            rows=list(csv.DictReader((workspace/'driver_monitoring.csv').open(encoding='utf-8-sig',newline='')))
            rows[0]['model_cell_or_formula']=''
            with (workspace/'driver_monitoring.csv').open('w',encoding='utf-8-sig',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
            failed=subprocess.run(validate,capture_output=True,text=True)
            self.assertNotEqual(failed.returncode,0,failed.stdout+failed.stderr)
            self.assertIn('missing model_cell_or_formula',failed.stdout+failed.stderr)

if __name__=='__main__':
    unittest.main()
