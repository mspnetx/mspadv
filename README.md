# MSPADV — Marcelo Paiva Advocacia

Site institucional bilíngue (português / inglês), estático, publicado no GitHub Pages.
Não usa banco de dados nem dependências: um único script Python (`build.py`) lê a pasta `content/` e gera o site.

## Publicar pela primeira vez

1. Crie um repositório **público** vazio no GitHub (por exemplo `mspadv`), sem README.
2. Nesta pasta, rode:

   ```
   git init -b main
   git add .
   git commit -m "Site MSPADV"
   git remote add origin https://github.com/SEU-USUARIO/mspadv.git
   git push -u origin main
   ```

3. No GitHub: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
4. Aguarde 1–2 minutos (aba **Actions**). O site fica em `https://SEU-USUARIO.github.io/mspadv/`.

Depois disso, todo `git push` republica o site automaticamente.

> Dica: mantenha esta pasta fora do Google Drive (por exemplo em `C:\Sites\mspadv`). O Drive e o Git costumam conflitar.

## Publicar um artigo novo

1. Copie `content/pt/artigos/_modelo.md`, dê um nome sem acentos nem espaços (ex.: `guarda-compartilhada-como-funciona.md`) e escreva o texto.
2. (Opcional) Para a versão em inglês, crie um arquivo **com o mesmo nome** em `content/en/artigos/`. O campo `slug` define o endereço em inglês.
3. `git add . && git commit -m "Novo artigo" && git push`.

Também dá para criar o arquivo direto no site do GitHub (**Add file → Create new file**), sem usar o computador.

Formatação aceita: `## Subtítulo`, `### Subtítulo menor`, listas com `- `, `**negrito**`, `*itálico*`, `> destaque`, `[texto](https://link)` e `[texto](@nome-do-arquivo)` para apontar a outra página do site.

## Onde editar cada coisa

| O quê | Onde |
| --- | --- |
| Telefone, WhatsApp, e-mail, domínio | `content/site.json` |
| Textos da home, escritório, contato, menu, rodapé | `content/pt/textos.json` e `content/en/textos.json` |
| Lista de áreas (cards, ordem, ícones) | `content/areas.json` |
| Páginas das áreas | `content/pt/areas/*.md` e `content/en/areas/*.md` |
| Artigos | `content/pt/artigos/*.md` e `content/en/artigos/*.md` |
| Privacidade e Termos | `content/*/paginas/*.md` |
| Visual e animações | `assets/css/styles.css` e `assets/js/main.js` |
| Fotos e logo | `assets/img/` |

Nas páginas de área, o bloco `::: servicos` lista os serviços (`- **Título** | descrição`) e o bloco `::: faq` lista as perguntas (linha começando com `?`, resposta na linha seguinte).

## Ver o site no computador antes de publicar

```
python build.py --serve
```

Abra http://localhost:8000.

## Domínio próprio

Em `content/site.json`, preencha `"dominio": "www.mspadv.com.br"` e `"url": "https://www.mspadv.com.br"`, publique e aponte o DNS do domínio para o GitHub Pages (CNAME `www` → `SEU-USUARIO.github.io`).

## Formulário de contato

Por padrão o formulário abre o WhatsApp ou o programa de e-mail do visitante com a mensagem pronta. Para receber os envios direto na caixa de entrada, crie um formulário em um serviço como o Formspree e cole o endereço em `"formulario_endpoint"` no `content/site.json`.
