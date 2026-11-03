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


## Geração automática de imagens (opcional e paga)
O comando `/render` gera seis imagens individuais para cada usuário usando a OpenAI Images API, quando a integração estiver habilitada. As imagens ficam em `output/users/<telegram_user_id>/scenes/` e são reutilizadas em uma nova renderização do mesmo roteiro.

Configure na hospedagem (nunca publique chaves no GitHub):
- `IMAGE_PROVIDER=openai`
- `OPENAI_API_KEY` com uma chave de API com faturamento habilitado
- `IMAGE_MODEL=gpt-image-2` (padrão)
- `IMAGE_QUALITY=low` (padrão econômico)

A integração permanece desativada por padrão. Sem `IMAGE_PROVIDER=openai`, o bot não chama a API nem gera cobrança. A referência de preço publicada para GPT Image 2 em baixa qualidade e retrato 1024x1536 é aproximadamente US$ 0,005 por imagem; seis imagens ficam em torno de US$ 0,03 por vídeo, antes de eventuais custos de entrada e variações. Consulte a tabela atual antes de ativar: https://developers.openai.com/api/docs/guides/image-generation

A consistência dos personagens é incentivada repetindo a descrição visual completa em cada prompt, mas não é garantida perfeitamente entre seis gerações independentes. Esta etapa gera imagens estáticas com movimento de câmera, não animação corporal.
