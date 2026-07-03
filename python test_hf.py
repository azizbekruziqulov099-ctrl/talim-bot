"""
HF token test — Railway da ishga tushiring
python test_hf.py
"""
import asyncio, aiohttp, os

HF_TOKEN = os.getenv("HF_TOKEN","")

async def test():
    if not HF_TOKEN:
        print("❌ HF_TOKEN topilmadi!")
        return
    
    prompt = "Educational illustration of human skeleton, labeled bones, white background, medical diagram, professional"
    url = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
    headers = {"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"}
    
    print(f"🔑 Token: {HF_TOKEN[:10]}...")
    print(f"📝 Prompt: {prompt}")
    print("⏳ Rasm yaratilmoqda (30-60 sekund)...")
    
    async with aiohttp.ClientSession() as s:
        async with s.post(url, json={"inputs": prompt}, headers=headers,
                         timeout=aiohttp.ClientTimeout(total=90)) as r:
            print(f"Status: {r.status}")
            if r.status == 200:
                data = await r.read()
                with open("test_rasm.png","wb") as f:
                    f.write(data)
                print(f"✅ Rasm yaratildi! {len(data)//1024}KB")
            else:
                txt = await r.text()
                print(f"❌ Xato: {txt[:200]}")

asyncio.run(test())
