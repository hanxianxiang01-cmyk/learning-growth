'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '../../..');
const read = p => fs.readFileSync(path.join(root, p), 'utf8');

/** Source-level guard, NOT a replacement for browser E2E or style computation. */
test('task-pinned Router carries the responsive grid-item class for BOTH implementation paths', () => {
 const source=read('apps/child-web/src/features/math-interaction/TaskRendererImplementationBoundary.tsx');
 assert.match(source, /className="mik-implementation-route"[^>]*data-testid="mik-route"/);
 assert.match(source, /decision\.version === 'kernel' \? kernel : legacy/);
});
test('route shell shrinks as a grid item; does not hide scrolling math content', () => {
 const css=read('apps/child-web/app/globals.css');
 const m=css.match(/\.mik-implementation-route\s*\{([^}]+)\}/);
 assert.ok(m,'route constraint CSS must exist');
 assert.match(m[1],/min-width\s*:\s*0\s*;/);
 assert.match(m[1],/max-width\s*:\s*100%\s*;/);
 assert.match(m[1],/width\s*:\s*100%\s*;/);
 assert.doesNotMatch(m[1],/(?:overflow|display\s*:\s*none)/,'do not conceal overflow instead of constraining the grid item');
});
test('browser regression names every previously failing renderer and both phone widths and skins', () => {
 const source=read('apps/child-web/e2e-v6/route-responsive.spec.mjs');
 for(const id of ['number-line','place-value','ten-frame','shape-canvas','direction-grid','ruler']){
   assert.ok(source.includes(`'${id}'`),`${id} not covered`);
 }
 for(const skin of ['exploration-lab','healing'])assert.ok(source.includes(`'${skin}'`));
 for(const width of ['320','390'])assert.ok(source.includes(width));
 assert.match(source,/scrollWidth\s*-\s*window\.innerWidth/);
});
test('existing V6 gallery still checks all 20 fixture interactions and viewport overflow', () => {
 const source=read('apps/child-web/e2e-v6/full-gallery.spec.mjs');
 assert.match(source,/for\s*\(const \[index,fixture\] of fixtures\.entries\(\)\)/);
 assert.match(source,/\[768,390,320\]/);
 assert.match(source,/document\.documentElement\.scrollWidth-window\.innerWidth/);
});
