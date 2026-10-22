/* EasyVideo visual studio — dependency-free and offline capable. */
(function(){
"use strict";
const $=s=>document.querySelector(s);
const $$=s=>Array.from(document.querySelectorAll(s));
const escape=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const roles={hero:"Full chair",detail:"Close-up",function:"Feature demo",workspace:"Desk / workspace",inventory:"Multiple chairs",proof:"Showroom / proof"};
const styleIds=["stomp","cinematic","features","business","social","voice_story"];
let project=null,stage=1,mode="new",audioMode="generated",audioStart=0,audioLength=18,chosen=new Set(),health=null,timer=null,voiceProvider="auto";
function toast(message){const box=$("#toast");box.textContent=message;box.classList.add("show");setTimeout(()=>box.classList.remove("show"),4500);}
async function api(path,method="GET",body){
 const upload=body instanceof FormData;
 const response=await fetch(path,{method,headers:body&&!upload?{"Content-Type":"application/json"}:{},body:upload?body:body?JSON.stringify(body):undefined});
 if(!response.ok){let detail=response.statusText;try{const err=await response.json();detail=typeof err.detail==="string"?err.detail:JSON.stringify(err.detail)}catch{}throw Error(detail);}
 return response.json();
}
const head=(number,label,title,description)=>'<div class="hero-line">'+number+' / '+label+'</div><h1 class="title">'+title+'</h1>'+(description?'<p class="description">'+description+'</p>':"");
function stageTo(n){
 if(n>1&&!project){toast("Create a campaign first");return;}
 if(n===3&&(!project.audit.ready||(project.brief.source_mode==="remix"&&!project.reference))){
  toast("Finish the required footage and original Reel first");return;
 }
 stage=n;$$(".nav-item").forEach(e=>e.classList.toggle("active",Number(e.dataset.stage)===stage));
 $("#breadcrumb").textContent=["","DIRECTION","FOOTAGE","REEL LAB"][n];
 render();
}
function newProject(){
 stopPoll();project=null;stage=1;mode="new";audioMode="generated";audioStart=0;audioLength=18;chosen.clear();
 $("#project-state").textContent="UNTITLED CAMPAIGN";stageTo(1);
}
function briefValues(){
 return {source_mode:mode,intent:$("#intent").value.trim(),audience:$("#audience").value.trim(),
 product:$("#product").value.trim(),brand_name:$("#brand-name").value.trim(),location:$("#location").value.trim(),offer:$("#offer").value.trim(),facts:$("#facts").value.trim(),
 call_to_action:$("#cta").value.trim(),script:$("#script").value.trim()};
}
function showDirection(){
 $("#view").innerHTML=head("01","Creative direction","Make something worth watching.","Start with the outcome. We'll guide the footage.")+
 '<div class="grid-main"><div class="stack">'+
 '<div class="type-grid">'+
 '<button class="type-card '+(mode==="new"?"selected":"")+'" type="button" data-mode="new"><span class="type-art idea"><span class="art-word">NEW<br>IDEA.</span></span><span><strong>New campaign</strong><small>Start from a creative goal</small></span></button>'+
 '<button class="type-card '+(mode==="remix"?"selected":"")+'" type="button" data-mode="remix"><span class="type-art remix"><span class="play">▶</span></span><span><strong>Remix a Reel</strong><small>Keep its audio. Change the edit.</small></span></button></div>'+
 '<div class="panel"><h2 class="panel-title">Your brief</h2><label class="field-title" for="intent">What should this video achieve?</label>'+
 '<textarea id="intent" class="input" placeholder="Introduce ergonomic chairs to startups and generate office enquiries." required></textarea>'+
 '<div class="field-grid"><div><label class="field-title" for="audience">Audience</label><input id="audience" class="input" value="Office and home-workspace buyers"></div>'+
 '<div><label class="field-title" for="product">Product</label><input id="product" class="input" value="Ergonomic office chair"></div></div>'+
 '<details class="detail-expand"><summary>Script & campaign details +</summary>'+
 '<label class="field-title" for="brand-name">Brand name</label><input id="brand-name" class="input" value="Furnihub Interiors">'+
 '<label class="field-title" for="location">Served city / area (optional)</label><input id="location" class="input" placeholder="Bengaluru, only if you serve it">'+
 '<label class="field-title" for="script">ChatGPT script (optional)</label><textarea id="script" class="input" placeholder="Paste a voiceover script"></textarea>'+
 '<label class="field-title" for="offer">Stock / offer</label><input id="offer" class="input" placeholder="Available today · bulk orders welcome">'+
 '<label class="field-title" for="facts">Verified features</label><input id="facts" class="input" placeholder="Mesh back · adjustable arms, if true">'+
 '<label class="field-title" for="cta">Call to action</label><input id="cta" class="input" value="DM us for availability"></details>'+
 '<div class="btn-row"><button class="primary" id="create-project">Plan my Reel →</button></div></div></div>'+
 '<div class="panel"><div class="preview-stage"><div class="mock-phone"><span>MAKE<br>IT<br>MOVE.</span></div><div class="mock-phone second"><span>MORE<br>THAN<br>AN AD.</span></div></div>'+
 '<h3 class="aside-phrase">Six directions.<br>One clear goal.</h3><p class="aside-note">Cinematic · STOMP · Product story · Office · Social</p>'+
 '<div class="stat-strip"><span class="stat-pill">9:16</span><span class="stat-pill">No GPU</span><span class="stat-pill">Local</span></div></div></div>';
 $$("[data-mode]").forEach(b=>b.onclick=()=>{mode=b.dataset.mode;$$("[data-mode]").forEach(x=>x.classList.toggle("selected",x.dataset.mode===mode));});
 $("#create-project").onclick=async()=>{
  const payload=briefValues();if(payload.intent.length<10){toast("Describe your goal in at least ten characters.");return;}
  $("#create-project").disabled=true;
  try{project=await api("/api/projects","POST",payload);chosen.clear();audioMode=mode==="remix"?"reference":"generated";stageTo(2);}
  catch(e){toast(e.message);$("#create-project").disabled=false;}
 };
}
function choices(current){return Object.entries(roles).map(([k,v])=>'<option value="'+k+'" '+(current===k?"selected":"")+'>'+escape(v)+'</option>').join("");}
function shotList(){
 const available=new Set(project.clips.map(c=>c.role));
 return project.shotlist.map((s,i)=>'<div class="shot"><span class="shot-number">'+String(i+1).padStart(2,"0")+'</span><div class="shot-info"><strong>'+escape(s.label)+'</strong><small>'+escape(s.instruction)+'</small></div><span class="status '+(available.has(s.role)?"ok":s.required?"missing":"")+'">'+(available.has(s.role)?"✓ Ready":s.required?"Needed":"Optional")+'</span></div>').join("");
}
function clipList(){
 if(!project.clips.length)return '<div class="footnote">No clips yet.</div>';
 return project.clips.map(c=>'<div class="clip-item">'+
 '<video class="clip-thumb" src="/api/projects/'+project.id+'/clips/'+c.id+'/media" preload="metadata" muted playsinline></video>'+
 '<div class="clip-text"><strong>'+escape(c.filename)+'</strong><small>'+Math.round(c.duration)+'s · '+c.width+'×'+c.height+'</small></div>'+
 '<select class="input clip-role" data-id="'+c.id+'" aria-label="Shot role">'+choices(c.role)+'</select>'+
 '<button type="button" class="danger-text remove-clip" data-id="'+c.id+'">Remove</button></div>').join("");
}
function referencePanel(){
 const ref=project.reference;
 if(project.brief.source_mode!=="remix"&&!ref)return "";
 return '<div class="panel"><div class="hero-line">ORIGINAL REEL</div><h2 class="panel-title" style="margin-top:13px">'+(ref?"Original attached":"Bring your original Reel")+'</h2>'+
 '<div class="upload-area"><strong>Upload old Reel</strong><p>We can reuse its complete audio track</p><label for="reference-upload" class="secondary">Choose Reel ↑</label><input class="file-hidden" id="reference-upload" type="file" accept="video/*,.mkv,.mov,.m4v"></div>'+
 (ref?'<video class="reference-video" src="'+escape(ref.media_url)+'" preload="metadata" controls playsinline></video>'+
 '<div class="stat-strip"><span class="stat-pill">'+ref.duration.toFixed(1)+'s video</span><span class="stat-pill">'+(ref.has_audio?"Audio detected":"No audio track")+'</span></div>'+
 (ref.has_audio?'<audio class="reference-audio" preload="none" controls src="'+escape(ref.audio_url)+'"></audio>':'<div class="flag">This Reel has no sound. Use a fresh offline voiceover.</div>')+
 '<div class="mini-divider"></div><h3 class="panel-title">Pick a moment</h3>'+
 '<div class="field-grid"><div><label class="field-title" for="section-start">Start (seconds)</label><input id="section-start" class="input" type="number" min="0" max="'+Math.max(0,ref.duration-2)+'" value="0" step="0.5"></div>'+
 '<div><label class="field-title" for="section-duration">Length (seconds)</label><input id="section-duration" class="input" type="number" min="2" max="60" value="5" step="0.5"></div></div>'+
 '<label class="field-title" for="section-role">Shot type</label><select id="section-role" class="input">'+choices("hero")+'</select>'+
 '<div class="btn-row"><button class="secondary" type="button" id="import-section">Add selected moment +</button></div>'+
 '<p class="footnote">Review the old Reel, choose a meaningful time range and label the real footage.</p>'+
 '<p class="footnote">Original audio can include music, effects and narration. Speech is not isolated. Use only audio you have rights to reuse.</p>':"")+
 '</div>';
}
function showFootage(){
 const a=project.audit,refNeeded=project.brief.source_mode==="remix"&&!project.reference;
 $("#view").innerHTML=head("02","Production","Your footage, organized.",a.ready?"Your coverage is ready. Review the footage before editing.":"Upload the shots marked Needed to unlock production.")+
 '<div class="grid-main"><div class="stack">'+
 (project.brief.source_mode==="remix"?referencePanel():"")+
 '<div class="panel"><h2 class="panel-title">Shot checklist <span class="stat-pill">'+a.matched_required+'/'+a.required_total+' essential</span></h2>'+shotList()+'</div></div>'+
 '<div class="stack"><div class="panel"><h2 class="panel-title">Footage library</h2>'+
 '<div class="upload-area"><strong>Drop in your clips</strong><p>Choose what each video shows</p><div class="upload-controls"><select class="input" id="upload-role">'+choices("hero")+'</select><label class="secondary" for="video-upload">Add footage ↑</label></div>'+
 '<input class="file-hidden" id="video-upload" type="file" accept="video/*,.mkv,.mov,.m4v" multiple></div>'+
 '<div id="clip-list">'+clipList()+'</div>'+
 (a.missing.length?'<div class="mini-divider"></div>'+a.missing.map(s=>'<div class="flag">Missing: '+escape(s.label)+'</div>').join(""):'<div class="flag info">All essential shots are covered.</div>')+
 (a.warnings.filter(w=>!w.startsWith("Shot roles")).slice(0,3).map(w=>'<div class="flag info">'+escape(w)+'</div>').join(""))+
 '<div class="btn-row"><button class="primary" id="to-studio" '+(!a.ready||refNeeded?"disabled":"")+'>Create five Reels →</button></div>'+
 '<p class="footnote">We inspect duration and framing; please confirm your shot labels visually.</p></div></div></div>';
 const upload=$("#video-upload");
 upload.onchange=async()=>{const files=[...upload.files],role=$("#upload-role").value;for(const file of files){const form=new FormData();form.append("file",file);form.append("role",role);try{toast("Checking "+file.name);project=await api("/api/projects/"+project.id+"/clips","POST",form);}catch(e){toast(e.message);}}render();};
 const importButton=$("#import-section");
 if(importButton)importButton.onclick=async()=>{
  const payload={role:$("#section-role").value,start:Number($("#section-start").value),duration:Number($("#section-duration").value)};
  if(payload.start+payload.duration>project.reference.duration+0.03){toast("That range exceeds the Reel duration");return;}
  importButton.disabled=true;
  try{project=await api("/api/projects/"+project.id+"/reference/segments","POST",payload);render();toast("Selected moment added to footage");}
  catch(e){toast(e.message);importButton.disabled=false;}
 };
 const startInput=$("#section-start");
 if(startInput)startInput.onchange=()=>{const vid=$(".reference-video");if(vid)vid.currentTime=Math.max(0,Number(startInput.value)||0);};
 const old=$("#reference-upload");
 if(old)old.onchange=async()=>{if(!old.files.length)return;const form=new FormData();form.append("file",old.files[0]);try{toast("Inspecting original Reel");project=await api("/api/projects/"+project.id+"/reference","POST",form);if(!project.reference.has_audio)audioMode="generated";else{audioMode="reference";audioLength=Math.max(8,Math.min(18,Math.floor(project.reference.audio_seconds)));}render();}catch(e){toast(e.message);}};
 $$(".clip-role").forEach(e=>e.onchange=async()=>{try{project=await api("/api/projects/"+project.id+"/clips/"+e.dataset.id,"PATCH",{role:e.value});render();}catch(err){toast(err.message)}});
 $$(".remove-clip").forEach(e=>e.onclick=async()=>{try{project=await api("/api/projects/"+project.id+"/clips/"+e.dataset.id,"DELETE");render();}catch(err){toast(err.message)}});
 $("#to-studio").onclick=()=>stageTo(3);
}
function reelCard(item,index){
 const exportUrl=project.exports[item.id].final||project.exports[item.id].preview;
 const source=project.clips[0]&&"/api/projects/"+project.id+"/clips/"+project.clips[0].id+"/media";
 const video=exportUrl?'<video controls playsinline preload="metadata" src="'+escape(exportUrl)+'"></video>':
 (source?'<video class="source" muted preload="metadata" playsinline src="'+source+'"></video>':'');
 const cover=exportUrl?'':'<div class="reel-overlay"><small>EASYVIDEO / 0'+(index+1)+'</small><strong>'+escape(item.beats[0])+'</strong><small>9:16 • ORIGINAL FOOTAGE</small></div>';
 const missing=[...new Set(item.roles)].filter(role=>!project.clips.some(c=>c.role===role));
 return '<article class="reel-card '+(chosen.has(item.id)?"selected":"")+'"><div class="reel-screen '+item.id+'">'+video+cover+'<span class="style-index">0'+(index+1)+'</span></div>'+
 '<div class="reel-description"><h3>'+escape(item.title)+'</h3><p>'+escape(item.subtitle)+'</p>'+
 '<label class="pick"><input class="reel-pick" type="checkbox" data-style="'+item.id+'" '+(chosen.has(item.id)?"checked":"")+'> Choose this Reel</label>'+
 (missing.length?'<div class="reel-warning">Uses substitute footage for '+missing.map(r=>escape(roles[r]||r)).join(", ")+'</div>':"")+
 '<details><summary>View creative & narration</summary><blockquote>'+escape(item.voiceover)+'</blockquote><small>'+escape(item.marketing_goal)+'</small></details>'+
 '<details class="search-assets"><summary>Instagram SEO & posting</summary><p>Searchable title, caption, alt text, and pinned comment</p>'+
 '<div class="seo-actions"><button class="caption-action" type="button" data-copy="caption" data-style="'+item.id+'">Caption</button>'+
 '<button class="caption-action" type="button" data-copy="cover_title" data-style="'+item.id+'">Cover title</button>'+
 '<button class="caption-action" type="button" data-copy="alt_text" data-style="'+item.id+'">Alt text</button>'+
 '<button class="caption-action" type="button" data-copy="pinned_comment" data-style="'+item.id+'">Pinned comment</button></div></details>'+
 (exportUrl?'<a class="download" download href="'+escape(exportUrl)+'">↓ Download '+(project.exports[item.id].final?"1080p":"draft")+'</a>':"")+
 '</div></article>';
}
function metricsUI(){
 const fields=[["views","Views"],["reach","Reach"],["avg_watch_seconds","Avg watch (sec)"],["shares","Shares"],["saves","Saves"],["enquiries","Enquiries"]];
 const entries=Object.entries(project.performance||{});
 return '<section class="results"><details><summary>Organic performance ↗</summary><p class="small-copy">Enter your published Reel results to compare real enquiries.</p>'+
 '<div class="field-grid"><div><label class="field-title">Reel</label><select class="input" id="metric-style">'+project.creatives.map(c=>'<option value="'+c.id+'">'+escape(c.title)+'</option>').join("")+'</select></div>'+
 '<div><label class="field-title">Instagram link</label><input id="metric-url" class="input" placeholder="Post URL"></div></div>'+
 '<div class="metric-grid">'+fields.map(([id,name])=>'<div><label for="m-'+id+'">'+name+'</label><input class="input" id="m-'+id+'" type="number" min="0" step="'+(id==="avg_watch_seconds"?"0.1":"1")+'" value="0"></div>').join("")+'</div>'+
 '<div class="btn-row"><button class="secondary" id="save-metrics">Save results</button></div>'+
 (entries.length?'<div class="mini-divider"></div>'+entries.map(([style,p])=>'<div class="metric-row"><strong>'+escape(style)+'</strong><span>'+p.enquiries+' enquiries</span><span>'+p.shares+' shares</span><span>'+p.avg_watch_seconds+'s avg watch</span></div>').join(""):"")+'</details></section>';
}
function fillMetrics(){
 const p=(project.performance||{})[$("#metric-style").value]||{};
 ["views","reach","avg_watch_seconds","shares","saves","enquiries"].forEach(k=>$("#m-"+k).value=p[k]??0);
 $("#metric-url").value=p.post_url||"";
}
function showStudio(){
 const busy=["queued","running"].includes(project.job.status);
 const ref=project.reference;
 const allowReference=!!ref&&!!ref.has_audio&&ref.audio_seconds>=8;
 const previews=styleIds.every(id=>!!project.exports[id].preview);
 const list=[...chosen],canFinal=list.length>0&&list.every(id=>project.exports[id].preview);
 $("#view").innerHTML=head("03","Reel lab","The edit makes the difference.","Six distinct edits. Choose the three worth publishing.")+
 '<div class="panel"><div class="picker-row"><div><h2 class="panel-title">Soundtrack</h2><div class="voice-switch">'+
 '<button type="button" data-audio="generated" class="'+(audioMode==="generated"?"active":"")+'">AI / offline voiceover</button>'+
 '<button type="button" data-audio="reference" class="'+(audioMode==="reference"?"active":"")+'" '+(!allowReference?"disabled":"")+'>Original Reel audio</button>'+
 '<button type="button" data-audio="uploaded" class="'+(audioMode==="uploaded"?"active":"")+'">My narration</button></div></div>'+
 '<div><span class="stat-pill">'+(audioMode==="reference"?"Existing audio":"Offline voice")+'</span></div></div>'+
 (audioMode==="generated"?'<div class="voice-provider"><label class="field-title" for="voice-provider">Voice engine</label><select id="voice-provider" class="input">'+
 [{id:"auto",label:"Auto • best available"},...(health?.voices||[]).map(id=>({id,label:id==="voicestudio"?"VoiceStudio • local AI":id==="piper"?"Piper • offline neural":id==="sapi"?"Windows voice • basic":id}))].map(x=>'<option value="'+x.id+'" '+(voiceProvider===x.id?"selected":"")+'>'+escape(x.label)+'</option>').join("")+
 '</select><p class="help">VoiceStudio runs separately on this PC. Choose a lightweight model for 8 GB RAM.</p></div>':'')+
 (audioMode==="uploaded"?'<div class="upload-area" style="margin-top:15px"><strong>Upload your voiceover</strong><p>Recording or licensed generated speech</p><label class="secondary" for="narration-upload">Choose audio ↑</label><input class="file-hidden" id="narration-upload" type="file" accept="audio/*,.m4a,.wav,.mp3"></div>'+
 (project.narration?'<audio class="reference-audio" controls src="'+escape(project.narration.audio_url)+'"></audio><p class="help">'+escape(project.narration.filename)+' · '+project.narration.duration.toFixed(1)+'s</p>':''):'' )+
 (audioMode==="reference"?'<div class="ranges"><label>Start <input class="input" id="audio-start" type="number" min="0" max="'+Math.max(0,ref.audio_seconds-8).toFixed(1)+'" step="0.5" value="'+audioStart+'"></label>'+
 '<label>Seconds <input class="input" id="audio-length" type="number" min="8" max="90" step="0.5" value="'+audioLength+'"></label>'+
 '<span class="help">'+ref.audio_seconds.toFixed(1)+'s available</span></div>'+
 '<p class="help">The complete original audio mix is used; background music is not separated from speech.</p>':"")+'</div>'+
 (busy?'<div class="progress"><strong>Rendering on this computer</strong><span id="live-progress">'+escape(project.job.message)+'</span></div>':project.job.status==="error"?'<div class="flag">'+escape(project.job.message)+'</div>':"")+
 '<div class="reel-grid">'+project.creatives.map(reelCard).join("")+'</div>'+
 '<div class="btn-row"><button class="primary" id="generate-five" '+(busy?"disabled":"")+'>'+(previews?"↻ Regenerate six":"✦ Generate six drafts")+'</button>'+
 '<button class="secondary" id="final-export" '+(!canFinal||busy?"disabled":"")+'>Export selected · '+list.length+'/3 →</button></div>'+
 '<p class="footnote">Preview at 540p · Final export at 1080p. Three choices maximum.</p>'+
 metricsUI();
 $$("[data-audio]").forEach(b=>b.onclick=()=>{if(b.disabled)return;audioMode=b.dataset.audio;render();});
 const voiceSelect=$("#voice-provider");
 if(voiceSelect)voiceSelect.onchange=()=>voiceProvider=voiceSelect.value;
 const uploadNarration=$("#narration-upload");
 if(uploadNarration)uploadNarration.onchange=async()=>{
    if(!uploadNarration.files.length)return;
    const form=new FormData();form.append("file",uploadNarration.files[0]);
    try{project=await api("/api/projects/"+project.id+"/narration","POST",form);render();toast("Narration uploaded");}
    catch(e){toast(e.message);}
 };
 if(audioMode==="reference"){
   $("#audio-start").onchange=e=>audioStart=Math.max(0,Number(e.target.value)||0);
   $("#audio-length").onchange=e=>audioLength=Math.max(8,Number(e.target.value)||18);
 }
 $$(".reel-pick").forEach(cb=>cb.onchange=async()=>{
  if(cb.checked){if(chosen.size>=3){cb.checked=false;toast("Choose up to three");return;}chosen.add(cb.dataset.style);}
  else chosen.delete(cb.dataset.style);
  try{project=await api("/api/projects/"+project.id+"/selection","POST",{styles:[...chosen]});render();}
  catch(e){toast(e.message);}
 });
 $$("[data-copy]").forEach(b=>b.onclick=async()=>{
  const asset=project.social_pack?.[b.dataset.style];
  if(!asset)return;
  try{await navigator.clipboard.writeText(asset[b.dataset.copy]||"");toast("Copied. Verify all details before publishing.");}
  catch{toast("Clipboard unavailable");}
 });
 $("#generate-five").onclick=()=>beginRender(styleIds,"preview");
 $("#final-export").onclick=()=>beginRender(list,"final");
 $("#metric-style").onchange=fillMetrics;fillMetrics();
 $("#save-metrics").onclick=async()=>{
  const style=$("#metric-style").value;const data={post_url:$("#metric-url").value};
  ["views","reach","avg_watch_seconds","shares","saves","enquiries"].forEach(k=>data[k]=Number($("#m-"+k).value||0));
  try{project=await api("/api/projects/"+project.id+"/performance/"+style,"PUT",data);render();$("#metric-style").value=style;fillMetrics();toast("Results saved locally");}catch(e){toast(e.message);}
 };
 if(busy)poll();else stopPoll();
}
async function beginRender(styles,resolution){
 if(audioMode==="uploaded"&&!project.narration){toast("Upload a narration track first");return;}
 if(audioMode==="reference"){
  const limit=project.reference?.audio_seconds||0;
  if(audioStart+audioLength>limit+0.1){toast("Audio range exceeds original Reel duration");return;}
 }
 try{
  await api("/api/projects/"+project.id+"/renders","POST",{styles,resolution,
   audio_source:audioMode,reference_start:audioStart,reference_seconds:audioLength,voice_engine:voiceProvider});
  project=await api("/api/projects/"+project.id);
  toast("Started the local render queue");
  render();
 }catch(e){toast(e.message);}
}
function poll(){
 if(timer)return;
 timer=setInterval(async()=>{
  if(!project||stage!==3){stopPoll();return;}
  try{
   const updated=await api("/api/projects/"+project.id);
   const before=project.job.status;
   project=updated;
   if(["ready","error"].includes(updated.job.status)){stopPoll();render();toast(updated.job.status==="ready"?"Your videos are ready":"Render failed");}
   else {const progress=$("#live-progress");if(progress)progress.textContent=updated.job.message;}
  }catch(e){console.warn("Status check:",e.message);}
 },3000);
}
function stopPoll(){if(timer){clearInterval(timer);timer=null;}}
function render(){
 if(project)$("#project-state").textContent=project.brief.product.toUpperCase().slice(0,26);
 if(stage===1)showDirection();else if(stage===2)showFootage();else showStudio();
}
$$(".nav-item").forEach(b=>b.onclick=()=>stageTo(Number(b.dataset.stage)));
$("#new-project").onclick=newProject;
(async function init(){
 try{health=await api("/api/health");$("#engine-state").textContent=(health.ffmpeg?"Editor ready":"FFmpeg missing")+" · "+(health.voices.length?"Voice available":"Voice model needed");}
 catch{ $("#engine-state").textContent="Local server unavailable";}
 try{
  const history=await api("/api/projects");
  if(history.length){
   project=await api("/api/projects/"+history[0].id);
   mode=project.brief.source_mode||"new";
   audioMode=mode==="remix"&&project.reference?.has_audio?"reference":"generated";
   if(project.reference)audioLength=Math.max(8,Math.min(18,Math.floor(project.reference.audio_seconds)));
   chosen=new Set(project.selected||[]);
   stageTo(2);return;
  }
 }catch(e){console.warn(e.message);}
 render();
})();
})();