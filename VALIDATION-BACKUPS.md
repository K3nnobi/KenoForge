# Validação da versão 1.5.23

Build `1.5.23-backup-v3-20261104`.

| Verificação | Resultado |
| --- | --- |
| `tests/test-backups.py` | 10 testes passaram |
| `tests/test-wine-prefix-repair.py` | 34 testes passaram |
| `tests/test-maintenance.py` | 7 testes passaram |
| `tests/test-install-safety.py` | 12 testes passaram |
| `tests/test-migration.py` | 6 testes passaram |
| `tests/test-patch-persistence.py` | 7 testes passaram |
| `tests/test-stable.sh` | Instalação, restauração e integrações passaram |
| `tests/test-run-installer.sh` | Construção, checksum e extração `.run` passaram |
| `install.sh --check` | Integridade e sintaxe aprovadas |

Total das seis suítes Python: **76 testes**. As suites de instalação usam
`KENOFORGE_TEST_SIMULATE=1` em cópias descartáveis; o bloqueio de root continua
ativo no instalador entregue. Operações de arquivamento, cópia e extração são
reais, mas dados e Homes são fictícios. Consultas de pacotes, sessão gráfica,
processos Wine ativos e falhas de espaço/publicação são simulados quando
necessário. Não foram executados Wine/EXEs reais, instalados pacotes no host ou
restaurados arquivos pessoais do usuário.

Os cenários de backup conferem os dados recuperados, a preservação do runtime
atual e de backups anteriores, a recusa de adulterações, a migração entre Homes,
a importação offline de prefixo, a delegação AFI/Toolkit e formatos legados.
Este resultado não certifica hardware, drivers, GNOME ou Wine no computador final.
