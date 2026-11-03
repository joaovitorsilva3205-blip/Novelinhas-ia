import os, json, urllib.request

PROMPT = """
Você é roteirista de novelinhas verticais com frutas humanizadas 3D.
Transforme a história em exatamente 6 cenas de cerca de 10 segundos (60s total).
Mantenha consistência dos personagens em todas as cenas: fruta, cores, roupas,
acessórios e traços. Estética: animação 3D cinematográfica original, luz dramática,
expressões claras, composição vertical 9:16. Português brasileiro.
Não imite franquias nem personagens protegidos.
Retorne somente JSON válido:
{
 "title":"", "logline":"",
 "characters":[{"name":"","fruit":"","appearance":"","outfit":"","voice":"female ou male"}],
 "scenes":[
  {"number":1,"duration_seconds":10,"visual_prompt":"",
   "action":"","dialogue":[{"character":"","voice":"female ou male","text":""}],
   "sound_design":""}
 ],
 "ending_hook":""
}
"""

def create_production_plan(script):
    provider = os.getenv("PLANNER_PROVIDER", "ollama").lower()
    if provider == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        r = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            response_format={"type":"json_object"},
            messages=[{"role":"system","content":PROMPT},
                      {"role":"user","content":script}],
            temperature=0.8
        )
        return json.loads(r.choices[0].message.content)

    # Ollama local: gratuito, mas exige computador com Ollama instalado e modelo baixado.
    host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    body = json.dumps({
        "model": model, "stream": False, "format": "json",
        "messages": [{"role":"system","content":PROMPT},
                     {"role":"user","content":script}]
    }).encode()
    req = urllib.request.Request(
        host.rstrip("/") + "/api/chat", data=body,
        headers={"Content-Type":"application/json"}
    )
    with urllib.request.urlopen(req, timeout=600) as response:
        data = json.loads(response.read().decode())
    return json.loads(data["message"]["content"])
