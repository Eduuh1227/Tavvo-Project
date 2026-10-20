# Backup e restauração

Estado: estratégia preparada; nenhum backup produtivo ou restauração destrutiva foi executado. RPO, RTO, retenção, região e responsáveis aguardam definição. Uma proposta inicial para discussão é snapshot diário mais arquivamento contínuo de WAL/PITR, versionamento de objetos e ensaio mensal de restauração. Esses valores não são compromisso de serviço.

## Conjunto recuperável

Preserve o banco PostgreSQL, objetos do bucket, versão do código/migrações, permissões/roles e configuração criptográfica em depósitos protegidos e independentes. `TAVVO_MFA_ENCRYPTION_KEY` é necessária para ler segredos MFA restaurados. Não grave essa chave no mesmo dump sem controle separado. `.env` e backups não entram no Git.

Para consistência de banco e imagens, use janela sem escritas ou um snapshot coordenado com versionamento dos objetos. Uma cópia somente do PostgreSQL não restaura imagens. Valide o acesso e os checksums dos objetos, retenção/imutabilidade e permissão de restauração do operador. Conta de backup deve ler todas as linhas necessárias; a conta runtime com RLS não é apropriada para dump completo.

## Exemplo local não destrutivo

Estes comandos criam um dump dentro do contêiner e o copiam em formato binário, evitando redirecionamento de bytes pelo PowerShell. Troque `2026-10-20` pela data da operação e guarde fora do repositório.

```sh
docker compose exec -T db pg_dump -U postgres -d tavvo --format=custom --file=/tmp/tavvo-2026-10-20.dump
docker compose cp db:/tmp/tavvo-2026-10-20.dump ./tavvo-2026-10-20.dump
docker compose exec -T db pg_restore --list /tmp/tavvo-2026-10-20.dump
```

Em produção, use destino criptografado, credencial via secret manager/pgpass e dump versionado. A listagem de um arquivo não prova restauração. O storage requer backup de objetos/versionamento do provedor; copiar o diretório ativo de dados MinIO/PostgreSQL não é um backup consistente.

## Ensaio de restauração isolado

1. Registre hora do snapshot, versão do PostgreSQL, commit, inventário de objetos e checksums. Meça a duração e a perda máxima de alterações.
2. Provisione um banco **novo e isolado**, sem tráfego, e um bucket de restauração separado. Nunca aponte comandos de ensaio ao banco ativo. Restaure as roles e permissões necessárias antes de importar.
3. Revise o conteúdo do dump; use `pg_restore --exit-on-error --dbname=<nova-conexao> <arquivo>` sem `--clean` ou `--create` contra instância compartilhada. O destino e a credencial devem ser revisados antes de executar.
4. Restaure os objetos no bucket isolado e configure as chaves correspondentes. Inicie a mesma versão de código do backup; migre apenas depois da validação inicial.
5. Verifique contagens, relacionamentos, hashes/amostras de imagens, estados publicados, login+MFA e ausência de exposição pública de rascunhos. Teste RLS com `tavvo_app` e isolamento de dois restaurantes.
6. Registre evidência e tempos atingidos. Trate o ensaio como reprovado se imagens, chaves MFA ou permissões estiverem faltando, mesmo que o restore do PostgreSQL tenha terminado.

## Recuperação após incidente

A troca de tráfego ou restauração sobre um ambiente existente exige autorização, janela, comunicação e plano de retorno. Preserve evidências do incidente antes de alteração; interrompa escritas para impedir divergência durante o corte. Confirme o ponto de recuperação aprovado e possíveis dados perdidos. Após o corte, monitore e mantenha o ambiente anterior isolado pelo período definido; não o apague automaticamente.

Referências: [dump PostgreSQL](https://www.postgresql.org/docs/18/app-pgdump.html), [restore PostgreSQL](https://www.postgresql.org/docs/18/app-pgrestore.html), [backup contínuo/PITR](https://www.postgresql.org/docs/18/continuous-archiving.html).
