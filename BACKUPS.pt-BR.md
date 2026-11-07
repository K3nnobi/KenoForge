# KenoForge 1.5.24 — backups e recuperação

Build: `1.5.24-hidden-home-20261106`. Atualização integrada ao gerenciador,
aos atalhos AFI e às entradas de compatibilidade do Toolkit.

## Atualizar

Extraia este pacote e execute `./install.sh --check`. Depois execute
`./install.sh` como seu usuário normal. O instalador mantém suas cópias de
segurança e preferências; não execute o KenoForge com sudo.

O diretório padrão agora é `~/.kenoforge/Backups`. Ao atualizar, o
instalador move o antigo `~/KenoForge` com as cópias existentes. Backups
feitos na raiz anterior continuam legíveis.

Crie **um novo backup completo** após atualizar. Uma atualização do programa
não acrescenta retroativamente os dados que faltam em arquivos antigos.

## Cobertura

| Componente | Completo | Configurações | Projeto |
| --- | --- | --- | --- |
| Config, Zsh, preferências do MediaDeck e CSS Nautilus | Sim | Sim | Não |
| Launchers MIME personalizados em `.local/share/applications` | Sim | Sim | Não |
| Estado de manutenção, seleção de patches e tarefas pendentes | Sim | Sim | Não |
| Logs e material de recuperação gerenciado pelos patches | Sim | Sim | Não |
| Cópias Wine `backup`, `work`, original preservado e cópia reparada retida, quando registradas | Sim | Sim | Não |
| Core e Toolkit, com identificação de build | Sim | Não | Sim |
| GNOME e listas de pacotes | Sim | Não | Não |
| Arquivos pessoais de música/vídeo e prefixos Wine ativos | Não | Não | Não |

O manifesto inclui o escopo efetivamente capturado e suas exclusões. Cache de
capas é regenerável. O backup não é uma imagem do sistema, do Home ou das
instalações Steam. Backups antigos completos do instalador, outros arquivos
`.kenoforge` e cópias genéricas de restauração não são incluídos recursivamente.
O material Firefox em `Backups/Safety/firefox-chatgpt-emoji` e os recibos e
snapshots dos patches reconhecidos são incluídos como dados offline.

Feche os programas Wine antes de criar a cópia. A captura verifica processos e
integridade dos snapshots de reparo Wine e recusa publicação se esses dados
mudarem. Ela não inicia Wine, não executa EXEs e não altera Steam ou drivers.
Um backup de configurações que inclua material de recuperação pode ser grande;
espaço insuficiente ou falha de leitura interrompe a criação, sem publicar uma
cópia incompleta. Evite alterações nas configurações enquanto cria o backup;
não há snapshot transacional de todo o Home.

## Integridade e publicação

Os nomes usam horário com nanossegundos e identificador aleatório. O arquivo é
gravado temporariamente, extraído e validado antes de ser publicado sem
sobrescrever outro backup. Falhas deixam os arquivos anteriores intactos.
O SHA-256 externo é consultado quando o arquivo `.sha256` acompanha o backup.
Leve ambos ao copiar um backup para outro disco.

O formato 3 registra todos os caminhos, tipos, permissões, hashes de arquivos
e destinos literais de links. Conteúdo extra, ausente ou adulterado é recusado.
A extração recusa caminhos absolutos, travessia `..`, duplicatas, dispositivos,
hardlinks externos e arquivos sob links. Links são preservados como links,
sem escrita em seus destinos. Restauração recusa diretórios de destino ou
ancestrais ligados simbolicamente; selecione um destino real e revise o link.
Arquivos regulares são substituídos atomicamente, sem escrever por hardlinks.
Esses checksums detectam corrupção; não são assinatura de autenticidade.

## Restaurar e migrar

1. Instale primeiro esta versão no usuário de destino.
2. Escolha o backup no menu de restauração. Confira o resumo e os componentes.
3. O gerenciador faz uma cópia de segurança das configurações atuais em
   `Backups/Safety/before-restore-*` antes de restaurar dados.
4. Configurações e estado de manutenção voltam para o novo usuário. Referências
   dentro do Home antigo no JSON do player e do monitoramento Wine são
   remapeadas. Caminhos externos e arquivos pessoais ausentes precisam ser
   revistos na biblioteca do player ou no diagnóstico Wine.
5. Os quatro launchers oficiais são recriados para a instalação atual. Arquivos
   `.desktop` personalizados são preservados; comandos particulares que usem
   caminhos absolutos externos devem ser revistos pelo usuário.
6. A seleção de patches volta, mas as unidades da persistência são geradas com
   os novos caminhos **sem habilitar ou iniciar o timer**. Revise a seleção no
   Centro de Manutenção → Persistência dos patches e habilite quando desejar.
   Se um timer já estiver rodando na sessão, desative-o pelo menu antes de
   restaurar o estado. A restauração não controla serviços já carregados.
