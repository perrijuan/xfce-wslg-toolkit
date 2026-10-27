# Instalação

Este roteiro descreve instalação e configuração; não certifica instalação limpa. Para evidência de execução, consulte [VALIDATION.md](VALIDATION.md). Ambiente original comprovado: Ubuntu 26.04.1 / WSL 3.0.3 / WSLg 1.0.79, NVIDIA RTX 3060 com D3D12. Outras versões, GPUs e uma distro recém-criada exigem validação própria.

## 1. Preparar Windows e Ubuntu

Use Windows com suporte a WSLg, virtualização habilitada e driver de GPU fornecido para o Windows pelo fabricante. Em PowerShell elevado, quando WSL/Ubuntu ainda não estiverem instalados:

```powershell
wsl --install -d Ubuntu
```

Reinicie o Windows se solicitado e conclua a criação do usuário Linux normal. Para uma instalação existente, não reinstale a distro. Confira:

```powershell
wsl --update
wsl --version
wsl --list --verbose
```

O Ubuntu deve estar em WSL2; se necessário, usando o nome exato listado:

```powershell
wsl --set-version Ubuntu 2
wsl -d Ubuntu
```

Não confunda **WSL2**, a geração da máquina virtual, com **WSL 3.0.3**, a versão do pacote no ambiente original. Consulte as instruções oficiais de [instalação do WSL](https://learn.microsoft.com/en-us/windows/wsl/install).

## 2. Preparar a cópia local no Linux

Obtenha os fontes por um meio de confiança e extraia/copie a pasta para o filesystem Linux; não há URL de repositório publicado presumida neste guia. No terminal Ubuntu, dentro da pasta `xfce-wslg-toolkit`:

```bash
chmod +x install.sh
./install.sh --dry-run
./install.sh
```

O `--dry-run` serve para revisar o plano sem aplicar a instalação. A instalação normal usa apt para dependências e pode pedir sudo **para essa etapa**; execute `./install.sh` como usuário normal. Não instala display manager, não troca o desktop do Windows e não exige liberar globalmente sockets X11. Os pacotes vêm do apt; não há binários ou wallpaper baixados incluídos no projeto.

Destinos padrão:

| Item | Destino |
| --- | --- |
| Runtime Linux | `~/.local/share/xfce-wslg-toolkit/{bin,lib}` |
| Links de comandos | `~/.local/bin` |
| Configuração local | `~/.config/xfce-wsl/config.json` |
| Estado e diagnósticos privados | `~/.local/state/xfce-wsl` |
| Integração Windows | Helpers/atalhos por usuário configurados pela etapa Windows |

Não confunda `--prefix` com o diretório da cópia do repositório: ele seleciona o destino do **runtime**. O arquivo `windows/Setup-Windows.ps1` implementa a preparação Windows; use as opções efetivamente expostas por ele, sem adivinhar parâmetros. A integração depende do PowerShell acessível pela interoperabilidade WSL e de caminhos locais corretos.

## 3. Opções de instalação

```bash
./install.sh --dry-run
./install.sh --skip-packages
./install.sh --skip-windows
./install.sh --no-alias
./install.sh --prefix "$HOME/.local/share/xfce-wslg-toolkit-alternativo"
```

| Opção | Efeito e responsabilidade |
| --- | --- |
| `--dry-run` | Mostrar o plano sem aplicar alterações |
| `--skip-packages` | Não instalar via apt; você deve fornecer as dependências |
| `--skip-windows` | Pular helpers/atalhos Windows; não comprova funcionamento da integração nativa |
| `--no-alias` | Não adicionar os aliases Bash `xfce` e `xfce144` |
| `--prefix DIR` | Escolher o destino do runtime Linux por usuário |

Para preparar uma cópia sem apt nem integração Windows, por exemplo em staging:

```bash
./install.sh --skip-packages --skip-windows --no-alias \
  --prefix "$HOME/.local/share/xfce-wslg-toolkit-staging"
```

Isso ainda instala arquivos locais; **não** é simulação e **não** prova que a sessão pode abrir. Use `--dry-run` junto para apenas inspecionar. Sem helpers Windows, não espere clipboard nativo ou foco Windows funcionando.

## 4. Configuração e primeira abertura

Confira `config/settings.example.json`. Ele contém placeholders, não caminhos utilizáveis até serem ajustados. Edite a configuração gerada em `~/.config/xfce-wsl/config.json` com seu editor; não sobrescreva uma configuração existente sem revisão.

- `windows_helper_dir`: caminho **Windows nativo** da pasta dos helpers, não `/mnt/c/...`.
- `powershell_wsl`: caminho Linux para o executável PowerShell via WSL, por exemplo `/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe`.
- `refresh_rate`: alvo de apresentação, padrão `144`; não é medição de FPS.
- `adapter`: `auto` por padrão; não presuma uma GPU NVIDIA em outra máquina.
- `window_title`: título usado para identificar a janela; mantenha os helpers coerentes com ele.
- `windowed`: `true` para abertura redimensionável por padrão.

Abra um novo Bash ou carregue `source ~/.bash_aliases`. Garanta `~/.local/bin` no PATH, se usar os comandos sem caminho completo.

```bash
xfce
xfce status
xfce-wsl-display list
xfce direita
xfce esquerda
xfce janela
xfce-wsl-run xfce4-terminal
```

`xfce144` explicita o alvo 144. Sem aliases: `~/.local/bin/xfce-wsl`. Salve seus aplicativos e use a saída de sessão do Xfce ao encerrar; não mate todos os processos Python ou WSLg.

## 5. Alvo WSLg de 144 Hz (opcional)

A configuração do Xephyr e a configuração do compositor WSLg são camadas distintas. Revise a documentação oficial de [frame rate](https://github.com/microsoft/wslg/wiki/Controlling-WSLg-frame-rate) e [configuração WSLg](https://github.com/microsoft/wslg/wiki/WSLg-Configuration-Options-for-Debugging). Para WSL distribuído pela Store, use `.wslgconfig` no perfil Windows (`%USERPROFILE%`), como no ambiente original; a documentação também distingue o caminho ProgramData para WSL inbox. Não mova o arquivo nem exija administrador sem identificar a variante instalada. Mescle sem apagar opções existentes:

```ini
[system-distro-env]
; Alvo do compositor, nao promessa de FPS
WESTON_RDP_MONITOR_REFRESH_RATE=144
```

Use comentários INI com `;`, não `#`. Essa opção não altera a taxa física dos monitores. Confira as taxas no Windows; uma configuração mista 60/144 Hz continua limitada por cada monitor.

A alteração só passa a valer após reiniciar o WSL. **Somente após salvar o trabalho e autorizar a interrupção de todas as distros**, execute no Windows:

```powershell
wsl --shutdown
```

Depois reabra Ubuntu e Xfce. O instalador/configuração não deve ser confundido com confirmação de que Weston aplicou a opção ou de que o aplicativo atingiu 144 FPS. Preserve os padrões de DPI do Windows; ajuste escala e redimensionamento separadamente.
