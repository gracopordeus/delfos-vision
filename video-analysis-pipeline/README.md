# Pipeline de Análise de Vídeo com Detecção de Objetos e Estimativa de Distância

## Visão Geral

Este projeto implementa uma pipeline de processamento de vídeo de ponta a ponta, focada em detecção de objetos e estimativa de distância em tempo real, otimizada para inferência em CPU. A solução utiliza GStreamer para manipulação de fluxo de vídeo, Python para a lógica de processamento e ONNX Runtime para inferência de modelos de detecção de objetos. O vídeo processado, com as sobreposições de detecção e distância, é retransmitido via protocolo SRT (Secure Reliable Transport) para baixa latência e alta confiabilidade.

**Arquitetura de Alto Nível:**

- **Entrada de Vídeo:** GStreamer ingere fluxos de vídeo de arquivos ou fontes de rede (ex: RTSP).
- **Processamento em Python:** Frames decodificados são passados para scripts Python via `appsink`.
- **Detecção de Objetos:** Modelos ONNX (preferencialmente quantizados INT8) são utilizados para inferência em CPU via ONNX Runtime.
- **Estimativa de Distância:** Um método geométrico de baixo custo computacional estima a distância para cada objeto detectado.
- **Sobreposição Visual:** Caixas delimitadoras e informações de distância são desenhadas nos frames usando OpenCV.
- **Saída de Vídeo:** Frames processados são enviados de volta ao GStreamer via `appsrc`, codificados em H.265 (HEVC) e transmitidos via SRT.

## Instalação

### Dependências do Sistema (GStreamer)

Para sistemas baseados em Debian/Ubuntu, instale os seguintes pacotes GStreamer:

```bash
sudo apt update
sudo apt install -y python3-gi python3-gst-1.0 gir1.2-gstreamer-1.0 gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-libav
```

Para outras distribuições Linux ou sistemas operacionais, consulte a documentação oficial do GStreamer para a instalação dos pacotes de desenvolvimento e plugins necessários.

### Dependências Python

Navegue até o diretório raiz do projeto e instale as dependências Python usando `pip`:

```bash
cd /Users/glauco.pordeus/gemini_projects/video-analysis-pipeline
pip install -r requirements.txt
```

## Estrutura do Projeto

```
video-analysis-pipeline/
├── scripts/
│   ├── main.py             # Script principal da pipeline
│   ├── quantize_model.py   # Script para quantização de modelos ONNX
│   └── calibrate.py        # Script para calibração da câmera
├── models/
│   ├── mobilenet_ssd.onnx          # Placeholder para o modelo FP32 original
│   └── mobilenet_ssd_quantized.onnx # Placeholder para o modelo INT8 quantizado
├── data/                   # Para imagens de teste e calibração
├── utils/
│   └── estimate_distance.py # Funções auxiliares para estimativa de distância
├── config.json             # Arquivo de configuração (distância focal, larguras de objetos)
└── requirements.txt        # Dependências Python
```

## Aquisição e Otimização do Modelo de Detecção

Este projeto espera um modelo MobileNet-SSD no formato ONNX. Para otimização de desempenho em CPU, é altamente recomendada a quantização do modelo para INT8.

1.  **Selecionar e Baixar o Modelo Base:**
    Pesquise e baixe um modelo MobileNet-SSD pré-treinado. Fontes recomendadas incluem o TensorFlow Model Zoo.

2.  **Converter o Modelo para ONNX (se necessário):**
    Se o seu modelo estiver em outro formato (ex: TensorFlow SavedModel), utilize ferramentas como `tf2onnx` para convertê-lo para `.onnx`.

3.  **Quantização Pós-Treinamento (PTQ):**
    Utilize o script `scripts/quantize_model.py` para quantizar o modelo ONNX de FP32 para INT8. Este processo requer um pequeno conjunto de dados de calibração (algumas imagens representativas) no diretório `data/`.

    ```bash
    python scripts/quantize_model.py
    ```
    *Nota: O script `quantize_model.py` atual é um placeholder. A implementação completa da quantização com `onnxruntime.quantization` precisará ser adicionada.*

