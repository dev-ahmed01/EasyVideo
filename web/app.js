/* EasyVideo local studio — straightforward DOM, no heavy client runtime. */
(function () {
  "use strict";
  const $ = (s) => document.querySelector(s);
  let current = null, stage = 1, selected = new Set(), health = null, timer = null, plan = null;
  const roles = {hero:"Full chair / hero",detail:"Material / detail",function:"Function demo",workspace:"Workspace",inventory:"Inventory / multiple",proof:"Trust / showroom"};
  const styles = ["stomp","cinematic","features","business","social"];
  const html = (x) => String(x == null ? "" : x).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const toast = (msg) => { const el=$("#toast"); el.textContent=msg;el.classList.add("show");setTimeout(()=>el.classList.remove("show"),4200); };
  async function api(path,method="GET",body,upload=false){
    const r=await fetch(path,{method,headers:upload?{}:body?{"Content-Type":"application/json"}:{},body:upload?body:body?JSON.stringify(body):undefined});
    if(!r.ok){let message=r.statusText;try{const data=await r.json();message=typeof data.detail==="string"?data.detail:JSON.stringify(data.detail)}catch{}throw new Error(message)}
    return r.json();
  }
  function setStage(next){if(next>1&&!current){toast("Create a brief first.");return;}stage=next;$(".nav-steps").querySelectorAll(".nav-step").forEach(b=>b.classList.toggle("active",Number(b.dataset.stage)===stage));$("#breadcrumb").textContent=["","BRIEF","FOOTAGE","REEL STUDIO"][stage];render();}
  function briefForm(){
    return {
      intent:$("#intent").value.trim(), audience:$("#audience").value.trim(), product:$("#product").value.trim(),
      offer:$("#offer").value.trim(), facts:$("#facts").value.trim(),
      call_to_action:$("#cta").value.trim(), script:$("#script").value.trim()
    };
  }
  function showBrief(){
    $("#view").innerHTML='<div class="overline">01 / Marketing direction</div><h1 class="page-title">The idea comes before the footage.</h1><p class="subtitle">Tell us what this Reel should achieve. We’ll build a campaign direction and tell you exactly what to film before you upload anything.</p>'+
      '<div class="two-col"><div class="panel"><h3>Creative brief</h3><p>Start with your marketing goal, not a template.</p>'+
      '<label class="label" for="intent">What should these Reels accomplish? *</label><textarea id="intent" class="field" placeholder="Show our office chair collection to local startups. Build trust and generate enquiries for a 20-chair office setup."></textarea>'+
      '<div class="columns"><div><label class="label" for="audience">Who should see it?</label><input id="audience" class="field" value="Startups and office buyers"></div><div><label class="label" for="product">Product</label><input id="product" class="field" value="Ergonomic office chair"></div></div>'+
      '<label class="label" for="offer">Offer / availability (optional)</label><input id="offer" class="field" placeholder="Models in stock · bulk enquiries welcome">'+
      '<label class="label" for="facts">Verified product facts only</label><input id="facts" class="field" placeholder="Mesh back, armrests, available in black — if verified">'+
      '<label class="label" for="cta">Call to action</label><input id="cta" class="field" value="DM us for current availability">'+
      '<label class="label" for="script">Your ChatGPT script (optional)</label><textarea id="script" class="field" placeholder="Paste an approved narration. The feature-led Reel will use it; other formats receive different scripts."></textarea>'+
      '<div class="button-row"><button class="btn" id="plan-btn">Plan my campaign →</button></div></div>'+
      '<div class="panel"><span class="capsule">MARKETING-FIRST APPROACH</span><div class="side-quote">Create a reason to stop. A reason to watch. A reason to enquire.</div><div class="tip">Five different narratives, not five filters. Each edit has a unique hook, cadence, on-screen copy, narration and business objective.</div><div id="plan-preview"></div></div></div>';
    $("#plan-btn").onclick=async()=>{const data=briefForm();if(data.intent.length<10){toast("Write a little more about your goal.");return;}try{plan=await api("/api/plan","POST",data);const shots=plan.shotlist.filter(x=>x.required).map(x=>"<li>"+html(x.label)+"</li>").join("");$("#plan-preview").innerHTML='<div class="label">Footage we will request</div><ul>'+shots+'</ul><div class="button-row"><button class="btn full" id="create-btn">Create project & shot list →</button></div>';$("#create-btn").onclick=async()=>{try{current=await api("/api/projects","POST",data);selected.clear();setStage(2);toast("Shot list created. Film and label your clips.");}catch(e){toast(e.message)}};}catch(e){toast(e.message)}};
  }
  function renderShots(){
    const have=new Set(current.clips.filter(c=>c.duration>=1).map(c=>c.role));
    return current.shotlist.map((x,i)=>'<div class="shot"><span class="shot-index">'+String(i+1).padStart(2,"0")+'</span><div class="shot-info"><strong>'+html(x.label)+'</strong><p>'+html(x.instruction)+'</p></div><span class="shot-status '+(have.has(x.role)?"yes":x.required?"no":"")+'">'+(have.has(x.role)?"✓ Added":x.required?"Required":"Optional")+'</span></div>').join("");
  }
  function roleOptions(active){return Object.entries(roles).map(([key,name])=>'<option value="'+key+'" '+(key===active?"selected":"")+'>'+html(name)+'</option>').join("");}
  function showFootage(){
    const audit=current.audit;
    $("#view").innerHTML='<div class="overline">02 / Production checklist</div><h1 class="page-title">Know what to shoot. Then we edit.</h1><p class="subtitle">Upload the clips from your shot list, label what each one shows, and we’ll check duration, format, coverage and framing before rendering.</p>'+
    '<div class="two-col"><div class="panel"><h3>Your shot list</h3><p>Required shots change with your campaign intent.</p><div class="shot-list">'+renderShots()+'</div></div>'+
    '<div class="panel"><h3>Footage library</h3><p>MP4, MOV, M4V, WebM or MKV. Max 250 MB per clip.</p>'+
    '<div class="upload-zone"><div style="font-size:30px">▣</div><strong>Add your footage</strong><p>Choose a role, then upload one or more clips</p><div class="upload-row"><select id="upload-role" class="field">'+roleOptions("hero")+'</select><label for="file-upload" class="btn small">Choose video files</label><input id="file-upload" type="file" multiple accept="video/*,.mkv,.m4v"></div></div><div id="clips">'+(current.clips.length?current.clips.map(c=>'<div class="clip-row"><div class="clip-meta"><strong title="'+html(c.filename)+'">'+html(c.filename)+'</strong><small>'+Math.round(c.duration)+'s · '+c.width+'×'+c.height+'</small></div><select class="field clip-role" data-id="'+c.id+'">'+roleOptions(c.role)+'</select><button class="clip-delete" data-id="'+c.id+'">Remove</button></div>').join(""):'<div class="empty-note">Your clips will appear here.</div>')+'</div>'+
    '<div class="label">Footage audit</div><span class="capsule '+(!audit.ready?"warn":"")+'">'+audit.matched_required+' / '+audit.required_total+' REQUIRED SHOTS READY</span>'+
    audit.missing.map(x=>'<div class="flag">Missing: '+html(x.label)+'</div>').join("")+
    audit.warnings.map(x=>'<div class="flag info">'+html(x)+'</div>').join("")+
    (audit.suggested.length?'<div class="label">Optional coverage opportunities</div>'+audit.suggested.map(x=>'<div class="flag info">Consider filming: '+html(x.label)+'</div>').join(""):"")+
    '<div class="button-row"><button id="go-reels" class="btn full" '+(!audit.ready?"disabled":"")+'>Continue to Reel studio →</button></div></div></div>'+
    '<div class="footnote">The app checks media metadata, not visual truth. Role labels should describe the actual footage. Missing optional clips are replaced by existing relevant shots and should be reviewed.</div>';
    $("#file-upload").onchange=async(e)=>{const files=Array.from(e.target.files);const role=$("#upload-role").value;for(const file of files){const f=new FormData();f.append("file",file);f.append("role",role);try{toast("Inspecting "+file.name);current=await api("/api/projects/"+current.id+"/clips","POST",f,true)}catch(err){toast(file.name+": "+err.message)}}render();};
    document.querySelectorAll(".clip-role").forEach(x=>x.onchange=async()=>{try{current=await api("/api/projects/"+current.id+"/clips/"+x.dataset.id,"PATCH",{role:x.value});render();}catch(e){toast(e.message)}});
    document.querySelectorAll(".clip-delete").forEach(x=>x.onclick=async()=>{try{current=await api("/api/projects/"+current.id+"/clips/"+x.dataset.id,"DELETE");render();}catch(e){toast(e.message)}});
    $("#go-reels").onclick=()=>setStage(3);
  }
  function reelCard(x,i){
    const url=current.exports[x.id].final||current.exports[x.id].preview;
    const poster=url?'<video controls preload="metadata" src="'+html(url)+'"></video>':'<span class="poster-letter">'+html(x.beats[0])+'</span>';
    return '<article class="reel-card '+(selected.has(x.id)?"selected":"")+'"><div class="reel-poster">'+poster+'<span class="reel-number">0'+(i+1)+'</span></div><h4>'+html(x.title)+'</h4><p>'+html(x.subtitle)+'</p><label class="reel-pick"><input type="checkbox" class="pick" data-style="'+x.id+'" '+(selected.has(x.id)?"checked":"")+'> Select Reel</label><details><summary>View narration</summary><blockquote>'+html(x.voiceover)+'</blockquote><small>'+html(x.marketing_goal)+'</small></details>'+(url?'<a class="download" href="'+html(url)+'" download>↓ Download '+(current.exports[x.id].final?"1080p":"preview")+'</a>':'')+'</article>';
  }
  function performanceSummary(){
    const entries=Object.entries(current.performance||{});
    if(!entries.length)return '<p class="footnote">No Reel results entered yet. Post your exports, then add their Insights here.</p>';
    return '<div class="metric-summary">'+entries.map(([id,p])=>{
      const name=current.creatives.find(x=>x.id===id)?.title||id;
      const shareRate=p.reach?((p.shares/p.reach)*1000).toFixed(1):"—";
      return '<div class="metric-row"><strong>'+html(name)+'</strong><span>'+p.enquiries+' enquiries</span><span>'+shareRate+' shares / 1k reached</span><span>'+p.avg_watch_seconds+'s avg watch</span></div>';
    }).join("")+'</div>';
  }
  function fillMetrics(style){
    const item=(current.performance||{})[style]||{};
    for(const key of ["views","reach","avg_watch_seconds","shares","saves","enquiries"])
      $("#metric-"+key).value=item[key]??0;
    $("#metric-url").value=item.post_url||"";
  }
  function showStudio(){
    const busy=["queued","running"].includes(current.job.status);
    const previews=styles.every(x=>current.exports[x].preview);
    const chosen=Array.from(selected);
    $("#view").innerHTML='<div class="overline">03 / Five creative directions</div><h1 class="page-title">Five ways to tell one story.</h1><p class="subtitle">Each format has a different opening, pacing, text treatment and offline voiceover. Generate drafts, watch them with sound, then choose up to three for full-quality export.</p>'+
    '<div class="panel"><div style="display:flex;gap:15px;align-items:center;justify-content:space-between;flex-wrap:wrap"><div><h3>Reel collection</h3><p style="margin:4px 0">9:16 vertical · original chair footage · locally synthesized narration</p></div><span class="capsule">'+html(current.clips.length)+' SOURCE CLIPS</span></div>'+
    (busy?'<div class="progress"><strong>Rendering in progress</strong>'+html(current.job.message)+'<br><small>The render queue runs sequentially to conserve memory. You can leave this tab open.</small></div>':current.job.status==="error"?'<div class="flag">Render error: '+html(current.job.message)+'</div>':"")+
    '<div class="reel-grid">'+current.creatives.map(reelCard).join("")+'</div>'+
    '<div class="button-row"><button class="btn" id="make-drafts" '+(busy?"disabled":"")+'>✦ '+(previews?"Regenerate five drafts":"Generate five previews")+'</button><button class="btn secondary" id="export-finals" '+(busy||chosen.length===0?"disabled":"")+'>Export selected in 1080p ('+chosen.length+'/3)</button></div>'+
    '<div class="footnote">These previews may take several minutes on a CPU-only computer. Voiceover is mandatory; if an offline speech engine is unavailable, the app will flag it rather than export a silent Reel.</div></div>'+
    '<div class="panel performance-panel"><h3>Organic results tracker</h3><p>After posting, record actual Instagram insights. Prioritize real enquiries over vanity metrics; no Instagram account connection is needed.</p>'+
    '<div class="columns"><div><label class="label" for="metric-style">Reel format</label><select class="field" id="metric-style">'+current.creatives.map(x=>'<option value="'+x.id+'">'+html(x.title)+'</option>').join("")+'</select></div><div><label class="label" for="metric-url">Post link (optional)</label><input id="metric-url" class="field" placeholder="https://www.instagram.com/reel/..."></div></div>'+
    '<div class="metric-grid">'+[["views","Views / plays"],["reach","Accounts reached"],["avg_watch_seconds","Average watch (seconds)"],["shares","Shares / sends"],["saves","Saves"],["enquiries","Real enquiries"]].map(([id,label])=>'<div><label class="label" for="metric-'+id+'">'+label+'</label><input id="metric-'+id+'" class="field" type="number" step="'+(id==="avg_watch_seconds"?"0.1":"1")+'" min="0" value="0"></div>').join("")+'</div>'+
    '<div class="button-row"><button class="btn secondary" id="save-metrics">Save results locally</button></div>'+
    '<div id="performance-summary">'+performanceSummary()+'</div></div>'+
    '<div class="tip">Organic growth loop: compare hook retention, average watch time, shares, saves and genuine enquiries after posting. Five different ideas give you a useful test—not a guarantee of reach.</div>';
    document.querySelectorAll(".pick").forEach(x=>x.onchange=()=>{if(x.checked){if(selected.size>=3){x.checked=false;toast("Choose up to three Reels.");return;}selected.add(x.dataset.style)}else selected.delete(x.dataset.style);render();});
    $("#make-drafts").onclick=()=>startRender(styles,"preview");
    $("#export-finals").onclick=()=>startRender(chosen,"final");
    $("#metric-style").onchange=()=>fillMetrics($("#metric-style").value);
    fillMetrics($("#metric-style").value);
    $("#save-metrics").onclick=async()=>{
      const style=$("#metric-style").value, data={post_url:$("#metric-url").value};
      for(const key of ["views","reach","avg_watch_seconds","shares","saves","enquiries"]) data[key]=Number($("#metric-"+key).value||0);
      try{current=await api("/api/projects/"+current.id+"/performance/"+style,"PUT",data);render();$("#metric-style").value=style;fillMetrics(style);toast("Organic performance saved locally.");}
      catch(e){toast(e.message);}
    };
    if(busy)beginPoll();else stopPoll();
  }
  async function startRender(which,resolution){
    try{await api("/api/projects/"+current.id+"/renders","POST",{styles:which,resolution,voice_engine:"auto"});current=await api("/api/projects/"+current.id);render();toast("Rendering "+which.length+" video(s) locally.");}catch(e){toast(e.message)}
  }
  function beginPoll(){if(timer)return;timer=setInterval(async()=>{if(!current)return;try{const before=current.job.status;current=await api("/api/projects/"+current.id);if(stage===3)render();if(before!==current.job.status&&current.job.status==="ready")toast("Your videos are ready.");}catch(e){console.error(e)}},2700);}
  function stopPoll(){if(timer){clearInterval(timer);timer=null;}}
  function render(){if(current)$("#project-state").textContent=current.brief.product.toUpperCase().slice(0,24);if(stage===1)showBrief();if(stage===2)showFootage();if(stage===3)showStudio();}
  document.querySelectorAll(".nav-step").forEach(b=>b.onclick=()=>setStage(Number(b.dataset.stage)));
  $("#new-project").onclick=()=>{stopPoll();current=null;plan=null;selected.clear();setStage(1);};
  async function init(){
    try{health=await api("/api/health");$("#engine-state").textContent=(health.ffmpeg?"FFmpeg ready":"FFmpeg missing")+" · "+(health.voices.length?health.voices.join(", ")+" voice":"Voice engine missing");}catch(e){$("#engine-state").textContent="Server unavailable"}
    try{const projects=await api("/api/projects");if(projects.length){current=await api("/api/projects/"+projects[0].id);selected=new Set(current.selected||[]);setStage(2);return;}}catch(e){console.warn(e)}
    render();
  }
  init();
})();