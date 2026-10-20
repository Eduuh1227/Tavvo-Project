# ADR 0001 — Fundação do Tavvo Restaurants

Estado: aceito para implementação em 19/10/2026. Fluxo do MVP validado localmente e na CI em 20/10/2026; [evidências e limites](../verification/2026-10-20.md).

## Contexto

O usuário forneceu o prompt de requisitos, revisou a proposta técnica e indicou `https://github.com/Eduuh1227/Tavvo-Project.git`, instruindo iniciar o trabalho. A inspeção remota e o clone confirmaram repositório vazio. Não havia código, migrações, testes ou documentação v1.0; o prompt é a referência de produto.

## Decisões

- Monólito modular Django 5.2/DRF, PostgreSQL compartilhado e entidades identificadas por UUID.
- Autorização por usuário ativo, associação ativa, papel e restaurante do recurso; chaves compostas no banco e RLS como defesa adicional.
- Sessões persistidas no servidor, cookies protegidos, CSRF no login e nas mutações, recuperação de acesso e MFA obrigatório para administradores Tavvo.
- Django auth + django-otp e cryptography implementam o contrato de autenticação. Substituem a sugestão preliminar de allauth para manter uma única API e evitar recursos de cadastro/social login fora do escopo; TOTP e criptografia usam bibliotecas mantidas, não algoritmos próprios.
- Aplicativo administrativo React/Vite com áreas Tavvo e restaurante, ambas pela API. Site Next.js consome contrato público; sem produtos fixos no frontend.
- Produtos só aparecem quando restaurante está ativo e produto e categoria publicados. Indisponibilidade é estado separado. Edição de item publicado é imediata após commit; não há revisão editorial.
- Imagens em S3 privado e servidas após autorização/elegibilidade, sem cache persistente inicialmente. QR público não concede permissão administrativa.
- Desenvolvimento local reproduzível; PostgreSQL real nos testes; produção e contratação de infraestrutura dependem de autorização adicional.

## Pendências operacionais

Hospedagem no Brasil, fornecedor S3/SMTP, domínio oficial, retenção, RPO/RTO e orçamento. Nenhum provedor foi contratado. Não se implementam pedidos, pagamentos, assinaturas, microsserviços ou personalização visual avançada nesta etapa.
