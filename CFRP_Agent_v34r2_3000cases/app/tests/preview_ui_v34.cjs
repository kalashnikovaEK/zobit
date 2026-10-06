// [NEW v34] Exercise the actual preview UI extension with a minimal DOM.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
class El{constructor(){this.style={};this.listeners={};this.disabled=false;this.hidden=false;this.value='원문';}append(){}after(){}focus(){}addEventListener(e,f){(this.listeners[e]??=[]).push(f);}fire(e){for(const f of this.listeners[e]||[])f();}requestSubmit(){this.submitted=true;}}
const ids={};for(const id of ['chatForm','chatInput','chatSend','simForm','modelProfile','chatClear','resetBtn','loadJsonBtn','runBtn'])ids[id]=new El();
const made=[];let inputs={thickness:10};
const ctx={window:{},document:{createElement(){const el=new El();made.push(el);return el;}},$:id=>ids[id],payload:()=>inputs,setStatus(){}};
vm.createContext(ctx);const s=fs.readFileSync(__dirname+'/../chat_ui.js','utf8');vm.runInContext(s.slice(s.indexOf('// [NEW v34] Explicit confirmation')),ctx);
const preview={confirmation_token:'TOKEN',preview:{action:'물리 계산',target:'최고온도 최소화',material:'AS4/8552 평판',change_labels:['2차 승온속도'],fixed_variables:['두께'],condition:{thickness:10},limits:{Tmax:195,delta_Tmax:20,final_DoC:.9}}};
ctx.window.showChatPreviewV34(preview);assert.equal(made[0].hidden,false);assert(made[2].textContent.includes('195'));
made[3].fire('click');assert(ids.chatForm.submitted);let body=ctx.window.chatBodyV34({request:'원문'});assert.equal(body.confirmation_token,'TOKEN');assert.equal(made[0].hidden,true);
ctx.window.showChatPreviewV34(preview);inputs={thickness:12};made[3].fire('click');assert.equal(made[0].hidden,true);assert.equal(ctx.window.chatBodyV34({request:'새 요청'}).confirmation_token,undefined);
ctx.window.showChatPreviewV34(preview);ids.chatInput.fire('input');assert.equal(made[0].hidden,true);
console.log('PASS: preview text, explicit confirmation token, changed-input and edited-request invalidation');
