# Identidade e autenticação

Login usa sessão PostgreSQL e CSRF explícito inclusive para requisições anônimas. Instalar `SessionPolicyMiddleware` após `AuthenticationMiddleware`; a sessão tem inatividade, limite absoluto e versão por usuário para revogação. Uma sessão administrativa sem MFA só permite configurar e confirmar o segundo fator, buscar CSRF e sair. Alteração de senha ou privilégios invalida sessões existentes. Toda consulta de memberships busca o vínculo ativo novamente.

Confirmar a ativação do MFA também invalida todas as sessões anteriores, mantendo somente a sessão que confirmou o código. Tentativas de recuperação com senha rejeitada pela política de segurança continuam consumindo o limite de tentativas.

MFA usa `django-otp` (`TOTP.verify`, tolerância de um período e `min_t` persistido) em transação com bloqueio de linha para impedir reuso concorrente. Segredo é protegido por Fernet (`cryptography`) com chave de ambiente separada. Códigos de recuperação são aleatórios e armazenados com hash de senha Django; só podem ser utilizados uma vez. Não há algoritmo criptográfico próprio. Esta integração pequena foi escolhida sobre allauth headless para manter uma API de sessão consistente com os painéis e armazenar o segredo criptografado explicitamente. A política de MFA para administradores é obrigatória.

Configurar `TAVVO_MFA_ENCRYPTION_KEY` (Fernet), `TAVVO_SESSION_IDLE_SECONDS` (1800), `TAVVO_SESSION_ABSOLUTE_SECONDS` (43200), `TAVVO_PASSWORD_RESET_URL` (URL pública do formulário administrativo), `PASSWORD_RESET_TIMEOUT` (1800), SMTP e `DEFAULT_FROM_EMAIL`. Não usar backend console em produção: ele expõe links de recuperação. Executar periodicamente `python manage.py process_auth_mail --limit 100`; a fila recebe tanto emails existentes quanto inexistentes, sem consulta de conta ou envio SMTP no caminho da resposta pública. A entrega expira após 15 minutos, tenta no máximo cinco vezes e não imprime destinatários nem tokens.

Rate limits usam contadores PostgreSQL atômicos com chave HMAC. Endereço de origem é `REMOTE_ADDR`; o proxy deve sobrescrever a origem de forma confiável. Cabeçalhos X-Forwarded-For enviados pelo cliente nunca são usados diretamente. Este limite na aplicação complementa, sem substituir, limites de conexão e volume no proxy. Limpar contadores antigos e solicitações processadas conforme política de retenção operacional.

Referências: https://django-otp-official.readthedocs.io/en/stable/extend.html ; https://docs.djangoproject.com/en/5.2/topics/http/sessions/ ; https://cryptography.io/en/latest/fernet/ .
