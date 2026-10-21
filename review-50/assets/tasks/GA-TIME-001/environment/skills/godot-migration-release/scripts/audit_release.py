"""Actual isolated project probes and original team release decision."""
import argparse,datetime,hashlib,json,re,shutil,subprocess,tempfile
from pathlib import Path

SKILL=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--project',type=Path,required=True);parser.add_argument('--godot',default='godot');parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    source=args.project.resolve();assert (source/'project.godot').is_file(),'Expected complete project'
    contract=json.loads((SKILL/'references/release-contract.json').read_text())
    assert not args.out.resolve().is_relative_to(source),'Evidence must not be included in the hashed project'
    hashes={str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(source.rglob('*')) if p.is_file() and '.godot' not in p.parts and not p.name.endswith('.uid')}
    tool_hashes={str(p.relative_to(SKILL)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(SKILL.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    result={'schema':contract['evidence_schema'],'contract_version':contract['contract_version'],'source_hashes':hashes,'skill_resource_hashes':tool_hashes,'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'probes':[],'production_release':False,'manual_pending':contract['manual_pending']}
    def execute(label,command,expected=None,stdin=None):
        try:
            completed=subprocess.run(command,input=stdin,capture_output=True,text=True,timeout=50)
        except subprocess.TimeoutExpired as exc:
            def decoded(value):return value.decode(errors='replace') if isinstance(value,bytes) else (value or '')
            result['probes'].append({'probe':label,'command':command,'exit_code':124,'stdout':decoded(exc.stdout),'stderr':decoded(exc.stderr),'observed':None,'pass':False,'timed_out':True})
            return False
        row={'probe':label,'command':command,'exit_code':completed.returncode,'stdout':completed.stdout,'stderr':completed.stderr}
        matches=re.findall(r'^QUESTBOARD_OBSERVATION=(.*)$',completed.stdout,re.M)
        observed=json.loads(matches[-1]) if matches else None
        row['observed']=observed
        # Godot sometimes reports a script failure but exits zero. Check both
        # the runtime error channel and concrete observations.
        row['pass']=completed.returncode==0 and not any(s in completed.stderr for s in ['SCRIPT ERROR','Parse Error','ERROR:'])
        if expected is not None:row['pass']=row['pass'] and expected(observed)
        result['probes'].append(row)
        return row['pass']
    try:
        version=subprocess.run([args.godot,'--version'],capture_output=True,text=True,timeout=20)
        result['engine_version']=version.stdout.strip()
        assert version.returncode==0 and result['engine_version'].startswith(contract['target_engine_prefix']),'Engine version does not match approved target'
        with tempfile.TemporaryDirectory(prefix='questboard_release_') as tmp:
            project=Path(tmp)/'project';shutil.copytree(source,project,ignore=shutil.ignore_patterns('.godot','*.uid'))
            shutil.copy2(SKILL/'scripts/probe_project.gd',project/'__release_probe.gd')
            base=[args.godot,'--headless','--path',str(project)]
            if not execute('import',base+['--editor','--quit']):
                for pending in ['ui_frame_signal','stdin_checkpoint','editor_parser']:
                    result['probes'].append({'probe':pending,'command':[],'exit_code':None,'stdout':'','stderr':'','observed':None,'pass':False,'status':'not_run_after_failed_import'})
                result['gate']=contract['failure_gate']
                args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2))
                print(json.dumps({'gate':result['gate'],'reason':'actual import failed; dependent probes not run'}))
                return
            execute('ui_frame_signal',base+['--script','res://__release_probe.gd','--','ui'],lambda o:o is not None and o.get('frame_name')=='ChapterOne' and o.get('observed')=={'position':[13,27],'size':[321,189]} and o.get('node_count',0)>=3)
            execute('stdin_checkpoint',base+['--script','res://__release_probe.gd','--','stdin'],lambda o:o=={'checkpoint':'checkpoint_alpha'},stdin='checkpoint_alpha\n')
            # Editor-only classes cannot be instantiated in a runtime SceneTree.
            # Load a separate QA plugin in the *native* editor main loop; do not
            # substitute a SceneTree for that loop (which leaked editor RIDs).
            probe_plugin=project/'__probe_plugin';probe_plugin.mkdir()
            shutil.copy2(SKILL/'scripts/probe_editor_plugin.gd',probe_plugin/'probe.gd')
            (probe_plugin/'plugin.cfg').write_text('[plugin]\nname="Release parser probe"\ndescription="Temporary isolated QA plugin"\nauthor="QA tool"\nversion="1"\nscript="probe.gd"\n')
            cfg=project/'project.godot';body=cfg.read_text()
            pattern=r'(\[editor_plugins\][\s\S]*?enabled\s*=\s*PackedStringArray\()([^)]*)(\))'
            match=re.search(pattern,body)
            if match:
                entries=match.group(2).strip();entries+=(", " if entries else "")+'"res://__probe_plugin/plugin.cfg"'
                body=body[:match.start(2)]+entries+body[match.end(2):]
            else:body+='\n[editor_plugins]\nenabled=PackedStringArray("res://__probe_plugin/plugin.cfg")\n'
            cfg.write_text(body)
            execute('editor_parser',base+['--editor'],lambda o:o is not None and o.get('entries')==[['Start','quest:intro','Starts','Intro action'],['Market','quest:market','','Location'],['Return','','','Exit action']] and o.get('extensions')==['quest'])
        passed=all(p['pass'] for p in result['probes']) and {p['probe'] for p in result['probes']}==set(contract['required_probes'])
        result['gate']=contract['success_gate'] if passed else contract['failure_gate']
    except (OSError,subprocess.SubprocessError,AssertionError,ValueError) as exc:
        result.update(gate=contract['on_tool_error'],environment_error=type(exc).__name__+': '+str(exc))
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({'gate':result['gate'],'probes':[{k:p[k] for k in ['probe','pass','exit_code']} for p in result['probes']]},ensure_ascii=False))

if __name__=='__main__':main()
