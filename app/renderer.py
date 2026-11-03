import os, subprocess, re
from pathlib import Path

def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

def safe_name(s):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", s or "personagem").strip("_").lower()

def render_video(plan, base: Path):
    ffmpeg = os.getenv("FFMPEG_BIN", "ffmpeg")
    piper = os.getenv("PIPER_BIN", "piper")
    female_model = os.getenv("PIPER_FEMALE_MODEL", "")
    male_model = os.getenv("PIPER_MALE_MODEL", "")
    if not female_model or not male_model:
        raise RuntimeError("Configure PIPER_FEMALE_MODEL e PIPER_MALE_MODEL no .env")
    scene_dir = base / "assets" / "scenes"
    work = base / "output" / "work"
    work.mkdir(parents=True, exist_ok=True)
    clips = []
    srt = []
    subtitle_time = 0.0

    for scene in plan["scenes"]:
        n = int(scene["number"])
        image = scene_dir / f"scene_{n:02d}.png"
        if not image.exists():
            raise RuntimeError(f"Falta a imagem {image.name} em assets/scenes/")
        wavs = []
        for j, line in enumerate(scene.get("dialogue", [])):
            text = (line.get("text") or "").strip()
            if not text:
                continue
            gender = (line.get("voice") or "female").lower()
            model = male_model if gender in ("male", "masculina", "masculino") else female_model
            wav = work / f"scene_{n:02d}_line_{j:02d}.wav"
            cmd = [piper, "--model", model, "--output_file", str(wav)]
            subprocess.run(cmd, input=text.encode("utf-8"), check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            wavs.append(wav)
            # Legenda aproximada; áudio real é sincronizado na faixa da cena.
            words = max(1, len(text.split()))
            dur = max(1.0, words / 2.7)
            start = subtitle_time
            end = start + dur
            srt.append((start, end, text))
            subtitle_time = end

        duration = float(scene.get("duration_seconds", 10))
        # Concatena as falas e completa o restante da cena com silêncio.
        audio = work / f"scene_{n:02d}.wav"
        if wavs:
            listfile = work / f"audio_{n:02d}.txt"
            listfile.write_text("".join(f"file '{w.as_posix()}'\n" for w in wavs), encoding="utf-8")
            run([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(listfile),
                 "-ar", "44100", "-ac", "2", str(audio)])
        else:
            run([ffmpeg, "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                 "-t", str(duration), str(audio)])

        clip = work / f"scene_{n:02d}.mp4"
        # Movimento Ken Burns: zoom lento + leve deslocamento. Não é animação corporal.
        vf = ("scale=1080:1920:force_original_aspect_ratio=increase,"
              "crop=1080:1920,zoompan=z='min(zoom+0.0008,1.08)':"
              "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
              "d=250:s=1080x1920:fps=25,format=yuv420p")
        run([ffmpeg, "-y", "-loop", "1", "-i", str(image), "-i", str(audio),
             "-vf", vf, "-t", str(duration), "-r", "25",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "25",
             "-af", "apad", "-c:a", "aac", "-b:a", "128k", str(clip)])
        clips.append(clip)
        subtitle_time = max(subtitle_time, (n) * duration)

    concat = work / "concat.txt"
    concat.write_text("".join(f"file '{p.as_posix()}'\n" for p in clips), encoding="utf-8")
    output = base / "output" / "novelinha_final.mp4"
    run([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
         "-c", "copy", str(output)])
    return output
