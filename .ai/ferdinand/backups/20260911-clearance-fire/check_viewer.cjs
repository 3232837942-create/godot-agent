const {chromium}=require('C:/Users/32328/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs');const {pathToFileURL}=require('url');
const dir='X:/迅雷下载/godot-agent/assets/3d/ferdinand_v3';
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--use-angle=swiftshader','--enable-unsafe-swiftshader','--allow-file-access-from-files']});
 const page=await browser.newPage({viewport:{width:1800,height:1120},deviceScaleFactor:1});const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
 await page.goto(pathToFileURL(dir+'/viewer.html').href);await page.waitForSelector('body[data-ready="true"]',{timeout:45000,state:'attached'});await page.waitForTimeout(1500);
 await page.screenshot({path:dir+'/viewer_iso.png'});
 const snapshots={iso:await page.evaluate(()=>ferdinandInspection.snapshot())};
 for(const view of ['front','side','top','rear']){await page.click('[data-view="'+view+'"]');await page.waitForTimeout(180);snapshots[view]=await page.evaluate(()=>ferdinandInspection.snapshot());}
 await page.click('[data-view="iso"]');
 for(const action of ['drive','aim','fire','hatches']){await page.click('[data-action="'+action+'"]');await page.waitForTimeout(550);snapshots[action]=await page.evaluate(()=>ferdinandInspection.snapshot());}
 const poses=await page.evaluate(()=>{const out={};for(const [name,time] of [['rest',1/30],['drive',.5],['down',110/30],['up',145/30],['recoil',186/30],['hatch',250/30]]){ferdinandInspection.seek(time);out[name]=ferdinandInspection.snapshot();}out.hatchReadout=document.querySelector('#hatch').textContent;return out;});
 if(Math.abs(poses.hatch.hatch*180/Math.PI)>80.01||Math.abs(poses.hatch.hatch*180/Math.PI)<79.99||poses.hatchReadout!=='100%')throw Error('Hatch pose/readout mismatch '+JSON.stringify(poses));
 if(Math.abs(poses.up.elevation*180/Math.PI-14)>.01||Math.abs(poses.down.elevation*180/Math.PI+4)>.01)throw Error('Aim extrema mismatch');
 if(Math.abs(poses.recoil.recoil+.23)>.001)throw Error('Recoil distance mismatch');
 if(Math.hypot(...poses.drive.trackPosition.map((v,i)=>v-poses.rest.trackPosition[i]))<.02)throw Error('Track animation did not move');
 await page.evaluate(()=>ferdinandInspection.seek(250/30));await page.waitForTimeout(300);await page.screenshot({path:dir+'/viewer_hatches.png'});
 await page.click('[data-action="explode"]');await page.waitForTimeout(1500);await page.screenshot({path:dir+'/viewer_exploded.png'});snapshots.explode=await page.evaluate(()=>ferdinandInspection.snapshot());
 await page.click('[data-action="reset"]');await page.mouse.move(950,530);await page.mouse.down();await page.mouse.move(1100,580,{steps:8});await page.mouse.up();await page.mouse.wheel(0,-140);await page.waitForTimeout(200);snapshots.orbit=await page.evaluate(()=>ferdinandInspection.snapshot());
 await page.setViewportSize({width:960,height:700});await page.click('[data-view="iso"]');await page.waitForTimeout(400);await page.screenshot({path:dir+'/viewer_small.png'});
 fs.writeFileSync(dir+'/viewer_validation.json',JSON.stringify({errors,snapshots,poses},null,2));await browser.close();
 if(errors.length)throw Error(errors.join('\n'));if(snapshots.iso.trackCount!==212)throw Error('Track count mismatch');console.log('VIEWER_QA_OK',JSON.stringify(snapshots));
})().catch(e=>{console.error(e);process.exit(1)});
