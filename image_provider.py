import os, uuid
from pathlib import Path
from typing import Any, Optional
import httpx
OUTPUT_DIR=Path(os.getenv("ARIA_OUTPUT_DIR","outputs")); OUTPUT_DIR.mkdir(parents=True,exist_ok=True)
HF_TOKEN=os.getenv("HF_TOKEN") or os.getenv("HF_TOKEN_1") or os.getenv("HUGGINGFACEHUB_API_TOKEN")
REPLICATE_TOKEN=os.getenv("REPLICATE_API_TOKEN")
HF_IMAGE_MODEL=os.getenv("HF_IMAGE_MODEL","black-forest-labs/FLUX.1-schnell")
REPLICATE_IMAGE_MODEL=os.getenv("REPLICATE_IMAGE_MODEL","")
def _save(b,s):
 p=OUTPUT_DIR/f"image-{uuid.uuid4().hex}{s}"; p.write_bytes(b); return str(p)
def huggingface_flux(prompt:str,**kwargs:Any)->Optional[str]:
 if not HF_TOKEN:return None
 with httpx.Client(timeout=180,follow_redirects=True) as c:
  r=c.post(f"https://api-inference.huggingface.co/models/{HF_IMAGE_MODEL}",headers={"Authorization":f"Bearer {HF_TOKEN}"},json={"inputs":prompt}); r.raise_for_status()
  if not r.headers.get("content-type","").startswith("image/"): raise RuntimeError("Hugging Face returned non-image content")
  return _save(r.content,".png")
def replicate_image(prompt:str,**kwargs:Any)->Optional[str]:
 if not REPLICATE_TOKEN or not REPLICATE_IMAGE_MODEL:return None
 h={"Authorization":f"Bearer {REPLICATE_TOKEN}","Content-Type":"application/json"}
 with httpx.Client(timeout=180,follow_redirects=True) as c:
  r=c.post("https://api.replicate.com/v1/predictions",headers=h,json={"version":REPLICATE_IMAGE_MODEL,"input":{"prompt":prompt}}); r.raise_for_status(); d=r.json(); out=d.get("output")
  if not out: raise RuntimeError(f"Replicate did not return an output: {d}")
  u=out[0] if isinstance(out,list) else out
  if not isinstance(u,str): raise RuntimeError("Unsupported Replicate image output format")
  m=c.get(u); m.raise_for_status(); return _save(m.content,".png")
def local_stable_diffusion(prompt:str,**kwargs:Any)->Optional[str]: return None
IMAGE_PROVIDERS={"huggingface_flux":huggingface_flux,"replicate_image":replicate_image,"local_stable_diffusion":local_stable_diffusion}
