export const services = [
  {name: 'Revisão preventiva', detail: 'Uma avaliação dos principais sistemas para planejar os cuidados do seu carro.', label: 'Manutenção'},
  {name: 'Freios e suspensão', detail: 'Inspeção de pastilhas, discos e componentes de suspensão.', label: 'Segurança'},
  {name: 'Troca de óleo e filtros', detail: 'Consulta da especificação correta para o motor do seu veículo.', label: 'Motor'},
  {name: 'Diagnóstico eletrônico', detail: 'Leitura de falhas e avaliação técnica antes de definir o reparo.', label: 'Diagnóstico'},
];

export const parts = [
  {id: 'freio', name: 'Jogo de pastilhas de freio', category: 'Freios', price: 149.90, fit: 'Consulte por modelo, ano e versão', detail: 'Conjunto para substituição no eixo dianteiro. Confirme a aplicação com a oficina.', code: 'TRQ-001'},
  {id: 'oleo', name: 'Óleo de motor sintético 5W-30', category: 'Motor', price: 49.90, fit: 'Consulte a especificação do fabricante', detail: 'Embalagem de 1 litro. A viscosidade e a homologação devem corresponder ao motor.', code: 'TRQ-002'},
  {id: 'filtro', name: 'Filtro de óleo', category: 'Motor', price: 32.90, fit: 'Consulte por modelo, ano e motorização', detail: 'Elemento de reposição para manutenção do sistema de lubrificação.', code: 'TRQ-003'},
  {id: 'amortecedor', name: 'Amortecedor dianteiro', category: 'Suspensão', price: 289.90, fit: 'Consulte aplicação e lado de montagem', detail: 'Valor por unidade. Instalação e alinhamento são orçados separadamente.', code: 'TRQ-004'},
  {id: 'bateria', name: 'Bateria automotiva 60 Ah', category: 'Elétrica', price: 459.90, fit: 'Consulte dimensões e posição dos polos', detail: 'Confirme a capacidade e a tecnologia exigidas pelo seu veículo.', code: 'TRQ-005'},
  {id: 'palheta', name: 'Par de palhetas do limpador', category: 'Acessórios', price: 79.90, fit: 'Consulte tamanho e tipo de encaixe', detail: 'Par de palhetas dianteiras. A oficina ajuda a identificar o conjunto adequado.', code: 'TRQ-006'},
];
