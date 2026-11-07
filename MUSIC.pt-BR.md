# KenoForge 1.5.24 — Music Center

Integração do player de música do MediaDeck 0.6.5.0 ao KenoForge.

## Atualizar o KenoForge

Extraia o pacote e, dentro da pasta `KenoForge-1.5.24`, execute como seu usuário:

```bash
./install.sh --check
./install.sh
```

O instalador faz uma cópia da versão anterior. Não execute o instalador inteiro
com sudo. As configurações de música ficam em `~/.kenoforge/Config/MediaDeck`,
fora do código substituído durante a atualização.

## Primeiro uso

1. Abra `kenoforge` em um terminal da sua sessão gráfica.
2. Entre em **Music Center → Install Music Dependencies**.
3. Revise os pacotes e confirme a instalação pelo Pacman.
4. Entre em **Open Music Player**.
5. Clique em **Escolher pasta** e selecione sua biblioteca de músicas.

Também é possível usar:

```bash
kenoforge-music --status
kenoforge-music --install-deps
kenoforge-music
```

Para liberar o terminal imediatamente, use `kenoforge-music --detach`.
Pelo menu, o player já abre separado do console. Fechar o KenoForge não encerra
essa janela. Use **Fechar player** para parar a reprodução e encerrar o aplicativo.

## Recursos

- Biblioteca de arquivos locais com busca, artistas, álbuns e capas.
- Favoritos, músicas recentes, playlists e fila de reprodução persistentes.
- Aleatório, repetição, avanço de faixa, pausa e controle de posição.
- Volume próprio do player, sem alterar o volume global do computador.
- Spectrum e seis modos de visualização, com botão para desligar a captura.
- O botão **Tela inteira** na barra superior amplia o player; **Sair da tela
  inteira** restaura a janela. F11 também alterna esse modo; Esc volta da
  visualização à biblioteca.
- Uma instância por configuração, para evitar disputa sobre as playlists.

O leitor considera MP3, FLAC, OGG, Opus, WAV, M4A, AAC e WMA. A reprodução de
cada arquivo depende do suporte do backend multimídia e dos codecs instalados.
Não inclui streaming, login Spotify, busca online nem download de músicas.

## Onde os dados ficam

| Conteúdo | Local padrão |
| --- | --- |
| Biblioteca, favoritos, fila e playlists | `~/.kenoforge/Config/MediaDeck/music.json` |
| Preferência do visualizador | `~/.kenoforge/Config/MediaDeck/visualizer.json` |
| Cache das capas | `~/.kenoforge/Cache/MediaDeck/covers` |
| Log da abertura pelo menu | `~/.kenoforge/Logs/MediaDeck/player.log` |

As músicas continuam na pasta escolhida. Não são copiadas para o KenoForge nem
incluídas automaticamente nos backups de configurações. O comando respeita
`KENOFORGE_DATA_HOME` quando definido; use o mesmo valor em todas as aberturas.

## Dependências e sessão

O Music Center instala apenas os pacotes opcionais listados pelo seu comando
de instalação. Usa o ambiente gráfico e o áudio já configurados no computador.
Não executa o instalador de sessão dedicada do MediaDeck. Não altera login,
GRUB, autostart, serviços de rede, grupos do usuário nem a configuração do áudio.

O visualizador analisa o monitor da saída de som via `parec`, podendo reagir
também a outros sons do computador. Sem monitor de áudio disponível, o player
continua funcionando e o visualizador informa sua indisponibilidade.

Referências dos pacotes: [Qt Multimedia FFmpeg](https://archlinux.org/packages/extra/x86_64/qt6-multimedia-ffmpeg/)
e [libpulse / parec](https://archlinux.org/packages/extra/x86_64/libpulse/files/).

## Diagnóstico

Se a janela não aparecer, consulte **Player Status** e o log indicado. Execute
`kenoforge-music` em primeiro plano para ver mensagens diretamente no terminal.
Em TTY, o KenoForge continua disponível, mas o player precisa de uma sessão gráfica.

Validação desta integração: testes de biblioteca e persistência, decodificação
real de WAV pelo Qt, carregamento e renderização QML e testes isolados do
instalador. O ambiente de desenvolvimento não tem saída física de áudio: som
audível, codecs variados, Bluetooth e aceleração gráfica devem ser conferidos
no computador de destino.
