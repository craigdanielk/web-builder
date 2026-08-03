const { chromium } = require('playwright');
(async () => {
  const url = process.argv[2], out = process.argv[3];
  const b = await chromium.launch();
  const p = await (await b.newContext({viewport:{width:1440,height:900},deviceScaleFactor:1})).newPage();
  await p.goto(url, {waitUntil:'networkidle', timeout:90000}).catch(()=>{});
  await p.waitForTimeout(2000);
  await p.evaluate(async()=>{for(let y=0;y<document.body.scrollHeight;y+=600){scrollTo(0,y);await new Promise(r=>setTimeout(r,160));}scrollTo(0,0);});
  await p.waitForTimeout(2500);
  await p.evaluate(()=>{try{if(window.ScrollTrigger)ScrollTrigger.getAll().forEach(t=>t.kill());if(window.gsap)gsap.set('.rv',{opacity:1,y:0});}catch(e){}document.querySelectorAll('.rv').forEach(e=>{e.style.opacity=1;e.style.transform='none';});});
  await p.waitForTimeout(800);
  await p.screenshot({path:out, fullPage:true});
  console.log('LIVE shot ok'); await b.close();
})().catch(e=>{console.error(e.message);process.exit(2)});
