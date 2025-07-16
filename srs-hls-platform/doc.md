# Plataforma de Streaming de Vídeo com SRS e Nginx

## 1. Visão Geral

Este documento detalha a arquitetura e a implementação de uma plataforma de streaming de vídeo ao vivo, de baixa latência, utilizando SRS (Simple Realtime Server), Nginx e Docker. A solução é projetada para ser robusta, escalável e fácil de implantar.

O sistema ingere um stream de vídeo via protocolo RTMP e o transcodifica em tempo real para HLS (HTTP Live Streaming), disponibilizando-o para reprodução em navegadores web através de um player baseado em `hls.js`.

### Arquitetura

A plataforma utiliza uma arquitetura de dois contêineres Docker para uma clara separação de responsabilidades:

1.  **`srs-server`**: Um contêiner executando o **SRS**, responsável por:
    *   Receber o stream de vídeo de entrada (ingest) via RTMP.
    *   Processar o vídeo, convertendo-o (transmuxing) para o formato HLS.
    *   Gerar os arquivos de manifesto (`.m3u8`) e os segmentos de vídeo (`.ts`).

2.  **`web-server`**: Um contêiner executando o **Nginx**, responsável por:
    *   Servir a página web do player (`index.html`).
    *   Entregar os arquivos HLS (manifesto e segmentos de vídeo) para os espectadores.

Os dois contêineres compartilham um volume Docker (`hls-data`), permitindo que o Nginx acesse e sirva os arquivos HLS que o SRS gera.

## 2. Pré-requisitos

