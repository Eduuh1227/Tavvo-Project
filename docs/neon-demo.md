# Demonstração gratuita: Neon e Vercel Blob

O banco da demonstração usa PostgreSQL no Neon Free. A API continua no Django,
com transações por requisição e as políticas RLS existentes. O armazenamento
de imagens usa um Vercel Blob **privado**, dentro da franquia do plano Hobby.
Ambos os serviços têm limites de uso; este ambiente é uma demonstração.

## Configuração

- `DATABASE_URL`: conexão com pool do usuário `tavvo_app`, sem superusuário,
  propriedade das tabelas ou capacidade de ignorar RLS.
- `MIGRATION_DATABASE_URL`: conexão direta do proprietário, somente nas ferramentas
  de administração locais; não configurar no preview publicado.
- `IMAGE_STORAGE_BACKEND=vercel_blob` e `BLOB_READ_WRITE_TOKEN`: acesso servidor
  ao armazenamento privado. Nunca usar prefixos `VITE_` ou `NEXT_PUBLIC_`.
- O padrão `IMAGE_STORAGE_BACKEND=s3` mantém compatibilidade com o desenvolvimento
  local e com outros provedores S3.

O SDK Blob preserva as chaves com o identificador do restaurante. Downloads
continuam passando pela autorização da API e pelas regras de publicação do
cardápio, com resposta `Cache-Control: no-store`. URLs diretas do Blob exigem
credencial. O comando `reconcile_images` também funciona com o novo provedor.

## Preparação do banco dedicado

1. Criar Neon no plano gratuito e obter as variáveis em `.local/vercel-neon.env`.
   O script espera `NEON_DATABASE_URL`, `NEON_DATABASE_URL_UNPOOLED` e
   `BLOB_READ_WRITE_TOKEN`. A configuração anterior de sessão/MFA fica em
   `.local/vercel-demo.env`.
2. Executar `python scripts/prepare_neon_demo.py --dedicated-demo --env-file .local/vercel-neon.env`.
   O script prepara o usuário restrito, aplica as migrações existentes, verifica
   isolamento/auditoria e salva `.local/vercel-neon-demo.env` sem imprimir segredos.
3. Configurar no preview apenas a conexão restrita e o provedor de imagens.
4. Publicar, cadastrar os exemplos através da API e verificar login, cardápio,
   publicação, upload, acesso entre restaurantes e logout.

## Dados anteriores

O Supabase anterior está suspenso e não aceitou conexões de exportação do banco
nem do armazenamento. Ele não foi apagado. O novo banco recebe **dados novos de
demonstração**, não uma cópia dos registros anteriores. Se o acesso antigo ou
um backup ficar disponível, a importação precisa ser planejada separadamente,
incluindo imagens e preservação dos identificadores.

Arquivos de credenciais, cookies e resultados sensíveis ficam em `.local/`,
excluída do Git e do pacote de publicação. Manter os backups antigos separados
dos dados novos; não executar restauração destrutiva sobre a demonstração ativa.
