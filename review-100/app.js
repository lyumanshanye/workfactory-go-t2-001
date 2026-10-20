'use strict';
const $=s=>document.querySelector(s);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const sets={ours:window.WORK100,nyang:window.NYANG100};
const names={ours:'本轮100题',nyang:'南杨100题 · c0–c3'};
const all=[...sets.ours.tasks.map(t=>({...t,source:'ours'})),...sets.nyang.tasks];
const byId=new Map(all.map(t=>[t.id,t])),cache=new Map(),tables=new Map();
const paneTabs={main:'task',pin:'task'};
const tabItems=[['task','完整题面'],['materials','输入材料'],['gold','参考交付'],['rubrics','评分项'],['review','审阅与来源']];
let source='ours',domain='',query='',id='',active=null,pinned=null,generation=0;
const isNY=r=>r.id.startsWith('NYC-');
const recordSource=r=>isNY(r)?'nyang':'ours';
const pretty=v=>JSON.stringify(v,null,2);
const safeURL=u=>/^https?:\/\//i.test(u||'')?u:'';
const assetURL=u=>/^(assets\/|\.\.\/review-500\/assets\/)/.test(u||'')?u:'';
function md(text){
  let code=false,paragraph=[];const out=[];
  const inline=t=>esc(t).replace(/`([^`]+)`/g,'<code>$1</code>').replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>');
  const flush=()=>{if(paragraph.length){out.push('<p>'+inline(paragraph.join('\n'))+'</p>');paragraph=[];}};
  for(const line of String(text).split('\n')){
    if(line.trim().startsWith('```')){flush();out.push(code?'</pre>':'<pre>');code=!code;continue;}
    if(code){out.push(esc(line)+'\n');continue;}
    const heading=/^#{1,6}\s+(.+)$/.exec(line);
    if(heading){flush();out.push('<h3>'+inline(heading[1])+'</h3>');}
    else if(!line.trim())flush();
    else if(/^\s*(?:[-*+]\s|\d+[.)]\s)/.test(line)){flush();out.push('<p class="bullet">'+inline(line)+'</p>');}
    else paragraph.push(line);
  }
  flush();if(code)out.push('</pre>');return '<div class="md">'+out.join('')+'</div>';
}
function subset(){return sets[source].tasks.filter(t=>(!domain||t.domain===domain)&&(!query||[t.id,t.title,t.role,t.domain,t.l2,t.l3].join(' ').toLowerCase().includes(query)));}
function sources(){
  $('#sources').innerHTML=Object.keys(sets).map(s=>`<button class="source ${s==='nyang'?'nyang':''}" data-source="${s}" aria-pressed="${source===s}"><b>${esc(names[s])}</b><span>${s==='ours'?'七大领域 · 100道独立agent内容复审候选 · 正式验收待做':'原固定随机样本 · 39种原职业 · 结构validated，不冒充内容复审'}</span></button>`).join('');
}
function domains(){
  const entries=Object.entries(sets[source].counts);
  if(source==='nyang')$('#domains').innerHTML=`<label for="occupation-filter">南杨原职业</label><select id="occupation-filter" aria-label="筛选南杨原职业"><option value="">全部职业 · 100题</option>${entries.map(([k,n])=>`<option value="${esc(k)}" ${domain===k?'selected':''}>${esc(k)} · ${n}</option>`).join('')}</select>`;
  else $('#domains').innerHTML=[['',100],...entries].map(([k,n])=>`<button class="${domain===k?'active':''}" data-domain="${esc(k)}" aria-pressed="${domain===k}">${esc(k||'全部领域')}<small>${n}</small></button>`).join('');
}
function list(){
  const xs=subset();$('#count').textContent=`${xs.length}道 / 当前批次100道`;
  $('#list').innerHTML=xs.map(t=>`<button class="task ${t.id===id?'active':''}" data-id="${t.id}" aria-current="${t.id===id}"><span class="id">${esc(t.id)}</span><span class="name">${esc(t.title)}</span><span class="meta">${esc(t.domain)} · ${t.inputs}份材料 · ${t.rubrics}项评分</span></button>`).join('')||'<p class="note">没有匹配题目，请修改检索词。</p>';
  const n=xs.findIndex(t=>t.id===id);$('#position').textContent=n<0?'当前题不在筛选结果中':`${names[source]} · ${n+1} / ${xs.length}`;
}
function setHash(){history.replaceState(null,'','#'+id+(pinned?'~'+pinned.id:''));}
async function load(taskId){if(!cache.has(taskId)){const r=await fetch('data/'+taskId+'.json?v=2');if(!r.ok)throw new Error('HTTP '+r.status);cache.set(taskId,await r.json());}return cache.get(taskId);}
async function select(next,update=true){
  if(!byId.has(next))next=sets[source].tasks[0].id;
  const nextSource=byId.get(next).source;
  if(source!==nextSource){source=nextSource;domain='';query='';$('#search').value='';sources();domains();}
  id=next;active=null;list();const token=++generation;$('#content').textContent='正在载入完整题目…';if(update)setHash();
  try{const r=await load(next);if(token!==generation)return;active=r;renderReader('main',r);}
  catch(e){if(token===generation)$('#content').innerHTML='<p class="note">题目载入失败：'+esc(e.message)+'</p>';}
}
async function activate(s){source=s;domain='';query='';$('#search').value='';sources();domains();await select(sets[s].tasks[0].id);}
function drawTable(key,page=0){
  const s=tables.get(key),rows=s.rows||[],limit=80,header=rows[0]||[],start=page*limit;
  const body=rows.slice(Math.max(1,start),Math.min(rows.length,start+limit)),max=Math.max(0,Math.ceil(rows.length/limit)-1);
  const warn=s.preview_truncated?'<p class="preview-warning">源预览有截断；下方仅为已保存部分，完整表格请打开原文件。</p>':'';
  return `<div class="sheet" data-sheet="${key}"><div class="sheetbar"><b>${esc(s.name)} · 原表${s.row_count}行${s.preview_truncated?' · 预览'+rows.length+'行':''}</b><span><button data-page="${Math.max(0,page-1)}" data-key="${key}" ${page===0?'disabled':''}>←</button> ${page+1}/${max+1} <button data-page="${Math.min(max,page+1)}" data-key="${key}" ${page===max?'disabled':''}>→</button></span></div>${warn}<div class="tablewrap"><table><thead><tr>${header.map(v=>`<th>${esc(v)}</th>`).join('')}</tr></thead><tbody>${body.map(r=>'<tr>'+r.map(v=>`<td>${esc(v)}</td>`).join('')+'</tr>').join('')}</tbody></table></div></div>`;
}
function filePreview(f,i,pane){
  let out='';const download=assetURL(f.download_url),visual=assetURL(f.visual_url),image=assetURL(f.image_url);
  if(download)out+=`<div class="file-actions"><a href="${esc(download)}" target="_blank" rel="noopener">打开原文件 ↗</a><a href="${esc(download)}" download>下载 ↓</a></div>`;
  if(f.preview_truncated)out+='<p class="preview-warning">已有文字预览被截断，不是原文件全文；请打开原文件。</p>';
  if(visual)out+=`<iframe loading="lazy" src="${esc(visual)}" title="${esc(f.path)} 视觉预览"></iframe>`;
  if(image)out+=`<img class="preview-image" loading="lazy" src="${esc(image)}" alt="${esc(f.path)}">`;
  if(f.kind==='sheets')out+=(f.sheets||[]).map((s,j)=>{const key=pane+'-'+i+'-'+j;tables.set(key,s);return drawTable(key);}).join('');
  else if(f.text)out+=`<details ${visual?'':'open'}><summary>完整${f.preview_truncated?'已保存预览':'文字 / 代码'}内容</summary><div class="prose">${esc(f.text)}</div></details>`;
  for(const u of f.embedded_images||[])if(assetURL(u))out+=`<img class="preview-image" loading="lazy" src="${esc(u)}" alt="${esc(f.path)}中的图片">`;
  return `<section class="file"><h3>${esc(f.path)}</h3><p>${esc(f.description)}</p>${f.note?'<p class="small">'+esc(f.note)+'</p>':''}<div class="hash">SHA256 ${esc(f.sha256||'原记录未注明')}</div>${out}</section>`;
}
function renderReader(pane,r){
  for(const k of tables.keys())if(k.startsWith(pane+'-'))tables.delete(k);
  const root=pane==='main'?$('#main-reader'):$('#pin-reader');if(!root)return;
  const ny=isNY(r),tab=paneTabs[pane],heading=root.querySelector(pane==='main'?'#heading':'.pin-heading'),tabs=root.querySelector('.tabs'),content=root.querySelector(pane==='main'?'#content':'.pin-content');
  heading.innerHTML=`<span class="label">${esc(r.id)} · ${esc(names[recordSource(r)])}</span><h2>${esc(r.title)}</h2><span class="tag ${ny?'ny':''}">${esc(r.domain)}</span><span class="tag ${ny?'ny':''}">${ny?'原记录：结构validated':'agent内容复审：候选通过'}</span><span class="tag pending">${ny?'本轮内容复审：未做':'正式验收：未完成'}</span><div class="subline">${esc(r.l2)} / ${esc(r.l3)} · ${esc(r.role)}</div>`;
  tabs.innerHTML=tabItems.map(([key,label])=>`<button data-tab="${key}" class="${key===tab?'active':''}" aria-pressed="${key===tab}">${label}${key==='materials'?' · '+r.materials.length:key==='gold'?' · '+r.gold.length:key==='rubrics'?' · '+r.criteria.length:''}</button>`).join('');
  let h='';
  if(tab==='task')h=`<div class="note">完整原文，不自动翻译、不压缩为摘要。${ny?'南杨沿用原抽样题面。':'本轮当前 instruction.md。'}</div>`+md(r.instruction);
  if(tab==='materials'){
    h=`<div class="note">${ny?'南杨实际材料与旧页公开附件一致；有截断会明确提示，可打开原文件。':'本轮完整离线附件在已交付题包中；公开页列清单与溯源，不上传尚未核清外发权利的原文件。'}</div>`;
    h+=ny?r.materials.map((f,i)=>filePreview(f,i,pane)).join(''):r.materials.map(f=>`<section class="file"><span class="label">${esc(f.path.split('.').pop())} · ${(f.bytes/1024).toFixed(1)} KB</span><h3>${esc(f.path)}</h3><p>${esc(f.description)}</p><p class="small">${esc(f.transformation)}</p><p>${safeURL(f.source_url)?`<a href="${esc(f.source_url)}" target="_blank" rel="noopener">查看公开来源 ↗</a>`:'原创业务委托 / 本地构造材料，不冒充官方规则'}</p><p class="small">许可 / 外发状态：${esc(typeof f.license==='string'?f.license:pretty(f.license))}</p><div class="hash">SHA256 ${esc(f.sha256)}</div></section>`).join('');
    if(!r.materials.length)h+='<p class="note">此题原样本没有输入附件（0份），未另造占位材料补齐。请结合完整题面和设计规格查看题目给定条件。</p>';
  }
  if(tab==='gold')h=`<div class="note">${ny?'南杨出题方保存的参考产物，不是本轮作答或已验证正确的答案。预览沿用旧页，有截断请打开原文件。':'本轮agent编写、交叉审阅后的参考候选，不是专家认证或正式judge通过。表格可翻页查看全部行；文字提取不还原原始Office排版。'}</div>`+r.gold.map((f,i)=>filePreview(f,i,pane)).join('');
  if(tab==='rubrics'){
    const positive=r.criteria.filter(c=>c.weight>0).reduce((a,c)=>a+c.weight,0);
    h=`<div class="note">${r.criteria.length}项${ny?'':' · 原正权重合计'+positive.toFixed(2)}。${ny?'保留南杨原weight / polarity / 判据，不换算为本轮±10/7/3标准，未标字段不替作者补造。':'本轮原始权重与判据。'} 没有本次正式judge分数。</div>`;
    h+=r.criteria.map(c=>`<section class="criterion"><span class="weight ${c.weight<0?'negative':''}">${c.weight>0?'+':''}${esc(c.weight)}</span><span class="label">${esc(c.id)} · ${esc(c.type)}${c.polarity?' · '+esc(c.polarity):''}</span><p>${esc(c.description)}</p><div class="small">${esc(c.dimension)} · ${esc(c.criterion_type)} / ${esc(c.criterion_necessity)}${c.requirement_refs?.length?' · 对应要求 '+esc(c.requirement_refs.join('、')):''}</div>${c.levels?'<pre>'+esc(pretty(c.levels))+'</pre>':''}<details><summary>${ny?'原始条目 / 证据与提示':'判定依据 / 锚点'}</summary><pre>${esc(pretty(c.original||c.evidence))}</pre></details></section>`).join('');
  }
  if(tab==='review'){
    h=`<div class="note">${ny?'南杨原验收记录：结构 / 材料 validated，不是本轮agent内容复审，也不是正式正确率。作者自报Gold通过策略单独保留，不当作实际执行证据。':'当前：pass-candidate / 独立agent内容复审通过；不是专家审核、Gold>0.85或三模型难度验收。首轮缺陷与关闭记录均保留。'}</div>`;
    if(r.original_url)h+=`<p><a href="${esc(r.original_url)}" target="_blank" rel="noopener">回到旧500题页的同一道原题 ↗</a></p>`;
    const checks=r.review.verified||r.review.manual_checks||r.review.positive_observations||[];
    if(checks.length)h+='<ul class="reviewcheck">'+checks.map(v=>'<li>'+esc(typeof v==='string'?v:pretty(v))+'</li>').join('')+'</ul>';
    h+=`<details open><summary>${ny?'完整来源与结构验收记录':'完整独立审阅记录与文件哈希'}</summary><pre>${esc(pretty(r.review))}</pre></details><details><summary>分类 / 设计规格 / 生成元数据</summary><pre>${esc(pretty(r.metadata))}</pre></details>`;
  }
  content.innerHTML=h;
}
function renderPin(){
  const existing=$('#pin-reader');if(existing)existing.remove();
  $('#reader-panels').classList.toggle('comparing',Boolean(pinned));$('#compare-note').hidden=!pinned;
  $('#compare-toggle').setAttribute('aria-pressed',Boolean(pinned));$('#compare-toggle').textContent=pinned?'退出并排比较':'固定当前题，并排看另一批 →';
  if(!pinned)return;
  const article=document.createElement('article');article.id='pin-reader';article.className='reader';
  const options=sets[recordSource(pinned)].tasks.map(t=>`<option value="${t.id}" ${pinned.id===t.id?'selected':''}>${esc(t.id+' · '+t.title)}</option>`).join('');
  article.innerHTML=`<div class="readerbar"><b>固定对照 · ${esc(names[recordSource(pinned)])}</b><select data-pin-picker class="pin-picker" aria-label="更换固定对照题">${options}</select></div><div class="pin-heading"></div><nav class="tabs" aria-label="固定题详情"></nav><div class="pin-content"></div>`;
  $('#reader-panels').prepend(article);renderReader('pin',pinned);
}
async function toggleCompare(){if(pinned){pinned=null;renderPin();setHash();return;}if(!active)return;pinned=active;paneTabs.pin=paneTabs.main;renderPin();await activate(recordSource(pinned)==='ours'?'nyang':'ours');}
function step(delta){const xs=subset();if(xs.length)select(xs[(Math.max(0,xs.findIndex(t=>t.id===id))+delta+xs.length)%xs.length].id);}
$('#sources').addEventListener('click',e=>{const b=e.target.closest('[data-source]');if(b)activate(b.dataset.source);});
$('#domains').addEventListener('click',e=>{const b=e.target.closest('[data-domain]');if(!b)return;domain=b.dataset.domain;domains();list();const xs=subset();if(xs.length&&!xs.some(t=>t.id===id))select(xs[0].id);});
$('#domains').addEventListener('change',e=>{if(e.target.id!=='occupation-filter')return;domain=e.target.value;list();const xs=subset();if(xs.length&&!xs.some(t=>t.id===id))select(xs[0].id);});
$('#search').addEventListener('input',e=>{query=e.target.value.trim().toLowerCase();list();});
$('#list').addEventListener('click',e=>{const b=e.target.closest('[data-id]');if(b)select(b.dataset.id);});
$('#reader-panels').addEventListener('click',e=>{const page=e.target.closest('[data-page]');if(page){page.closest('[data-sheet]').outerHTML=drawTable(page.dataset.key,Number(page.dataset.page));return;}const button=e.target.closest('[data-tab]');if(!button)return;const pane=button.closest('article').id==='pin-reader'?'pin':'main';paneTabs[pane]=button.dataset.tab;const r=pane==='pin'?pinned:active;if(r)renderReader(pane,r);});
$('#reader-panels').addEventListener('change',async e=>{if(e.target.matches('[data-pin-picker]')){try{pinned=await load(e.target.value);renderPin();setHash();}catch(err){$('#toast').textContent=err.message;$('#toast').hidden=false;}}});
$('#prev').onclick=()=>step(-1);$('#next').onclick=()=>step(1);$('#compare-toggle').onclick=toggleCompare;$('#close-compare').onclick=toggleCompare;
$('#random').onclick=()=>{const xs=subset();if(xs.length)select(xs[Math.floor(Math.random()*xs.length)].id);};
$('#copy').onclick=async()=>{try{await navigator.clipboard.writeText(location.href);$('#toast').textContent='题目 / 对照链接已复制';}catch{$('#toast').textContent='地址栏就是当前题目 / 对照链接，可直接复制';}$('#toast').hidden=false;setTimeout(()=>$('#toast').hidden=true,2300);};
async function initial(){const [main,pin]=decodeURIComponent(location.hash.slice(1)).split('~');await select(main||'GO-P100-001',false);if(pin&&byId.has(pin)){pinned=await load(pin);renderPin();}}
window.addEventListener('hashchange',initial);sources();domains();initial();
