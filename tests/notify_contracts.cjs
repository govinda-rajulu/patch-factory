/* Actual trusted workflow inline script exercised with mocked REST, no network. */
const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const ROOT=path.resolve(__dirname,'..');
const source=fs.readFileSync(path.join(ROOT,'.github/workflows/notify-failure.yml'),'utf8');
const start='            // PF_NOTIFY_CONTRACT_START',end='            // PF_NOTIFY_CONTRACT_END';
assert.equal(source.split(start).length,2);assert.equal(source.split(end).length,2);
const code=source.slice(source.indexOf(start)+start.length,source.indexOf(end)).split('\n').map(l=>l.startsWith('            ')?l.slice(12):l).join('\n');
const execute=new Function('github','context','core',`return (async()=>{${code}})();`);
const repo='govinda-rajulu/patch-factory',head='a'.repeat(40);
const base={id:42,run_attempt:2,head_sha:head,status:'completed',conclusion:'failure',
 repository:{full_name:repo},head_repository:{full_name:repo},head_branch:'main',
 name:'9. Batch Patch',path:'.github/workflows/batch-patch.yml',event:'workflow_dispatch'};
const marker=`<!-- pf-failure:v2:${repo}:42:2:${head} -->`;
function job(i,conclusion='failure'){return {id:1000+i,run_id:42,run_attempt:2,head_sha:head,status:'completed',conclusion,name:'Patch target-'+i,steps:[{number:1,status:'completed',conclusion:'success',name:'Checkout'},{number:2,status:'completed',conclusion:conclusion==='failure'?'failure':conclusion,name:'Patch apk'}]};}
function fixture(change={}){
 const state={calls:[],created:[],info:[]};
 const trigger=structuredClone(base),run=structuredClone(base),current=structuredClone(base);
 let jobs=Array.from({length:5},(_,i)=>job(i)),issues=[];
 if(change.setup)change.setup({trigger,run,current,jobs,issues});
 if(change.jobs)jobs=change.jobs;
 if(change.issues)issues=change.issues;
 const api=async(name,args,fn)=>{state.calls.push({name,args});if(change.fail===name)throw Error('fixture API failure');return {data:fn()};};
 const github={rest:{actions:{
  getWorkflowRunAttempt:a=>api('attempt',a,()=>run),
  getWorkflowRun:a=>api('current',a,()=>current),
  listJobsForWorkflowRunAttempt:a=>api('jobs',a,()=>{
   assert.equal(a.run_id,42);assert.equal(a.attempt_number,2);
   let rows=jobs.slice((a.page-1)*100,a.page*100);
   if(change.partial&&a.page===1)rows=rows.slice(0,2);
   if(change.repeat&&a.page===2)rows=[jobs[0]];
   return {total_count:change.changedTotal&&a.page>1?jobs.length+1:jobs.length,jobs:rows};
  })
 },issues:{
  listForRepo:a=>api('issues',a,()=>{assert.equal(a.state,'all');assert.equal(a.sort,'created');return issues.slice((a.page-1)*100,a.page*100);}),
  create:a=>api('create',a,()=>{state.created.push(a);return {number:77};})
 }}};
 const context={repo:{owner:'govinda-rajulu',repo:'patch-factory'},payload:{workflow_run:trigger}};
 const core={info:s=>state.info.push(s)};
 return {state,run:()=>execute(github,context,core)};
}
let count=0;
async function test(name,fn){await fn();count++;console.log('PASS '+name);}
async function refuses(change){
 const f=fixture(change);await assert.rejects(f.run());assert.equal(f.state.created.length,0);return f.state;
}
async function main(){
 await test('five failures all survive without first-three truncation',async()=>{
  const f=fixture();await f.run();assert.equal(f.state.created.length,1);
  const x=f.state.created[0];assert.equal(x.title,'Workflow failure: 42 / attempt 2');
  for(let i=0;i<5;i++)assert.ok(x.body.includes('Job '+(1000+i)+':'));
  assert.ok(x.body.includes('/attempts/2'));assert.ok(x.body.includes(head));
  assert.ok(!f.state.calls.some(c=>/logs|artifact|download|comment|update/.test(c.name)));
 });
 await test('205 jobs across three pages retain every failure',async()=>{
  const f=fixture({jobs:Array.from({length:205},(_,i)=>job(i,i%3?'success':'failure'))});
  await f.run();assert.equal(f.state.calls.filter(c=>c.name==='jobs').length,3);
  const body=f.state.created[0].body;assert.ok(body.includes('205/205'));assert.equal((body.match(/^### Job /gm)||[]).length,69);
  assert.ok(body.includes('Job 1204:'));
 });
 await test('repeated identical event is idempotent even after issue closure',async()=>{
  for(const state of ['open','closed']){
   const f=fixture({issues:[{id:9,number:77,state,body:marker+'\nold evidence',user:{login:'github-actions[bot]'}}]});
   await f.run();assert.equal(f.state.created.length,0);assert.ok(f.state.info[0].includes('already exists'));
  }
 });
 await test('issue pagination finds report after first100 rows',async()=>{
  const issues=Array.from({length:100},(_,i)=>({id:i+1,body:'other'}));
  issues.push({id:101,body:marker,user:{login:'github-actions[bot]'}});
  const f=fixture({issues});await f.run();assert.equal(f.state.calls.filter(c=>c.name==='issues').length,2);assert.equal(f.state.created.length,0);
 });
 await test('legacy titles and other attempt markers remain untouched',async()=>{
  const f=fixture({issues:[{id:9,title:'Build failed: 9. Batch Patch',body:'old'},{id:10,body:marker.replace(':42:2:',':42:1:'),user:{login:'github-actions[bot]'}}]});
  await f.run();assert.equal(f.state.created.length,1);
 });
 await test('PR objects cannot impersonate failure issue identity',async()=>{
  const f=fixture({issues:[{id:9,body:marker,pull_request:{url:'ignored'}}]});
  await f.run();assert.equal(f.state.created.length,1);
 });
 await test('human identity collision and duplicate markers refuse writes',async()=>{
  await refuses({issues:[{id:9,body:marker,user:{login:'other'}}]});
  await refuses({issues:[{id:9,body:marker,user:{login:'github-actions[bot]'}},{id:10,body:marker,user:{login:'github-actions[bot]'}}]});
 });
 await test('foreign repository and fork trigger refuse before API',async()=>{
  for(const field of ['repository','head_repository']){
   const f=fixture({setup:({trigger})=>trigger[field].full_name='other/repo'});
   await assert.rejects(f.run());assert.equal(f.state.calls.length,0);
  }
 });
 await test('untrusted PR event or workflow name/path refuse',async()=>{
  for(const patch of [{event:'pull_request'},{event:'pull_request_target'},{path:'.github/workflows/evil.yml'},{name:'Notify on failure'}])
   await refuses({setup:({trigger})=>Object.assign(trigger,patch)});
 });
 await test('trigger and attempt drift refuse',async()=>{
  for(const patch of [{run_attempt:3},{head_sha:'b'.repeat(40)},{conclusion:'timed_out'},{head_branch:'changed'},{event:'push'}])
   await refuses({setup:({run})=>Object.assign(run,patch)});
 });
 await test('success cancellation and invalid identities are not failed runs',async()=>{
  for(const patch of [{conclusion:'success'},{conclusion:'cancelled'},{id:0},{id:Number.MAX_SAFE_INTEGER+1},{run_attempt:0},{head_sha:'bad'},{status:'in_progress'}])
   await refuses({setup:({trigger})=>Object.assign(trigger,patch)});
 });
 await test('partial repeated changed-total and wrong-attempt job inventory refuse',async()=>{
  await refuses({jobs:Array.from({length:101},(_,i)=>job(i)),partial:true});
  await refuses({jobs:Array.from({length:101},(_,i)=>job(i)),repeat:true});
  await refuses({jobs:Array.from({length:101},(_,i)=>job(i)),changedTotal:true});
  for(const patch of [{run_attempt:3},{head_sha:'b'.repeat(40)},{run_id:9},{conclusion:'unknown'},{status:'queued'}])
   await refuses({setup:({jobs})=>Object.assign(jobs[0],patch)});
 });
 await test('API failures propagate with no issue writes',async()=>{
  for(const fail of ['attempt','jobs','issues','current'])await refuses({fail});
 });
 await test('posting failure is not reported as success',async()=>{
  const f=fixture({fail:'create'});await assert.rejects(f.run());assert.equal(f.state.info.length,0);
 });
 await test('later rerun prevents outdated notification',async()=>{
  await refuses({setup:({current})=>current.run_attempt++});
  await refuses({setup:({current})=>current.status='in_progress'});
 });
 await test('zero-job startup failure is explicit unknown not recovery',async()=>{
  const f=fixture({jobs:[],setup:({trigger,run,current})=>{for(const r of [trigger,run,current])r.conclusion='startup_failure';}});
  await f.run();assert.ok(f.state.created[0].body.includes('NOT recovery or an all-clear'));
  assert.ok(f.state.created[0].body.includes('0/0'));
 });
 await test('timeout cancelled skipped neutral outcomes stay distinct',async()=>{
  const f=fixture({jobs:['failure','timed_out','cancelled','skipped','neutral','success'].map((s,i)=>job(i,s))});
  await f.run();const b=f.state.created[0].body;assert.ok(b.includes('Failed or interrupted jobs: 3'));assert.ok(b.includes('Skipped: 1; neutral: 1'));
 });
 await test('all failed steps retained and malicious metadata cannot mention or link',async()=>{
  const f=fixture({setup:({jobs,trigger,run,current})=>{
   jobs[0].name='@everyone [click](https://evil.invalid) <script> ghp_SECRET123';
   jobs[0].steps.push({number:3,status:'completed',conclusion:'failure',name:'Second failure'});
   for(const r of [trigger,run,current])r.head_branch='@maintainer\nbranch';
  }});
  await f.run();const b=f.state.created[0].body;
  assert.ok(!b.includes('@everyone'));assert.ok(!b.includes('@maintainer'));
  assert.ok(!b.includes('[click]('));assert.ok(!b.includes('<script>'));assert.ok(!b.includes('ghp_SECRET123'));
  assert.ok(b.includes('Step 2:'));assert.ok(b.includes('Step 3:'));
 });
 await test('duplicate and malformed step metadata refuse',async()=>{
  await refuses({setup:({jobs})=>jobs[0].steps.push({...jobs[0].steps[0]})});
  await refuses({setup:({jobs})=>jobs[0].steps[1].conclusion='made-up'});
  await refuses({setup:({jobs})=>jobs[0].steps=0});
  await refuses({setup:({jobs})=>jobs[0].steps=null});
 });
 await test('oversized report refuses instead of truncating coverage',async()=>{
  const jobs=Array.from({length:400},(_,i)=>job(i));for(const j of jobs)j.name='x'.repeat(200);
  await refuses({jobs});
 });
 await test('workflow hooks include all three watches and Batch without privileged checkout',async()=>{
  assert.ok(source.includes('"9. Batch Patch"'));assert.ok(source.includes('run_attempt'));
  assert.ok(source.includes('cancel-in-progress: false'));
  assert.ok(source.includes('issues: write'));assert.ok(source.includes('actions: read'));
  for(const forbidden of ['actions/checkout','download-artifact','/logs','createComment','issues.update','bad.slice','secrets: inherit','pull_request_target:'])
   assert.ok(!source.includes(forbidden),forbidden);
  const watches=[
   ['agent-watch.yml','6. Provider watch'],
   ['watch.yml','7. Nightly watch'],
   ['community-watch.yml','8. Community watch']
  ];
  const hook=source.match(/workflows: (\[[^\n]+\])/);
  assert.ok(hook);
  const names=JSON.parse(hook[1]);
  assert.equal(names.length,8);assert.equal(new Set(names).size,8);
  for(const [file,name] of watches){
   assert.ok(names.includes(name));
   assert.ok(fs.readFileSync(path.join(ROOT,'.github/workflows',file),'utf8').startsWith('name: '+name+'\n'));
   for(const event of ['schedule','workflow_dispatch']){
    const f=fixture({setup:({trigger,run,current})=>{
     for(const r of [trigger,run,current])Object.assign(r,{name,path:'.github/workflows/'+file,event});
    }});
    await f.run();assert.equal(f.state.created.length,1);
    assert.ok(f.state.created[0].body.includes(name));
    assert.ok(f.state.created[0].body.includes('5/5'));
   }
   await refuses({setup:({trigger})=>Object.assign(trigger,{name,path:'.github/workflows/batch-patch.yml'})});
   await refuses({setup:({trigger,run,current})=>{
    for(const r of [trigger,run,current])Object.assign(r,{name,path:'.github/workflows/'+file,event:'pull_request'});
   }});
  }
 });
 console.log('NOTIFY_CONTRACTS_PASS='+count);
}
main().catch(e=>{console.error(e);process.exit(1);});