4.  **Benchmark de Desempenho:**
    Após a quantização, é crucial medir e comparar o tempo de inferência e a precisão entre o modelo FP32 original e o modelo INT8 quantizado para justificar a escolha do modelo otimizado. Os resultados devem ser documentados nesta seção.

    **Resultados do Benchmark (Placeholder):**
    | Modelo             | Tempo de Inferência (ms/frame) | Precisão (mAP) |
    | :----------------- | :----------------------------- | :------------- |
    | MobileNet-SSD FP32 | X                              | Y              |
    | MobileNet-SSD INT8 | Z (esperado 2x-4x mais rápido) | W (perda mínima) |

## Calibração da Câmera

A estimativa de distância requer a distância focal da câmera. Utilize o script `scripts/calibrate.py` para calculá-la:

1.  Coloque um objeto de referência com largura real conhecida (ex: uma folha A4) a uma distância conhecida da câmera.
2.  Capture uma imagem deste cenário.
3.  Execute o script de calibração:

    ```bash
    python scripts/calibrate.py
    ```
    O script calculará a distância focal e a salvará automaticamente no `config.json`.

    *Nota: O script `calibrate.py` atual é um placeholder. Você precisará adaptá-lo para detectar o objeto de referência na imagem e medir sua largura em pixels.*

## Configuração (`config.json`)

O arquivo `config.json` armazena parâmetros essenciais para a pipeline:

```json
{
    "camera_focal_length_pixels": 0.0,
    "object_real_widths_cm": {
        "person": 50,
        "car": 180,
        "bicycle": 20,
        "motorcycle": 30,
        "bus": 250,
        "truck": 250
    }
}
```

-   `camera_focal_length_pixels`: A distância focal da câmera em pixels, calculada pelo script de calibração.
-   `object_real_widths_cm`: Um dicionário mapeando classes de objetos (conforme detectadas pelo modelo) às suas larguras reais médias em centímetros.

## Execução da Aplicação

Para iniciar a pipeline de análise de vídeo, execute o script `main.py` fornecendo a URI de entrada do vídeo e a URI de saída SRT:

```bash
python scripts/main.py --input-uri "file:///path/to/your/video.mp4" --srt-output-uri "srt://<ip_destino>:<porta>"
```

**Parâmetros:**

-   `--input-uri`: A URI da fonte de vídeo. Pode ser um caminho de arquivo local (ex: `file:///home/user/video.mp4`), ou uma URL de stream (ex: `rtsp://your_camera_ip/stream`).
-   `--srt-output-uri`: A URI de destino para o stream SRT. Formato: `srt://<endereço_ip_destino>:<porta>`.

**Exemplo:**

```bash
# Para processar um arquivo de vídeo local e transmitir para localhost na porta 1234
python scripts/main.py --input-uri "file:///home/user/videos/sample.mp4" --srt-output-uri "srt://127.0.0.1:1234"

# Para processar um stream RTSP e transmitir para um servidor SRT remoto
python scripts/main.py --input-uri "rtsp://your_camera_ip/live" --srt-output-uri "srt://your_srt_server_ip:5000"
```

## MLOps / Deploy

### Conteinerização (Docker)

Recomenda-se conteinerizar a aplicação usando Docker para garantir um ambiente consistente e reprodutível em diferentes estágios (desenvolvimento, teste, produção). Um `Dockerfile` pode ser criado para empacotar todas as dependências do sistema (GStreamer) e Python.

### Gerenciamento de Configurações

As configurações como o caminho do modelo, URI de entrada/saída e parâmetros de calibração podem ser gerenciadas de forma flexível:

-   **Variáveis de Ambiente:** Para ambientes de produção, é uma prática comum usar variáveis de ambiente para injetar configurações sensíveis ou específicas do ambiente.
-   **Argumentos de Linha de Comando:** Conforme demonstrado no `main.py`, os parâmetros de entrada e saída já são configuráveis via argumentos de linha de comando, facilitando a automação e o deploy.
-   **Arquivo `config.json`:** Para configurações menos dinâmicas, o `config.json` serve como um repositório central.

Ao implantar, certifique-se de que o modelo ONNX (preferencialmente o quantizado) esteja acessível no caminho especificado e que o `config.json` contenha os valores de calibração corretos e as larguras reais dos objetos.
