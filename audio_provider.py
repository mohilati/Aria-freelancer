import os, uuid
from pathlib import Path
from typing import Any, Optional
import httpx
OUTPUT_DIR=Path(os.getenv("ARIA_OUTPUT_DIR","outputs")); OUTPUT_DIR.mkdir(parents=True,exist_ok=True)
HF_TOKEN=os.getenv("HF_TOKEN") or os.getenv("HF_TOKEN_1") or os.getenv("HUGGINGFACEHUB_API_TOKEN")
ELEVENLABS_API_KEY=os.getenv("ELEVENLABS_API_KEY"); GEMINI_API_KEY=os.getenv("GEMINI_API_KEY")
HF_TTS_MODEL=os.getenv("HF_TTS_MODEL","espnet/kan-bayashi_ljspeech_vits"); HF_MUSIC_MODEL=os.getenv("HF_MUSIC_MODEL","facebook/musicgen-small")
ELEVENLABS_VOICE_ID=os.getenv("ELEVENLABS_VOICE_ID",""); ELEVENLABS_MODEL_ID=os.getenv("ELEVENLABS_MODEL_ID","eleven_multilingual_v2")
LYRIA_MODEL=os.getenv("LYRIA_MODEL","lyria-3.5")
def _save(b,s):
 p=OUTPUT_DIR/f"audio-{uuid.uuid4().hex}{s}"; p.write_bytes(b); return str(p)
def elevenlabs_tts(text:str,**kwargs:Any)->Optional[str]:
 if not ELEVENLABS_API_KEY or not ELEVENLABS_VOICE_ID:return None
 with httpx.Client(timeout=180,follow_redirects=True) as c:
  r=c.post(f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}",headers={"xi-api-key":ELEVENLABS_API_KEY,"Content-Type":"application/json","Accept":"audio/mpeg"},json={"text":text,"model_id":ELEVENLABS_MODEL_ID}); r.raise_for_status(); return _save(r.content,".mp3")
def huggingface_tts(text:str,**kwargs:Any)->Optional[str]:
 if not HF_TOKEN:return None
 with httpx.Client(timeout=180,follow_redirects=True) as c:
  r=c.post(f"https://api-inference.huggingface.co/models/{HF_TTS_MODEL}",headers={"Authorization":f"Bearer {HF_TOKEN}"},json={"inputs":text}); r.raise_for_status(); return _save(r.content,".wav")
def lyria_music(prompt:str,**kwargs:Any)->Optional[str]: return None
def musicgen_local(prompt:str,**kwargs:Any)->Optional[str]: return None
def huggingface_musicgen(prompt:str,**kwargs:Any)->Optional[str]:
 if not HF_TOKEN:return None
 with httpx.Client(timeout=300,follow_redirects=True) as c:
  r=c.post(f"https://api-inference.huggingface.co/models/{HF_MUSIC_MODEL}",headers={"Authorization":f"Bearer {HF_TOKEN}"},json={"inputs":prompt}); r.raise_for_status(); return _save(r.content,".wav")
TTS_PROVIDERS={"elevenlabs_tts":elevenlabs_tts,"huggingface_tts":huggingface_tts}
MUSIC_PROVIDERS={"lyria_music":lyria_music,"huggingface_musicgen":huggingface_musicgen,"musicgen_local":musicgen_local}
