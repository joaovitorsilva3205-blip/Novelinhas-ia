import asyncio
import json
import hashlib
import logging
import os
import secrets
from pathlib import Path

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, CallbackQueryHandler, filters

from app.planner import create_production_plan
from app.renderer import render_video
from app.image_generator import generate_scene_images
from app.flow_renderer import render_flow_video

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
    context.user_data.clear()
    context.user_data["wizard_step"] = "waiting_script"
    await update.message.reply_text(
        "🍓 NOVELA FRUTAS AI 2.0\\n\\n"
        "Vamos criar sua novelinha de 60 segundos!\\n"
        "Primeiro, envie o roteiro ou conte a ideia da história. "
        "Pode escrever do seu jeito: eu organizo tudo em 6 cenas."
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "NOVELA FRUTAS AI 2.0 — modo híbrido\n\n"
        "1) Envie a ideia da história.\n"
        "2) Use /flow para receber 6 prompts de vídeo (10s cada).\n"
        "3) Gere os 6 clipes no Google Flow e envie-os aqui, um por vez, na ordem.\n"
        "4) Use /status para conferir os clipes recebidos.\n"
        "5) Use /montar para unir os clipes, aplicar as falas em português e receber o MP4 9:16.\n\n"
        "Dica: mantenha a mesma referência visual/personagens em todas as cenas."
    )


async def _create_and_send_plan(update: Update, context: ContextTypes.DEFAULT_TYPE, script: str):
    msg = await update.message.reply_text("✍️ Criando roteiro, personagens e cenas...")
    try:
        plan = await asyncio.to_thread(create_production_plan, script)
        plan["duration_seconds"] = 60
        plan["scene_count"] = 6
        path = plan_path_for(update)
        path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        context.user_data["wizard_step"] = "ready"
        lines = [f"🎬 {plan.get('title', 'Sua novelinha')}", plan.get("logline", ""), "\\nPERSONAGENS:"]
        for character in plan.get("characters", []):
            lines.append(f"• {character.get('name', 'Personagem')} — {character.get('fruit', '')} — {character.get('appearance', '')} — voz {character.get('voice', 'female')}")
        for scene in plan.get("scenes", []):
            lines.append(f"\\nCENA {scene.get('number')}: {scene.get('action', '')}")
            for dialogue in scene.get("dialogue", []):
                lines.append(f"{dialogue.get('character', 'Personagem')}: {dialogue.get('text', '')}")
        await msg.edit_text("✅ História e personagens preparados!")
        output = "\\n".join(lines)
        for i in range(0, len(output), 3500):
            await update.message.reply_text(output[i:i + 3500])
        await update.message.reply_text(
            "🎥 Agora vou preparar os prompts para o Google Flow. Digite /flow para recebê-los.\\n"
            "Depois gere os 6 clipes no Flow e envie-os aqui para eu montar o episódio."
        )
    except Exception:
        log.exception("Falha ao criar plano")
        context.user_data["wizard_step"] = "waiting_script"
        await msg.edit_text("❌ Não consegui criar o roteiro. Tente novamente enviando a história.")


async def script_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (update.message.text or "").strip()
    step = context.user_data.get("wizard_step")
    if step == "waiting_script":
        if len(message) < 10:
            await update.message.reply_text("Conte um pouco mais da história, com pelo menos 10 caracteres.")
            return
        context.user_data["story_script"] = message
        context.user_data["wizard_step"] = "choosing_characters"
        await update.message.reply_text(
            "🍍 Agora escolha como vamos criar os personagens:\\n\\n"
            "1️⃣ — Quero criar os personagens. Vou descrever cada um.\\n"
            "2️⃣ — Deixe a inteligência artificial criar todos os personagens.\\n\\n"
            "Responda apenas 1 ou 2."
        )
        return

    if step == "choosing_characters":
        choice = message.lower()
        if choice in ("1", "criar", "eu", "quero criar"):
            context.user_data["wizard_step"] = "waiting_character_details"
            await update.message.reply_text(
                "✍️ Descreva seus personagens: nome, fruta, aparência, roupa, personalidade e se a voz é masculina ou feminina.\\n"
                "Pode mandar todos de uma vez."
            )
            return
        if choice in ("2", "ia", "inteligência artificial", "inteligencia artificial", "deixe a ia", "deixa a ia"):
            story = context.user_data.get("story_script", "")
            context.user_data["wizard_step"] = "creating_plan"
            await update.message.reply_text("🤖 A IA vai criar os personagens e organizar as 6 cenas...")
            await _create_and_send_plan(update, context, story + "\\n\\nCrie todos os personagens do zero, com frutas variadas, aparência 3D humanizada, roupas próprias e vozes adequadas.")
            return
        await update.message.reply_text("Responda 1 para criar os personagens ou 2 para deixar a IA criar.")
        return

    if step == "waiting_character_details":
        if len(message) < 5:
            await update.message.reply_text("Me conte um pouco mais sobre os personagens.")
            return
        story = context.user_data.get("story_script", "")
        context.user_data["wizard_step"] = "creating_plan"
        await update.message.reply_text("🎭 Perfeito! Vou respeitar suas descrições e criar as cenas...")
        await _create_and_send_plan(
            update, context,
            story + "\\n\\nPERSONAGENS DEFINIDOS PELO USUÁRIO — preserve fielmente nomes, frutas, aparência, roupas, personalidades e gêneros de voz:\\n" + message
        )
        return

    if step == "creating_plan":
        await update.message.reply_text("Ainda estou preparando seu episódio. Aguarde um instante.")
        return

    if step == "ready":
        await update.message.reply_text("Seu episódio já está planejado. Use /flow para ver os prompts ou /start para começar outra história.")
        return

    await update.message.reply_text("Digite /start para começar uma nova novelinha.")



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
            loop = asyncio.get_running_loop()

            def report_progress(message):
                loop.call_soon_threadsafe(
                    lambda: asyncio.create_task(msg.edit_text(message))
                )

            await msg.edit_text("Iniciando geração das imagens...")
            await asyncio.to_thread(
                generate_scene_images,
                plan,
                scene_dir,
                update.effective_user.id,
                report_progress,
            )
            await msg.edit_text("🎬 Imagens prontas! Montando vídeo e áudio...")
            output = await asyncio.to_thread(
                render_video, plan, BASE, scene_dir, work_dir, output_path
            )
            await msg.edit_text("✅ Vídeo pronto! Enviando...")
            with output.open("rb") as video_file:
                await update.message.reply_video(
                    video=video_file,
                    caption=f"🍓 {plan.get('title', 'Novelinha')}"
                )
    except Exception as exc:
        log.exception("Falha ao renderizar vídeo")
        await msg.edit_text(
            "❌ Não consegui renderizar o vídeo. "
            "Confira os logs do Render para identificar o erro. "
            "Se puder, envie aqui o trecho do erro sem tokens ou senhas."
        )



