import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL=Path(__file__).resolve().parents[1]

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
            manifest['forward_evidence_min_signals']=3
            manifest['workbook_formula_min']=0
            manifest['selected_mechanisms']=['unit-volume-price-cost']
            manifest['phase_status']={k:'complete' for k in manifest['phase_status']}
            (workspace/'run_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')

            sources=[]
            for i in range(6):
                sources.append({
                    'source_id':f'SRC{i}','source_type':'filing' if i==0 else ('earnings' if i==1 else 'official-product'),
                    'publisher':'Example Corp','published_at':f'2026-0{min(i+1,6)}-01T00:00:00Z','retrieved_at':'2026-07-18T00:00:00Z',
                    'period_scope':'FY2026','evidence_tier':'E0' if i==0 else 'E1','content_hash':f'unhashed:test-fixture-{i}',
                    'location':f'https://example.com/{i}','claim_or_fact':'official fact','allowed_use':'base anchor','limitations':''
                })
            source_manifest=json.loads((workspace/'source_manifest.json').read_text(encoding='utf-8'))
            source_manifest['sources']=sources
            (workspace/'source_manifest.json').write_text(json.dumps(source_manifest,indent=2),encoding='utf-8')

            with (workspace/'assumption_register.csv').open('a',encoding='utf-8',newline='') as f:
                f.write('A1,TEST,Total,unit-volume-price-cost,revenue,FY2027,base,10,USD bn,E1,SRC1,medium,TEST,,8,next earnings,analyst,\n')

            signal_headers=['signal_id','case_id','source_id','publisher','published_at','source_family','evidence_tier','evidence_role','independence_cluster','method_transparency','specificity','causal_proximity','falsifiability','incentive_bias','direction','strength','horizon','allowed_use','model_driver','model_impact','source_url','limitations']
            signal_rows=[
                ['S1','TEST','SIG1','Example Corp','2026-04-01','official-dialogue','E1','state_signal','C1','2','2','2','2','1','1','2','0-1y','base_driver','demand','raise usage','https://example.com/s1','incentive reviewed'],
                ['S2','TEST','SIG2','Independent Research','2026-05-01','industry-research','E3','timing_signal','C2','2','2','2','2','0','-1','2','0-1y','base_driver','inventory','lower ASP','https://example.com/s2','method recorded'],
                ['S3','TEST','SIG3','Paper','2026-03-01','technical-paper-standard','E2','failure_boundary','C3','2','2','1','2','0','1','1','2-5y','scenario_probability','technical','tail only','https://example.com/s3','not commercial'],
            ]
            with (workspace/'forward_signal_cards.csv').open('w',encoding='utf-8-sig',newline='') as f:
                w=csv.writer(f);w.writerow(signal_headers);w.writerows(signal_rows)
            with (workspace/'historical_query_log.csv').open('w',encoding='utf-8-sig',newline='') as f:
                w=csv.writer(f);w.writerow(['query_id','case_id','searched_at','cutoff','query_text','domains','result_source_ids','future_outcome_terms_used','reviewer','notes'])
                for i in range(3):w.writerow([f'Q{i+1}','TEST','2026-07-18T12:00:00Z','2026-07-18T23:59:59Z',f'query {i+1}','example.com',f'SIG{i+1}','false','reviewer','point-in-time'])
            with (workspace/'source_independence_map.csv').open('w',encoding='utf-8-sig',newline='') as f:
                w=csv.writer(f);w.writerow(['cluster_id','original_source_id','derived_source_id','relationship','independence_weight','notes'])
                for i in range(3):w.writerow([f'C{i+1}',f'SIG{i+1}','','original',1.0,'independent source chain'])

            red='''# Red-team review\n\n| ID | Severity | Area | Finding | Evidence | Model impact | Required action | Status |\n|---|---|---|---|---|---|---|---|\n| RT-001 | P1 | double counting | Double-count capex and COGS test | SRC0 | FCF | reconcile | closed |\n| RT-002 | P1 | valuation | Normalization and terminal valuation challenge | SRC0 | value | stress | closed |\n| RT-003 | P1 | demand | Base demand share unsupported | SRC1 | revenue | cap share | closed |\n| RT-004 | P1 | supply | Capacity constraint omitted | SRC2 | revenue | add supply | closed |\n| RT-005 | P1 | accounting | GAAP cash bridge incomplete | SRC0 | profit | bridge | closed |\n| RT-006 | P1 | source independence | Repeated reports may share one original source cluster | SIG1/SIG2 | Base | map source chains | closed |\n'''
            (workspace/'red_team.md').write_text(red,encoding='utf-8')
            report=(SKILL/'assets/examples/sandisk_v73/Sandisk_SNDK_v7.3_模型报告.md').read_text(encoding='utf-8')
            report+='\n\n## Forward evidence and research synthesis\nInvestor dialogue, independent research, technical papers, source independence clusters, rejected signals and falsification triggers were reviewed.\n\n## 买入纪律\nRecommended buy price derives from Bear fair value with margin of safety.\n\n## 一致性检查\nArithmetic consistency: implied tax rate, segment sums, EPS x shares reconcile.\n'
            (workspace/'report.md').write_text(report,encoding='utf-8')
            (workspace/'model').mkdir(exist_ok=True)
            (workspace/'model/model.xlsx').write_bytes((SKILL/'assets/examples/sandisk_v73/Sandisk_SNDK_v7.3_五年财务模型.xlsx').read_bytes())

            snapshot=json.loads((workspace/'forecast_snapshot.json').read_text(encoding='utf-8'))
            snapshot['source_pack_hash']='sha256:test'
            snapshot['mechanism_weights']={'unit-volume-price-cost':1.0}
            snapshot['scenario_probabilities']={'bear':0.2,'base':0.55,'bull':0.2,'regime_break':0.05}
            (workspace/'forecast_snapshot.json').write_text(json.dumps(snapshot,indent=2),encoding='utf-8')

            validate=[sys.executable,str(SKILL/'scripts/validate_delivery.py'),'--workspace',str(workspace),'--strict']
            r=subprocess.run(validate,capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            result=json.loads((workspace/'delivery_validation.json').read_text(encoding='utf-8'))
            self.assertTrue(result['passed'])

if __name__=='__main__':
    unittest.main()
