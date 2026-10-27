# Segurança e privacidade

## Fronteiras de confiança

O toolkit executa aplicativos Linux como seu usuário e helpers PowerShell como seu usuário Windows. A interoperabilidade WSL acessa recursos do host: não execute fontes desconhecidos nem trate a sessão como sandbox para software hostil. Aplicativos X11 da mesma sessão podem interagir entre si.

A sessão usa D-Bus e cookie X11 privados, sem listener X11 TCP, sem display manager e sem mudanças globais de permissão de sockets. Não use `xhost +` nem compartilhe o cookie para contornar falhas. Configuração de GPU é restrita à sessão, não exports globais em `.bashrc`. Isso reduz interferências, não elimina a confiança no usuário e nos aplicativos.

A instalação de pacotes usa apt/sudo; o runtime é por usuário. Revise `./install.sh --dry-run` e os fontes antes de autorizar alterações. Helpers Windows e atalhos são opcionais; caminhos configurados devem apontar a arquivos confiáveis.

## Clipboard

O bridge transfere **texto** entre Windows e desktop aninhado. Não transfere arquivos, imagens ou rich text. O clipboard Windows permanece compartilhado com outros aplicativos; não é armazenamento seguro. Não adicionar logging de payloads, nem persistir texto para diagnóstico. Use somente conteúdo sintético em testes e preserve o clipboard original em memória quando um teste automatizado o substituir.

## Material que nunca deve ser publicado

- Credenciais, tokens, chaves, variáveis secretas ou dumps de ambiente.
- Homes/caminhos reais de usuários, diretórios privados ou arquivos pessoais.
- Logs brutos, `session.json`, cookies X11, `Xauthority`, arquivos de autenticação e estado de sessão.
- Capturas com aplicativos, abas, notificações, nomes de arquivos ou documentos pessoais abertos.
- Clipboard real e payloads de mensagens dos bridges.

`.gitignore` é defesa adicional, não sanitizador. Um arquivo já rastreado ou uma imagem permitida pode conter dados privados. Use placeholders nos exemplos e revise visualmente cada captura; `docs/screenshots/xfce-wsl.png` deve mostrar apenas conteúdo de demonstração seguro. O repositório não inclui binários baixados nem wallpaper.

## Comunicar um problema

Não publique vulnerabilidades com segredos ou detalhes exploráveis em uma issue pública. Contate o responsável por um canal privado previamente confirmado. Se a hospedagem futura oferecer relato privado de vulnerabilidades, use essa opção; este projeto local não presume esse canal ou um prazo de resposta existente.

Forneça versão/revisão, ambiente, impacto e reprodução mínima com dados sintéticos. Não envie arquivos de autenticação ou logs brutos mesmo em relato privado. Publicação remota é uma ação manual separada, que exige comando explícito do usuário e revisão de privacidade prévia.
