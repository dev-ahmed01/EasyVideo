"""Director v2 — lightweight CPU renderer for marketing-led vertical Reels.

Uses real uploaded video, Pillow for crisp safe-area graphics, and FFmpeg for
sequential edits. Each shot role comes from the uploader; no fake vision claims.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import array, io, json, math, os, random, subprocess, wave

from PIL import Image, ImageDraw, ImageFont

from .creative import creatives

STYLE_SHOTS = {
 "stomp": (["hero","detail","hero","workspace","function","inventory","detail","hero","proof"],[1.2,1.2,1.4,1.3,1.25,1.5,1.15,1.3,1.5]),
 "cinematic": (["hero","detail","hero","workspace","detail","inventory","hero"],[2.6,2.4,2.8,2.4,2.3,2.4,2.8]),
 "features": (["hero","function","detail","hero","workspace","detail","hero","proof"],[2.1,2.0,2.1,2.0,2.3,2.0,2.0,2.0]),
 "business": (["workspace","inventory","hero","inventory","workspace","hero","proof","hero"],[2.2,2.1,2.0,2.1,2.0,2.2,2.0,2.1]),
 "social": (["hero","detail","workspace","hero","detail","inventory","hero","proof","hero"],[1.5,1.25,1.45,1.35,1.3,1.55,1.3,1.25,1.7]),
 "voice_story": (["hero","detail","workspace","hero","inventory","detail","hero","proof"],[2.6,2.0,2.3,2.3,2.3,1.8,2.3,2.2]),
}
PALETTE = {
 "stomp": ("#D4F978", 56),
 "cinematic": ("#F1E4D1", 43),
 "features": ("#9EE6DB", 44),
 "business": ("#F4C896", 44),
 "social": ("#EAC6F8", 49),
 "voice_story": ("#DCF5CF", 45),
}
def run(args: list[str], timeout: int = 180, binary: bool = False):
    p=subprocess.run(args,capture_output=True,text=not binary,timeout=timeout)
    if p.returncode:
        err=p.stderr.decode("utf-8","replace") if binary else p.stderr
        raise RuntimeError("Media processing failed: "+err[-1300:])
    return p.stdout

def seconds(path: Path) -> float:
    return float(run(["ffprobe","-v","error","-show_entries","format=duration","-of",
                      "default=noprint_wrappers=1:nokey=1",str(path)],25).strip())

def _font(size: int, bold=True):
    env=os.environ.get("EASYVIDEO_FONT")
    candidates=([env] if env else [])+(
        ["C:/Windows/Fonts/arialbd.ttf","C:/Windows/Fonts/segoeuib.ttf"]
        if bold else ["C:/Windows/Fonts/arial.ttf","C:/Windows/Fonts/segoeui.ttf"]
    )+[
      "/usr/share/fonts/truetype/lato/Lato-Black.ttf" if bold else "/usr/share/fonts/truetype/lato/Lato-Medium.ttf",
      "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return ImageFont.truetype(candidate,size)
    return ImageFont.load_default()

def _graphic(output:Path, title:str, style:str, width:int, height:int):
    canvas=Image.new("RGBA",(width,height),(0,0,0,0))
    if not title:
        canvas.save(output);return
    draw=ImageDraw.Draw(canvas)
    accent,raw_size=PALETTE[style]
    text_font=_font(max(24,round(raw_size*width/540)))
    small_font=_font(max(10,round(12*width/540)),False)
    max_width=round(width*.78)
    lines=[];line=""
    for word in title.strip().upper().split():
        trial=(line+" "+word).strip()
        if line and draw.textbbox((0,0),trial,font=text_font)[2]>max_width:
            lines.append(line);line=word
        else:line=trial
    if line:lines.append(line)
    lines=lines[:3]
    x=int(width*.095);y=int(height*.125)
    leading=int(raw_size*width/540*1.14)
    text_width=max((draw.textbbox((0,0),s,font=text_font)[2] for s in lines),default=0)
    pad=int(width*.033)
    edge=min(width-int(width*.045),x+text_width+pad)
    draw.rounded_rectangle((x-pad,y-pad,edge,y+len(lines)*leading+pad),radius=12,fill=(9,24,19,222))
    if style=="stomp":
        draw.rectangle((x-pad,y-pad,x-pad+max(4,int(width*.009)),y+len(lines)*leading+pad),fill=accent)
    for i,t in enumerate(lines):
        draw.text((x,y+i*leading),t,font=text_font,fill=accent)
    tag_height=int(height*.043);tag_y=int(height*.049)
    draw.rounded_rectangle((x-pad,tag_y-5,x+int(width*.54),tag_y+tag_height),
                           radius=7,fill=(8,25,20,198))
    draw.text((x,tag_y+1),"FURNIHUB / OFFICE SEATING",font=small_font,fill="#EBF8E9")
    canvas.save(output)

def _content_area(src:Path, timestamp:float) -> tuple[int,int,int,int]:
    # Detect black bars baked into footage. This is media geometry, not scene recognition.
    try:
        raw=run(["ffmpeg","-v","error","-ss",str(timestamp),"-i",str(src),
                 "-frames:v","1","-f","image2pipe","-vcodec","png","-"],25,True)
        img=Image.open(io.BytesIO(raw)).convert("L");w,h=img.size
        sample=img.crop((int(w*.2),0,int(w*.8),h)).resize((28,h))
        rawdata=sample.tobytes()
        rows=[sum(rawdata[i*28:(i+1)*28])/28 for i in range(h)]
        seen=[i for i,val in enumerate(rows) if val>11]
        if not seen:return 0,0,w,h
        top=max(0,seen[0]-5);bottom=min(h,seen[-1]+6)
        if top<h*.07 and bottom>h*.92:return 0,0,w,h
        if bottom-top<h*.35:return 0,0,w,h
        return 0,top,w,bottom-top
    except Exception:
        return 0,0,720,1280

def _cut(src:Path,dst:Path,png:Path,start:float,duration:float,width:int,height:int):
    x,y,w,h=_content_area(src,start+min(duration*.5,1))
    filt=(
      f"[0:v]fps=24,crop={w}:{h}:{x}:{y},split=2[bg0][fg0];"
      f"[bg0]scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},"
      "boxblur=9:1,eq=brightness=-0.14:saturation=0.84[bg];"
      f"[fg0]scale={width}:{int(height*.87)}:force_original_aspect_ratio=decrease,setsar=1[fg];"
      "[bg][fg]overlay=(W-w)/2:(H-h)/2:format=auto[plate];"
      "[1:v]format=rgba,fade=t=in:st=0:d=0.13:alpha=1[card];"
      "[plate][card]overlay=0:0:format=auto,format=yuv420p[out]"
    )
    run(["ffmpeg","-y","-v","error","-ss",str(round(start,3)),"-i",str(src),
         "-loop","1","-framerate","24","-i",str(png),"-t",str(duration),
         "-filter_complex",filt,"-map","[out]","-an",
         "-c:v","libx264","-preset","ultrafast","-crf","25","-threads","2",
         "-pix_fmt","yuv420p",str(dst)],240)

def _percussion(output:Path, durations:list[float], style:str):
    rate=16000;total=sum(durations);n=max(1,math.ceil(total*rate))
    samples=array.array("h",[0])*n;randomizer=random.Random(42)
    strength={"stomp":0.40,"social":0.2}.get(style,0.08)
    offsets=[0.0];elapsed=0.
    for item in durations[:-1]:
        elapsed+=item;offsets.append(elapsed)
    for offset in offsets:
        base=round(offset*rate)
        for i in range(min(round(rate*.13),n-base)):
            t=i/rate
            v=(math.sin(2*math.pi*(85-25*t)*t)*math.exp(-23*t)
               +.11*(2*randomizer.random()-1)*math.exp(-34*t))*strength
            samples[base+i]=max(-32768,min(32767,samples[base+i]+round(v*32767)))
    with wave.open(str(output),"wb") as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate)
        f.writeframes(samples.tobytes())

def _choose(role, clips, used, index, style):
    options=[x for x in clips if x["role"]==role and x.get("duration",0)>=1]
    if not options: options=[x for x in clips if x["role"]=="hero"] or clips
    if not options:raise RuntimeError("No usable clips")
    n=used.get(role,0);used[role]=n+1
    return options[(n+(index if style=="social" else 0))%len(options)],n

def render_directed(brief,clips,style:str,project_dir:Path,resolution="preview",
                    voice_engine="auto",progress=None,reference_video:Path|None=None,
                    reference_start=0,reference_seconds=18,voiceover_file:Path|None=None,
                    synthesize_fn=None):
    if style not in STYLE_SHOTS:raise ValueError("Unknown creative style")
    if not clips:raise ValueError("Upload video clips before rendering")
    if resolution not in ("preview","final"):raise ValueError("Invalid resolution")
    width,height=(540,960) if resolution=="preview" else (1080,1920)
    work=project_dir/"work"/f"{style}_{resolution}"
    work.mkdir(parents=True,exist_ok=True)
    plan=next(p for p in creatives(brief) if p["id"]==style)
    roles,durations=STYLE_SHOTS[style]
    if style=="voice_story" and reference_video is None and voiceover_file is None:
        # Voiceover-first edit should never cut off a longer narration.
        pass
    voice=work/"narration.wav"
    engine=None
    if voiceover_file is not None:
        voice=voiceover_file
        engine="uploaded narration"
    elif reference_video is not None:
        if progress:progress("Extracting original Reel audio")
        run(["ffmpeg","-y","-v","error","-ss",str(reference_start),
             "-i",str(reference_video),"-t",str(reference_seconds),
             "-map","0:a:0","-vn","-ac","1","-ar","16000","-c:a","pcm_s16le",str(voice)],120)
        engine="original Reel audio"
    else:
        if synthesize_fn is None:raise RuntimeError("Offline voice engine not configured")
        if progress:progress("Generating an offline voiceover")
        engine=synthesize_fn(plan["voiceover"],voice,preferred=voice_engine)
    voice_duration=seconds(voice)
    durations=list(durations)
    total=sum(durations)
    # A spoken story determines timing; cuts flex to allow full narration.
    if voice_duration+0.6>total:
        factor=(voice_duration+0.6)/total
        durations=[round(d*factor,3) for d in durations]
    used={};pieces=[]
    title_positions={0:0,2:1,4:2,len(durations)-1:3}
    for index,(role,duration) in enumerate(zip(roles,durations)):
        clip,count=_choose(role,clips,used,index,style)
        src=project_dir/"clips"/clip["stored_name"]
        if not src.is_file():raise RuntimeError("Missing original clip: "+clip["filename"])
        # Move through longer clips, reusing time points instead of freezing four long blocks.
        room=max(0,clip["duration"]-duration)
        frac=((index*0.17+count*.28+(0.12 if style=="cinematic" else 0))%0.86)
        start=round(room*frac,2)
        title=plan["beats"][title_positions[index]] if index in title_positions else ""
        png=work/f"graphic_{index:02d}.png";_graphic(png,title,style,width,height)
        scene=work/f"scene_{index:02d}.mp4"
        _cut(src,scene,png,start,duration,width,height);pieces.append(scene)
        if progress:progress(f"{plan['title']}: cut {index+1}/{len(durations)}")
    manifest=work/"scene_list.txt"
    manifest.write_text("\n".join("file '"+str(p.resolve()).replace("'","'\\''")+"'" for p in pieces))
    combined=work/"picture.mp4"
    run(["ffmpeg","-y","-v","error","-f","concat","-safe","0","-i",str(manifest),"-c","copy",str(combined)],120)
    accents=work/"accents.wav";_percussion(accents,durations,style)
    outdir=project_dir/"exports";outdir.mkdir(parents=True,exist_ok=True)
    output=outdir/f"{style}_{resolution}.mp4"
    filt=("[1:a]volume=1.14,highpass=f=75,acompressor=threshold=-22dB:"
          "ratio=2:attack=8:release=110[vo];[2:a]volume=0.38[fx];"
          "[vo][fx]amix=inputs=2:duration=longest:dropout_transition=0[a]")
    run(["ffmpeg","-y","-v","error","-i",str(combined),"-i",str(voice),"-i",str(accents),
         "-filter_complex",filt,"-map","0:v:0","-map","[a]","-c:v","copy",
         "-c:a","aac","-b:a","128k","-t",str(sum(durations)),
         "-movflags","+faststart",str(output)],120)
    if progress:progress(f"{plan['title']} finished with {engine}")
    return output