async def flow_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    path = plan_path_for(update)
    if not path.exists():
        await update.message.reply_text("Envie primeiro a ideia da história para eu criar o roteiro.")
        return
    plan = json.loads(path.read_text(encoding="utf-8"))
    await update.message.reply_text(
        "🎥 PROMPTS PARA GOOGLE FLOW\n\nGere cada cena como um clipe vertical 9:16 de 10 segundos. "
        "Use a mesma descrição de personagens em todas as cenas. Depois envie os 6 vídeos aqui, um por vez, na ordem.\n\n"
        "REFERÊNCIA VISUAL:\n" + str(plan.get("flow_global_style", ""))[:900]
    )
    for scene in plan.get("scenes", []):
        prompt = scene.get("flow_prompt") or scene.get("visual_prompt") or scene.get("action", "")
        await update.message.reply_text(f"CENA {scene['number']}/6 — 10 SEGUNDOS\n{prompt}"[:3900])


async def video_clip_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    path = plan_path_for(update)
    if not path.exists():
        await update.message.reply_text("Envie primeiro uma história para criar o roteiro.")
        return
    clips_dir = path.parent / "flow_clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    received = sorted(clips_dir.glob("scene_*.mp4"))
    if len(received) >= 6:
        await update.message.reply_text("Já recebi 6 clipes. Use /montar ou /limpar_clipes.")
        return
    media = update.message.video or update.message.document
    if not media:
        return
    destination = clips_dir / f"scene_{len(received) + 1:02d}.mp4"
    telegram_file = await context.bot.get_file(media.file_id)
    await telegram_file.download_to_drive(custom_path=str(destination))
    number = len(received) + 1
    await update.message.reply_text(
        f"✅ Clipe {number}/6 recebido." if number < 6 else "✅ Todos os clipes recebidos! Use /montar."
    )


async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clips_dir = plan_path_for(update).parent / "flow_clips"
    count = len(list(clips_dir.glob("scene_*.mp4"))) if clips_dir.exists() else 0
    await update.message.reply_text(f"📦 Clipes recebidos: {count}/6.")


async def clear_clips_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clips_dir = plan_path_for(update).parent / "flow_clips"
    if clips_dir.exists():
        for clip in clips_dir.glob("scene_*.mp4"):
            clip.unlink()
    await update.message.reply_text("🧹 Clipes apagados. Envie novamente os 6 vídeos na ordem correta.")


async def assemble_flow_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    path = plan_path_for(update)
    if not path.exists():
        await update.message.reply_text("Envie primeiro uma história para criar o roteiro.")
        return
    user_dir = path.parent
    clips_dir = user_dir / "flow_clips"
    clips = [clips_dir / f"scene_{i:02d}.mp4" for i in range(1, 7)]
    missing = [str(i) for i, clip in enumerate(clips, start=1) if not clip.exists()]
    if missing:
        await update.message.reply_text("Ainda faltam os clipes das cenas: " + ", ".join(missing) + ".")
        return
    msg = await update.message.reply_text("🎬 Montando sua novelinha de 60 segundos...")
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
        async with RENDER_LOCK:
            output = await asyncio.to_thread(
                render_flow_video, plan, clips_dir, user_dir / "flow_work", user_dir / "novelinha_60s.mp4"
            )
            with output.open("rb") as video_file:
                await update.message.reply_video(
                    video=video_file, caption=f"🍓 {plan.get('title', 'Novelinha')} — NOVELA FRUTAS AI 2.0"
                )
        await msg.edit_text("✅ Episódio finalizado!")
    except Exception:
        log.exception("Falha ao montar clipes do Google Flow")
        await msg.edit_text("❌ Não consegui montar os clipes. Confira os logs do Render e envie o erro sem tokens ou senhas.")



def main():
    public_url = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")
    port = int(os.getenv("PORT", "10000"))
    if not public_url:
        raise RuntimeError(
            "RENDER_EXTERNAL_URL não definida. Configure o domínio público do serviço Render."
        )

    webhook_path = os.getenv("WEBHOOK_PATH") or secrets.token_urlsafe(24)
    raw_webhook_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET") or secrets.token_urlsafe(32)
    webhook_secret = hashlib.sha256(raw_webhook_secret.encode("utf-8")).hexdigest()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ajuda", help_cmd))
    app.add_handler(CommandHandler("render", render_handler))
    app.add_handler(CommandHandler("flow", flow_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("montar", assemble_flow_cmd))
    app.add_handler(CommandHandler("limpar_clipes", clear_clips_cmd))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, video_clip_handler))
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