7. A rota completa mantém as integrações opcionais de desktop que já eram
   reaplicadas pelo gerenciador. Recuperação Wine offline não executa esses
   reparos nem inicia prefixos.

Configurações Zsh executáveis devem ser arquivos regulares. Se uma cópia tiver
`.zshrc` ou os arquivos canônicos de aliases/p10k ligados simbolicamente, a
validação recusa o backup; organize esses arquivos antes de criar outra cópia.

O código do backup é recuperado em `~/.kenoforge/Recovered-Projects/snapshot-*`,
com Core e Toolkit separados. **Nenhum snapshot substitui automaticamente o
runtime ativo**, inclusive quando tem o mesmo número de versão. Use o
instalador da versão desejada para ativar código. Isso evita misturar Toolkit
atual com Core antigo ou remover módulos novos durante a própria restauração.
O identificador de build é guardado no manifesto e no snapshot recuperado.

Para desfazer uma restauração de dados, encerre programas, revise a pasta
`Backups/Safety/before-restore-*` correspondente e recupere os itens necessários.
A rotina de cópia segura pode ser usada, por exemplo:

```bash
python3 -B "$HOME/.kenoforge/System/Core/tools/backup_engine.py" copy \
  "/caminho/before-restore-IDENTIFICADOR/.kenoforge/Config" "$HOME/.kenoforge/Config"
```

Essa operação mescla os arquivos presentes na cópia anterior; não remove
arquivos novos criados posteriormente. Os snapshots anteriores permanecem
intactos para revisão. Não apague prefixos nem pastas de recuperação para
contornar uma falha de restauração.

## Recuperação Wine portátil

Os dados ficam em `~/.kenoforge/Recovered-Data/backup-*/recovery`. Os logs são
preservados separadamente na mesma área de recuperação. Recibos antigos mantêm
os caminhos e identificadores originais como evidência; **não são importados
como sessões ativas**. Identidades de dispositivo/inode perdem validade após
copiar para outro disco.

No menu Restauração → Opções avançadas → **Recuperar snapshot Wine offline**,
selecione `.../recovery/prefixes/SESSAO/NUMERO` e informe um caminho novo dentro
do seu Home. A rotina verifica o catálogo, copia sem executar Wine, valida o
resultado e publica sem sobrescrever prefixos existentes. Prefixos Steam são
recusados. Faça depois o diagnóstico da cópia no módulo Wine e confirme
explicitamente qualquer teste ou ativação.

Para instalações com Wine Compatibility Pack anterior, snapshots ficam também
em `recovery/receipts/Wine`. Eles são preservados como material offline;
a importação guiada acima é destinada ao catálogo das sessões Wine Prefix Repair.

## Compatibilidade e verificações

O gerenciador, o Toolkit e a validação AFI usam a mesma implementação. O diretório
escolhido nas configurações é passado ao gerenciador. O catálogo aceita tanto
`chave=valor` quanto o formato JSON anterior. Arquivos tar legados com manifesto
TXT ou JSON e catálogo completo de hashes continuam legíveis. Eles não possuem
inventário de links: a validação informa essa limitação e o código é sempre
recuperado separadamente. ZIP e formatos sem hashes não são considerados
backups verificáveis por esta rotina.

Os testes usam Homes descartáveis e arquivos fictícios. Cobrem publicação
concorrente, falha de publicação sem perda da cópia anterior, migração,
repetição da restauração, remapeamento, recuperação Wine, falta de espaço,
processo Wine simulado, arquivos maliciosos, checksums e compatibilidade legada.
Não substituem um teste com seus arquivos pessoais no Arch/GNOME real.

## Correspondência com a auditoria anterior

| Achado | Correção |
| --- | --- |
| 1. Sobrescrita e arquivo parcial | Nome único, temporário validado, publicação exclusiva |
| 2. Recuperação Wine ausente | Exportação de recibos, logs e snapshots; importação offline validada |
| 3. Seleção de persistência ausente | Estado incluído e unidades regeneradas |
| 4. Downgrade com versão igual | Build identificada e runtime recuperado separadamente |
| 5. Links de destino | Cópia com descritores e `O_NOFOLLOW`, recusa de redirecionamento |
| 6. Links fora do checksum | Inventário completo e SHA externo quando disponível |
| 7. Caminhos antigos | Remapeamento dos JSONs e recriação de launchers/unidades |
| 8. MIME sem launcher | Diretório de aplicações personalizadas incluído |
| 9. Diretório e catálogo divergentes | Preferência respeitada e parser corrigido |
| 10. Rotas incompatíveis | Toolkit e AFI delegam à rotina comum, leitor legado compartilhado |
