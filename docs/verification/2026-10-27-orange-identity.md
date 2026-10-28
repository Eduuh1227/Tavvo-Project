# Identidade preto e laranja — 27/10/2026

## Resultado e escopo

A identidade azul/roxo com Sora foi substituída pela referência fornecida em
24/10: preto `#0B0D0F`, laranja `#FF6A2E`, cinza `#6B6F76`, branco `#F5F5F5`
e Montserrat. Os valores da prancha são referências de implementação; falta
manual original para confirmação definitiva.

Login, recuperação e MFA recebem o tema através do CSS compartilhado. Os
painéis central e de restaurante mantêm navegação escura e superfícies claras,
ações e seleções laranja, campos e estados consistentes. Diagonais e recortes
decorativos ficam no login e no cabeçalho do cardápio demonstrativo. O tema do
frontend de referência não muda configurações nem impõe identidade aos demais
frontends de restaurantes.

Não houve alteração em TSX, handlers, hooks, requisições, validações, rotas,
backend, contratos, permissões, banco, migrações, publicação, QR ou hospedagem.
Nenhuma biblioteca, tela, métrica ou funcionalidade foi adicionada.

Base limpa antes do trabalho: `1670a2d`, preservada no histórico Git.

## Arquivos alterados

| Arquivo | Alteração |
| --- | --- |
| `packages/brand/tokens.css` | Paleta, cores de contraste e fonte centralizadas |
| `packages/brand/fonts.css` | Montserrat local variável, Latin/Latin Extended |
| `packages/brand/fonts/Montserrat-latin.woff2` | Fonte web, 37.956 bytes |
| `packages/brand/fonts/Montserrat-latin-ext.woff2` | Fonte web complementar, 70.688 bytes |
| `packages/brand/fonts/Sora-variable.ttf` | Fonte antiga removida |
| `packages/brand/fonts/OFL.txt` | Licença da Montserrat |
| `packages/brand/README.md` | Origem, aplicação, contraste e pendências da marca |
| `apps/admin/src/style.css` | Controles, texto, foco e identificação institucional |
| `apps/admin/src/auth.css` | Login e geometria decorativa |
| `apps/admin/src/panels.css` | Navegação, links, editores, badges e estados |
| `apps/public-reference/app/style.css` | Tema do cardápio de referência |
| `tests/e2e/restaurants.spec.ts` | Rolagem até imagem lazy antes de validar carregamento |
| `docs/verification/2026-10-27-orange-identity.md` | Este registro de implementação e validação |

## Acessibilidade e marca

- Texto preto sobre botão laranja: 6,82:1; hover: 5,77:1.
- Link laranja escuro em branco: 6,47:1. Foco usa variante escura em claro
  e laranja principal em fundo preto.
- Badge neutro usa texto `#41454B` sobre `#F0F0ED`, contraste de 8,45:1,
  corrigindo a combinação anterior de 4,42:1 encontrada na revisão.
- Estados de sucesso/erro/alerta mantêm cores semânticas e rótulos.
- Áreas de toque, labels, foco por teclado e redução de movimento preservados.
- Montserrat servida localmente com OFL e `font-display: swap`; sem serviço
  externo de fontes em tempo de execução. Fontes e origem documentadas em
  [packages/brand](../../packages/brand/README.md).

Não foram encontrados arquivos individuais oficiais do logotipo ou símbolo.
A identificação textual TAVVO permanece temporária e os espaços de marca
estão preparados para receber SVGs. Não houve desenho aproximado, recorte da
prancha ou substituição de favicons. Faltam variantes oficiais para fundo
claro/escuro, símbolo isolado e favicon autorizado.

## Validação executada

| Verificação | Resultado |
| --- | --- |
| Backend (`scripts/test_backend.py -q`, 24/10) | 40 testes passaram, 16,92 s |
| E2E (`scripts/test_e2e.py`, 24–25/10) | 3 testes passaram, 22,3 s |
| TypeScript (`npm run typecheck`, 24/10) | Admin, público e cliente API aprovados |
| Compilação (`npm run build`, 27/10) | Vite e Next.js aprovados, incluindo TypeScript |
| Escopo do código | 153 chamadas e 19 handlers preservados; nenhum TSX alterado |
| Responsividade | Login, central, restaurante e público em 320/390/768/1024/1440 px, sem overflow |
| Navegação | Seis abas de restaurante, formulário de produto e usuários centrais revisados em mobile |
| Público | Fonte carregada, âncoras, foco, hover, seleção e estado 404 verificados |
| JavaScript no navegador | Nenhum `pageerror` nas verificações visuais |

