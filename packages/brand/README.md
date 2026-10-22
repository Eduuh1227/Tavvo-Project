# Fundação visual Tavvo

`tokens.css` centraliza cores, semântica de estados, tipografia, espaçamento,
bordas, raios, sombras, dimensões, transições e referências de breakpoints.
Os frontends continuam usando CSS convencional, sem nova biblioteca ou dependência.

## Paleta de referência

| Token | Valor aplicado | Uso |
| --- | --- | --- |
| `--brand-night` | `#0B0F1A` | Navegação e áreas institucionais |
| `--brand-tech` | `#6366F1` | Identidade, foco e elementos gráficos |
| `--brand-gray` | `#E5E7EB` | Referência de neutros |
| `--brand-green` | `#10B981` | Referência de sucesso |

Os valores foram derivados da prancha JPEG fornecida pelo titular. Eles são
tokens de implementação provisórios, a confirmar com um manual/arquivo original
da marca; não constituem uma certificação dos códigos oficiais. Os neutros e
variantes semânticas complementares também são decisões de interface.

O botão primário usa `--color-primary: #4F46D8`, uma variante mais escura para
legibilidade do texto branco. O verde de texto/status é `#087D60`, sobre
`#E6F5EE`. Estados são identificados por texto além da cor.

## Fonte e licença

Sora variável (pesos 100–800) é servida localmente por `fonts.css`, com
`font-display: swap`. O arquivo tem aproximadamente 109 KiB; a página não
depende de requisições a serviços de fontes externos.

Origem: [Google Fonts / Sora](https://github.com/google/fonts/tree/main/ofl/sora).
Arquivo original `Sora[wght].ttf`, preservado sem alterações e renomeado para
`Sora-variable.ttf`. A licença SIL Open Font License 1.1 está em
[`fonts/OFL.txt`](fonts/OFL.txt). Download em 21/10/2026.

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

Não havia logotipo individual no repositório. A identificação textual “Tavvo”
existente foi preservada temporariamente, sem redesenhar o símbolo geométrico
e sem recortar a prancha. Para a aplicação final da marca, fornecer:

1. Logotipo completo em SVG, variantes para fundo claro e escuro.
2. Símbolo isolado em SVG e regras de área de proteção/tamanho mínimo.
3. Paleta oficial em valores digitais e orientações de uso.

A substituição futura da identificação textual pelos arquivos originais é uma
pendência visual; não depende de mudanças de API ou de modelo de dados.
