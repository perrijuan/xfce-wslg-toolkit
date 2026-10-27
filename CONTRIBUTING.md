# Contribuição

Prefira mudanças pequenas, com reprodução e validação do comportamento afetado. Documentação é em português; preserve nomes de comandos, chaves e protocolos. Não altere integração do host, DPI ou perfis de outros desktops para resolver um problema local do Xephyr.

## Antes de propor mudanças

1. Leia [Arquitetura](docs/ARCHITECTURE.md) e [Segurança](SECURITY.md).
2. Reproduza com dados sintéticos e anote versões Windows, Ubuntu, WSL, WSLg, Mesa/GPU e topologia de monitores, sem homes reais.
3. Exercite os testes existentes e o caminho real afetado; registre os comandos, resultados, limitações e o que não foi testado em `docs/VALIDATION.md`. Não confunda testes unitários ou staging com desktop funcionando.
4. Para alterações visuais, verifique a janela Windows real; para ponteiro, obtenha confirmação do usuário. Teste monitores/clipboard/GPU apenas quando o ambiente e a autorização permitirem, sem interromper trabalhos alheios.
5. Revise o diff e todos os arquivos/artefatos antes de compartilhar. Nunca adicione logs, credenciais, cookies, `session.json`, homes reais, clipboard ou capturas de aplicativos/arquivos pessoais. Não inclua binários baixados nem wallpaper.

O pipeline original comprovado não equivale a teste do instalador em uma distro limpa. Diferencie evidência herdada, teste automatizado, teste ao vivo e item não executado. Não declare compatibilidade universal, 144 FPS garantidos ou publicação remota sem evidência.

## Preparação local e publicação manual

Nenhum remoto é criado automaticamente por estas instruções. **Somente após comando explícito do usuário**, revisão dos arquivos e confirmação de destino/visibilidade, um mantenedor pode executar manualmente os exemplos abaixo. Os placeholders precisam ser substituídos; não são identificadores de um repositório existente.

Preparação local, a partir da raiz do projeto (exemplo para um repositório ainda sem Git):

```bash
git init
git add README.md docs SECURITY.md CONTRIBUTING.md LICENSE \
  .gitignore .gitattributes .editorconfig config/settings.example.json \
  install.sh tools linux windows tests
git diff --cached --check
git diff --cached --stat
# Revise tambem o conteudo completo, inclusive imagens e arquivos novos.
git diff --cached
git commit -m "Prepare xfce-wslg-toolkit"
```

Publicação opcional pelo GitHub CLI, já instalado e autenticado pelo próprio mantenedor. O exemplo escolhe **privado** explicitamente; publicar como público exige decisão separada:

```bash
gh repo create "<OWNER>/<REPO>" --private --source=. --remote=origin --push
```

Esses comandos são exemplos, não histórico de execução. Nada aqui afirma que commit, remoto ou push já existam. Não envie credenciais pelo chat nem inclua arquivos de autenticação no projeto.
