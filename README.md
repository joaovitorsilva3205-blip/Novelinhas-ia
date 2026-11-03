# NOVELA FRUTAS AI v2 — modo econômico

## O que esta versão faz
- Recebe um roteiro no Telegram.
- Cria título, personagens, 6 cenas e diálogos com IA.
- Gera até seis imagens estáticas 3D usando Cloudflare Workers AI quando ativado.
- Renderiza um MP4 vertical de aproximadamente 60 segundos.
- Gera falas localmente com Piper TTS.
- Aplica movimento de câmera (Ken Burns) às imagens.
- Envia o MP4 de volta pelo Telegram.

**Limitação importante:** o modo econômico anima a câmera sobre imagens estáticas. Os personagens não fazem movimentos corporais reais. A geração de imagens não garante consistência perfeita entre cenas.

## Requisitos
- Python 3.10+
- FFmpeg instalado e disponível no PATH
- Ollama em execução ou planejador OpenAI
- Piper TTS e dois modelos de voz pt_BR
- Token do Telegram via @BotFather
- Conta Cloudflare gratuita para geração automática de imagens

## Configuração
1. Instale as dependências: `pip install -r requirements.txt`.
2. Copie `.env.example` para `.env`.
3. Configure token e caminhos dos modelos Piper.
4. Para geração automática, crie uma conta Cloudflare e ative Workers AI.
5. No painel Cloudflare, abra Workers AI > Use REST API, crie o token e copie também o Account ID.
6. Configure na hospedagem: `IMAGE_PROVIDER=cloudflare`, `CLOUDFLARE_ACCOUNT_ID` e `CLOUDFLARE_API_TOKEN`.
7. Execute o bot e envie um roteiro; depois use `/render`.

Nunca publique `.env`, tokens ou chaves no GitHub. Use somente variáveis secretas da hospedagem.

## Cota gratuita das imagens
Workers AI oferece 10.000 neurônios por dia no plano Free. A cota é compartilhada com o uso de outros modelos Workers AI da conta e reinicia diariamente às 00:00 UTC. Ao atingir o limite no plano Free, novas requisições falham até a renovação da cota; não faça upgrade para um plano pago se quiser manter o custo em zero. O consumo depende da resolução e dos passos do modelo. Consulte a página oficial de preços antes de uso frequente:
https://developers.cloudflare.com/workers-ai/platform/pricing/

Modelo de imagem: `@cf/black-forest-labs/flux-1-schnell`.
Documentação: https://developers.cloudflare.com/workers-ai/models/flux-1-schnell/

## Planejador
Padrão: Ollama local, sem cobrança por chamada de API (usa recursos do servidor).
Para usar OpenAI, configure `PLANNER_PROVIDER=openai` e `OPENAI_API_KEY`.

## Vozes
Piper oferece vozes pt_BR. Baixe arquivos `.onnx` e `.onnx.json` de vozes compatíveis. Leia a licença de cada voz antes de uso comercial.
Documentação: https://github.com/rhasspy/piper

## Vídeo avançado
A versão atual não faz animação corporal real nem adiciona música/efeitos sonoros automaticamente. Para image-to-video será necessário outro workflow, normalmente com GPU ou créditos.
