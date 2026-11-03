import os
import json
import urllib.request


PROMPT = """
Você é roteirista de novelinhas verticais com frutas humanizadas 3D.
Transforme a história em exatamente 6 cenas de 10 segundos cada (60s total). Cada cena será gerada como clipe independente no Google Flow. Crie prompts visuais autossuficientes e mantenha continuidade visual entre cenas.
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
   "sound_design":"", "flow_prompt":"Prompt completo para gerar clipe de 10 segundos no Google Flow, com ação contínua, movimento de câmera e áudio/dialogo. Repetir descrição dos personagens para consistência."}
 ],
 "ending_hook":"", "flow_global_style":"Descrição curta do estilo visual e regras de continuidade para todas as cenas."
}
"""


def _cloudflare_chat(script):
    account_id = os.environ["CLOUDFLARE_ACCOUNT_ID"].strip()
    token = os.environ["CLOUDFLARE_API_TOKEN"].strip()
    model = os.getenv("CLOUDFLARE_TEXT_MODEL", "@cf/meta/llama-3.1-8b-instruct")
    url = (
        "https://api.cloudflare.com/client/v4/accounts/"
        + account_id
        + "/ai/run/"
        + model
    )
    body = json.dumps({
        "messages": [
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": script},
        ],
        "max_tokens": 3500,
        "temperature": 0.7,
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as response:
        payload = json.loads(response.read().decode("utf-8"))
    result = payload.get("result") or {}
    text = result.get("response") or result.get("output")
    if not text:
        raise RuntimeError("Cloudflare não retornou um roteiro.")

    # Alguns modelos da Cloudflare já devolvem JSON estruturado como dict.
    if isinstance(text, dict):
        if "title" in text and "scenes" in text:
            return text
        for key in ("response", "output", "content"):
            if isinstance(text.get(key), str):
                text = text[key]
                break
        else:
            raise RuntimeError(
                "Cloudflare retornou um objeto JSON em formato inesperado."
            )

    if not isinstance(text, str):
        raise RuntimeError("Cloudflare retornou um formato de roteiro inválido.")

    # Accept a JSON object even if the model wraps it in Markdown fences.
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end <= start:
        raise RuntimeError("O modelo não retornou JSON válido.")
    return json.loads(cleaned[start:end + 1])


def create_production_plan(script):
    provider = os.getenv("PLANNER_PROVIDER", "cloudflare").lower()
    if provider == "cloudflare":
        return _cloudflare_chat(script)
    if provider == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        r = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": PROMPT},
                {"role": "user", "content": script},
            ],
            temperature=0.8,
        )
        return json.loads(r.choices[0].message.content)

    # Ollama local: requires a separate machine running Ollama.
    host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    body = json.dumps({
        "model": model, "stream": False, "format": "json",
        "messages": [
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": script},
        ],
    }).encode()
    req = urllib.request.Request(
        host.rstrip("/") + "/api/chat", data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=600) as response:
        data = json.loads(response.read().decode())
    return json.loads(data["message"]["content"])
