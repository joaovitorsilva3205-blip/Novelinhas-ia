# NOVELA FRUTAS AI v2 — implantação econômica

## O que o projeto prepara
- Bot do Telegram em Python usando webhook para hospedagem web.
- Roteiros de seis cenas gerados por Cloudflare Workers AI.
- Seis imagens 3D estáticas geradas por FLUX.1 Schnell na Cloudflare.
- Renderização vertical MP4 com movimento de câmera (Ken Burns).
- Falas com Piper TTS, desde que os binários e modelos de voz estejam instalados.
- Envio do vídeo pelo Telegram.

**Limitações:** as imagens são estáticas; os personagens não fazem animação corporal real. A cota Cloudflare de texto e imagem é compartilhada. A renderização ainda depende de FFmpeg e dos dois modelos Piper pt_BR, que não estão incluídos neste repositório.

## Deploy de teste no Render Free
1. No Render, escolha **New > Blueprint** e conecte este repositório.
2. Selecione a branch `melhorias-seguranca-mult-usuario` se o painel permitir escolher branch; caso contrário, o Blueprint pode usar a branch padrão.
3. Revise o serviço `novelinhas-ia-bot` e mantenha o plano **Free**.
4. Configure as variáveis secretas `TELEGRAM_BOT_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` e `CLOUDFLARE_API_TOKEN`.
5. Faça o deploy e confira os logs antes de testar o bot no Telegram.

O arquivo `render.yaml` contém o blueprint. O Render disponibiliza a variável `RENDER_EXTERNAL_URL` para o endereço público do serviço; o bot usa essa URL para registrar o webhook.

## Importante sobre o plano gratuito
Render Free suspende serviços web após 15 minutos sem tráfego de entrada e pode reiniciá-los. O sistema de arquivos é efêmero: arquivos gravados localmente podem ser perdidos quando o serviço reinicia ou suspende. Por isso, este deploy é apenas uma prova de conceito; um roteiro salvo localmente pode desaparecer após a suspensão. O plano Free também tem limites de horas, CPU e memória.
Documentação: https://render.com/docs/free

## Cloudflare Workers AI
O plano Free oferece 10.000 neurônios por dia, compartilhados entre os modelos. O limite reinicia diariamente às 00:00 UTC; ao atingir a cota no plano Free, as chamadas falham até a renovação. Não ative um plano pago se quiser manter custo zero.
Preços e limites: https://developers.cloudflare.com/workers-ai/platform/pricing/

Modelos padrão:
- Texto: `@cf/meta/llama-3.1-8b-instruct`
- Imagem: `@cf/black-forest-labs/flux-1-schnell`

## Dependências de renderização ainda necessárias
- FFmpeg instalado no ambiente.
- Piper instalado no ambiente.
- Dois modelos Piper pt_BR compatíveis, com licença adequada ao uso comercial.
- Configurar `PIPER_BIN`, `PIPER_FEMALE_MODEL`, `PIPER_MALE_MODEL` e `FFMPEG_BIN`.

**Não considerar o bot pronto para produção até instalar essas dependências, validar a persistência dos roteiros e testar uma geração completa.**

## Segurança
Nunca grave tokens em arquivos versionados. Configure todos os segredos diretamente no painel de hospedagem. Não compartilhe tokens no chat nem no Telegram.
