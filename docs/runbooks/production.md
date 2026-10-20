# Preparação de produção e operação

Estado: procedimento proposto, sem ambiente contratado e sem deploy realizado. Hospedagem no Brasil, domínio, fornecedor S3/SMTP, orçamento, retenção e metas RPO/RTO permanecem pendentes. A publicação exige a definição desses itens e autorização explícita. O workflow atual verifica código; não publica nem executa migrações de produção.

## Configuração de ambiente

Use secret manager do provedor, sem arquivos de segredos no repositório/imagem. Separe ambientes e buckets. Gere `DJANGO_SECRET_KEY` forte e `TAVVO_MFA_ENCRYPTION_KEY` Fernet; preserve cópia protegida desta chave para restauração de MFA. Rotação de Fernet precisa de procedimento de recriptografia e rollback; trocar a variável isoladamente invalida segredos existentes.

| Variável | Configuração esperada |
| --- | --- |
| `TAVVO_ENV` | `production` |
| `DATABASE_URL` | Conta runtime sem owner/superuser/BYPASSRLS |
| `MIGRATION_DATABASE_URL` | Conta owner, disponibilizada somente ao job de migração |
| `DATABASE_SSLMODE` | `verify-full`, com CA confiável e hostname correto |
| `DJANGO_ALLOWED_HOSTS` | Lista explícita de hosts, sem wildcard |
| `CSRF_TRUSTED_ORIGINS` | Origens HTTPS administrativas exatas |
| `TAVVO_ADMIN_ORIGIN` / `TAVVO_PUBLIC_ORIGIN` | URLs HTTPS oficiais |
| `S3_ENDPOINT_URL` / `S3_REGION` / `S3_BUCKET` | Fornecedor e bucket privado; endpoint omitido apenas quando aplicável |
| `S3_ACCESS_KEY` / `S3_SECRET_KEY` | Conta restrita ao bucket necessário; não usar usuário root |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS` | SMTP transacional autenticado |
| `DEFAULT_FROM_EMAIL` | Remetente do domínio verificado |
| `DJANGO_HTTPS_REDIRECT` | `true` após configurar corretamente a terminação TLS |

No Compose local, o usuário S3 compartilha a credencial do serviço MinIO para simplificar o desenvolvimento. Produção exige uma conta de serviço restrita; Mailpit e MinIO local não são o ambiente produtivo.

## Publicação manual planejada

1. Selecionar commit com CI verde e registrar artefatos, versões, imagens por digest e responsáveis. Executar revisão de dependências e configuração.
2. Restaurar um backup em staging e validar migrações, isolamento e o fluxo de dois restaurantes. Confirmar capacidade, latência e SMTP/S3 reais.
3. Obter backup verificável e plano de rollback. Aplicar migrações compatíveis usando exclusivamente a credencial owner em job temporário. Não expor esse segredo aos workers HTTP/email.
4. Publicar a API Gunicorn, worker de email, build estático do Vite e servidor Next.js atrás do proxy. O painel deve encaminhar `/v1` para a API na mesma origem; `API_INTERNAL_URL` é somente do servidor. Nunca disponibilizar credenciais aos bundles.
5. Configurar TLS e redirecionamento HTTPS sem loops. O proxy deve substituir cabeçalhos de origem, bloquear acesso direto à API e aplicar limites de corpo/conexões/requisições. A aplicação não confia em `X-Forwarded-For` recebido do cliente. O ajuste de confiança no proxy depende da topologia e deve ser testado antes de ativar.
6. Expor apenas hosts autorizados. Vincular e verificar domínio no cadastro do restaurante; falhar fechado em hostname desconhecido. DNS/certificados automáticos continuam fora desta etapa.
7. Executar `python scripts/manage.py check --deploy`, health/readiness, login+MFA, publicação/remoção e leitura pública. Testar novamente isolamento de dois tenants.
8. Liberar tráfego gradualmente e acompanhar falhas, filas, latência e métricas de banco. Se necessário, voltar para artefato compatível anterior. Não reverter migrações ou restaurar sobre banco ativo sem avaliar perda de dados e obter autorização.

## Logs e observabilidade

Os processos enviam logs para stdout/stderr e a API associa identificadores de requisição. Configure coleta, correlação e retenção no provedor. Não registre cookies, senhas, tokens MFA, códigos de recuperação ou URLs de redefinição com querystring. O Gunicorn local não habilita access log; proxies também precisam de redaction de querystrings.

`/health/` indica processo vivo. `/ready/` confirma conexão PostgreSQL; S3 e SMTP exigem probes operacionais separados e alertas de erros. Monitore 5xx/latência, conexões e espaço do banco, backup atrasado, fila de email com `attempts >= 5`, objetos órfãos e auditoria. Defina limiares conforme carga observada; não há SLO contratado nesta etapa.

Execute o worker `python infra/mail_worker.py` como serviço supervisionado; ele chama `process_auth_mail --limit 100`. Para limpeza de imagens, liste primeiro com `python scripts/manage.py reconcile_images --restaurant-id UUID`; `--delete` é ação destrutiva separada, somente após revisar a lista e validar backup/política. Limpeza de sessões/limites/fila e retenção de auditoria precisam de agenda e política aprovadas.

A role runtime não pode alterar/apagar auditoria. A manutenção administrativa deve ser separada, registrada e limitada. Faça revisão periódica das permissões e teste RLS usando a conta real da aplicação, não o owner.
