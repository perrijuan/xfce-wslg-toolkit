# Arquitetura

## Caminho de apresentação

```text
Windows (monitores, DPI, driver GPU, clipboard)
  └─ WSL2 / WSLg (Weston + Xwayland; display host :0)
      └─ Xephyr (janela host, display X11 aninhado)
          └─ D-Bus privado + xfce4-session
              ├─ xfwm4 / xfdesktop / painel / aplicativos
              ├─ bridge de clipboard ↔ helper PowerShell nativo
              └─ bridge de propriedades de wallpaper
```

É um desktop X11 aninhado, não um display manager nem substituição do WSLg. O namespace local de sockets é preparado sem mudar permissões globais; Xephyr usa cookie X11 privado e não escuta TCP. Aplicativos da mesma sessão X11 compartilham seu domínio de confiança: cookie e D-Bus privados não são isolamento completo entre aplicativos.

## Componentes

| Fontes | Responsabilidade |
| --- | --- |
| `linux/bin/start-xfce-wsl`, `xfce-wsl` | Entrada, aliases/argumentos e prevenção de sessão duplicada |
| `linux/lib/common.py` | Resolução comum de instalação/configuração |
| `linux/lib/session.py` | Cookie, GPU, Xephyr, sessão privada e ciclo de vida |
| `linux/lib/present.py` | Apresentação/foco da sessão existente |
| `linux/bin/xfce-wsl-display` | Detectar monitores e transitar entre janela/tela cheia via EWMH |
| `linux/bin/xfce-wsl-restore-cursor` | Atualizar o cursor aninhado e host sem reiniciar |
| `linux/bin/xfce-wsl-run` | Executar aplicativos com o ambiente da sessão ativa |
| `linux/lib/clipboard-bridge.py`, `windows/clipboard-host.ps1` | Ponte de texto entre X11 aninhado e clipboard nativo |
| `linux/lib/wallpaper-bridge.py` | Sincronização compatível de propriedades Xfconf do monitor virtual |
| `windows/Focus-Xfce.ps1` | Foco nativo da janela correta |
| `windows/Setup-Windows.ps1`, `install.sh`, `tools/install.py` | Preparação opcional Windows e instalação Linux por usuário |

O destino padrão é `~/.local/share/xfce-wslg-toolkit/{bin,lib}`; links ficam em `~/.local/bin` e configuração em `~/.config/xfce-wsl/config.json`. Estado de sessão e diagnósticos são locais e privados, não conteúdo versionável.

## Decisões e limites observados

- **GPU:** o launcher verifica o caminho Mesa/D3D12 e mantém overrides no ambiente da sessão e na ativação do seu D-Bus, não em `.bashrc`. Há fallback por software; detectar GPU não significa que todos os aplicativos estejam acelerados.
- **Clipboard:** notificações X selection do host WSLg não eram confiáveis no pipeline observado. O helper Windows observa a sequência nativa e troca mensagens por pipes com o bridge. O contrato é texto bidirecional; sem arquivos, imagens, rich text ou PRIMARY. Não registrar payloads, evitar ecos e não sobrescrever uma cópia Windows mais nova com estado antigo.
- **Geometria:** monitores são detectados no host. A janela Xephyr é movida e recebe estado EWMH para tela cheia; `-output` derrubou o build testado. Redimensionamento e escala HiDPI são independentes; manter defaults de DPI do Windows.
- **Perfil virtual:** `/AutoEnableProfiles=0` no canal Xfconf `displays` impede que o único monitor virtual raiz restaure resolução `1600x1200` obsoleta e gere faixa preta. Não alterar perfis físicos alheios.
- **Wallpaper:** sincronizar os caminhos `monitor0`/`monitordefault` da sessão observada, preservando escolha local. Nenhuma imagem é incluída.
- **Ponteiro:** atualizar imagem X11 não prova visibilidade na apresentação Windows. A confirmação final é do usuário.
- **144 Hz:** alvo de relógio/apresentação sintético do Xephyr e configuração Weston são camadas separadas. RandR em 0 Hz não descreve monitor físico; alvo 144 não é FPS garantido. Uma combinação física 60/144 Hz mantém os limites de cada tela.

O ambiente original comprovado foi Ubuntu 26.04.1 / WSL 3.0.3 / WSLg 1.0.79 / NVIDIA RTX 3060 D3D12. Essas decisões derivam desse pipeline, não demonstram instalação limpa em uma distro nova. [VALIDATION.md](VALIDATION.md) deve delimitar a cobertura corrente.

## Referências oficiais

- Microsoft: [instalação do WSL](https://learn.microsoft.com/en-us/windows/wsl/install).
- WSLg: [opções de configuração](https://github.com/microsoft/wslg/wiki/WSLg-Configuration-Options-for-Debugging) e [controle de frame rate](https://github.com/microsoft/wslg/wiki/Controlling-WSLg-frame-rate).
- Mesa: [driver Gallium D3D12 e seleção de adapter](https://docs.mesa3d.org/drivers/d3d12.html).
- Xfce: [documentação dos componentes e Xfconf](https://docs.xfce.org/).
- X.Org: [manual Xephyr(1)](https://xorg.freedesktop.org/archive/X11R7.5/doc/man/man1/Xephyr.1.html); consulte também `man Xephyr` para as opções do pacote realmente instalado. A disponibilidade de uma opção no manual não comprova seu funcionamento nesta combinação WSLg/build.