-   **Docker**: [Instruções de instalação](https://docs.docker.com/engine/install/)
-   **Docker Compose**: [Instruções de instalação](https://docs.docker.com/compose/install/)
-   Um software de encoder de vídeo, como o **OBS Studio** (gratuito) ou **FFmpeg**.

## 3. Estrutura do Projeto

```
srs-hls-platform/
├── docker-compose.yml
├── doc.md
├── srs/
│   └── srs.conf
└── web/
    ├── nginx.conf
    └── html/
        └── index.html
```

## 4. Arquivos de Configuração e Scripts

Abaixo estão os conteúdos completos e comentados de todos os arquivos necessários para o projeto.

### 4.1. `docker-compose.yml`

Este arquivo orquestra a criação e a rede dos nossos contêineres.

```yaml
version: '3.8'

services:
  srs-server:
    image: ossrs/srs:5
    container_name: srs-server
    restart: always
    ports:
      - "1935:1935"      # Porta RTMP (TCP) para ingestão
      - "8080:8080"      # Porta HTTP (TCP) para o console de API do SRS
    volumes:
      - ./srs/srs.conf:/usr/local/srs/conf/srs.conf
      - hls-data:/usr/local/srs/objs/nginx/html
    command: ./objs/srs -c conf/srs.conf

  web-server:
    image: nginx:stable
    container_name: web-server
    restart: always
    ports:
      # Mapeia a porta 80 do contêiner para a 8081 no host para evitar conflitos.
      - "8081:80"
    volumes:
      - ./web/nginx.conf:/etc/nginx/nginx.conf:ro
      # Monta apenas o index.html para evitar conflitos de volume
      - ./web/html/index.html:/usr/share/nginx/html/index.html:ro
      # Monta o volume compartilhado onde os arquivos HLS estão
      - hls-data:/usr/share/nginx/html/hls:ro
    depends_on:
      - srs-server

volumes:
  hls-data:
```

### 4.2. `srs/srs.conf`

Configuração do servidor SRS, otimizada para baixa latência com HLS.

```nginx
# Configuração principal para o servidor SRS
listen              1935;
max_connections     1000;
srs_log_tank        console;
daemon              off;

http_server {
    enabled         on;
    listen          8080;
    dir            ./objs/nginx/html;
}

# O servidor SRT foi desativado para evitar erros de log desnecessários.
# srt_server {
#     enabled         on;
#     listen          10080;
# }

vhost __defaultVhost__ {
    hls {
        enabled         on;
        hls_path       ./objs/nginx/html;
        # Parâmetros para baixa latência:
        # hls_fragment: Duração de cada segmento de vídeo em segundos.
        hls_fragment    2;
        # hls_window: Duração total da playlist (soma dos segmentos).
        hls_window      10;
        hls_m3u8_file   [app]/[stream].m3u8;
        hls_ts_file     [app]/[stream]-[seq].ts;
    }
}
```

### 4.3. `web/nginx.conf`

Configuração do Nginx para servir o player e os arquivos HLS.

```nginx
worker_processes auto;

events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;
    sendfile      on;
    keepalive_timeout  65;

    server {
        listen 80;
        server_name localhost;

        # Servir a página principal do player
        location / {
            root   /usr/share/nginx/html;
            index  index.html;
        }

        # Servir os arquivos HLS (m3u8 e ts)
        location /hls {
            # O alias mapeia esta localização para o diretório onde o SRS está escrevendo os arquivos
            alias /usr/share/nginx/html/hls;

            # Adiciona os tipos MIME corretos para HLS
            types {
                application/vnd.apple.mpegurl m3u8;
                video/mp2t ts;
            }

            # Impede o cache do manifesto e segmentos para garantir a atualização ao vivo.
            add_header Cache-Control 'no-cache, no-store';
            # Cabeçalhos CORS para permitir a incorporação em outros domínios.
            add_header 'Access-Control-Allow-Origin' '*' always;
            add_header 'Access-Control-Expose-Headers' 'Content-Length,Content-Range';
            add_header 'Access-Control-Allow-Headers' 'Range';
        }

        error_page   500 502 503 504  /50x.html;
        location = /50x.html {
            root   /usr/share/nginx/html;
        }
    }
}
```

### 4.4. `web/html/index.html`

O player de vídeo web que usa `hls.js`.

```html
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Player de Streaming SRS</title>
    <style>
        body { font-family: sans-serif; background-color: #f0f0f0; margin: 0; padding: 20px; display: flex; justify-content: center; align-items: center; flex-direction: column; }
        h1 { color: #333; }
        #video-container { max-width: 800px; width: 100%; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
        video { width: 100%; display: block; background-color: #000; }
    </style>
</head>
<body>
    <h1>Meu Stream ao Vivo</h1>
    <div id="video-container">
        <video id="video" controls autoplay muted></video>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
    <script>
        document.addEventListener('DOMContentLoaded', () => {
            const video = document.getElementById('video');
            const streamName = 'live/livestream'; 
            const videoSrc = `/hls/${streamName}.m3u8`;

            if (Hls.isSupported()) {
                console.log("HLS.js é suportado. Inicializando o player.");
                const hls = new Hls();
                hls.loadSource(videoSrc);
                hls.attachMedia(video);
                hls.on(Hls.Events.MANIFEST_PARSED, function() {
                    console.log("Manifesto carregado, tentando reproduzir.");
                    video.play().catch(error => {
                        console.error("Erro ao tentar reproduzir o vídeo:", error);
                    });
                });
                hls.on(Hls.Events.ERROR, function(event, data) {
                    if (data.fatal) {
                        switch(data.type) {
                            case Hls.ErrorTypes.NETWORK_ERROR:
                                console.error("Erro de rede fatal, tentando recuperar...", data);
                                hls.startLoad();
                                break;
                            case Hls.ErrorTypes.MEDIA_ERROR:
                                console.error("Erro de mídia fatal, tentando recuperar...", data);
                                hls.recoverMediaError();
                                break;
                            default:
                                console.error("Erro fatal irrecuperável", data);
                                hls.destroy();
                                break;
                        }
                    }
                });
            } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
                console.log("Suporte nativo a HLS detectado (ex: Safari).");
                video.src = videoSrc;
                video.addEventListener('loadedmetadata', function() {
                    video.play().catch(error => {
                        console.error("Erro ao tentar reproduzir o vídeo nativamente:", error);
                    });
                });
            } else {
                alert("Seu navegador não suporta HLS.");
            }
        });
    </script>
</body>
</html>
```

## 5. Como Executar

### Passo 1: Iniciar os Serviços
Navegue até o diretório raiz do projeto (`srs-hls-platform`) e execute:
```bash
docker-compose up -d
```
Este comando irá baixar as imagens e iniciar os contêineres em segundo plano.

### Passo 2: Configurar o Encoder (OBS Studio)
Abra o OBS e configure a transmissão:
- **Serviço**: Personalizado...
- **Servidor**: `rtmp://<IP_DO_SEU_SERVIDOR>:1935/live`
  - Se estiver rodando localmente, use `rtmp://localhost:1935/live`.
  - Se estiver em uma VPS, use o IP público da VPS e **certifique-se de que a porta 1935 (TCP) está aberta no firewall**.
- **Chave do Stream**: `livestream`

**Para Baixa Latência (MUITO IMPORTANTE):**
- Vá em **Configurações > Saída**.
- Mude o **Modo de Saída** para **Avançado**.
- Na aba **Streaming**, defina o **Intervalo de Keyframe** (ou "Keyframe interval") para **2** segundos.

### Passo 3: Iniciar a Transmissão
Inicie a transmissão no seu encoder.

### Passo 4: Assistir ao Stream
Abra seu navegador e acesse:
- `http://localhost:8081` (se local)
- `http://<IP_DO_SEU_SERVIDOR>:8081` (se em VPS)

## 6. Diagnóstico e Solução de Problemas

- **Verificar logs do SRS**:
  ```bash
  docker-compose logs -f srs-server
  ```
- **Verificar logs do Nginx**:
  ```bash
  docker-compose logs -f web-server
  ```
- **Verificar se os arquivos HLS estão sendo criados**:
  ```bash
  docker exec srs-server ls -l /usr/local/srs/objs/nginx/html/live
  ```
- **Vídeo não carrega (loading infinito)**:
  1. Verifique se o endereço do servidor no encoder está correto (`localhost` vs. IP da VPS).
  2. Confirme se a porta `1935` está aberta no firewall da VPS.
  3. Verifique se a Chave do Stream corresponde ao que o player espera (`live/livestream`).
