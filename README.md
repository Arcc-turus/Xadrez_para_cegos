# Xadrez Sem Barreiras

Projeto em Python para acompanhar um tabuleiro físico de xadrez por câmera, detectar movimentos, atualizar o estado da partida em FEN e falar o lance realizado.

## O que o projeto faz

- Captura vídeo da webcam com OpenCV.
- Permite calibrar as 4 quinas do tabuleiro manualmente ou tentar calibração automática.
- Divide o tabuleiro em 8x8 casas.
- Detecta mudanças visuais nas casas.
- Usa `python-chess` para validar os lances.
- Suporta lances normais, en passant e roque.
- Salva o FEN da posição atual.
- Usa voz para anunciar [peça] [posição inicial] [posição final].

## Estrutura do repositório

```text
xadrez-sem-barreiras/
├── src/xadrez_sem_barreiras/
│   ├── app.py
│   ├── camera.py
│   ├── segmentador.py
│   ├── tradutor.py
│   ├── voz.py
│   └── xadrez.py
├── tests/
├── data/
├── assets/
├── docs/
├── pyproject.toml
├── requirements.txt
├── run.py
├── .gitignore
└── README.md
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

## Como executar

### Interface web

```bash
python run.py --web
# Acesse http://localhost:5000
```

Forma recomendada:

```bash
pip install -e .
xadrez-sem-barreiras --camera 1
```

Atalho simples:

```bash
python run.py --camera 1
```

Se a câmera não abrir, teste outros índices:

```bash
python run.py --camera 0
python run.py --camera 2
```


## Interface web atualizada

A interface web agora inclui painel de status, histórico de jogadas, FEN atual, configuração de voz no navegador e botão de máscara de diferença. Depois de calibrar, use **Salvar referência** para iniciar o rastreio automaticamente.

## Velocidade da voz

Use a flag `--voz` para ajustar a velocidade da fala. Aceita valores de 1.0 a 4.0 (com uma casa decimal):

```bash
python run.py --voz 2.0     # 2x mais rápido que o normal
python run.py --voz 3.5     # 3.5x mais rápido
python run.py --voz 1.0     # velocidade normal (padrão)
```

Se usar `--sem-voz`, a voz fica desligada independente da velocidade.

### Alfabeto fonético NATO

Use a flag `--voz-af` para que a voz anuncie as letras da coluna no alfabeto fonético NATO (Alpha, Bravo, Charlie...). Aceita um valor opcional de velocidade:

```bash
python run.py --voz-af          # fonético, velocidade normal
python run.py --voz-af 2.0      # fonético, 2x mais rápido
python run.py --voz-af 3.5      # fonético, 3.5x mais rápido
```

Combinações disponíveis:

| Comando | Exemplo de voz |
|---|---|
| (padrão) | `Peão e 2 e 4.` |
| `--voz-af` | `Peão Echo 2 Echo 4.` |
| `--voz-af 2.0` | `Rei Echo 1 Golf 1. Roque pequeno.` |
| `--voz 2.0` | `Peão e 2 e 4.` (mais rápido) |
| `--sem-voz` | (silêncio) |

### Janela de configuração de voz

Dentro do programa, pressione `f` para abrir uma janela com:
- **Toggle "Voz ativa"** — liga/desliga a voz
- **Toggle "Alfabeto fonético NATO"** — usa Alpha, Bravo, Charlie...
- **Slider de velocidade** — de 1.0x a 4.0x, mostra o valor atual ao arrastar

## Comandos dentro do programa

| Tecla | Função |
|---|---|
| `c` | Calibrar manualmente as quinas do tabuleiro |
| `v` | Tentar calibração automática |
| `s` | Salvar o estado visual atual como referência |
| `f` | Abrir janela de configuração de voz |
| `z` | Desfazer o último lance |
| `r` | Reiniciar a partida |
| `q` | Sair |

## Arquivos gerados

Durante a execução, o programa salva arquivos dentro da pasta `data/`:

- `estado_partida.fen`: posição atual do tabuleiro em FEN.
- `estado_visual_pecas.jpg`: imagem retificada usada como referência visual.

Esses arquivos são ignorados pelo Git para não sujar o repositório.

## Voz no sistema

A voz anuncia cada lance no formato: **[peça] [posição inicial] [posição final]**.

Exemplos:
- `Peão e2 e4.`
- `Cavalo g1 f3.`
- `Rei e1 g1. Roque pequeno.`
- `Rei e1 c1. Roque grande.`
- `Peão e7 e8. Promoção para Dama.`

### Motores de voz

- Windows: usa o sintetizador nativo via PowerShell.
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

## Desenvolvimento

Verificar se os arquivos compilam:

```bash
python -m compileall src tests
```

Rodar testes simples:

```bash
pytest
```
