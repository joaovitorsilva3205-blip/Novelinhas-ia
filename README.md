# NOVELA FRUTAS AI v2 — modo econômico

## O que esta versão faz
- Recebe um roteiro no Telegram.
- Cria título, personagens, 6 cenas e diálogos com IA.
- Renderiza um MP4 vertical de aproximadamente 60 segundos.
- Gera falas localmente com Piper TTS.
- Aplica movimento de câmera (Ken Burns) às imagens.
- Envia o MP4 de volta pelo Telegram.

**Limitação importante:** o modo econômico anima a câmera sobre imagens estáticas. Os personagens não fazem movimentos corporais reais. Para isso, conecte um workflow de image-to-video no ComfyUI ou um serviço externo, que pode exigir GPU/ créditos.

## Requisitos
- Python 3.10+
- FFmpeg instalado e disponível no PATH
- Ollama instalado e em execução (opção sem API paga) ou chave OpenAI
- Piper TTS e dois modelos de voz pt_BR
- 6 imagens verticais PNG em `assets/scenes/scene_01.png` ... `scene_06.png`
- Token do Telegram via @BotFather

## Configuração
1. `python -m venv .venv`
2. Ative o ambiente virtual.
3. `pip install -r requirements.txt`
4. Copie `.env.example` para `.env`.
5. Configure token e caminhos dos modelos Piper.
6. Para Ollama, execute `ollama pull qwen2.5:7b` e mantenha o Ollama ativo.
7. Crie as seis imagens em estilo consistente e coloque-as na pasta indicada.
8. Execute `python run.py`.
9. No Telegram, envie `/start`, depois o roteiro e, quando as imagens estiverem prontas, `/render`.

## Planejador
Padrão: Ollama local, sem cobrança por chamada de API (o custo é seu computador/energia).
Para usar OpenAI: defina `PLANNER_PROVIDER=openai` e `OPENAI_API_KEY`.

## Imagens 3D
Use ComfyUI local para gerar as imagens. A interface e backend são open-source e oferecem API local.
Site: https://github.com/Comfy-Org/ComfyUI
Depois de gerar 6 imagens, salve-as com os nomes scene_01.png a scene_06.png.
Mantenha uma imagem de referência/descrição fixa por personagem para reduzir mudanças de aparência.

## Vozes
Piper oferece vozes pt_BR. Baixe os arquivos `.onnx` e `.onnx.json` de vozes compatíveis.
Leia o MODEL_CARD/licença de cada voz antes de uso comercial; licenças variam por modelo.
Documentação: https://github.com/rhasspy/piper
Não use uma voz que imite pessoa real sem autorização.

## Vídeo avançado
ComfyUI pode executar workflows de image-to-video com modelos como LTX. Isso pode exigir GPU potente, bastante armazenamento e tempo de processamento.
Guia: https://docs.ltx.io/open-source-model/usage-guides/image-to-video
Se usar provedor de nuvem, confira preços e licença comercial antes de produzir em escala.

## Limites do Telegram
O Bot API documenta envio de vídeos de até 50 MB. O projeto usa MP4 H.264/AAC; se o arquivo ultrapassar o limite, reduza o bitrate ou envie como documento conforme os limites vigentes.
https://core.telegram.org/bots/api
