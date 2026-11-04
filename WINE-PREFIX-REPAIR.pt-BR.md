# Diagnóstico e reparo controlado de prefixos Wine

O módulo fica em **Maintenance Center → Diagnosticar / Reparar Wine e Proton**,
no console AFI e no gerenciador clássico. O Rollback Center também abre esse
módulo. Ele complementa o Wine Compatibility Pack; não instala runtimes,
não aplica DXVK e não modifica esse módulo anterior.

## Comece pelo diagnóstico

Atualize o KenoForge com `./install.sh`, como seu usuário. Depois use a opção
de diagnóstico do novo menu, ou:

```bash
python3 "$HOME/KenoForge/System/Core/tools/wine-prefix-repair.py" --diagnose
```

O prefixo padrão vem de `WINEPREFIX`, quando definido, ou de `~/.wine`. Outro
prefixo pode ser selecionado no menu ou com `--prefix /caminho/absoluto`.

O diagnóstico não inicializa Wine, não chama wineboot, não cria prefixos e não
grava estado do KenoForge. Lê os cabeçalhos dos registros, verifica os componentes
essenciais, inspeciona links sem percorrer diretórios simbólicos e consulta a
versão instalada do Wine e as associações MIME. Informações de pacotes gráficos
são apenas inventário, sem afirmar que a GPU está saudável ou defeituosa.

`--json` gera um relatório estruturado na saída padrão. Para examinar um log
existente, sem executar Wine:

```bash
python3 "$HOME/KenoForge/System/Core/tools/wine-prefix-repair.py" \
  --diagnose --log /caminho/do/log.txt
```

O erro `could not load kernel32.dll` ou `c0000135` não basta para iniciar um
reparo. O módulo exige links quebrados confirmados em `drive_c/windows`,
arquitetura reconhecida e registros regulares acessíveis. Um prefixo saudável,
ou um prefixo com DLL essencial simplesmente ausente sem ser link quebrado,
não entra automaticamente nesse procedimento.

## Etapas do menu

1. **Diagnóstico:** relatório com links quebrados, referências ao Proton,
   kernel32/ntdll, arquitetura, processos e padrões MIME.
2. **Preparação:** após digitar `REPAIR`, verifica processos e espaço livre,
   cria um backup verificado e uma cópia de trabalho e gera um prefixo limpo.
   Substitui apenas links quebrados que tenham um arquivo regular equivalente
   no mesmo caminho relativo do prefixo limpo. DLLs, executáveis e drivers PE
   também precisam corresponder à arquitetura esperada.
3. **Validação:** execute winecfg na cópia após digitar `TEST`. O teste de um
   executável confiável é opcional e exige seleção de caminho e nova confirmação.
   Feche a janela do aplicativo quando terminar o teste. O retorno do comando
   não substitui sua avaliação visual do funcionamento do programa.
4. **Ativação:** após confirmar o funcionamento, digite `ACTIVATE ID_DA_SESSAO`.
   O prefixo original é renomeado e preservado; a cópia reparada assume o caminho
   original. Se o original tiver mudado desde a preparação, a ativação é recusada.
5. **Rollback:** digite `ROLLBACK ID_DA_SESSAO`. O prefixo anterior volta ao lugar.
   O reparado, incluindo dados criados depois da ativação, fica preservado com
   outro nome. Esta opção também recupera uma ativação interrompida.

Cada etapa é separada: preparar não ativa, executar winecfg não ativa e habilitar
verificações não autoriza reparo. Não há opção global `--yes` que dispense a
confirmação de ativação ou de rollback.

## Isolamento e restrições

São necessários Wine do sistema (`wine`, `wineboot`, `winecfg`, `wineserver`),
Python 3 e **Bubblewrap**. A associação MIME usa `gio` (glib2). O módulo não usa
sudo, não instala esses pacotes automaticamente e nunca executa Wine como root.
Se os namespaces do Bubblewrap estiverem bloqueados, a execução para; não há
alternativa automática sem isolamento.

Os processos de reparo e teste recebem o sistema de arquivos do host somente
para leitura. Apenas a cópia selecionada e um Home temporário da sessão ficam
graváveis. Rede e IPC são isolados; o barramento D-Bus do usuário não é exposto.
Os sockets de exibição necessários são disponibilizados para abrir a janela.
O ambiente remove seletores externos de Wine/Proton e variáveis de injeção.

Isso significa que um aplicativo pode abrir para teste, mas não conseguir editar
documentos em pastas externas, acessar a rede ou reproduzir todo o fluxo que
teria depois da ativação. Escolha somente executáveis conhecidos e confiáveis:
este recurso não é uma ferramenta para análise de malware.

