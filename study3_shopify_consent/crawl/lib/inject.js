// Emulated GPC: defines navigator.globalPrivacyControl = true on Navigator / WorkerNavigator.
// Also leaves a marker (__cs3_gpc) with the number of own globals at injection time, so we can later
// verify that the injection ran BEFORE the target's own scripts (they add globals afterwards).
const GPC_INJECT = `(function(){var g=(typeof globalThis!=='undefined')?globalThis:self;try{
var n0=Object.getOwnPropertyNames(g).length;
var P=(typeof WorkerNavigator!=='undefined'&&typeof Navigator==='undefined')?WorkerNavigator.prototype:((typeof WorkerNavigator!=='undefined'&&g.navigator instanceof WorkerNavigator)?WorkerNavigator.prototype:Navigator.prototype);
Object.defineProperty(P,'globalPrivacyControl',{get:function(){return true},configurable:true,enumerable:true});
if(!Object.prototype.hasOwnProperty.call(g,'__cs3_gpc'))Object.defineProperty(g,'__cs3_gpc',{value:{t:(g.performance?g.performance.now():null),n0:n0,href:String(g.location&&g.location.href).slice(0,200)},enumerable:false,configurable:true,writable:true});
}catch(e){try{g.__cs3_gpc_err=String(e).slice(0,200)}catch(_){}}})();`;

// Expression evaluated later inside each worker to verify the injection.
const GPC_VERIFY = `(function(){var g=(typeof globalThis!=='undefined')?globalThis:self;return {gpc:(typeof navigator!=='undefined')?navigator.globalPrivacyControl:null,inj:g.__cs3_gpc||null,err:g.__cs3_gpc_err||null,n1:Object.getOwnPropertyNames(g).length,href:String(g.location&&g.location.href).slice(0,300)};})()`;

module.exports = { GPC_INJECT, GPC_VERIFY };
