"""Opt-in, loopback-only VoiceStudio speech provider.

Integrates VoiceStudio via its published /v1/audio/speech API without copying
its AGPL application code. VoiceStudio must already be running locally.
No external HTTP origins, redirects or proxies are accepted.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import socket
import urllib.error
import urllib.request
from urllib.parse import urlsplit

LOCAL_HOSTS={"localhost","127.0.0.1","::1"}
MAX_AUDIO_BYTES=24*1024*1024

class VoiceStudioError(RuntimeError):
    pass

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise VoiceStudioError("VoiceStudio redirect rejected; only loopback is allowed")

def _base_url() -> str:
    configured=os.getenv("EASYVIDEO_VOICESTUDIO_URL","http://127.0.0.1:3900").rstrip("/")
    parsed=urlsplit(configured)
    if (parsed.scheme!="http" or parsed.hostname not in LOCAL_HOSTS or
        parsed.username or parsed.password or parsed.query or parsed.fragment or
        (parsed.path and parsed.path!="/") or not parsed.port):
        raise VoiceStudioError("VoiceStudio must use a local http://127.0.0.1:PORT URL")
    return configured

def _call(path:str, data:bytes|None=None, timeout:float=3.0) -> bytes:
    url=_base_url()+path
    req=urllib.request.Request(
        url, data=data,
        headers={"Content-Type":"application/json","Accept":"audio/wav,application/json"},
        method="POST" if data is not None else "GET",
    )
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),_NoRedirect())
    try:
        with opener.open(req, timeout=timeout) as response:
            body=response.read(MAX_AUDIO_BYTES+1)
            if len(body)>MAX_AUDIO_BYTES:
                raise VoiceStudioError("Speech response exceeds local maximum")
            return body
    except (urllib.error.URLError, socket.timeout, TimeoutError) as e:
        raise VoiceStudioError("VoiceStudio isn't available locally. Start it, then retry.") from e

def available() -> bool:
    try:
        data=json.loads(_call("/.well-known/voicestudio-speech",timeout=0.65))
        return isinstance(data,dict)
    except (ValueError,VoiceStudioError, OSError):
        return False

def synthesize(text:str, output:Path) -> str:
    model=os.getenv("EASYVIDEO_VOICESTUDIO_MODEL","tts-1").strip() or "tts-1"
    voice=os.getenv("EASYVIDEO_VOICESTUDIO_VOICE","alloy").strip() or "alloy"
    request=json.dumps({
        "model":model,"voice":voice,"input":text[:1200],
        "response_format":"wav","speed":1.0
    },ensure_ascii=False).encode("utf-8")
    audio=_call("/v1/audio/speech",data=request,timeout=180)
    if not audio.startswith(b"RIFF") or audio[8:12]!=b"WAVE":
        raise VoiceStudioError("VoiceStudio did not return WAV audio. Check model and voice profile.")
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_bytes(audio)
    return "voicestudio"
