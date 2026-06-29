# Alterações desta versão


1) Roque corrigido
------------------
Antes o sistema aceitava somente 2 casas alteradas. No roque, mudam 4 casas:
- rei: origem e destino
- torre: origem e destino

Agora o Main.py aceita 2, 3 ou 4 casas alteradas:
- 2 casas: lance normal
- 3 casas: en passant
- 4 casas: roque

O Xadrez.py compara as casas detectadas com todos os lances legais do python-chess.
Assim, se as casas e1, g1, h1 e f1 mudarem, ele entende como o lance e1g1.

2) Voz adicionada
-----------------
Foi criado o arquivo Voz.py.
Depois de cada lance válido, o programa fala a peça e a casa final, por exemplo:
- Peão para casa e 4.
- Cavalo para casa f 3.
- Rei para casa g 1. Roque pequeno.

Atalho novo:
- f: liga/desliga a voz

No Windows, a voz usa o sintetizador nativo via PowerShell/System.Speech.
No Linux, tenta usar spd-say ou espeak se estiver instalado.
No macOS, tenta usar o comando say.

3) Detecção visual ajustada para roque
--------------------------------------
O Segmentador.py não corta mais a lista para apenas 2 casas alteradas.
Ele retorna todas as casas candidatas, e o Main.py decide quando aceitar ou ignorar.
Se aparecerem mais de 4 casas, o sistema considera que provavelmente é mão/sombra/ruído e espera estabilizar.

4) Interface web corrigida e aprimorada
---------------------------------------
- Corrigido o arquivo JavaScript da interface: o HTML chamava `main.js`, mas o projeto trazia `main.j_`.
- Adicionado painel visual de status para câmera, calibração, rastreio e voz.
- Adicionados FEN atual, vez do jogador e histórico mais legível.
- O botão **Salvar referência** agora inicia o rastreio automaticamente.
- A calibração manual aceita os quatro cantos e ordena os pontos antes de aplicar a perspectiva.
- A configuração de voz do modal agora atualiza o backend, incluindo ligar/desligar voz.
- O rastreio passou a usar o frame bruto da câmera, evitando aplicar a retificação duas vezes.
- Adicionados tratamentos de erro no frontend para câmera ausente, calibração inválida e ações fora de ordem.
- Dependências Flask e Flask-SocketIO adicionadas a `requirements.txt` e `pyproject.toml`.

5) Detecção de movimentos mais robusta
--------------------------------------
O detector visual foi refeito para reduzir falsos positivos quando o tabuleiro ou a câmera mexem um pouco.

Principais mudanças:
- Antes de comparar as casas, o sistema tenta alinhar o frame atual com a referência usando compensação de deslocamento global.
- Pequenas tremidas do tabuleiro/câmera deixam de aparecer como lance.
- A comparação por casa passou a usar LAB + compensação local de iluminação, em vez de depender só de diferença simples em escala de cinza.
- A mudança precisa ocupar uma área conectada mínima, parecida com a base de uma peça, o que reduz disparos por ruído, sombra fina ou reflexo.
- O rastreio web agora espera alguns frames estáveis antes de salvar a referência.
- Se muitas casas mudarem ao mesmo tempo, o sistema ignora como ruído global em vez de tentar registrar um lance.
- Foram adicionados testes para garantir que deslocamento global do tabuleiro não registra movimento e que um lance real continua sendo detectado mesmo com pequena tremida.

Arquivos principais alterados:
- `src/xadrez_sem_barreiras/segmentador.py`
- `src/xadrez_sem_barreiras/app.py`
- `web/app.py`
- `web/static/js/main.js`
- `tests/test_segmentador.py`
