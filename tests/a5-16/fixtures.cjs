'use strict';
const all=[
  [{rendererId:'number-input',text:'',integerOnly:true,maxLength:4},null,null,null],
  [{rendererId:'formula-board',slots:[{id:'s',label:'空格'}],activeSlotId:'s',digits:[4],operators:['+']},'digit:4','slot:s','applyNumberKey'],
  [{rendererId:'ten-frame',frames:[Array.from({length:10},()=>({occupied:false}))]},'bank','cell:0:0','applyCell'],
  [{rendererId:'grouping-board',groupCounts:[1,0],poolCount:3},'pool','group:1','applyAddItem'],
  [{rendererId:'money-board',denominationsJiao:[1,5,10,50],walletCounts:{10:1}},'bank:10','wallet','applyAddCoin'],
  [{rendererId:'bar-model',blocks:[2],maxBlocks:[6]},'bar:0','bar:0:1','applyBarDelta'],
  [{rendererId:'array-board',rows:2,cols:3,maxRows:5,maxCols:6},'row','row:1','applyRowDelta'],
  [{rendererId:'place-value',pool:[{id:'a',label:'2'},{id:'b',label:'7'}],pickedPoolIndex:0,slots:[{id:'tens',label:'十位'},{id:'ones',label:'个位'}]},'pool:0','slot:0','applySlot'],
  [{rendererId:'sorting-board',cards:[{id:'a',label:'2'},{id:'b',label:'1'}],selectedCardId:'a'},'card:0','target:1','applySwap'],
  [{rendererId:'number-line',currentTick:4,minTick:0,maxTick:10},'cursor','tick:8','applyJump'],
  [{rendererId:'ruler',marks:[0,2],minTick:0,maxTick:20,step:1},'mark:0','tick:8','applyPlaceMark'],
  [{rendererId:'direction-grid',rows:3,cols:3,current:{r:1,c:1}},'cursor','cell:1:2','applyMoveTo'],
  [{rendererId:'shape-canvas',minX:0,maxX:2,minY:0,maxY:2},'pen','point:2:1','applyAddPoint'],
  [{rendererId:'pattern-board',palette:[1,2],blanks:[{locked:false,label:'第一个空格'}]},'token:1','blank:0','applyReplaceAt'],
  [{rendererId:'shape-gallery',shapes:[{id:'circle-a',label:'圆形'}],selectedShapeId:'circle-a',homeIds:[]},'shape:0','home','applyPlaceHome'],
  [{rendererId:'estimation-canvas',min:0,max:20,step:1,currentEstimate:null},'estimate','range','applyEstimate']
];
module.exports.samples=all;
