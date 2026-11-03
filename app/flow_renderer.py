import asyncio
import os
import subprocess
from pathlib import Path

import edge_tts
import imageio_ffmpeg


def _run(command):
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


async def _speak(text, voice, path):
    await edge_tts.Communicate(text=text, voice=voice).save(str(path))


def _make_voice(text, voice, path):
    asyncio.run(_speak(text, voice, path))


def render_flow_video(plan, clips_dir, work_dir, output_path):
    """Normalize six Flow clips, preserve quiet ambience and overlay Brazilian Portuguese dialogue."""
    ffmpeg = os.getenv("FFMPEG_BIN") or imageio_ffmpeg.get_ffmpeg_exe()
    clips_dir, work_dir, output_path = Path(clips_dir), Path(work_dir), Path(output_path)
    work_dir.mkdir(parents=True, exist_ok=True)
    female = os.getenv("TTS_FEMALE_VOICE", "pt-BR-FranciscaNeural")
    male = os.getenv("TTS_MALE_VOICE", "pt-BR-AntonioNeural")
    rendered = []

    for scene in sorted(plan.get("scenes", []), key=lambda item: int(item["number"])):
        number = int(scene["number"])
        source = clips_dir / f"scene_{number:02d}.mp4"
        if not source.exists():
            raise RuntimeError(f"Clipe da cena {number} não encontrado.")
        lines = []
        for index, line in enumerate(scene.get("dialogue", [])):
            spoken = str(line.get("text", "")).strip()
            if not spoken:
                continue
            gender = str(line.get("voice", "female")).lower()
            voice = male if gender in ("male", "masculina", "masculino") else female
            audio = work_dir / f"scene_{number:02d}_line_{index:02d}.mp3"
            _make_voice(spoken, voice, audio)
            lines.append(audio)

        clip = work_dir / f"scene_{number:02d}_final.mp4"
        vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1"
        if lines:
            listing = work_dir / f"voice_{number:02d}.txt"
            listing.write_text("".join(f"file '{p.as_posix()}'\n" for p in lines), encoding="utf-8")
            voice_track = work_dir / f"voice_{number:02d}.mp3"
            _run([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-c:a", "libmp3lame", str(voice_track)])
            _run([
                ffmpeg, "-y", "-i", str(source), "-i", str(voice_track),
                "-filter_complex",
                "[0:a]volume=0.18[amb];[1:a]volume=1.0[voice];[amb][voice]amix=inputs=2:duration=first:dropout_transition=2[a]",
                "-map", "0:v:0", "-map", "[a]", "-vf", vf,
                "-t", "10", "-r", "25", "-c:v", "libx264", "-preset", "veryfast",
                "-crf", "23", "-c:a", "aac", "-b:a", "160k", str(clip)
            ])
        else:
            _run([
                ffmpeg, "-y", "-i", str(source), "-vf", vf, "-t", "10", "-r", "25",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                "-c:a", "aac", "-b:a", "160k", str(clip)
            ])
        rendered.append(clip)

    listing = work_dir / "final_concat.txt"
    listing.write_text("".join(f"file '{p.as_posix()}'\n" for p in rendered), encoding="utf-8")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _run([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
          "-t", "60", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
          "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(output_path)])
    return output_path
