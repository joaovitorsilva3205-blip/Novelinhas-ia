import asyncio
import os
import re
import subprocess
from pathlib import Path

import edge_tts
import imageio_ffmpeg


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def safe_name(s):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", s or "personagem").strip("_").lower()


def get_ffmpeg():
    configured = os.getenv("FFMPEG_BIN")
    return configured or imageio_ffmpeg.get_ffmpeg_exe()


def synthesize_edge_tts(text, voice, output_path):
    """Gera MP3 usando as vozes neurais pt-BR do serviço Edge TTS."""
    async def _synthesize():
        communicate = edge_tts.Communicate(text=text, voice=voice)
        await communicate.save(str(output_path))

    asyncio.run(_synthesize())


def render_video(plan, base: Path, scene_dir=None, work_dir=None, output_path=None):
    ffmpeg = get_ffmpeg()
    female_voice = os.getenv("TTS_FEMALE_VOICE", "pt-BR-FranciscaNeural")
    male_voice = os.getenv("TTS_MALE_VOICE", "pt-BR-AntonioNeural")

    scene_dir = Path(scene_dir) if scene_dir else base / "assets" / "scenes"
    work = Path(work_dir) if work_dir else base / "output" / "work"
    work.mkdir(parents=True, exist_ok=True)
    clips = []

    for scene in plan["scenes"]:
        n = int(scene["number"])
        image = scene_dir / f"scene_{n:02d}.png"
        if not image.exists():
            raise RuntimeError(f"Falta a imagem {image.name} em assets/scenes/")

        audio_parts = []
        for j, line in enumerate(scene.get("dialogue", [])):
            text = (line.get("text") or "").strip()
            if not text:
                continue
            gender = (line.get("voice") or "female").lower()
            voice = male_voice if gender in ("male", "masculina", "masculino") else female_voice
            mp3 = work / f"scene_{n:02d}_line_{j:02d}.mp3"
            wav = work / f"scene_{n:02d}_line_{j:02d}.wav"

            try:
                synthesize_edge_tts(text, voice, mp3)
                run([ffmpeg, "-y", "-i", str(mp3), "-ar", "44100", "-ac", "2", str(wav)])
            except Exception as exc:
                raise RuntimeError(
                    f"Falha ao gerar fala com a voz {voice}. Verifique a conexão com o serviço de voz."
                ) from exc
            audio_parts.append(wav)

        duration = float(scene.get("duration_seconds", 10))
        audio = work / f"scene_{n:02d}.wav"
        if audio_parts:
            listfile = work / f"audio_{n:02d}.txt"
            listfile.write_text(
                "".join(f"file '{w.as_posix()}'\n" for w in audio_parts),
                encoding="utf-8",
            )
            run([
                ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(listfile),
                "-ar", "44100", "-ac", "2", str(audio),
            ])
        else:
            run([
                ffmpeg, "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                "-t", str(duration), str(audio),
            ])

        clip = work / f"scene_{n:02d}.mp4"
        # Movimento de câmera Ken Burns; as imagens continuam estáticas.
        vf = (
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,zoompan=z='min(zoom+0.0008,1.08)':"
            "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            "d=250:s=1080x1920:fps=25,format=yuv420p"
        )
        run([
            ffmpeg, "-y", "-loop", "1", "-i", str(image), "-i", str(audio),
            "-vf", vf, "-t", str(duration), "-r", "25",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "25",
            "-af", "apad", "-c:a", "aac", "-b:a", "128k", str(clip),
        ])
        clips.append(clip)

    if not clips:
        raise RuntimeError("O roteiro não contém cenas para renderizar.")

    concat = work / "concat.txt"
    concat.write_text(
        "".join(f"file '{p.as_posix()}'\n" for p in clips),
        encoding="utf-8",
    )
    output = Path(output_path) if output_path else base / "output" / "novelinha_final.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)
    run([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(output)])
    return output
