import base64
import hashlib
import json
import os
import urllib.error
import urllib.request
from pathlib import Path


def _character_bible(plan):
    rows = []
    for character in plan.get("characters", []):
        rows.append(
            f"{character.get('name', 'Personagem')}: fruta {character.get('fruit', '')}; "
            f"aparência {character.get('appearance', '')}; roupa {character.get('outfit', '')}."
        )
    return "\n".join(rows)


def _safe_fallback_prompt(scene_number, plan):
    # Fallback deliberately avoids free-form scene text that may trigger image safety filters.
    fruits = [
        str(c.get("fruit", "fruta"))[:40]
        for c in plan.get("characters", [])[:3]
    ]
    cast = ", ".join(fruits) if fruits else "personagens-fruta"
    return (
        "Create a wholesome, family-friendly 3D animated illustration for a fictional "
        "Brazilian fruit soap opera. Portrait 2:3 composition. "
        f"Show {cast} as cute anthropomorphic fruit characters in a colorful living room. "
        "Scene number " + str(scene_number) + ": expressive surprised and concerned faces, "
        "a dramatic but harmless conversation, friendly body language, fully clothed, "
        "bright cinematic lighting, polished high-quality 3D animation. "
        "No romance, no intimacy, no violence, no weapons, no text, no subtitles, "
        "no logos, no watermark."
    )


def _generate_with_cloudflare(prompt, destination):
    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
    api_token = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
    if not account_id or not api_token:
        raise RuntimeError(
            "Configure CLOUDFLARE_ACCOUNT_ID e CLOUDFLARE_API_TOKEN na hospedagem."
        )

    model = os.getenv("CLOUDFLARE_IMAGE_MODEL", "@cf/black-forest-labs/flux-1-schnell")
    url = (
        "https://api.cloudflare.com/client/v4/accounts/"
        + account_id
        + "/ai/run/"
        + model
    )
    payload = json.dumps({"prompt": prompt, "steps": 4}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=240) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(
            f"Cloudflare recusou a geração (HTTP {exc.code}): {detail}"
        ) from exc
    except Exception as exc:
        raise RuntimeError(f"Falha ao chamar Cloudflare Workers AI: {exc}") from exc

    encoded = (result.get("result") or {}).get("image")
    if not encoded:
        raise RuntimeError("Cloudflare não retornou a imagem esperada.")
    destination.write_bytes(base64.b64decode(encoded))


def generate_scene_images(plan, output_dir: Path, telegram_user_id: int):
    """Generate six portrait stills with a safe fallback for image moderation rejections."""
    provider = os.getenv("IMAGE_PROVIDER", "disabled").lower()
    if provider != "cloudflare":
        raise RuntimeError(
            "Geração automática desativada. Configure IMAGE_PROVIDER=cloudflare "
            "e as credenciais Cloudflare na hospedagem."
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    bible = _character_bible(plan)
    fingerprint = hashlib.sha256(
        json.dumps(plan, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    manifest = output_dir / "plan.sha256"
    if not manifest.exists() or manifest.read_text(encoding="utf-8").strip() != fingerprint:
        for old_image in output_dir.glob("scene_*.png"):
            old_image.unlink()
        manifest.write_text(fingerprint, encoding="utf-8")

    for scene in plan.get("scenes", []):
        number = int(scene["number"])
        destination = output_dir / f"scene_{number:02d}.png"
        if destination.exists() and destination.stat().st_size > 0:
            continue

        scene_text = str(scene.get("visual_prompt") or scene.get("action") or "")
        prompt = (
            "Create one wholesome, family-friendly cinematic 3D animated still for an "
            "original Brazilian fruit soap-opera story. Portrait composition 2:3. "
            "Expressive anthropomorphic fruit characters with clearly fruit-shaped heads, "
            "fully clothed, emotional but non-suggestive expressions, dramatic readable "
            "lighting, premium family animation look. No intimacy, no nudity, no violence, "
            "no text, no subtitles, no logos, no watermark. Character reference: "
            + bible[:1200]
            + ". Harmless scene description: "
            + scene_text[:700]
        )
        temporary = destination.with_suffix(".tmp")
        try:
            try:
                _generate_with_cloudflare(prompt, temporary)
            except RuntimeError as exc:
                # If the content filter rejects a generated description, retry with a
                # neutral, non-explicit family-friendly scene rather than bypassing safety.
                if "HTTP 400" not in str(exc) or "NSFW" not in str(exc):
                    raise
                _generate_with_cloudflare(
                    _safe_fallback_prompt(number, plan), temporary
                )
            temporary.replace(destination)
        finally:
            if temporary.exists():
                temporary.unlink()

    return output_dir
