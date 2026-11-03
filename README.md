# NOVELA FRUTAS AI v2 — implantação econômica

## O que o projeto prepara
- Bot do Telegram em Python usando webhook para hospedagem web.
- Roteiros de seis cenas gerados por Cloudflare Workers AI.
- Seis imagens 3D estáticas geradas por FLUX.1 Schnell na Cloudflare.
- Renderização vertical MP4 com movimento de câmera (Ken Burns).
- Falas com vozes neurais brasileiras via Edge TTS: Francisca (feminina) e Antonio (masculina).
- Envio do vídeo pelo Telegram.

**Limitações:** as imagens são estáticas; os personagens não fazem animação corporal real. A cota Cloudflare de texto e imagem é compartilhada. O Edge TTS precisa de conexão com a internet e depende de um serviço online de terceiros; a disponibilidade e os limites podem mudar. A biblioteca edge-tts é um cliente não oficial, não uma API comercial contratada da Microsoft. Antes de monetizar vídeos, verifique os termos aplicáveis ao uso comercial das vozes e do serviço.

## Vozes configuradas
- Feminina: `pt-BR-FranciscaNeural`
- Masculina: `pt-BR-AntonioNeural`

Para trocar as vozes, configure `TTS_FEMALE_VOICE` e `TTS_MALE_VOICE` nas variáveis do Render. Não é necessário baixar modelos Piper nem instalar o Piper.

## Deploy de teste no Render Free
1. Conecte este repositório e selecione a branch `melhorias-seguranca-mult-usuario`.
2. Mantenha o serviço `novelinhas-ia-bot` no plano Free.
3. Configure `TELEGRAM_BOT_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` e `CLOUDFLARE_API_TOKEN` no painel do Render.
4. Faça o deploy e confira os logs antes de testar o bot no Telegram.

O Render disponibiliza `RENDER_EXTERNAL_URL` para o endereço público do serviço; o bot usa essa URL para registrar o webhook.

## Importante sobre o plano gratuito
Render Free suspende serviços web após 15 minutos sem tráfego de entrada e pode reiniciá-los. O sistema de arquivos é efêmero: arquivos gravados localmente podem ser perdidos quando o serviço reinicia ou suspende. Por isso, este deploy é apenas uma prova de conceito; um roteiro salvo localmente pode desaparecer após a suspensão. O plano Free também tem limites de horas, CPU e memória.
Documentação: https://render.com/docs/free

## Cloudflare Workers AI
O plano Free tem cota diária compartilhada entre os modelos. Ao atingir a cota, as chamadas falham até a renovação. Não ative um plano pago se quiser manter custo zero.
Preços e limites: https://developers.cloudflare.com/workers-ai/platform/pricing/

Modelos padrão:
- Texto: `@cf/meta/llama-3.1-8b-instruct`
- Imagem: `@cf/black-forest-labs/flux-1-schnell`

## Renderização
O projeto usa `imageio-ffmpeg` para disponibilizar um binário FFmpeg no ambiente Python. A primeira geração de fala requer conexão com o serviço Edge TTS. O tempo de geração depende da conexão e dos limites do serviço externo.

## Segurança
Nunca grave tokens em arquivos versionados. Configure todos os segredos diretamente no painel de hospedagem. Não compartilhe tokens no chat nem no Telegram.