Wineboot pode processar entradas Run/Startup e serviços. Antes de executar Wine
na cópia, o módulo compara essas entradas com o prefixo limpo e recusa entradas
adicionais/desconhecidas e pastas Startup preenchidas ou redirecionadas. Não
apaga nem desabilita silenciosamente essas configurações; casos bloqueados
precisam de revisão manual. Prefira deixar esse bloqueio ativo.

O wineboot `-u` é executado apenas na cópia de trabalho. As alterações de arquivos
são inventariadas. Se ele alterar arquivos ou links preexistentes além dos
registros e do marcador de atualização, a ativação automática desse trabalho é
bloqueada e as cópias são mantidas para inspeção.

O módulo também recusa reparo quando:

- O prefixo pertence ao Steam/Proton gerenciado, por exemplo `compatdata/.../pfx`.
  Esses prefixos continuam disponíveis para diagnóstico.
- O prefixo está fora de Home, pertence a outro usuário, é um link simbólico ou
  tem ancestrais simbólicos. O diagnóstico de caminhos externos é permitido.
- Há processos Wine associados, espaço insuficiente, arquitetura desconhecida
  ou incompatível, ou arquivos especiais não copiáveis.
- O Wine instalado mudou durante o fluxo, ou faltam equivalentes regulares seguros.
- A renomeação atômica sem sobrescrita não está disponível no sistema de arquivos.

Não são feitas alterações no Steam, Proton, drivers NVIDIA, Vulkan ou Mesa.
Não há `rm -rf` nem exclusão automática de prefixos ou sessões.

## Backups, logs e recuperação

Cada sessão tem um ID único. A área de trabalho fica ao lado do prefixo, no mesmo
sistema de arquivos, com nome `.PREFIXO.kenoforge-repair-ID` e permissão 0700.
Ela contém `backup`, `work`, `clean` e `runtime-home`. O backup copia dados,
permissões, atributos estendidos, registros e links simbólicos literais; não
copia o conteúdo externo alcançado por esses links.

O original ativado fica em `PREFIXO.kenoforge-original-ID`. No rollback, o reparado
fica em `PREFIXO.kenoforge-repaired-ID_UNICO`. Nenhuma dessas pastas é sobrescrita.

Recibos e eventos: `~/KenoForge/Installer-Backups/Wine-Prefix-Repair/ID/session.json`.
Logs: `~/KenoForge/Logs/Wine-Prefix-Repair/`. `KENOFORGE_DATA_HOME` é respeitado,
com as mesmas regras de diretórios privados usadas pelos outros módulos.

Se uma etapa falhar, volte à lista de sessões e examine o estado e os logs.
Não remova ou renomeie manualmente as pastas enquanto pretende usar o rollback.
Se houver interrupção durante a ativação, escolha **Rollback / recover interrupted
activation**. A recuperação verifica identidades de diretórios e nunca substitui
um caminho inesperado que tenha surgido no lugar do prefixo.

## Associações MIME opcionais

O diagnóstico consulta `application/x-ms-dos-executable` e `application/x-msdownload`.
A configuração opcional usa o `wine.desktop` já instalado, sem criar ou alterar
arquivos `.desktop` personalizados. O padrão anterior precisa ser conhecido para
permitir reversão. Cada operação gera um recibo em `Installer-Backups/Wine-MIME`.

Isso seleciona o Wine padrão, não um prefixo personalizado. Se você usa Proton-GE
intencionalmente, mantenha sua associação atual. O rollback MIME não sobrescreve
uma preferência que tenha sido alterada por outro meio depois do patch.

## Verificação após atualizações

As opções **Enable/Disable integrity watch** são opt-in por prefixo. O Update
Guardian reutiliza esse cadastro em verificações e mudanças de pacotes relevantes.
São examinados somente poucos componentes essenciais, sem percorrer a biblioteca
de aplicativos nem executar Wine. Problemas geram tarefas de manutenção; nunca
um reparo automático. Não foi adicionado serviço de inicialização nem timer.

## Validação e limites desta entrega

Os testes usam prefixos simulados com cabeçalhos PE válidos para as arquiteturas
e executam de verdade as cópias, hashes, gravações de recibos, renomeações atômicas
e recuperações em pastas temporárias. As chamadas ao Wine são simuladas.

Este ambiente não tem Wine instalado e não permite criar namespaces Bubblewrap.
Portanto, ainda é necessário validar a integração gráfica com Wine e Bubblewrap
no Arch de destino. Nenhum prefixo pessoal foi usado nos testes.

Referências de implementação:

- [Wine — código de wineboot](https://github.com/wine-mirror/wine/blob/master/programs/wineboot/wineboot.c)
- [Wine — manual wineboot](https://man.archlinux.org/man/extra/wine-staging/wineboot.1.en)
- [Proton — gerenciamento de prefixos](https://github.com/ValveSoftware/Proton/wiki/Proton-FAQ)
