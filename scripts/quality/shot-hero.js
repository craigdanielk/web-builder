const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await (await b.newContext({viewport:{width:1440,height:860}})).newPage();
  await p.goto('file://'+process.argv[2], {waitUntil:'networkidle',timeout:60000}).catch(()=>{});
  await p.waitForTimeout(3000);
  await p.screenshot({path:process.argv[3]});
  console.log('HERO ok'); await b.close();
})().catch(e=>{console.error(e.message);process.exit(2)});
