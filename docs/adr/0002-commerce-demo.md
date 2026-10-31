# 0002 — Pedidos e cobrança em demonstração

Em 30–31/10/2026, o usuário ampliou o escopo inicial e pediu a implementação dos módulos faltantes. Escolheu Stripe para pedidos e assinaturas, exclusivamente em testes. Em 31/10 autorizou um endereço público fixo da Vercel e adiou o envio real de e-mails.

O app `commerce` mantém pedidos e assinaturas separados do catálogo. Preços, taxas, disponibilidade e área por prefixos de CEP são conferidos no servidor. Pedidos guardam uma cópia dos itens e preços; mudanças posteriores no catálogo não alteram a compra. Chaves de idempotência impedem duplicatas na repetição da mesma requisição. Alterações de status usam versão otimista e bloqueio de linha.

RLS é obrigatória em pedidos, itens, política de atendimento e assinatura. Chaves estrangeiras compostas impedem associações entre restaurantes. Dois índices globais mínimos servem ao roteamento e deduplicação de webhooks, sem contatos, valores ou payloads de clientes. Consulta pública exige um token de acesso e não devolve nome, telefone ou endereço.

Stripe Checkout hospedado recebe os dados de cartão. Eventos assinados e consulta ao estado atual da Stripe confirmam pagamento e assinatura; a página de retorno não libera pedidos. O código rejeita chaves live. O plano de R$ 99,00/mês é uma fixture do sandbox, não uma definição comercial aprovada.

Esta entrega não habilita recebimento real por restaurantes: isso exige Stripe Connect, onboarding dos recebedores e regras comerciais/fiscais. A assinatura de demonstração não bloqueia os módulos existentes por inadimplência. Não há integração com transportadoras: entrega é uma operação manual do restaurante, com status de saída e conclusão.

A recuperação de senha mantém outbox no PostgreSQL e possui consumidor privado Vercel Queues, com cinco tentativas. O produtor só é ativado por configuração após SMTP validado. Mensagens de fila levam somente um UUID; falhas de publicação preservam a outbox para o comando de recuperação. SMTP tem semântica de entrega pelo menos uma vez: uma interrupção após envio e antes do commit pode produzir repetição.

Domínio próprio continua dependendo de um nome de domínio pertencente ao usuário. `tavvosystems@gmail.com` é um endereço de e-mail, não um domínio próprio disponível para configuração DNS.
