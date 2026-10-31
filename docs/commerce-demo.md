# Pedidos, delivery e Stripe de teste

No painel do gestor, **Entrega e retirada** configura recebimento, modalidades, taxa, pedido mínimo, prazo e prefixos de CEP. **Pedidos** acompanha os pedidos e permite avançar status, confirmar pagamento presencial e pedir estorno online. Funcionários podem operar pedidos, mas não alterar a política, contratar assinatura ou estornar.

O cliente adiciona produtos no cardápio, informa os dados necessários e acompanha o pedido na mesma aba. Pedidos de mesa exigem o QR ativo daquela mesa. O token fica no sessionStorage; fechar a sessão do navegador pode perder o acesso ao acompanhamento. Dados de cartão são preenchidos somente no checkout hospedado da Stripe.

**Assinatura** oferece checkout e portal do plano fictício de teste. Valores e status são reconciliados por webhooks. O ambiente rejeita credenciais live. Guarde chaves em variáveis protegidas e prefira chaves restritas com as permissões necessárias; nunca coloque chaves no Git ou no cliente.

## Configuração do servidor

- `STRIPE_SECRET_KEY`: chave exclusiva de sandbox.
- `STRIPE_WEBHOOK_SECRET`: segredo de assinatura do endpoint `/v1/payments/stripe/webhook/`.
- `STRIPE_SUBSCRIPTION_PRICE_ID` e `STRIPE_PORTAL_CONFIGURATION_ID`: recursos do mesmo sandbox.
- `TAVVO_ADMIN_ORIGIN` e `TAVVO_PUBLIC_ORIGIN`: endereço HTTPS fixo do demo.
- `STRIPE_PLAN_LABEL`: descrição visível do plano fictício.

Eventos necessários: checkout.session.completed, checkout.session.async_payment_succeeded, checkout.session.async_payment_failed, checkout.session.expired, customer.subscription.created/updated/deleted, invoice.paid, invoice.payment_failed, charge.refunded, refund.created/updated/failed, charge.dispute.created/updated/closed e radar.early_fraud_warning.created.

## E-mail adiado pelo usuário

`TAVVO_RECOVERY_QUEUE_ENABLED=false` mantém envio automático desligado. Para ativar posteriormente: configurar SMTP autenticado (`EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL`), validar a entrega e ativar a flag. Não enviar senhas pelo chat. O consumidor privado está declarado em `apps/api/pyproject.toml`. O comando `process_auth_mail --limit 100` recupera mensagens que não foram publicadas na fila. Requisições com mais de 15 minutos são descartadas sem envio.

## Antes de operação comercial

Ainda são necessários onboarding/Connect, regras de repasse, política de cancelamento e cobrança, configuração fiscal e homologação de pagamentos completos, falhas e disputas. Stripe Tax só deve ser ativado após verificar os registros fiscais aplicáveis. Domínio próprio e autenticação do remetente dependem das contas do proprietário. Demonstração validada não equivale a homologação para vendas reais.
