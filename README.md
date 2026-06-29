# Xadrez Sem Barreiras

Sistema em Python para acompanhar um tabuleiro físico de xadrez por câmera, detectar movimentos, validar lances, manter o estado da partida em FEN e anunciar os lances por voz.

O projeto pode ser usado por uma **interface web** ou por uma **janela local do OpenCV**. A versão atual prioriza a interface web, com seleção de câmera, calibração visual, histórico de lances, FEN em tempo real, configuração de voz e diagnóstico da detecção.

## Principais recursos

- Captura de vídeo com OpenCV.
- Interface web com painel de status, câmera ao vivo e máscara de diferença.
- Calibração manual pelas quatro quinas do tabuleiro.
- Tentativa de calibração automática quando o tabuleiro está bem visível.
- Correção de perspectiva para transformar o tabuleiro físico em uma imagem 8x8.
- Detecção de movimentos com redução de falsos positivos por tremida, sombra e deslocamento leve.
- Validação dos lances com a biblioteca `chess`.
- Suporte a lances normais, capturas, roque, en passant e promoção.
- Histórico de jogadas e FEN atual.
- Voz configurável: ligada/desligada, velocidade e alfabeto fonético NATO.
- Salvamento automático do estado da partida e da referência visual em `data/`.
- Testes automatizados para regras, tradução, pipeline visual e interface web.

## Como a detecção funciona agora

A detecção foi ajustada para evitar o problema de registrar qualquer movimento mínimo do tabuleiro como lance.

O fluxo atual é:

1. O tabuleiro é calibrado e retificado para uma imagem quadrada de 800x800.
2. Ao clicar em **Salvar referência**, o sistema espera alguns frames estáveis antes de gravar a imagem base.
3. Em cada frame novo, o detector tenta alinhar o frame atual com a referência usando compensação de deslocamento global.
4. Cada casa é comparada em uma região de interesse mais segura, evitando bordas e linhas da grade.
5. A comparação usa espaço de cor LAB e compensação local de iluminação.
6. A mudança precisa formar uma área conectada mínima, parecida com a base de uma peça.
7. Se muitas casas mudarem ao mesmo tempo, o sistema considera ruído global, mão passando, sombra forte ou tabuleiro mexendo, e ignora o frame.
8. O lance só é confirmado depois de permanecer estável por tempo suficiente e ser compatível com um lance legal de xadrez.

Isso deixa o sistema menos sensível a pequenas tremidas da câmera ou do tabuleiro.

## Requisitos

- Python 3.10 ou superior.
- Webcam ou câmera USB.
- Navegador moderno para usar a interface web.
- Boa iluminação sobre o tabuleiro.
- Tabuleiro físico bem enquadrado na câmera.

Dependências principais:

```txt
numpy
opencv-python
chess
Flask
Flask-SocketIO
simple-websocket
pytest
```

## Instalação

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Instalação em modo editável

Opcional, mas útil para desenvolvimento:

```bash
pip install -e .
```

Depois disso, o comando `xadrez-sem-barreiras` fica disponível no terminal.

## Como executar

### Modo web recomendado

```bash
python run.py --web
```

Depois acesse:

```text
http://localhost:5000
```

A interface web roda em `0.0.0.0:5000`, então também pode ser acessada por outro dispositivo na mesma rede usando o IP da máquina, por exemplo:

```text
http://192.168.0.10:5000
```

### Modo local com OpenCV

```bash
python run.py --camera 0
```

ou, se instalou em modo editável:

```bash
xadrez-sem-barreiras --camera 0
```

Se a câmera não abrir, teste outros índices:

```bash
python run.py --camera 1
python run.py --camera 2
```

## Fluxo recomendado na interface web

1. Inicie o servidor com `python run.py --web`.
2. Abra `http://localhost:5000`.
3. Selecione a câmera.
4. Posicione o tabuleiro inteiro dentro da imagem.
5. Calibre o tabuleiro:
   - use calibração manual para mais precisão;
   - clique nas quatro quinas da área jogável do tabuleiro.
6. Arrume as peças na posição inicial ou na posição desejada.
7. Clique em **Salvar referência**.
8. Aguarde o sistema indicar que a referência foi salva.
9. Faça um lance físico no tabuleiro.
10. Mantenha o tabuleiro parado por alguns segundos até o lance ser confirmado.

Depois de desfazer um lance, reiniciar a partida ou mexer manualmente nas peças, salve uma nova referência.

## Fluxo recomendado no modo local

Ao abrir a janela do OpenCV, use estas teclas:

| Tecla | Função |
|---|---|
| `c` | Calibrar manualmente as quinas do tabuleiro |
| `v` | Tentar calibração automática |
| `s` | Salvar o estado visual atual como referência |
| `f` | Abrir a janela de configuração de voz |
| `z` | Desfazer o último lance |
| `r` | Reiniciar a partida |
| `q` | Sair |

Ordem sugerida:

1. Pressione `c` para calibrar manualmente ou `v` para tentar automático.
2. Pressione `s` para salvar a referência visual.
3. Faça um lance no tabuleiro físico.
4. Aguarde a confirmação do lance.
5. Use `z` para desfazer ou `r` para reiniciar, se necessário.

## Voz

A voz anuncia os lances no formato:

```text
[peça] [casa inicial] [casa final]
```

Exemplos:

- `Peão e2 e4.`
- `Cavalo g1 f3.`
- `Rei e1 g1. Roque pequeno.`
- `Rei e1 c1. Roque grande.`
- `Peão e7 e8. Promoção para Dama.`

### Configurar velocidade

```bash
python run.py --voz 1.0
python run.py --voz 2.0
python run.py --voz 3.5
```

