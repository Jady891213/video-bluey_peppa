import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createRequire} from 'node:module';
import ts from 'typescript';
import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {bundle} from '@remotion/bundler';
import {openBrowser, renderMedia, renderStill, selectComposition} from '@remotion/renderer';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '../..');
const out = path.join(root, 'materials/final/gift/待确认成片/SVG_Remotion_佩奇画画_20261015');
const tmp = path.join(root, 'TMP to delete - SVG小样');
const bundledBin=path.join(here,'node_modules/@remotion',`compositor-${process.platform}-${process.arch}`);
const bundledFfmpeg=path.join(bundledBin,'ffmpeg');
const ffmpegExecutable=fs.existsSync(bundledFfmpeg)?bundledFfmpeg:'ffmpeg';
const ffmpegEnv=fs.existsSync(bundledFfmpeg)?{...process.env,DYLD_LIBRARY_PATH:bundledBin}:process.env;
const stillsOnly = process.argv.includes('--stills');
fs.mkdirSync(tmp, {recursive:true});
execFileSync('python3', [path.join(here,'prepare.py')], {stdio:'inherit'});
let browser;
try {
  const serveUrl = await bundle({entryPoint:path.join(here,'src/index.ts'), outDir:path.join(tmp,'bundle'), publicDir:path.join(here,'public')});
  browser = await openBrowser('chrome', {
    browserExecutable:process.env.REMOTION_BROWSER_EXECUTABLE || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  });
  const composition = await selectComposition({serveUrl, id:'PeppaDrawing', puppeteerInstance:browser});
  if (stillsOnly) {
    for (const frame of [0,45,90,150,177,206,255,285]) {
      await renderStill({serveUrl, composition, frame, puppeteerInstance:browser,
        imageFormat:'png', output:path.join(tmp,`frame-${frame}.png`)});
    }
    console.log('Key frames rendered to TMP to delete - SVG小样');
  } else {
    const silent = path.join(tmp,'silent.mp4');
    let lastProgress=-20;
    await renderMedia({serveUrl, composition, puppeteerInstance:browser, codec:'h264',
      outputLocation:silent, concurrency:2, crf:17, pixelFormat:'yuv420p',
      onProgress:({progress})=>{const p=Math.floor(progress*100);if(p>=lastProgress+20){lastProgress=p;process.stdout.write(`render ${p}%\n`);}}});
    const args=['-v','error','-y','-i',silent,'-i',path.join(tmp,'dialogue-mix.wav')];
    const output=path.join(out,'准备礼物_佩奇画画与乔治拿笔_SVG小样_10秒.mp4');
    args.push('-map','0:v:0','-map','1:a:0',
      '-c:v','copy','-c:a','aac','-b:a','192k','-ar','48000','-ac','2','-t','10','-movflags','+faststart',output);
    execFileSync(ffmpegExecutable,args,{stdio:'inherit',env:ffmpegEnv,timeout:60000});
    await renderStill({serveUrl,composition,frame:90,puppeteerInstance:browser,imageFormat:'png',output:path.join(out,'预览封面.png')});
    // Export the same vector artwork, without any browser screenshot or raster trace.
    const compiled=ts.transpileModule(fs.readFileSync(path.join(here,'src/Scene.tsx'),'utf8'),{
      compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true,target:ts.ScriptTarget.ES2022},
    }).outputText;
    const componentModule={exports:{}};
    const localRequire=createRequire(path.join(here,'src/Scene.tsx'));
    new Function('require','module','exports',compiled)(localRequire,componentModule,componentModule.exports);
    const svg=renderToStaticMarkup(React.createElement(componentModule.exports.SceneArtwork,{frame:90}));
    fs.writeFileSync(path.join(out,'佩奇与乔治_分层矢量预览.svg'),svg+'\n');
    execFileSync('python3',[path.join(here,'validate.py')],{stdio:'inherit'});
    console.log('Rendered:',path.relative(root,output));
  }
} finally {
  if(browser)await browser.close({silent:true});
  if(!stillsOnly)fs.rmSync(tmp,{recursive:true,force:true});
}
