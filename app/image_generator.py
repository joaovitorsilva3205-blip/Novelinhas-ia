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
    """Generate six portrait stills with Cloudflare Workers AI free daily allowance."""
    provider = os.getenv("IMAGE_PROVIDER", "disabled").lower()
    if provider != "cloudflare":
        raise RuntimeError(
            "Geração automática desativada. Configure IMAGE_PROVIDER=cloudflare "
            "e as credenciais Cloudflare na hospedagem."
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    bible = _character_bible(plan)
    user_hash = hashlib.sha256(str(telegram_user_id).encode()).hexdigest()[:12]
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

        prompt = (
            "Create one polished cinematic 3D animated still for an original Brazilian "
            "vertical soap-opera story. Portrait composition 2:3, designed to be cropped "
            "to 9:16. Expressive anthropomorphic fruit characters, clearly fruit-shaped "
            "heads and human-like bodies, detailed appealing materials, dramatic but "
            "readable lighting, emotional facial expressions, premium family-friendly "
            "animation look. No text, no subtitles, no logos, no watermark. "
            "Keep every character visually consistent with this character reference: "
            + bible
            + "\nScene action and framing: "
            + str(scene.get("visual_prompt") or scene.get("action") or "")
            + "\nMood and sound context (visual guidance only): "
            + str(scene.get("sound_design") or "")
        )
        temporary = destination.with_suffix(".tmp")
        try:
            _generate_with_cloudflare(prompt, temporary)
            temporary.replace(destination)
        finally:
            if temporary.exists():
                temporary.unlink()

    return output_dir