A velocidade aceita valores de `1.0` a `4.0`.

### Desligar voz

```bash
python run.py --sem-voz
```

### Usar alfabeto fonético NATO

```bash
python run.py --voz-af
python run.py --voz-af 2.0
```

Exemplos de saída:

| Configuração | Exemplo |
|---|---|
| Padrão | `Peão e 2 e 4.` |
| `--voz-af` | `Peão Echo 2 Echo 4.` |
| `--voz-af 2.0` | `Rei Echo 1 Golf 1. Roque pequeno.` |
| `--sem-voz` | Sem anúncio de voz |

### Motores de voz por sistema

- Windows: sintetizador nativo via PowerShell/System.Speech.
- Linux: tenta usar `spd-say` ou `espeak`.
- macOS: tenta usar `say`.

No Linux, instale um sintetizador se necessário:

```bash
sudo apt install speech-dispatcher espeak
```

ou, no Fedora:

```bash
sudo dnf install speech-dispatcher espeak
```

## Opções de linha de comando

```bash
python run.py [opções]
```

| Opção | Descrição |
|---|---|
| `--web` | Inicia a interface web em `localhost:5000` |
| `--camera 0` | Escolhe o índice da câmera |
| `--sem-voz` | Inicia com a voz desligada |
| `--voz 2.0` | Define a velocidade da voz |
| `--voz-af` | Usa alfabeto fonético NATO |
| `--voz-af 2.0` | Usa NATO com velocidade personalizada |
| `--tempo-confirmacao 2.0` | Define o tempo de estabilidade antes de confirmar um lance no modo local |
| `--data-dir data` | Define a pasta para salvar FEN e referência visual |
| `--posicao-camera brancas_esquerda` | Define a orientação usada para traduzir linhas/colunas em casas |

## Arquivos gerados

Durante a execução, o sistema pode salvar arquivos em `data/`:

| Arquivo | Função |
|---|---|
| `estado_partida.fen` | Estado atual da partida em FEN |
| `estado_visual_pecas.jpg` | Imagem de referência usada pela detecção visual |

Esses arquivos representam o estado local da execução e podem ser recriados.

## Estrutura do projeto

```text
xadrez_sem_barreiras-voz-gui-opencv/
├── assets/
├── data/
├── docs/
│   └── ALTERACOES.md
├── src/
│   └── xadrez_sem_barreiras/
│       ├── app.py
│       ├── camera.py
│       ├── segmentador.py
│       ├── tradutor.py
│       ├── voz.py
│       ├── voz_gui.py
│       └── xadrez.py
├── tests/
├── web/
│   ├── app.py
│   ├── static/
│   │   ├── css/style.css
│   │   └── js/main.js
│   └── templates/index.html
├── pyproject.toml
├── requirements.txt
├── run.py
└── README.md
```

## Testes

Verificar sintaxe dos arquivos Python:

```bash
python -m compileall -q src web run.py tests
```

Rodar todos os testes:

```bash
pytest
```

Rodar apenas os testes principais de visão:

```bash
PYTHONPATH=src pytest -q tests/test_segmentador.py tests/test_cenarios_realistas.py
```

Verificar o JavaScript da interface:

```bash
node --check web/static/js/main.js
```

## Dicas para melhorar a detecção na prática

- Use iluminação uniforme, sem sombras fortes atravessando o tabuleiro.
- Evite reflexos em peças brilhantes ou casas plastificadas.
- Fixe a câmera para não balançar.
- Evite encostar no tabuleiro depois de salvar a referência.
- Depois de qualquer ajuste físico grande, clique em **Salvar referência** novamente.
- Faça um lance por vez e tire a mão do tabuleiro antes de esperar a confirmação.
- Na calibração manual, clique nas quinas da área jogável, não na borda externa decorativa.
- Se a detecção estiver instável, confira a máscara de diferença na interface web.

## Solução de problemas

### A câmera não abre

Teste outro índice:

```bash
python run.py --camera 0
python run.py --camera 1
python run.py --camera 2
```

No modo web, use o seletor de câmera da interface.

### O sistema detecta movimentos falsos

- Salve a referência novamente com o tabuleiro parado.
- Melhore a iluminação.
- Fixe melhor a câmera.
- Evite que a mão fique sobre o tabuleiro durante a confirmação.
- Confira se a calibração está alinhada com as casas.

### O lance real não é detectado

- Verifique se a referência foi salva depois que as peças estavam na posição correta.
- Confira se a peça realmente mudou de casa e não ficou entre duas casas.
- Confira se o lance é legal na posição atual do jogo.
- Se o estado físico e o FEN divergirem, reinicie a partida ou desfaça o lance e salve nova referência.

### A calibração automática falha

A calibração automática depende muito da imagem. Para melhores resultados:

- deixe o tabuleiro vazio;
- use fundo contrastante;
- evite sombras;
- enquadre todo o tabuleiro;
- se ainda falhar, use a calibração manual.

### A voz não sai no Linux

Instale `speech-dispatcher` ou `espeak`:

```bash
sudo apt install speech-dispatcher espeak
```

## Observações importantes

Este projeto usa visão computacional simples e validação por regra de xadrez. Ele não identifica peças individualmente por tipo; ele detecta quais casas mudaram e usa o estado atual da partida para inferir o lance legal correspondente.

Por isso, a posição física das peças e o FEN interno precisam estar sincronizados. Se alguém mexer nas peças sem o sistema registrar, salve uma nova referência ou reinicie o estado da partida.

## Copyright

Copyright © 2026 Arthur Gabriel, David Lucca, Matheus Pierry, Lageilson Gabriel e Pedro Henrique. Todos os direitos reservados.
