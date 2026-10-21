import {expect, test, type Page} from '@playwright/test';
import {previewAccess} from './preview-access';

test.beforeEach(async ({context}) => previewAccess(context));

const publicOrigin = process.env.TAVVO_E2E_PUBLIC_URL || 'http://localhost:3000';
const apiOrigin = process.env.TAVVO_E2E_API_URL || 'http://127.0.0.1:8000';

function required(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`Configure ${name} with the seeded local/CI fixture before running E2E.`);
  return value;
}

async function login(page: Page, tenant: 'a' | 'b' = 'a') {
  await page.goto('/');
  await page.getByLabel('E-mail', {exact: true}).fill(`gestor-${tenant}@example.test`);
  await page.getByLabel('Senha', {exact: true}).fill(required('TAVVO_E2E_PASSWORD'));
  await page.getByRole('button', {name: 'Entrar', exact: true}).click();
  await expect(page.getByRole('heading', {name: `Restaurante ${tenant.toUpperCase()}`, exact: true})).toBeVisible();
}

test('real manager publishes a menu, enforces tenant boundaries and revokes a table QR', async ({page, browser}) => {
  const restaurantB = required('TAVVO_E2E_RESTAURANT_B');
  const productB = required('TAVVO_E2E_PRODUCT_B');
  const suffix = `${Date.now()}-${test.info().workerIndex}`;
  const categoryName = `Categoria E2E ${suffix}`;
  const productName = `Prato E2E ${suffix}`;
  const tableLabel = `Mesa E2E ${suffix}`;
  let publicImageUrl = '';
  const visitor = await browser.newContext();
  await previewAccess(visitor);
  const publicPage = await visitor.newPage();
  const browserErrors: string[] = [];
  page.on('pageerror', error => browserErrors.push(error.message));
  publicPage.on('pageerror', error => browserErrors.push(error.message));

  try {
    await test.step('login with a real session and create a published category', async () => {
      await login(page);
      await expect(page.getByRole('button', {name: 'Administração central', exact: true})).toHaveCount(0);
      await expect(page.getByRole('option', {name: /Restaurante B/})).toHaveCount(0);
      await page.getByRole('button', {name: 'Adicionar', exact: true}).click();
      await page.getByLabel('Nome', {exact: true}).fill(categoryName);
      await page.getByLabel('Descrição', {exact: true}).fill('Categoria criada pelo fluxo real do navegador.');
      await page.getByLabel('Publicada', {exact: true}).check();
      await page.getByRole('button', {name: 'Salvar', exact: true}).click();
      await expect(page.locator('.records article').filter({hasText: categoryName})).toBeVisible();
    });

    await test.step('create a draft product and publish it through the panel', async () => {
      await page.getByRole('button', {name: 'Produtos', exact: true}).click();
      await page.getByRole('button', {name: 'Adicionar', exact: true}).click();
      await page.getByLabel('Nome', {exact: true}).fill(productName);
      await page.getByLabel('Descrição', {exact: true}).fill('Preparado durante a validação de ponta a ponta.');
      await page.getByLabel('Categoria', {exact: true}).selectOption({label: categoryName});
      await page.getByLabel('Preço (ex.: 25.90)', {exact: true}).fill('29.90');
      await page.getByRole('button', {name: 'Salvar', exact: true}).click();
      const card = page.locator('.records article').filter({has: page.getByText(productName, {exact: true})});
      await expect(card).toBeVisible();

      await publicPage.goto(`${publicOrigin}/r/restaurante-a`);
      await expect(publicPage.getByRole('heading', {name: 'Restaurante A', exact: true})).toBeVisible();
      await expect(publicPage.getByRole('heading', {name: productName, exact: true})).toHaveCount(0);

      await card.getByRole('button', {name: 'Editar', exact: true}).click();
      await page.getByLabel('Publicado', {exact: true}).check();
      await page.getByRole('button', {name: 'Salvar', exact: true}).click();
      await expect(page.getByRole('heading', {name: 'Editar registro', exact: true})).toHaveCount(0);
      await publicPage.reload();
      await expect(publicPage.getByRole('heading', {name: productName, exact: true})).toBeVisible();
      await expect(publicPage.getByRole('article').filter({hasText: productName})).toContainText('R$ 29,90');
    });

    await test.step('upload an image through the panel and render it through the public S3 proxy', async () => {
      const card = page.locator('.records article').filter({has: page.getByText(productName, {exact: true})});
      await card.getByText('Imagens (0)', {exact: true}).click();
      await card.getByLabel('Imagem JPEG, PNG ou WebP').setInputFiles('tests/fixtures/product.png');
      await card.getByRole('button', {name: 'Enviar imagem', exact: true}).click();
      await expect(card.getByText('Imagens (1)', {exact: true})).toBeVisible();
      await publicPage.reload();
      const image = publicPage.getByRole('img', {name: productName, exact: true});
      await expect(image).toBeVisible();
      await expect.poll(() => image.evaluate(node => (node as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
      publicImageUrl = new URL((await image.getAttribute('src'))!, publicOrigin).href;
      expect((await publicPage.request.get(publicImageUrl)).status()).toBe(200);
    });

    await test.step('hide the product and immediately remove it from the public menu', async () => {
      const card = page.locator('.records article').filter({has: page.getByText(productName, {exact: true})});
      await card.getByRole('button', {name: 'Editar', exact: true}).click();
      await page.getByLabel('Publicado', {exact: true}).uncheck();
      await page.getByRole('button', {name: 'Salvar', exact: true}).click();
      await expect(page.getByRole('heading', {name: 'Editar registro', exact: true})).toHaveCount(0);
      await publicPage.reload();
      await expect(publicPage.getByRole('heading', {name: productName, exact: true})).toHaveCount(0);
      expect((await publicPage.request.get(publicImageUrl)).status()).toBe(404);
      // Keep a visible product for the subsequent table and isolation checks.
      await card.getByRole('button', {name: 'Editar', exact: true}).click();
      await page.getByLabel('Publicado', {exact: true}).check();
      await page.getByRole('button', {name: 'Salvar', exact: true}).click();
      await expect(page.getByRole('heading', {name: 'Editar registro', exact: true})).toHaveCount(0);
    });

    await test.step('manager B cannot read or alter private products from A', async () => {
      const managerB = await browser.newContext({baseURL: new URL(page.url()).origin});
      await previewAccess(managerB);
      try {
        const otherPage = await managerB.newPage();
        await login(otherPage, 'b');
        const denied = await otherPage.evaluate(async ({restaurant, product}) => {
          const path = `/v1/restaurants/${restaurant}/products/${product}/`;
          const csrf = document.cookie.split('; ').find(part => part.startsWith('csrftoken='))?.slice(10) || '';
          const read = await fetch(path);
          const write = await fetch(path, {method: 'PATCH', headers: {'Content-Type': 'application/json', 'X-CSRFToken': decodeURIComponent(csrf)}, body: JSON.stringify({name: 'UNAUTHORIZED B TO A'})});
          return [read.status, write.status];
        }, {restaurant: required('TAVVO_E2E_RESTAURANT_A'), product: required('TAVVO_E2E_PRODUCT_A')});
        expect(denied).toEqual([404, 404]);
        await otherPage.getByRole('button', {name: 'Sair', exact: true}).click();
      } finally {
        await managerB.close();
      }
    });

    await test.step('tenant B stays distinct and rejects reads and mutations from manager A', async () => {
      const menuResponse = await publicPage.request.get(`${apiOrigin}/v1/public/restaurants/restaurante-b/menu/`);
      expect(menuResponse.status()).toBe(200);
      const menuB = await menuResponse.json() as {categories: {products: {id: string; name: string}[]}[]};
      const seededProductB = menuB.categories.flatMap(category => category.products).find(product => product.id === productB);
      expect(seededProductB, 'The seeded B product must be public for the isolation check').toBeDefined();
      await publicPage.goto(`${publicOrigin}/r/restaurante-b`);
      await expect(publicPage.getByRole('heading', {name: 'Restaurante B', exact: true})).toBeVisible();
      await expect(publicPage.getByRole('heading', {name: seededProductB!.name, exact: true})).toBeVisible();
      await expect(publicPage.getByRole('heading', {name: productName, exact: true})).toHaveCount(0);

      const denied = await page.evaluate(async ({restaurantId, productId}) => {
        const path = `/v1/restaurants/${restaurantId}/products/${productId}/`;
        const csrf = document.cookie.split('; ').find(part => part.startsWith('csrftoken='))?.slice('csrftoken='.length) || '';
        const read = await fetch(path, {credentials: 'same-origin'});
        const write = await fetch(path, {
          method: 'PATCH', credentials: 'same-origin',
          headers: {'Content-Type': 'application/json', 'X-CSRFToken': decodeURIComponent(csrf)},
          body: JSON.stringify({name: 'UNAUTHORIZED E2E MUTATION'}),
        });
        return {readStatus: read.status, writeStatus: write.status, readBody: await read.text()};
      }, {restaurantId: restaurantB, productId: productB});
      expect(denied.readStatus).toBe(404);
      expect(denied.writeStatus).toBe(404);
      expect(denied.readBody).not.toContain(seededProductB!.name);
      await publicPage.reload();
      await expect(publicPage.getByRole('heading', {name: seededProductB!.name, exact: true})).toBeVisible();
      await expect(publicPage.getByText('UNAUTHORIZED E2E MUTATION', {exact: true})).toHaveCount(0);
    });

    await test.step('remove an image and revoke its public URL', async () => {
      await page.getByRole('button', {name: 'Produtos', exact: true}).click();
      const card = page.locator('.records article').filter({has: page.getByText(productName, {exact: true})});
      if (!await card.getByRole('button', {name: 'Remover imagem', exact: true}).isVisible()) {
        await card.getByText('Imagens (1)', {exact: true}).click();
      }
      await card.getByRole('button', {name: 'Remover imagem', exact: true}).click();
      await expect(card.getByText('Imagens (0)', {exact: true})).toBeVisible();
      expect((await publicPage.request.get(publicImageUrl)).status()).toBe(404);
    });

    await test.step('create a table, open its QR destination and reject the revoked identifier', async () => {
      await page.getByRole('button', {name: 'Mesas e QR', exact: true}).click();
      await page.getByRole('button', {name: 'Adicionar', exact: true}).click();
      await page.getByLabel('Identificação da mesa', {exact: true}).fill(tableLabel);
      await page.getByRole('button', {name: 'Salvar', exact: true}).click();
      const tableCard = page.locator('.records article').filter({has: page.getByText(tableLabel, {exact: true})});
      await expect(tableCard).toBeVisible();
      const qrImage = tableCard.getByRole('img', {name: `QR Code da ${tableLabel}`, exact: true});
      await expect(qrImage).toBeVisible();
      await expect.poll(() => qrImage.evaluate(image => (image as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
      const qrUrl = await tableCard.locator('a').first().getAttribute('href');
      expect(qrUrl).toBeTruthy();
      const qrPath = new URL(qrUrl!).pathname;
      expect(qrPath).toMatch(/^\/q\/[0-9a-f]{32}\.[A-Za-z0-9_-]{32}$/);
      await publicPage.goto(qrUrl!);
      await expect(publicPage.getByRole('heading', {name: 'Restaurante A', exact: true})).toBeVisible();
      await expect(publicPage.getByText(`Mesa: ${tableLabel}`, {exact: true})).toBeVisible();
      await expect(publicPage.getByRole('heading', {name: productName, exact: true})).toBeVisible();
      await tableCard.getByRole('button', {name: 'Editar', exact: true}).click();
      await page.getByLabel('Status', {exact: true}).selectOption('inactive');
      await page.getByRole('button', {name: 'Salvar', exact: true}).click();
      await expect(tableCard.getByText('Este identificador está desativado.', {exact: true})).toBeVisible();
      await publicPage.reload();
      await expect(publicPage.getByRole('heading', {name: 'Cardápio não encontrado', exact: true})).toBeVisible();
      await expect(publicPage.getByRole('heading', {name: productName, exact: true})).toHaveCount(0);
    });

    await test.step('logout revokes the real browser session', async () => {
      await page.getByRole('button', {name: 'Sair', exact: true}).click();
      await expect(page.getByRole('button', {name: 'Entrar', exact: true})).toBeVisible();
      const sessionStatus = await page.evaluate(async () => (await fetch('/v1/auth/me/', {credentials: 'same-origin'})).status);
      expect([401, 403]).toContain(sessionStatus);
      expect(browserErrors).toEqual([]);
    });
  } finally {
    await visitor.close();
  }
});

test('public menu remains usable on a narrow mobile viewport', async ({page}) => {
  await page.setViewportSize({width: 390, height: 844});
  await page.goto(`${publicOrigin}/r/restaurante-b`);
  await expect(page.getByRole('heading', {name: 'Restaurante B', exact: true})).toBeVisible();
  await expect(page.getByRole('navigation', {name: 'Categorias do cardápio'})).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({path: test.info().outputPath('public-mobile.png'), fullPage: true});
});

test('MFA-authenticated Tavvo administrator creates and deactivates a restaurant', async ({browser, baseURL}) => {
  const statePath = required('TAVVO_E2E_ADMIN_STATE');
  const context = await browser.newContext({baseURL, storageState: statePath});
  await previewAccess(context);
  const page = await context.newPage();
  const suffix = String(Date.now());
  const name = `E2E Central ${suffix}`;
  const slug = `e2e-central-${suffix}`;
  try {
    await page.goto('/');
    await expect(page.getByRole('heading', {name: 'Administração Tavvo', exact: true})).toBeVisible();
    await page.getByRole('button', {name: 'Adicionar', exact: true}).click();
    await page.getByLabel('Nome', {exact: true}).fill(name);
    await page.getByLabel('Slug público', {exact: true}).fill(slug);
    await page.getByRole('button', {name: 'Salvar', exact: true}).click();
    const card = page.locator('.records article').filter({has: page.getByText(name, {exact: true})});
    await expect(card).toBeVisible();
    await expect(card).toContainText(`${slug} · active`);
    await card.getByRole('button', {name: 'Editar', exact: true}).click();
    await page.getByLabel('Status', {exact: true}).selectOption('inactive');
    await page.getByRole('button', {name: 'Salvar', exact: true}).click();
    await expect(card).toContainText(`${slug} · inactive`);
    const publicResponse = await page.request.get(`${apiOrigin}/v1/public/restaurants/${slug}/menu/`);
    expect(publicResponse.status()).toBe(404);
  } finally {
    await context.close();
  }
});
