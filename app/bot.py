import os, json, logging
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from app.planner import create_production_plan
from app.renderer import render_video

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("novela-frutas-ai")
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
BASE = Path(__file__).resolve().parent.parent

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🍓 NOVELA FRUTAS AI v2\n\n"
        "Envie um roteiro. Vou criar título, personagens e 6 cenas.\n"
        "Depois você pode enviar /render para montar o MP4 com imagens e vozes locais.\n\n"
        "Comandos: /start, /ajuda, /render"
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Fluxo econômico:\n"
        "1) Envie o roteiro em texto.\n"
        "2) O bot cria um plano de 6 cenas.\n"
        "3) Coloque uma imagem vertical por cena em assets/scenes/scene_01.png até scene_06.png.\n"
        "4) Configure duas vozes Piper em voices/ e os caminhos no .env.\n"
        "5) Envie /render para montar e receber o MP4.\n\n"
        "A geração de imagens/vídeos por IA não está incluída automaticamente nesta versão; "
        "use ComfyUI local para criar as imagens. O modo econômico anima imagens com movimento "
        "de câmera, não gera movimento corporal real."
    )

async def script_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if len(text) < 30:
        await update.message.reply_text("Envie uma história com pelo menos 30 caracteres.")
        return
    msg = await update.message.reply_text("✍️ Criando sua novelinha...")
    try:
        plan = create_production_plan(text)
        context.user_data["plan"] = plan
        (BASE / "output" / "last_plan.json").write_text(
            json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        lines = [f"🎬 {plan['title']}", plan.get("logline", ""), "\nPersonagens:"]
        for c in plan.get("characters", []):
            lines.append(f"• {c['name']} — {c['fruit']} — voz {c['voice']}")
        for s in plan["scenes"]:
            lines.append(f"\nCena {s['number']}: {s.get('action','')}")
            for d in s.get("dialogue", []):
                lines.append(f"{d['character']}: {d['text']}")
        await msg.edit_text("✅ Plano criado!")
        output = "\n".join(lines)
        for i in range(0, len(output), 3800):
            await update.message.reply_text(output[i:i+3800])
        await update.message.reply_text(
            "Quando as 6 imagens estiverem em assets/scenes, envie /render para gerar o MP4."
        )
    except Exception:
        log.exception("Falha no roteiro")
        await msg.edit_text("Erro ao criar roteiro. Confira a configuração do planejador no .env.")

async def render_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    plan_path = BASE / "output" / "last_plan.json"
    if not plan_path.exists():
        await update.message.reply_text("Primeiro envie um roteiro.")
        return
    msg = await update.message.reply_text("🎞️ Renderizando seu vídeo. Isso pode levar alguns minutos...")
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        output = render_video(plan, BASE)
        await msg.edit_text("✅ Vídeo pronto! Enviando...")
        with output.open("rb") as f:
            await update.message.reply_video(video=f, caption=f"🍓 {plan.get('title','Novelinha')}")
    except Exception as e:
        log.exception("Falha ao renderizar")
        await msg.edit_text(f"Não consegui renderizar: {e}\nConfira imagens, FFmpeg e vozes Piper.")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ajuda", help_cmd))
    app.add_handler(CommandHandler("render", render_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, script_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
