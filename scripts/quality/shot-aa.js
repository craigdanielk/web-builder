const { chromium } = require('playwright');
(async () => {
  const file = 'file://' + process.argv[2], out = process.argv[3];
  const b = await chromium.launch();
  const p = await (await b.newContext({viewport:{width:1440,height:900},deviceScaleFactor:1})).newPage();
  await p.goto(file, {waitUntil:'networkidle', timeout:60000}).catch(()=>{});
  await p.waitForTimeout(2500);
  // kill scroll-reveal state so the stitched full-page shot is true
  await p.evaluate(()=>{ try{ if(window.ScrollTrigger){ScrollTrigger.getAll().forEach(t=>t.kill());} if(window.gsap){gsap.set('.rv',{clearProps:'all',opacity:1,y:0});} }catch(e){} document.querySelectorAll('.rv').forEach(e=>{e.style.opacity=1;e.style.transform='none';}); });
  await p.waitForTimeout(500);
  await p.screenshot({path:out, fullPage:true});
  console.log('SHOT '+out); await b.close();
})().catch(e=>{console.error('FAIL',e.message);process.exit(2)});
