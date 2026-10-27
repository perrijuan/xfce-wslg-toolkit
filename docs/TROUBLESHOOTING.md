# Solução de problemas

Comece com `xfce status`, `xfce-wsl-display status` e `xfce-wsl-display list`. Se os aliases não existirem, use `~/.local/bin/xfce-wsl status`. Os comandos de controle exigem sessão ativa; abra com `xfce` primeiro. Registre localmente o erro exato, mas não publique logs, homes de usuário, cookies ou `session.json`.

## Não abre / WSLg indisponível

No Windows, confira `wsl --version` e `wsl --list --verbose`: use WSL2, WSLg disponível e driver Windows compatível. No Ubuntu, execute como usuário normal, não root. Confira se a instalação pulou pacotes ou Windows e se `~/.local/bin` está no PATH. Revise o plano `./install.sh --dry-run` antes de reinstalar.

Não use `xhost +`, `chmod` global em sockets, um display manager ou exports permanentes de `DISPLAY` como correção. O toolkit preserva o WSLg e prepara uma sessão aninhada privada.

## GPU ou fluidez abaixo do esperado

Com a sessão aberta:

```bash
xfce-wsl-run glxinfo -B
```

`/dev/dxg` presente ou `direct rendering: Yes` isoladamente não provam aceleração. Confira renderer e aceleração; `llvmpipe` é renderização por software. Compare o resultado dentro da sessão, não apenas no terminal WSLg externo. Verifique o driver Windows e a seleção de adapter; não fixe NVIDIA em uma máquina diferente.

Não exporte `GALLIUM_DRIVER`, `LIBGL_ALWAYS_SOFTWARE` ou `MESA_D3D12_DEFAULT_ADAPTER_NAME` globalmente em `.bashrc`. O ambiente de GPU pertence à sessão e ao seu D-Bus privado.

O Xephyr pode informar **0 Hz** no RandR sintético: não é o modo físico do monitor. `144` é alvo, não FPS garantido. Confira separadamente a taxa Windows de cada monitor, o alvo do Xephyr, a configuração efetiva do WSLg e a medição do aplicativo. Veja a [configuração opcional](INSTALLATION.md#5-alvo-wslg-de-144-hz-opcional). Um monitor de 60 Hz continua limitado a 60 Hz.

## Monitor errado, faixa preta ou escala

```bash
xfce-wsl-display list
xfce-wsl-display right
xfce-wsl-display left
xfce-wsl-display window
```

Esquerda/direita se referem à geometria detectada, não a identificadores de saída fixos. Use os controles externos; Alt+F11 dentro do Xfce pode afetar apenas a aplicação interna. No build testado, tela cheia via `Xephyr -output` causou crash; mantenha a transição EWMH implementada pelo toolkit.

Uma faixa preta pode ser perfil antigo, não falha de GPU. No único monitor virtual raiz do Xephyr, o toolkit usa `/AutoEnableProfiles=0` no canal `displays` e sincroniza a resolução inicial, evitando o perfil `1600x1200` em cache. Para diagnóstico dentro da sessão:

```bash
xfce-wsl-run xfconf-query -c displays -p /AutoEnableProfiles
xfce-wsl-run xrandr --query
```

Não aplique esse perfil a monitores físicos ou desktops alheios. Salve o trabalho e reabra a sessão após corrigir um perfil persistente; um simples reload de `xfdesktop` pode não eliminar o cache. Redimensionar a janela não equivale a escala HiDPI. Preserve o DPI padrão do Windows e avalie escala de fontes/elementos separadamente.

## Ponteiro invisível

```bash
xfce-wsl-restore-cursor
```

A recuperação atualiza os cursores do desktop aninhado e da janela host sem reiniciar aplicativos. Não confunda o ponteiro com o ícone de atalho do Xfce. Uma imagem de cursor presente em memória ou um screenshot não prova que o ponteiro aparece no Windows: **peça confirmação visual ao usuário**. Não comece por matar a sessão ou mudar globalmente os cursores Windows.

## Copiar/colar falha

O contrato é **texto**, não arquivos, imagens, PRIMARY ou rich text. No terminal Xfce, colar é normalmente `Ctrl+Shift+V`; em editores, `Ctrl+V`.

Confira a pasta de helpers Windows e `powershell_wsl` na configuração local. `--skip-windows` deixa essa integração incompleta. O helper nativo observa a sequência do clipboard Windows porque notificações X selection do WSLg podem ser perdidas. Não conclua que funciona apenas por um processo estar vivo ou por ler manualmente o clipboard WSLg antes do teste.

Teste com texto sintético, Unicode e quebras de linha nos dois sentidos; copie o mesmo texto novamente após perder a seleção. Não use segredos nem imprima payloads. Não encerre indiscriminadamente processos PowerShell: identifique somente o helper desta sessão. O clipboard é compartilhado com o Windows, não um canal secreto.

## Papel de parede não muda

O projeto não distribui wallpaper. Escolha uma imagem local existente. No monitor virtual observado, a interface Xfce escrevia `monitor0` enquanto `xfdesktop` lia `monitordefault`; o bridge sincroniza essas propriedades no D-Bus privado. Verifique a imagem realmente renderizada, não apenas a existência de uma chave xfconf. Não aplique a compatibilidade a outros desktops/monitores.

## Janela congelada ou foco

Estado de processo Linux não prova apresentação atual no Windows. Compare a janela real e o estado da sessão; confira se o helper de foco aponta para a janela Xephyr correta. Não mate todos os processos `msrdc`, Weston, Python ou todas as distros. Um `wsl --shutdown` interrompe trabalhos não relacionados e só deve ocorrer com autorização, após salvá-los.

Ao relatar falha, siga [SECURITY.md](../SECURITY.md) e [CONTRIBUTING.md](../CONTRIBUTING.md): descreva versões, passos e resultado com dados sintéticos e sanitizados, sem anexar estado bruto.
