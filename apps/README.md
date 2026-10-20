# Aplicações web

Execute `npm ci` na raiz, com Node.js 22.12 ou superior. O backend deve estar disponível na porta 8000.

- `npm run dev:admin`: painel em http://localhost:5173.
- `npm run dev:public`: referência pública em http://localhost:3000.
- `npm run typecheck`: verificação TypeScript.
- `npm run build`: builds Vite e Next.js.

O painel usa exclusivamente URLs relativas `/v1/` por um proxy Vite. Configure `API_INTERNAL_URL` no ambiente do processo (ou `apps/admin/.env.local`) se o backend não estiver em `http://127.0.0.1:8000`. `VITE_PUBLIC_SITE_URL` muda o destino do link de prévia. A origem do painel precisa estar em `CSRF_TRUSTED_ORIGINS` do Django. Não use hostnames diferentes para login e demais operações. Cookies administrativos são gerenciados pelo backend; nenhuma credencial é guardada em localStorage.

No site público, configure `API_INTERNAL_URL` no ambiente ou `apps/public-reference/.env.local`. Os dados são consultados pelo servidor em cada requisição (`no-store`). `/r/{slug}` é a rota explícita de referência; `/q/{code}` resolve a mesa no backend e consulta seu cardápio; `/` exige domínio verificado pelo backend. Em localhost, abra `/r/{slug}`. Nenhum restaurante padrão é selecionado quando o domínio é inválido. Imagens públicas passam por um proxy restrito a imagens públicas, sem encaminhar cookies administrativos.

No painel, o administrador Tavvo cadastra restaurantes e usuários, copia o ID do usuário da listagem e o associa ao restaurante. MFA é obrigatório para contas privilegiadas. O gestor escolhe um restaurante, cria categorias e produtos, publica ambos, envia imagens e cadastra mesas. Os valores monetários são enviados à API como strings decimais; a interface não calcula preços. O funcionário consulta o catálogo e altera somente disponibilidade. A autorização de cada operação é aplicada pelo backend.

O status verificado de um domínio é concedido manualmente pela Tavvo após confirmar propriedade e DNS; provisionamento DNS/TLS automático está fora do MVP. O fluxo de recuperação precisa de SMTP configurado ou do backend de e-mail local documentado para desenvolvimento.

Fontes técnicas: [fetch do Next.js](https://nextjs.org/docs/app/api-reference/functions/fetch), [Vite](https://vite.dev/guide/).
