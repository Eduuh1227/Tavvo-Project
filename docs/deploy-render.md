# Demonstração do Tavvo no Render

O arquivo `render.yaml` descreve um serviço gratuito. O Render constrói a imagem Docker e publica o painel, a API e o cardápio no mesmo endereço HTTPS `*.onrender.com`. Depois de um período sem tráfego, o primeiro acesso pode levar cerca de um minuto. [Limites do plano gratuito](https://render.com/docs/free)

1. Entre no [painel do Render](https://dashboard.render.com/), crie um Blueprint e selecione `Eduuh1227/Tavvo-Project`, branch `main`.
2. Em `DATABASE_URL`, use a conexão TLS da role de aplicação do Neon, com as migrações já aplicadas. Para um banco novo, use `infra/provision_database.py` e `scripts/manage.py migrate` em um ambiente administrativo separado. Mantenha a credencial do proprietário do banco fora do Render.
3. Gere `DJANGO_SECRET_KEY` com pelo menos 50 caracteres aleatórios. Em `TAVVO_MFA_ENCRYPTION_KEY`, use a chave existente se reutilizar o banco, pois ela permite ler os cadastros MFA. Para um banco novo, gere uma chave Fernet própria. Cadastre as duas nas variáveis do serviço. Os usuários precisarão entrar novamente no endereço novo.
4. Informe as variáveis `S3_*` de um bucket privado. Para Cloudflare R2, use `auto` como região e o endpoint S3 fornecido pelo R2. Ao reutilizar o banco da demonstração, copie as imagens existentes para o bucket mantendo as mesmas chaves dos objetos antes de validar o cardápio. [Compatibilidade S3 do R2](https://developers.cloudflare.com/r2/api/s3/api/)
5. Após o deploy, use a URL mostrada no painel. Confira `/health/` e `/ready/`, abra o painel em `/`, faça login e confira cardápio, foto e pedido presencial em um restaurante publicado.

A Stripe está pendente e o Blueprint não configura credenciais de pagamento. O serviço também não usa Vercel Queues. A recuperação de senha por e-mail fica desativada enquanto o envio por outro meio estiver pendente.
