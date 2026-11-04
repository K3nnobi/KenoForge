# Correção da transparência de miniaturas do Nautilus

O patch anterior podia ignorar o reparo ao encontrar uma marca antiga no CSS.
Também não contemplava a classe `.nautilus-image.file-thumbnail`, usada pelo
Nautilus atual. A correção atualiza somente o bloco gerenciado pelo KenoForge,
preserva outras regras e guarda uma cópia do CSS antes da alteração.

## Aplicar

Termine eventuais cópias/movimentações de arquivos antes de encerrar o Nautilus.
Extraia este pacote e, dentro da pasta `KenoForge-1.5.23`, execute como seu usuário:

```bash
./install.sh
bash "$HOME/KenoForge/System/Core/tools/configure-nautilus.sh" --transparency-only
nautilus -q
```

Reabra o aplicativo Arquivos. Não é necessário reiniciar o computador.
O modo `--transparency-only` não instala pacotes, não apaga o cache de miniaturas
e não encerra o Nautilus automaticamente. O último comando acima encerra o
aplicativo para que a próxima abertura carregue o CSS novo.

Para testar o reparo antes de atualizar a instalação inteira, também é possível
executar diretamente, dentro da pasta extraída:

```bash
python3 payload/kenoforge/tools/nautilus-thumbnail-css.py --apply
```

## Diagnóstico e reversão

```bash
python3 "$HOME/KenoForge/System/Core/tools/nautilus-thumbnail-css.py" --status
python3 "$HOME/KenoForge/System/Core/tools/nautilus-thumbnail-css.py" --remove
```

`--remove` retira somente o bloco do KenoForge e faz backup antes da alteração.
As cópias ficam em `~/KenoForge/Installer-Backups/gtk.css-before-nautilus-*`.
O destino padrão é `~/.config/gtk-4.0/gtk.css`; `XDG_CONFIG_HOME` é respeitado.

Esta correção trata o fundo desenhado pelo Nautilus. Não altera pixels do ícone
extraído do executável. Se o fundo persistir, precisamos conferir a versão do
Nautilus e a própria miniatura antes de modificar o extrator de ícones.
