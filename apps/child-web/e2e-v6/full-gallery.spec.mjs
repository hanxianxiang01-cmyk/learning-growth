import fs from "node:fs";
import { test, expect } from "@playwright/test";
const fixtures = JSON.parse(fs.readFileSync(new URL("../src/dev/v6/fixtures.json", import.meta.url), "utf8"));
const response = async page => JSON.parse(await page.getByTestId("v6-gallery-response").textContent());
const click = async (p, id, count = 1) => { for (let n = 0; n < count; n++) await p.getByTestId(id).click(); };
async function solve(p, renderer, correct, mode) {
  switch (renderer) {
    case "number-line": for (const n of (correct ? [25,30,35] : [25,30])) await click(p, `v6-line-tick-${n}`); break;
    case "column-arithmetic":
      for (const [label, value] of [["百位结果","0"],["十位结果","7"],["个位结果",correct ? "5" : "4"]]) await p.getByLabel(label, {exact:true}).fill(value);
      if (correct) await p.getByLabel("个位进位到十位",{exact:true}).click(); break;
    case "object-counter": await click(p,"oc-add-g1",4); await click(p,"oc-add-g2",correct ? 3 : 2); break;
    case "number-input": await p.getByTestId("ni-input").fill(correct ? "5" : "4"); break;
    case "ten-frame":
      for(let n=0;n<(correct?10:9);n++) await click(p,`tf-cell-${n}`);
      if(correct) {await click(p,"tf-make-ten");for(let n=0;n<3;n++)await click(p,`tf-cell-${n}`);} break;
    case "bar-model": for(const [bar,n] of [["a",5],["b",3],["c",correct?8:7]])await click(p,`bm-plus-${bar}`,n); break;
    case "place-value": for(const [i,n] of (correct?[3,5,2]:[2,5,3]).entries()){await click(p,`pv-tile-${n}`);await click(p,`pv-slot-${i}`);} break;
    case "formula-board":
      if(mode==="unknown_number"){await click(p,"fb-slot-box");await click(p,correct?"fb-key-5":"fb-key-4");}
      else{await click(p,"fb-slot-op0");await click(p,correct?"fb-op-minus":"fb-op-plus");} break;
    case "array-board":await click(p,"ab-row-plus",correct?3:2);await click(p,"ab-col-plus",4);break;
    case "grouping-board": {const count=correct?3:2;await click(p,"gb-add-group",count);for(let i=0;i<count;i++)await click(p,`gb-give-${i}`,correct?4:6);break;}
    case "estimation-canvas":
      await p.getByTestId("ec-slider").evaluate((e,value)=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,"value").set.call(e,String(value));e.dispatchEvent(new Event("input",{bubbles:true}));e.dispatchEvent(new Event("change",{bubbles:true}));},correct?40:30);
      await click(p,"ec-reason-use_reference");break;
    case "shape-gallery":for(const n of(correct?["s1","s2","s3"]:["r1"])){await click(p,`sg-shape-${n}`);await click(p,"v6-sg-place-home");}break;
    case "shape-canvas":for(const [x,y]of(correct?[[0,0],[3,0],[3,2],[0,2]]:[[0,0],[1,0],[1,1],[0,1]]))await click(p,`sc-peg-${x}-${y}`);break;
    case "sorting-board":await click(p,"sb-card-0");await click(p,"sb-card-1");if(correct){await click(p,"sb-card-1");await click(p,"sb-card-3");}break;
    case "direction-grid":await click(p,"dg-cell-2-3");if(correct){await click(p,"dg-cell-2-4");await click(p,"dg-cell-3-4");}break;
    case "clock":for(let i=0;i<(correct?3:2);i++)await p.getByLabel("小时加一",{exact:true}).click();break;
    case "money-board":await click(p,"mb-add-10",3);if(correct)await click(p,"mb-add-5");break;
    case "pattern-board":await click(p,correct?"pb-token-1":"pb-token-2");await click(p,"pb-token-2");break;
    case "ruler":await click(p,correct?"rl-tick-3":"rl-tick-0");await click(p,"rl-tick-8");break;
    default: throw new Error(`Missing independent test actions for ${renderer}`);
  }
}
for(const [index,fixture] of fixtures.entries()) {
  test(`${fixture.id} / ${fixture.renderer}: wrong/correct payload, skins, widths, lock/reset`,async({page},testInfo)=>{
    const errors=[], backendRequests=[];
    page.on("pageerror",e=>errors.push(e.message));
    await page.route("**/v1/**",route=>{backendRequests.push(route.request().url());return route.abort();});
    await page.goto("/dev/v6");
    await page.getByTestId("v6-gallery-renderer").selectOption(String(index));
    const board=page.locator("[data-v6-renderer]"), submit=board.locator("button.primary-button").last();
    await expect(board).toHaveCount(1);await expect(submit).toBeDisabled();
    await solve(page,fixture.renderer,false,fixture.task.ui_schema.workspaces[0].mode);
    await expect(submit).toBeEnabled();const wrong=await response(page);
    expect(String(wrong.answer)).not.toBe(fixture.expected);
    await submit.click();expect(JSON.parse(await page.getByTestId("v6-gallery-submission").textContent())).toEqual(wrong);
    await page.getByTestId("v6-gallery-skin").selectOption("healing");
    expect(await response(page)).toEqual(wrong);
    for(const width of [768,390,320]) {
      await page.setViewportSize({width,height:900});expect(await response(page)).toEqual(wrong);
      expect(await page.evaluate(()=>document.documentElement.scrollWidth-window.innerWidth)).toBeLessThanOrEqual(1);
    }
    await page.getByTestId("v6-gallery-lock").check();await expect(submit).toBeDisabled();
    await expect(board.locator("button:enabled,input:enabled")).toHaveCount(0);
    await page.getByTestId("v6-gallery-lock").uncheck();expect(await response(page)).toEqual(wrong);
    if(fixture.renderer==="number-input")await click(page,"v6-key-clear");
    else await board.getByRole("button",{name:fixture.renderer==="shape-canvas"?"清空":"重置",exact:true}).click();
    await expect(submit).toBeDisabled();
    await solve(page,fixture.renderer,true,fixture.task.ui_schema.workspaces[0].mode);
    await expect(submit).toBeEnabled();const correct=await response(page);expect(String(correct.answer)).toBe(fixture.expected);
    await submit.click();expect(JSON.parse(await page.getByTestId("v6-gallery-submission").textContent())).toEqual(correct);
    await page.setViewportSize({width:390,height:900});
    await page.locator(".v6-task-content").screenshot({path:testInfo.outputPath("healing-390.png")});
    await page.setViewportSize({width:1280,height:1000});await page.getByTestId("v6-gallery-skin").selectOption("exploration-lab");
    await page.locator(".v6-task-content").screenshot({path:testInfo.outputPath("lab-1280.png")});
    await testInfo.attach("actual-payloads",{body:JSON.stringify({wrong,correct},null,2),contentType:"application/json"});
    expect(backendRequests).toEqual([]);expect(errors).toEqual([]);
  });
}
