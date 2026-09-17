import os, uuid
from pathlib import Path
from typing import Any, Optional
import httpx
OUTPUT_DIR=Path(os.getenv("ARIA_OUTPUT_DIR","outputs")); OUTPUT_DIR.mkdir(parents=True,exist_ok=True)
HF_TOKEN=os.getenv("HF_TOKEN") or os.getenv("HF_TOKEN_1") or os.getenv("HUGGINGFACEHUB_API_TOKEN")
REPLICATE_TOKEN=os.getenv("REPLICATE_API_TOKEN"); FAL_KEY=os.getenv("FAL_KEY")
HF_VIDEO_MODEL=os.getenv("HF_VIDEO_MODEL","Wan-AI/Wan2.1-T2V-1.3B"); REPLICATE_VIDEO_MODEL=os.getenv("REPLICATE_VIDEO_MODEL",""); FAL_VIDEO_MODEL=os.getenv("FAL_VIDEO_MODEL","")
def _save(b,s=".mp4"):
 p=OUTPUT_DIR/f"video-{uuid.uuid4().hex}{s}"; p.write_bytes(b); return str(p)
def huggingface_video(prompt:str,**kwargs:Any)->Optional[str]:
 if not HF_TOKEN or not HF_VIDEO_MODEL:return None
 with httpx.Client(timeout=600,follow_redirects=True) as c:
  r=c.post(f"https://api-inference.huggingface.co/models/{HF_VIDEO_MODEL}",headers={"Authorization":f"Bearer {HF_TOKEN}"},json={"inputs":prompt}); r.raise_for_status(); return _save(r.content)
def replicate_video(prompt:str,**kwargs:Any)->Optional[str]:
 if not REPLICATE_TOKEN or not REPLICATE_VIDEO_MODEL:return None
 h={"Authorization":f"Bearer {REPLICATE_TOKEN}","Content-Type":"application/json"}
 with httpx.Client(timeout=900,follow_redirects=True) as c:
  r=c.post("https://api.replicate.com/v1/predictions",headers=h,json={"version":REPLICATE_VIDEO_MODEL,"input":{"prompt":prompt}}); r.raise_for_status(); d=r.json(); out=d.get("output")
  if not out: raise RuntimeError(f"Replicate did not return an output: {d}")
  u=out[0] if isinstance(out,list) else out
  m=c.get(u); m.raise_for_status(); return _save(m.content)
def fal_video(prompt:str,**kwargs:Any)->Optional[str]: return None
VIDEO_PROVIDERS={"huggingface_video":huggingface_video,"replicate_video":replicate_video,"fal_video":fal_video}
