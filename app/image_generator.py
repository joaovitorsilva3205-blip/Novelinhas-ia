import base64
import hashlib
import os
from pathlib import Path


def _character_bible(plan):
    rows = []
    for character in plan.get("characters", []):
        rows.append(
            f"{character.get('name', 'Personagem')}: fruta {character.get('fruit', '')}; "
            f"aparência {character.get('appearance', '')}; roupa {character.get('outfit', '')}."
        )
    return "\n".join(rows)


def generate_scene_images(plan, output_dir: Path, telegram_user_id: int):
    """Generate six portrait scene stills. Calls a paid API only when explicitly enabled."""
    provider = os.getenv("IMAGE_PROVIDER", "disabled").lower()
    if provider != "openai":
        raise RuntimeError(
            "Geração automática de imagens desativada. Para habilitar, configure "
            "IMAGE_PROVIDER=openai e OPENAI_API_KEY na hospedagem. Isso gera cobrança por imagem."
        )

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY não configurada na hospedagem.")

    from openai import OpenAI

    model = os.getenv("IMAGE_MODEL", "gpt-image-2")
    quality = os.getenv("IMAGE_QUALITY", "low")
    output_dir.mkdir(parents=True, exist_ok=True)
    bible = _character_bible(plan)
    user_hash = hashlib.sha256(str(telegram_user_id).encode()).hexdigest()
    client = OpenAI(api_key=api_key)

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

        result = client.images.generate(
            model=model,
            prompt=prompt,
            size="1024x1536",
            quality=quality,
            output_format="png",
            safety_identifier=user_hash,
        )
        encoded = result.data[0].b64_json
        if not encoded:
            raise RuntimeError(f"A API não retornou a imagem da cena {number}.")
        temporary = destination.with_suffix(".png.tmp")
        temporary.write_bytes(base64.b64decode(encoded))
        temporary.replace(destination)

    return output_dir