A primeira execução E2E encontrou uma limitação do teste: com dados acumulados
de execuções anteriores, a imagem ficava abaixo do limiar de carregamento lazy.
A rolagem manual carregou a imagem corretamente (64 px de largura natural).
O teste agora rola até ela antes de verificar o carregamento, sem remover
asserções ou mudar a aplicação. A suíte completa passou após esse ajuste.

O E2E verifica sessões reais e logout, publicação/despublicação, preços, upload
e remoção de imagem, acesso público, isolamento A/B, QR ativo/revogado, mobile
e operação central com sessão MFA. Backend cobre as regras existentes. As
verificações não constituem certificação completa de acessibilidade ou prontidão
comercial. Dados criados pelos testes são exclusivamente da demonstração local.

Capturas anteriores permanecem em `visual-after-*.png` no relatório de 21/10.
Novas capturas e relatórios completos estão na pasta local ignorada
`.local/orange-after`, `.local/orange-qa-report.json` e
`.local/orange-public-ui-review.json`; não contêm senhas ou tokens visíveis.
A sessão MFA temporária expirou e seu arquivo local foi removido em 27/10.

| Tela | Antes (21/10) | Nova identidade |
| --- | --- | --- |
| Login desktop | [Antes](visual-after-login-desktop.png) | [Depois](orange-login-desktop.png) |
| Login mobile | [Antes](visual-after-login-mobile.png) | [Depois](orange-login-mobile.png) |
| Público desktop | [Antes](visual-after-public-desktop.png) | [Depois](orange-public-desktop.png) |
| Público mobile | [Antes](visual-after-public-mobile.png) | [Depois](orange-public-mobile.png) |

As quatro imagens `orange-*.png` acima são evidências adicionais versionadas.

## Publicação

A atualização foi publicada em 27/10/2026 no Preview existente `tavvo-demo`:

- Código publicado: `875e4eb` — `feat(ui): adopt Tavvo black and orange visual identity`.
- Ajuste de teste: `198efa6` — `test(e2e): scroll lazy images into view before asserting load`.
- Deployment: `dpl_AU1gGyseQwo9ZdkPojckRxPWxDDC`.
- [Endereço do Preview](https://tavvo-demo-r9kisblre-eduardo-oliveiras-projects-9e8e2497.vercel.app).
- Estado da compilação Vercel: **Ready**, duração de 1 min 33 s, região `gru1`.
- Manifesto conferido antes do envio: 158 arquivos regulares, incluindo as
  duas fontes WOFF2; nenhum arquivo privado de `.local`, `.env` ou `.git`.

**A demonstração online ainda não está operacional.** A página de login e a
Montserrat foram carregadas no navegador remoto, mas a verificação de login
não pôde prosseguir: a API retornou HTTP 500. Os logs identificaram falha de
conexão com o banco (`ENOTFOUND: tenant/user not found`). A consulta da
integração confirmou o recurso Supabase `tavvo-demo` como **Suspended**.

Em 28/10, `vercel integration resource inspect tavvo-demo` confirmou novamente
a suspensão, o plano **Supabase Free Plan** e a conexão aos ambientes Preview
e Development. Recurso: `store_v3H5npW7PwERYXDd`.
[Painel do recurso](https://vercel.com/eduardo-oliveiras-projects-9e8e2497/~/stores/integration/store_v3H5npW7PwERYXDd).

Não foi alterado banco, credencial, plano ou configuração para contornar a
suspensão. A reativação do recurso e a validação remota de login/logout e
cardápios permanecem pendentes; esse trabalho operacional está fora do
escopo exclusivamente visual definido no briefing. O motivo específico da
suspensão não foi informado pelo comando de inspeção.
