import asyncio
import json
import logging
import os
import secrets
from pathlib import Path

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from app.planner import create_production_plan
from app.renderer import render_video
from app.image_generator import generate_scene_images

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("novela-frutas-ai")

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
BASE = Path(__file__).resolve().parent.parent
USER_DATA = BASE / "output" / "users"
RENDER_LOCK = asyncio.Lock()


def plan_path_for(update: Update) -> Path:
    user_id = update.effective_user.id
    user_dir = USER_DATA / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir / "plan.json"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🍓 NOVELA FRUTAS AI v2\n\n"
        "Envie um roteiro. Vou criar título, personagens e 6 cenas.\n"
        "Use /render para gerar as imagens (se ativadas) e montar o MP4.\n\n"
        "Comandos: /start, /ajuda, /render"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Fluxo econômico:\n"
        "1) Envie o roteiro em texto.\n"
        "2) O bot cria um plano de 6 cenas.\n"
        "3) Configure Cloudflare Workers AI para gerar as imagens automaticamente.\n"
        "4) Configure FFmpeg e os modelos Piper na hospedagem.\n"
        "5) Envie /render para montar e receber o MP4.\n\n"
        "As imagens são estáticas com movimento de câmera; não há animação corporal real."
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

        lines = [f"🎬 {plan['title']}", plan.get("logline", ""), "\nPersonagens:"]
        for character in plan.get("characters", []):
            lines.append(
                f"• {character['name']} — {character['fruit']} — voz {character['voice']}"
            )
        for scene in plan["scenes"]:
            lines.append(f"\nCena {scene['number']}: {scene.get('action', '')}")
            for dialogue in scene.get("dialogue", []):
                lines.append(f"{dialogue['character']}: {dialogue['text']}")

        await msg.edit_text("✅ Plano criado!")
        output = "\n".join(lines)
        for i in range(0, len(output), 3800):
            await update.message.reply_text(output[i:i + 3800])
        await update.message.reply_text(
            "Quando a hospedagem estiver configurada, envie /render para montar o vídeo."
        )
    except Exception:
        log.exception("Falha no roteiro")
        await msg.edit_text(
            "Não consegui criar o roteiro. Confira as configurações do planejador na hospedagem."
        )


async def render_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    path = plan_path_for(update)
    if not path.exists():
        await update.message.reply_text(
            "Não encontrei um roteiro salvo. Envie a história novamente e tente /render."
        )
        return

    msg = await update.message.reply_text(
        "🎞️ Seu vídeo entrou na fila de renderização. Aguarde..."
    )
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
        async with RENDER_LOCK:
            user_dir = path.parent
            scene_dir = user_dir / "scenes"
            work_dir = user_dir / "work"
            output_path = user_dir / "novelinha_final.mp4"
            await msg.edit_text("Gerando imagens das seis cenas...")
            await asyncio.to_thread(generate_scene_images, plan, scene_dir, update.effective_user.id)
            output = await asyncio.to_thread(
                render_video, plan, BASE, scene_dir, work_dir, output_path
            )
            await msg.edit_text("✅ Vídeo pronto! Enviando...")
            with output.open("rb") as video_file:
                await update.message.reply_video(
                    video=video_file,
                    caption=f"🍓 {plan.get('title', 'Novelinha')}"
                )
    except Exception:
        log.exception("Falha ao renderizar vídeo")
        await msg.edit_text(
            "Não consegui renderizar. Confira Cloudflare Workers AI, FFmpeg e os modelos Piper. "
            "Os registros do servidor mostram o erro técnico."
        )


def main():
    public_url = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")
    port = int(os.getenv("PORT", "10000"))
    if not public_url:
        raise RuntimeError(
            "RENDER_EXTERNAL_URL não definida. Configure o domínio público do serviço Render."
        )

    webhook_path = os.getenv("WEBHOOK_PATH") or secrets.token_urlsafe(24)
    webhook_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET") or secrets.token_urlsafe(32)
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ajuda", help_cmd))
    app.add_handler(CommandHandler("render", render_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, script_handler))

    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=webhook_path,
        webhook_url=f"{public_url}/{webhook_path}",
        secret_token=webhook_secret,
        drop_pending_updates=False,
        allowed_updates=Update.ALL_TYPES,
    )


if __name__ == "__main__":
    main()
