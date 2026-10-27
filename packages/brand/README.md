# Fundação visual Tavvo

`tokens.css` centraliza cores, semântica de estados, tipografia, espaçamento,
bordas, raios, sombras, dimensões, transições e referências de breakpoints.
Os frontends continuam usando CSS convencional, sem nova biblioteca ou dependência.

## Paleta preto e laranja

| Token | Valor aplicado | Uso |
| --- | --- | --- |
| `--brand-night` | `#0B0D0F` | Navegação e áreas institucionais |
| `--brand-orange` | `#FF6A2E` | Ações, seleção e elementos gráficos |
| `--brand-gray` | `#6B6F76` | Textos auxiliares |
| `--brand-white` | `#F5F5F5` | Fundo de conteúdo e textos sobre escuro |

Os valores seguem a nova prancha JPEG e o briefing fornecidos pelo titular em
24/10/2026, substituindo a identidade azul/roxo anterior. Não há manual vetorial
ou arquivo original de cor no repositório: os códigos permanecem referências
de implementação, sujeitos à confirmação oficial. Os neutros e variantes
semânticas complementares são decisões de interface.

O botão primário usa laranja `#FF6A2E` com texto preto `#0B0D0F`
(`--color-on-primary`), contraste de 6,82:1. No hover, o fundo `#F15A20`
mantém contraste de 5,77:1. Links sobre superfícies claras usam `#AB3508`
(`--color-link`), com 6,47:1 em branco. Não usar o laranja principal como
texto pequeno em branco, nem texto branco sobre o botão laranja.

O foco usa `#BB3C0B` em superfícies claras e `#FF6A2E` sobre escuro.
Cores semânticas de sucesso, erro e alerta foram preservadas, sempre
acompanhadas de texto. O verde remanescente é exclusivamente semântico.

## Fonte e licença

Montserrat variável (pesos 100–900) é servida localmente por `fonts.css`, com
`font-display: swap`. Os subconjuntos Latin e Latin Extended em WOFF2 somam
106 KiB; `unicode-range` permite carregar somente o necessário. Latin inclui
os caracteres acentuados comuns do português. A página não depende de
requisições a serviços de fontes externos. A fonte Sora anterior foi removida.

Origem: [Google Fonts / Montserrat](https://github.com/google/fonts/tree/main/ofl/montserrat).
A distribuição web foi obtida pela
[folha oficial Google Fonts](https://fonts.googleapis.com/css2?family=Montserrat:wght@100..900&display=swap),
em 24/10/2026, preservando os binários e intervalos Unicode:

- [Latin](https://fonts.gstatic.com/s/montserrat/v31/JTUSjIg1_i6t8kCHKm459Wlhyw.woff2): `fonts/Montserrat-latin.woff2`, 37.956 bytes.
- [Latin Extended](https://fonts.gstatic.com/s/montserrat/v31/JTUSjIg1_i6t8kCHKm459Wdhyzbi.woff2): `fonts/Montserrat-latin-ext.woff2`, 70.688 bytes.

A licença SIL Open Font License 1.1 está em [`fonts/OFL.txt`](fonts/OFL.txt).

## Aplicação e manutenção

- Importar `tokens.css` e `fonts.css` no CSS de cada frontend.
- Usar os tokens semânticos em componentes, sem repetir códigos de cor.
- Os breakpoints são 640 px (compacto), 960 px (navegação) e 1280 px (amplo).
  Variáveis CSS não são usadas como condição de media query; manter os valores
  literais sincronizados com os tokens e comentários.
- Os ícones de interface são SVGs decorativos simples, com `aria-hidden`,
  acompanhados dos rótulos existentes. Eles não representam o logotipo.
- O tema escuro do cardápio é específico do frontend de referência. Não muda
  os contratos nem impõe o mesmo tema a outros frontends de restaurantes.

## Marca pendente

Não há logotipo individual autorizado no repositório. A identificação textual
“Tavvo” existente foi preservada temporariamente (apresentada em caixa alta),
sem redesenhar o símbolo geométrico e sem recortar a prancha. Os espaços
`.brand-identification` no login e no cabeçalho da sidebar têm dimensões para
receber uma imagem oficial. Para a aplicação final da marca, fornecer:

1. Logotipo completo em SVG, variantes para fundo claro e escuro.
2. Símbolo isolado em SVG e regras de área de proteção/tamanho mínimo.
3. Paleta oficial em valores digitais e orientações de uso.
4. Favicon autorizado derivado do símbolo. Nenhum favicon de restaurante foi substituído.

A substituição futura da identificação textual pelos arquivos originais é uma
pendência visual; não depende de mudanças de API ou de modelo de dados.
