import asyncio
import json
import logging
import os
from pathlib import Path

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from app.planner import create_production_plan
from app.renderer import render_video

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("novela-frutas-ai")

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
BASE = Path(__file__).resolve().parent.parent
USER_DATA = BASE / "output" / "users"

# The current renderer uses shared scene assets and output/work paths.
# Serialize renders until the renderer is converted to isolated job workspaces.
RENDER_LOCK = asyncio.Lock()


def plan_path_for(update: Update) -> Path:
    user_id = update.effective_user.id
    user_dir = USER_DATA / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir / "plan.json"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🍓 NOVELA FRUTAS AI v2\\n\\n"
        "Envie um roteiro. Vou criar título, personagens e 6 cenas.\\n"
        "Quando as imagens e vozes estiverem configuradas, use /render para montar o MP4.\\n\\n"
        "Comandos: /start, /ajuda, /render"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Fluxo econômico:\\n"
        "1) Envie o roteiro em texto.\\n"
        "2) O bot cria um plano de 6 cenas.\\n"
        "3) As imagens devem estar em assets/scenes/scene_01.png até scene_06.png.\\n"
        "4) Configure duas vozes Piper em voices/ e os caminhos no .env.\\n"
        "5) Envie /render para montar e receber o MP4.\\n\\n"
        "A geração automática de imagens ainda não está incluída. O modo econômico usa "
        "movimento de câmera sobre imagens estáticas, sem animação corporal real."
    )


async def script_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    script = (update.message.text or "").strip()
    if len(script) < 30:
        await update.message.reply_text("Envie uma história com pelo menos 30 caracteres.")
        return

    msg = await update.message.reply_text("✍️ Criando sua novelinha...")
    try:
        plan = await asyncio.to_thread(create_production_plan, script)
        path = plan_path_for(update)
        path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

        lines = [f"🎬 {plan['title']}", plan.get("logline", ""), "\\nPersonagens:"]
        for character in plan.get("characters", []):
            lines.append(
                f"• {character['name']} — {character['fruit']} — voz {character['voice']}"
            )
        for scene in plan["scenes"]:
            lines.append(f"\\nCena {scene['number']}: {scene.get('action', '')}")
            for dialogue in scene.get("dialogue", []):
                lines.append(f"{dialogue['character']}: {dialogue['text']}")

        await msg.edit_text("✅ Plano criado!")
        output = "\\n".join(lines)
        for i in range(0, len(output), 3800):
            await update.message.reply_text(output[i:i + 3800])
        await update.message.reply_text(
            "Quando as 6 imagens estiverem prontas e as vozes configuradas, envie /render."
        )
    except Exception:
        log.exception("Falha no roteiro")
        await msg.edit_text(
            "Não consegui criar o roteiro. Confira o planejador e as configurações no .env."
        )


async def render_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    path = plan_path_for(update)
    if not path.exists():
        await update.message.reply_text("Primeiro envie um roteiro para este bot.")
        return

    msg = await update.message.reply_text(
        "🎞️ Seu vídeo entrou na fila de renderização. Aguarde..."
    )
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
        # Lock protects the shared FFmpeg work/output directory from simultaneous jobs.
        async with RENDER_LOCK:
            output = await asyncio.to_thread(render_video, plan, BASE)
            await msg.edit_text("✅ Vídeo pronto! Enviando...")
            with output.open("rb") as video_file:
                await update.message.reply_video(
                    video=video_file,
                    caption=f"🍓 {plan.get('title', 'Novelinha')}"
                )
    except Exception:
        log.exception("Falha ao renderizar vídeo")
        await msg.edit_text(
            "Não consegui renderizar. Confira as 6 imagens, FFmpeg e os modelos de voz Piper."
        )


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ajuda", help_cmd))
    app.add_handler(CommandHandler("render", render_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, script_handler))
    app.run_polling()


if __name__ == "__main__":
    main()
