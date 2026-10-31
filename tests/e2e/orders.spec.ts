import {test,expect} from '@playwright/test';
import {previewAccess} from './preview-access';

test('customer submits a pickup order and manager completes fulfillment',async({page,browser})=>{
  await previewAccess(page.context());
  await page.goto('/');
  await page.getByLabel('E-mail',{exact:true}).fill('gestor-a@example.test');
  await page.getByLabel('Senha',{exact:true}).fill(process.env.TAVVO_E2E_PASSWORD!);
  await page.getByRole('button',{name:'Entrar',exact:true}).click();
  await page.getByRole('button',{name:'Entrega e retirada',exact:true}).click();
  await page.getByLabel('Receber pedidos',{exact:true}).check();
  await page.getByLabel('Permitir retirada',{exact:true}).check();
  await page.getByLabel('Permitir pagamento presencial',{exact:true}).check();
  await page.getByRole('button',{name:'Salvar',exact:true}).click();
  await expect(page.getByText('Configurações salvas.',{exact:true})).toBeVisible();
  const context=await browser.newContext({viewport:{width:390,height:844}});
  await previewAccess(context);
  const visitor=await context.newPage();
  const errors:string[]=[];visitor.on('pageerror',e=>errors.push(e.message));
  const name=`Cliente E2E ${Date.now()}`;
  try{
    await visitor.goto(`${process.env.TAVVO_E2E_PUBLIC_URL||'http://localhost:3000'}/r/restaurante-a`);
    await visitor.getByRole('button',{name:'Adicionar ao pedido'}).first().click();
    await visitor.getByRole('link',{name:/Ver pedido/}).click();
    await visitor.getByLabel('Seu nome',{exact:true}).fill(name);
    await visitor.getByLabel('Telefone',{exact:true}).fill('11999999999');
    await visitor.getByRole('button',{name:'Enviar pedido',exact:true}).click();
    await expect(visitor.getByRole('heading',{name:'Acompanhe seu pedido'})).toBeVisible();
    await expect(visitor.getByText('Recebido',{exact:true})).toBeVisible();
    await visitor.reload();
    await expect(visitor.getByText('Recebido',{exact:true})).toBeVisible();
    await visitor.screenshot({path:'.local/commerce-mobile-order.png',fullPage:true});
    expect(await visitor.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
    await page.getByRole('button',{name:'Pedidos',exact:true}).click();
    const card=page.locator('.record-card').filter({hasText:name});
    await expect(card).toBeVisible();
    for(const label of ['Aceito','Em preparo','Pronto']){
      await card.getByRole('button',{name:label,exact:true}).click();
      await expect(card.locator('.badge')).toHaveText(label);
    }
    await card.getByRole('button',{name:'Confirmar pagamento recebido'}).click();
    await expect(card).toContainText('Pago');
    await card.getByRole('button',{name:'Concluído',exact:true}).click();
    await expect(card.locator('.badge')).toHaveText('Concluído');
    await expect(visitor.getByText('Concluído',{exact:true})).toBeVisible({timeout:20000});
    await page.screenshot({path:'.local/commerce-admin-orders.png',fullPage:true});
    await page.getByRole('button',{name:'Assinatura',exact:true}).click();
    await expect(page.getByRole('heading',{name:'Assinatura Tavvo'})).toBeVisible();
    expect(errors).toEqual([]);
  }finally{await context.close();}
});
