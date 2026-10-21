var Kt=globalThis,Gt=Kt.ShadowRoot&&(Kt.ShadyCSS===void 0||Kt.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,ce=Symbol(),Le=new WeakMap,wt=class{constructor(e,t,n){if(this._$cssResult$=!0,n!==ce)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=e,this.t=t}get styleSheet(){let e=this.o,t=this.t;if(Gt&&e===void 0){let n=t!==void 0&&t.length===1;n&&(e=Le.get(t)),e===void 0&&((this.o=e=new CSSStyleSheet).replaceSync(this.cssText),n&&Le.set(t,e))}return e}toString(){return this.cssText}},Yt=i=>new wt(typeof i=="string"?i:i+"",void 0,ce),k=(i,...e)=>{let t=i.length===1?i[0]:e.reduce((n,s,a)=>n+(r=>{if(r._$cssResult$===!0)return r.cssText;if(typeof r=="number")return r;throw Error("Value passed to 'css' function must be a 'css' function result: "+r+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(s)+i[a+1],i[0]);return new wt(t,i,ce)},Ne=(i,e)=>{if(Gt)i.adoptedStyleSheets=e.map(t=>t instanceof CSSStyleSheet?t:t.styleSheet);else for(let t of e){let n=document.createElement("style"),s=Kt.litNonce;s!==void 0&&n.setAttribute("nonce",s),n.textContent=t.cssText,i.appendChild(n)}},pe=Gt?i=>i:i=>i instanceof CSSStyleSheet?(e=>{let t="";for(let n of e.cssRules)t+=n.cssText;return Yt(t)})(i):i;var{is:En,defineProperty:Tn,getOwnPropertyDescriptor:Rn,getOwnPropertyNames:Hn,getOwnPropertySymbols:Ln,getPrototypeOf:Nn}=Object,Qt=globalThis,Oe=Qt.trustedTypes,On=Oe?Oe.emptyScript:"",Pn=Qt.reactiveElementPolyfillSupport,yt=(i,e)=>i,he={toAttribute(i,e){switch(e){case Boolean:i=i?On:null;break;case Object:case Array:i=i==null?i:JSON.stringify(i)}return i},fromAttribute(i,e){let t=i;switch(e){case Boolean:t=i!==null;break;case Number:t=i===null?null:Number(i);break;case Object:case Array:try{t=JSON.parse(i)}catch{t=null}}return t}},Ve=(i,e)=>!En(i,e),Pe={attribute:!0,type:String,converter:he,reflect:!1,useDefault:!1,hasChanged:Ve};Symbol.metadata??=Symbol("metadata"),Qt.litPropertyMetadata??=new WeakMap;var F=class extends HTMLElement{static addInitializer(e){this._$Ei(),(this.l??=[]).push(e)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(e,t=Pe){if(t.state&&(t.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(e)&&((t=Object.create(t)).wrapped=!0),this.elementProperties.set(e,t),!t.noAccessor){let n=Symbol(),s=this.getPropertyDescriptor(e,n,t);s!==void 0&&Tn(this.prototype,e,s)}}static getPropertyDescriptor(e,t,n){let{get:s,set:a}=Rn(this.prototype,e)??{get(){return this[t]},set(r){this[t]=r}};return{get:s,set(r){let o=s?.call(this);a?.call(this,r),this.requestUpdate(e,o,n)},configurable:!0,enumerable:!0}}static getPropertyOptions(e){return this.elementProperties.get(e)??Pe}static _$Ei(){if(this.hasOwnProperty(yt("elementProperties")))return;let e=Nn(this);e.finalize(),e.l!==void 0&&(this.l=[...e.l]),this.elementProperties=new Map(e.elementProperties)}static finalize(){if(this.hasOwnProperty(yt("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(yt("properties"))){let t=this.properties,n=[...Hn(t),...Ln(t)];for(let s of n)this.createProperty(s,t[s])}let e=this[Symbol.metadata];if(e!==null){let t=litPropertyMetadata.get(e);if(t!==void 0)for(let[n,s]of t)this.elementProperties.set(n,s)}this._$Eh=new Map;for(let[t,n]of this.elementProperties){let s=this._$Eu(t,n);s!==void 0&&this._$Eh.set(s,t)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(e){let t=[];if(Array.isArray(e)){let n=new Set(e.flat(1/0).reverse());for(let s of n)t.unshift(pe(s))}else e!==void 0&&t.push(pe(e));return t}static _$Eu(e,t){let n=t.attribute;return n===!1?void 0:typeof n=="string"?n:typeof e=="string"?e.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(e=>this.enableUpdating=e),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(e=>e(this))}addController(e){(this._$EO??=new Set).add(e),this.renderRoot!==void 0&&this.isConnected&&e.hostConnected?.()}removeController(e){this._$EO?.delete(e)}_$E_(){let e=new Map,t=this.constructor.elementProperties;for(let n of t.keys())this.hasOwnProperty(n)&&(e.set(n,this[n]),delete this[n]);e.size>0&&(this._$Ep=e)}createRenderRoot(){let e=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return Ne(e,this.constructor.elementStyles),e}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(e=>e.hostConnected?.())}enableUpdating(e){}disconnectedCallback(){this._$EO?.forEach(e=>e.hostDisconnected?.())}attributeChangedCallback(e,t,n){this._$AK(e,n)}_$ET(e,t){let n=this.constructor.elementProperties.get(e),s=this.constructor._$Eu(e,n);if(s!==void 0&&n.reflect===!0){let a=(n.converter?.toAttribute!==void 0?n.converter:he).toAttribute(t,n.type);this._$Em=e,a==null?this.removeAttribute(s):this.setAttribute(s,a),this._$Em=null}}_$AK(e,t){let n=this.constructor,s=n._$Eh.get(e);if(s!==void 0&&this._$Em!==s){let a=n.getPropertyOptions(s),r=typeof a.converter=="function"?{fromAttribute:a.converter}:a.converter?.fromAttribute!==void 0?a.converter:he;this._$Em=s;let o=r.fromAttribute(t,a.type);this[s]=o??this._$Ej?.get(s)??o,this._$Em=null}}requestUpdate(e,t,n,s=!1,a){if(e!==void 0){let r=this.constructor;if(s===!1&&(a=this[e]),n??=r.getPropertyOptions(e),!((n.hasChanged??Ve)(a,t)||n.useDefault&&n.reflect&&a===this._$Ej?.get(e)&&!this.hasAttribute(r._$Eu(e,n))))return;this.C(e,t,n)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(e,t,{useDefault:n,reflect:s,wrapped:a},r){n&&!(this._$Ej??=new Map).has(e)&&(this._$Ej.set(e,r??t??this[e]),a!==!0||r!==void 0)||(this._$AL.has(e)||(this.hasUpdated||n||(t=void 0),this._$AL.set(e,t)),s===!0&&this._$Em!==e&&(this._$Eq??=new Set).add(e))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(t){Promise.reject(t)}let e=this.scheduleUpdate();return e!=null&&await e,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(let[s,a]of this._$Ep)this[s]=a;this._$Ep=void 0}let n=this.constructor.elementProperties;if(n.size>0)for(let[s,a]of n){let{wrapped:r}=a,o=this[s];r!==!0||this._$AL.has(s)||o===void 0||this.C(s,void 0,a,o)}}let e=!1,t=this._$AL;try{e=this.shouldUpdate(t),e?(this.willUpdate(t),this._$EO?.forEach(n=>n.hostUpdate?.()),this.update(t)):this._$EM()}catch(n){throw e=!1,this._$EM(),n}e&&this._$AE(t)}willUpdate(e){}_$AE(e){this._$EO?.forEach(t=>t.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(e)),this.updated(e)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(e){return!0}update(e){this._$Eq&&=this._$Eq.forEach(t=>this._$ET(t,this[t])),this._$EM()}updated(e){}firstUpdated(e){}};F.elementStyles=[],F.shadowRootOptions={mode:"open"},F[yt("elementProperties")]=new Map,F[yt("finalized")]=new Map,Pn?.({ReactiveElement:F}),(Qt.reactiveElementVersions??=[]).push("2.1.2");var $e=globalThis,De=i=>i,Zt=$e.trustedTypes,Ue=Zt?Zt.createPolicy("lit-html",{createHTML:i=>i}):void 0,je="$lit$",q=`lit$${Math.random().toFixed(9).slice(2)}$`,We="?"+q,Vn=`<${We}>`,Q=document,kt=()=>Q.createComment(""),_t=i=>i===null||typeof i!="object"&&typeof i!="function",we=Array.isArray,Dn=i=>we(i)||typeof i?.[Symbol.iterator]=="function",ue=`[ 	
\f\r]`,xt=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,Be=/-->/g,Fe=/>/g,G=RegExp(`>|${ue}(?:([^\\s"'>=/]+)(${ue}*=${ue}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),ze=/'/g,qe=/"/g,Ke=/^(?:script|style|textarea|title)$/i,ye=i=>(e,...t)=>({_$litType$:i,strings:e,values:t}),d=ye(1),g=ye(2),bs=ye(3),Z=Symbol.for("lit-noChange"),p=Symbol.for("lit-nothing"),Ie=new WeakMap,Y=Q.createTreeWalker(Q,129);function Ge(i,e){if(!we(i)||!i.hasOwnProperty("raw"))throw Error("invalid template strings array");return Ue!==void 0?Ue.createHTML(e):e}var Un=(i,e)=>{let t=i.length-1,n=[],s,a=e===2?"<svg>":e===3?"<math>":"",r=xt;for(let o=0;o<t;o++){let l=i[o],h,u,c=-1,m=0;for(;m<l.length&&(r.lastIndex=m,u=r.exec(l),u!==null);)m=r.lastIndex,r===xt?u[1]==="!--"?r=Be:u[1]!==void 0?r=Fe:u[2]!==void 0?(Ke.test(u[2])&&(s=RegExp("</"+u[2],"g")),r=G):u[3]!==void 0&&(r=G):r===G?u[0]===">"?(r=s??xt,c=-1):u[1]===void 0?c=-2:(c=r.lastIndex-u[2].length,h=u[1],r=u[3]===void 0?G:u[3]==='"'?qe:ze):r===qe||r===ze?r=G:r===Be||r===Fe?r=xt:(r=G,s=void 0);let f=r===G&&i[o+1].startsWith("/>")?" ":"";a+=r===xt?l+Vn:c>=0?(n.push(h),l.slice(0,c)+je+l.slice(c)+q+f):l+q+(c===-2?o:f)}return[Ge(i,a+(i[t]||"<?>")+(e===2?"</svg>":e===3?"</math>":"")),n]},Mt=class i{constructor({strings:e,_$litType$:t},n){let s;this.parts=[];let a=0,r=0,o=e.length-1,l=this.parts,[h,u]=Un(e,t);if(this.el=i.createElement(h,n),Y.currentNode=this.el.content,t===2||t===3){let c=this.el.content.firstChild;c.replaceWith(...c.childNodes)}for(;(s=Y.nextNode())!==null&&l.length<o;){if(s.nodeType===1){if(s.hasAttributes())for(let c of s.getAttributeNames())if(c.endsWith(je)){let m=u[r++],f=s.getAttribute(c).split(q),v=/([.?@])?(.*)/.exec(m);l.push({type:1,index:a,name:v[2],strings:f,ctor:v[1]==="."?me:v[1]==="?"?fe:v[1]==="@"?be:ct}),s.removeAttribute(c)}else c.startsWith(q)&&(l.push({type:6,index:a}),s.removeAttribute(c));if(Ke.test(s.tagName)){let c=s.textContent.split(q),m=c.length-1;if(m>0){s.textContent=Zt?Zt.emptyScript:"";for(let f=0;f<m;f++)s.append(c[f],kt()),Y.nextNode(),l.push({type:2,index:++a});s.append(c[m],kt())}}}else if(s.nodeType===8)if(s.data===We)l.push({type:2,index:a});else{let c=-1;for(;(c=s.data.indexOf(q,c+1))!==-1;)l.push({type:7,index:a}),c+=q.length-1}a++}}static createElement(e,t){let n=Q.createElement("template");return n.innerHTML=e,n}};function dt(i,e,t=i,n){if(e===Z)return e;let s=n!==void 0?t._$Co?.[n]:t._$Cl,a=_t(e)?void 0:e._$litDirective$;return s?.constructor!==a&&(s?._$AO?.(!1),a===void 0?s=void 0:(s=new a(i),s._$AT(i,t,n)),n!==void 0?(t._$Co??=[])[n]=s:t._$Cl=s),s!==void 0&&(e=dt(i,s._$AS(i,e.values),s,n)),e}var ge=class{constructor(e,t){this._$AV=[],this._$AN=void 0,this._$AD=e,this._$AM=t}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(e){let{el:{content:t},parts:n}=this._$AD,s=(e?.creationScope??Q).importNode(t,!0);Y.currentNode=s;let a=Y.nextNode(),r=0,o=0,l=n[0];for(;l!==void 0;){if(r===l.index){let h;l.type===2?h=new St(a,a.nextSibling,this,e):l.type===1?h=new l.ctor(a,l.name,l.strings,this,e):l.type===6&&(h=new ve(a,this,e)),this._$AV.push(h),l=n[++o]}r!==l?.index&&(a=Y.nextNode(),r++)}return Y.currentNode=Q,s}p(e){let t=0;for(let n of this._$AV)n!==void 0&&(n.strings!==void 0?(n._$AI(e,n,t),t+=n.strings.length-2):n._$AI(e[t])),t++}},St=class i{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(e,t,n,s){this.type=2,this._$AH=p,this._$AN=void 0,this._$AA=e,this._$AB=t,this._$AM=n,this.options=s,this._$Cv=s?.isConnected??!0}get parentNode(){let e=this._$AA.parentNode,t=this._$AM;return t!==void 0&&e?.nodeType===11&&(e=t.parentNode),e}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(e,t=this){e=dt(this,e,t),_t(e)?e===p||e==null||e===""?(this._$AH!==p&&this._$AR(),this._$AH=p):e!==this._$AH&&e!==Z&&this._(e):e._$litType$!==void 0?this.$(e):e.nodeType!==void 0?this.T(e):Dn(e)?this.k(e):this._(e)}O(e){return this._$AA.parentNode.insertBefore(e,this._$AB)}T(e){this._$AH!==e&&(this._$AR(),this._$AH=this.O(e))}_(e){this._$AH!==p&&_t(this._$AH)?this._$AA.nextSibling.data=e:this.T(Q.createTextNode(e)),this._$AH=e}$(e){let{values:t,_$litType$:n}=e,s=typeof n=="number"?this._$AC(e):(n.el===void 0&&(n.el=Mt.createElement(Ge(n.h,n.h[0]),this.options)),n);if(this._$AH?._$AD===s)this._$AH.p(t);else{let a=new ge(s,this),r=a.u(this.options);a.p(t),this.T(r),this._$AH=a}}_$AC(e){let t=Ie.get(e.strings);return t===void 0&&Ie.set(e.strings,t=new Mt(e)),t}k(e){we(this._$AH)||(this._$AH=[],this._$AR());let t=this._$AH,n,s=0;for(let a of e)s===t.length?t.push(n=new i(this.O(kt()),this.O(kt()),this,this.options)):n=t[s],n._$AI(a),s++;s<t.length&&(this._$AR(n&&n._$AB.nextSibling,s),t.length=s)}_$AR(e=this._$AA.nextSibling,t){for(this._$AP?.(!1,!0,t);e!==this._$AB;){let n=De(e).nextSibling;De(e).remove(),e=n}}setConnected(e){this._$AM===void 0&&(this._$Cv=e,this._$AP?.(e))}},ct=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(e,t,n,s,a){this.type=1,this._$AH=p,this._$AN=void 0,this.element=e,this.name=t,this._$AM=s,this.options=a,n.length>2||n[0]!==""||n[1]!==""?(this._$AH=Array(n.length-1).fill(new String),this.strings=n):this._$AH=p}_$AI(e,t=this,n,s){let a=this.strings,r=!1;if(a===void 0)e=dt(this,e,t,0),r=!_t(e)||e!==this._$AH&&e!==Z,r&&(this._$AH=e);else{let o=e,l,h;for(e=a[0],l=0;l<a.length-1;l++)h=dt(this,o[n+l],t,l),h===Z&&(h=this._$AH[l]),r||=!_t(h)||h!==this._$AH[l],h===p?e=p:e!==p&&(e+=(h??"")+a[l+1]),this._$AH[l]=h}r&&!s&&this.j(e)}j(e){e===p?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,e??"")}},me=class extends ct{constructor(){super(...arguments),this.type=3}j(e){this.element[this.name]=e===p?void 0:e}},fe=class extends ct{constructor(){super(...arguments),this.type=4}j(e){this.element.toggleAttribute(this.name,!!e&&e!==p)}},be=class extends ct{constructor(e,t,n,s,a){super(e,t,n,s,a),this.type=5}_$AI(e,t=this){if((e=dt(this,e,t,0)??p)===Z)return;let n=this._$AH,s=e===p&&n!==p||e.capture!==n.capture||e.once!==n.once||e.passive!==n.passive,a=e!==p&&(n===p||s);s&&this.element.removeEventListener(this.name,this,n),a&&this.element.addEventListener(this.name,this,e),this._$AH=e}handleEvent(e){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,e):this._$AH.handleEvent(e)}},ve=class{constructor(e,t,n){this.element=e,this.type=6,this._$AN=void 0,this._$AM=t,this.options=n}get _$AU(){return this._$AM._$AU}_$AI(e){dt(this,e)}};var Bn=$e.litHtmlPolyfillSupport;Bn?.(Mt,St),($e.litHtmlVersions??=[]).push("3.3.3");var Ye=(i,e,t)=>{let n=t?.renderBefore??e,s=n._$litPart$;if(s===void 0){let a=t?.renderBefore??null;n._$litPart$=s=new St(e.insertBefore(kt(),a),a,void 0,t??{})}return s._$AI(i),s};var xe=globalThis,E=class extends F{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){let e=super.createRenderRoot();return this.renderOptions.renderBefore??=e.firstChild,e}update(e){let t=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(e),this._$Do=Ye(t,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return Z}};E._$litElement$=!0,E.finalized=!0,xe.litElementHydrateSupport?.({LitElement:E});var Fn=xe.litElementPolyfillSupport;Fn?.({LitElement:E});(xe.litElementVersions??=[]).push("4.2.2");var Qe={car:g`<path d="M4 13V9.5L5.6 5.4A1.5 1.5 0 0 1 7 4.5h6a1.5 1.5 0 0 1 1.4.9L16 9.5V13"/><path d="M3 13h14v2.5H3zM4 9.5h12"/><path d="M5 15.5V17M15 15.5V17"/>`,climate:g`<path d="M10 2.5v15M3.5 6.2l13 7.6M3.5 13.8l13-7.6"/><path d="M8 3.8L10 5.5 12 3.8M8 16.2L10 14.5 12 16.2"/>`,plug:g`<path d="M7 2.5v4M13 2.5v4"/><path d="M5 6.5h10v3a5 5 0 0 1-10 0z"/><path d="M10 14.5v3"/>`,pin:g`<path d="M10 17.5s5.5-5 5.5-9.5a5.5 5.5 0 0 0-11 0c0 4.5 5.5 9.5 5.5 9.5z"/><circle cx="10" cy="8" r="2"/>`,activity:g`<path d="M6 3v14"/><circle cx="6" cy="5" r="1.6"/><circle cx="6" cy="10" r="1.6"/><circle cx="6" cy="15" r="1.6"/><path d="M10 5h7M10 10h5M10 15h6"/>`,settings:g`<path d="M3 5.5h8M15 5.5h2M3 14.5h2M9 14.5h8"/><circle cx="13" cy="5.5" r="2"/><circle cx="7" cy="14.5" r="2"/>`,lock:g`<rect x="4" y="9" width="12" height="8.5" rx="1"/><path d="M6.5 9V6.5a3.5 3.5 0 0 1 7 0V9"/>`,unlock:g`<rect x="4" y="9" width="12" height="8.5" rx="1"/><path d="M6.5 9V6.5a3.5 3.5 0 0 1 6.8-1.2"/>`,ac:g`<path d="M10 3v14M4 6.5l12 7M4 13.5l12-7"/>`,vent:g`<path d="M3 15V8l4-4h10v11z"/><path d="M10 7.5v4.5M8 10l2 2 2-2"/>`,boot:g`<path d="M3 16V9.5L5.5 5h9L17 9.5V16z"/><path d="M3 11.5h14M8 14h4"/>`,horn:g`<path d="M3 8v4h3l6 4V4L6 8z"/><path d="M15 7a4 4 0 0 1 0 6"/>`,lights:g`<path d="M10 4.5C6.5 4.5 4 7 4 10s2.5 5.5 6 5.5z"/><path d="M13 6.5h4M13 10h4M13 13.5h4"/>`,windows:g`<path d="M3.5 16.5V9L8 4h8.5v12.5z"/><path d="M3.5 10.5h13"/>`,sunroof:g`<rect x="3.5" y="3.5" width="13" height="13" rx="1"/><rect x="6.5" y="6.5" width="7" height="5"/>`,refresh:g`<path d="M16 10a6 6 0 1 1-1.8-4.3"/><path d="M16.5 3.5v3.5H13"/>`,power:g`<path d="M10 3v7"/><path d="M6.2 5.8a6 6 0 1 0 7.6 0"/>`,bolt:g`<path d="M11 2.5L5 11h5l-1 6.5L15 9h-5z"/>`,seat:g`<path d="M7 3.5h3l1 8H7.5z"/><path d="M6.5 11.5h7l1.5 3.5H8z"/><path d="M8 15v2.5M14 15v2.5"/>`,wheel:g`<circle cx="10" cy="10" r="6.5"/><circle cx="10" cy="10" r="1.5"/><path d="M4 9.5h4.5M11.5 9.5H16M10 11.5v5"/>`,fridge:g`<rect x="5" y="2.5" width="10" height="15" rx="1"/><path d="M5 8h10M7.5 4.5v2M7.5 10v3"/>`,battery:g`<rect x="2.5" y="6" width="13" height="8" rx="1"/><path d="M17.5 8.5v3"/><path d="M5 8.5h4v3H5z"/>`,recirculate:g`<path d="M15 8a5 5 0 0 0-9.3-1.5M5 12a5 5 0 0 0 9.3 1.5"/><path d="M5 3.5v3.3h3.3M15 16.5v-3.3h-3.3"/>`,sterilise:g`<circle cx="10" cy="10" r="3"/><path d="M10 3v2M10 15v2M3 10h2M15 10h2M5 5l1.4 1.4M13.6 13.6L15 15M5 15l1.4-1.4M13.6 6.4L15 5"/>`,minus:g`<path d="M5 10h10"/>`,plus:g`<path d="M5 10h10M10 5v10"/>`,check:g`<path d="M4.5 10.5l3.5 3.5 7.5-8"/>`,map:g`<path d="M3 5.5l4.5-2 5 2 4.5-2v11l-4.5 2-5-2-4.5 2z"/><path d="M7.5 3.5v11M12.5 5.5v11"/>`,chevron:g`<path d="M7.5 5l5 5-5 5"/>`,connector:g`<circle cx="10" cy="10" r="6.5"/><circle cx="7.5" cy="8.5" r="1"/><circle cx="12.5" cy="8.5" r="1"/><circle cx="10" cy="12.5" r="1"/>`};function P(i){return d`<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5"
    stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${Qe[i]??Qe.car}</svg>`}function y(i){let e={ok:g`<rect x="1" y="1" width="10" height="10" fill="var(--gac-green)" stroke="var(--gac-green-case)"/>`,warn:g`<path d="M6 1L11.2 10.6H.8z" fill="var(--gac-yellow)" stroke="var(--gac-ink)" stroke-linejoin="round"/>`,fault:g`<path d="M6 1L11.2 10.6H.8z" fill="var(--gac-red)" stroke="var(--gac-ink)" stroke-linejoin="round"/>`,wait:g`<circle cx="6" cy="6" r="4.5" fill="none" stroke="var(--gac-mw)" stroke-width="1.5" stroke-dasharray="2.4 1.6"/>`,off:g`<rect x="1.5" y="1.5" width="9" height="9" fill="none" stroke="var(--gac-muted)"/>`,info:g`<circle cx="6" cy="6" r="4.25" fill="none" stroke="var(--gac-ink)" stroke-width="1.5"/>`,lamp:g`<path d="M6 1L11.2 10.6H.8z" fill="var(--gac-lamp-high)" stroke="var(--gac-ink)" stroke-linejoin="round"/>`};return d`<svg class="mark" viewBox="0 0 12 12" aria-hidden="true">${e[i]}</svg>`}var Xt=700,X=k`
  *,
  *::before,
  *::after {
    box-sizing: border-box;
  }
  :focus-visible {
    outline: 2px solid var(--gac-mw);
    outline-offset: 2px;
  }
`,Jt=k`
  .pending {
    position: relative;
    border-color: transparent !important;
    background: var(--gac-water) !important;
    color: var(--gac-mw-case) !important;
  }
  .pending::before {
    content: "";
    position: absolute;
    inset: -1px;
    border-radius: inherit;
    pointer-events: none;
    background:
      linear-gradient(90deg, var(--gac-mw-case) 50%, transparent 0) repeat-x top left / 8px 1.5px,
      linear-gradient(90deg, var(--gac-mw-case) 50%, transparent 0) repeat-x bottom left / 8px 1.5px,
      linear-gradient(0deg, var(--gac-mw-case) 50%, transparent 0) repeat-y top left / 1.5px 8px,
      linear-gradient(0deg, var(--gac-mw-case) 50%, transparent 0) repeat-y top right / 1.5px 8px;
    animation: march 0.8s linear infinite;
  }
  @keyframes march {
    to {
      background-position: 8px 0, -8px 100%, 0 -8px, 100% 8px;
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .pending::before {
      animation: none;
    }
  }
`,At=class extends E{constructor(){super(),this.state="idle",this.hold=!1,this._holding=!1,this._asked=!1}start(e){this.state==="unavailable"||this.state==="pending"||this.hold&&(e.preventDefault(),this._holding=!0,window.clearTimeout(this.timer),this.timer=window.setTimeout(()=>{this._holding=!1,navigator.vibrate?.(15),this.activate()},Xt))}cancel(){this._holding&&(this._holding=!1,window.clearTimeout(this.timer),this._asked=!0,window.clearTimeout(this.askTimer),this.askTimer=window.setTimeout(()=>this._asked=!1,1800))}onClick(){this.hold||this.state==="unavailable"||this.state==="pending"||this.activate()}key(e){!this.hold||e.key!=="Enter"&&e.key!==" "||(e.preventDefault(),e.type==="keydown"&&!e.repeat&&this.start(e),e.type==="keyup"&&this.cancel())}activate(){this.dispatchEvent(new CustomEvent("activate",{bubbles:!0,composed:!0}))}disconnectedCallback(){super.disconnectedCallback(),window.clearTimeout(this.timer),window.clearTimeout(this.askTimer)}render(){let e=[this.state,this.hold?"hold":"",this._holding?"holding":""].join(" "),t=this._asked?"Hold to confirm":this.label;return d`<button class=${e} aria-busy=${this.state==="pending"?"true":"false"}
      aria-disabled=${this.state==="unavailable"||this.state==="pending"?"true":"false"}
      aria-pressed=${this.state==="on"?"true":p}
      aria-description=${this.hint||(this.hold?"Press and hold to confirm":p)}
      title=${this.hint||p}
      @click=${this.onClick} @pointerdown=${this.start} @pointerup=${this.cancel} @pointerleave=${this.cancel}
      @pointercancel=${this.cancel} @keydown=${this.key} @keyup=${this.key} @contextmenu=${n=>this.hold&&n.preventDefault()}>
      ${this.icon?P(this.icon):p}<span>${t}</span><i class="bar"></i>
    </button>`}};At.properties={label:{},icon:{},state:{reflect:!0},hold:{type:Boolean},hint:{},_holding:{state:!0},_asked:{state:!0}},At.styles=[X,Jt,k`
    :host {
      display: block;
    }
    button {
      position: relative;
      width: 100%;
      height: 48px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 0 8px;
      font: 600 16px/1 var(--gac-label);
      letter-spacing: 0.02em;
      color: var(--gac-ink);
      background: var(--gac-paper);
      border: 1px solid var(--gac-edge);
      border-radius: 2px;
      cursor: pointer;
      overflow: hidden;
      transition: background-color 150ms ease-out, color 150ms ease-out, border-color 150ms ease-out;
      -webkit-tap-highlight-color: transparent;
      touch-action: manipulation;
      user-select: none;
    }
    button:hover {
      background: color-mix(in srgb, var(--gac-paper) 88%, var(--gac-ink));
    }
    button:active {
      background: color-mix(in srgb, var(--gac-paper) 80%, var(--gac-ink));
    }
    svg {
      width: 20px;
      height: 20px;
      flex: none;
    }
    span {
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .on {
      background: var(--gac-mw);
      color: var(--gac-mw-ink);
      border-color: var(--gac-mw-case);
    }
    .on:hover {
      background: color-mix(in srgb, var(--gac-mw) 88%, black);
    }
    .refused {
      border-color: var(--gac-red);
      color: var(--gac-red-ink);
      box-shadow: inset 0 0 0 1px var(--gac-red);
    }
    .unavailable {
      color: var(--gac-muted);
      border-style: dotted;
      cursor: not-allowed;
    }
    .unavailable:hover {
      background: var(--gac-paper);
    }
    .hold::after {
      content: "";
      position: absolute;
      left: 6px;
      right: 6px;
      bottom: 5px;
      height: 0;
      border-bottom: 1.5px dashed var(--gac-edge);
    }
    .bar {
      position: absolute;
      left: 0;
      bottom: 0;
      height: 5px;
      width: 0;
      background: var(--gac-mw);
      box-shadow: 0 -1px 0 var(--gac-mw-case);
      transition: width 120ms ease-out;
    }
    .holding .bar {
      width: 100%;
      transition: width ${Xt}ms linear;
    }
  `];var Ct=class extends E{constructor(){super(),this.checked=!1,this.pending=!1,this.disabled=!1,this.holdOn=!1,this._holding=!1}needsHold(){return this.holdOn&&!this.checked}down(e){!this.needsHold()||this.disabled||this.pending||(e.preventDefault(),this._holding=!0,this.timer=window.setTimeout(()=>{this._holding=!1,this.toggle()},Xt))}up(){this._holding=!1,window.clearTimeout(this.timer)}onClick(){this.needsHold()||this.disabled||this.pending||this.toggle()}key(e){!this.needsHold()||e.key!=="Enter"&&e.key!==" "||(e.preventDefault(),e.type==="keydown"&&!e.repeat&&this.down(e),e.type==="keyup"&&this.up())}toggle(){this.dispatchEvent(new CustomEvent("change",{detail:{checked:!this.checked},bubbles:!0,composed:!0}))}render(){let e=[this.checked?"on":"",this.pending?"pending":"",this._holding?"holding":""];return d`<button role="switch" aria-checked=${this.checked?"true":"false"} aria-label=${this.label}
      aria-disabled=${this.disabled||this.pending?"true":"false"} aria-busy=${this.pending?"true":"false"}
      aria-description=${this.needsHold()?"Press and hold to turn on":p}
      class=${e.join(" ")} @click=${this.onClick} @pointerdown=${this.down} @pointerup=${this.up}
      @pointerleave=${this.up} @pointercancel=${this.up} @keydown=${this.key} @keyup=${this.key}>
      <span class="track"><i class="fill"></i><i class="knob"></i></span>
    </button>`}};Ct.properties={checked:{type:Boolean},pending:{type:Boolean},disabled:{type:Boolean},label:{},holdOn:{type:Boolean,attribute:"hold-on"},_holding:{state:!0}},Ct.styles=[X,k`
    :host {
      display: inline-block;
      flex: none;
    }
    button {
      width: 60px;
      height: 48px;
      padding: 0;
      background: none;
      border: 0;
      cursor: pointer;
      display: grid;
      place-items: center;
      -webkit-tap-highlight-color: transparent;
      touch-action: manipulation;
    }
    button[aria-disabled="true"] {
      cursor: not-allowed;
      opacity: 0.5;
    }
    .track {
      position: relative;
      display: block;
      /* The original 20 px thumb on a 16 px track, with the track drawn 5 px shorter at each end
         than the thumb's travel, so the thumb covers its square corners at either end. */
      width: 38px;
      height: 16px;
      border-radius: 1px;
      background: var(--gac-minor);
      box-shadow: 0 0 0 1px var(--gac-minor-case), inset 0 0 0 1px var(--gac-minor-case);
      transition: background-color 180ms ease-out, box-shadow 180ms ease-out;
    }
    .on .track {
      background: var(--gac-mw);
      box-shadow: 0 0 0 1px var(--gac-mw-case);
    }
    .knob {
      position: absolute;
      top: 50%;
      left: 0;
      width: 20px;
      height: 20px;
      border-radius: 50%;
      background: var(--gac-minor);
      border: 1.5px solid var(--gac-ink);
      transform: translate(-7px, -50%);
      transition: transform 180ms cubic-bezier(0.2, 0.8, 0.2, 1);
    }
    .on .knob {
      transform: translate(25px, -50%);
    }
    .pending .track {
      background: var(--gac-water);
      box-shadow: none;
      outline: 1.5px dashed var(--gac-mw-case);
      outline-offset: 1px;
    }
    .fill {
      position: absolute;
      inset: 0;
      width: 0;
      background: var(--gac-mw);
      opacity: 0.5;
    }
    .holding .fill {
      width: 100%;
      transition: width ${Xt}ms linear;
    }
    @media (prefers-reduced-motion: reduce) {
      .knob,
      .track {
        transition: none;
      }
    }
  `];var Et=class extends E{constructor(){super(),this.options=[],this.pending=!1,this.disabled=!1}pick(e){this.disabled||this.pending||e===this.value||this.dispatchEvent(new CustomEvent("change",{detail:{value:e},bubbles:!0,composed:!0}))}key(e){let t=this.options.findIndex(a=>a.value===this.value),n=e.key==="ArrowRight"?1:e.key==="ArrowLeft"?-1:0;if(!n)return;e.preventDefault();let s=this.options[(t+n+this.options.length)%this.options.length];s&&this.pick(s.value)}render(){return d`<div role="radiogroup" aria-label=${this.label} aria-disabled=${this.disabled?"true":"false"}
      aria-busy=${this.pending?"true":"false"} class=${this.pending?"pending":""} @keydown=${this.key}>
      ${this.options.map(e=>d`<button role="radio" aria-checked=${e.value===this.value?"true":"false"}
        tabindex=${e.value===this.value||this.value===void 0&&e===this.options[0]?0:-1}
        @click=${()=>this.pick(e.value)}>${e.label}</button>`)}
    </div>`}};Et.properties={options:{attribute:!1},value:{},pending:{type:Boolean},disabled:{type:Boolean},label:{}},Et.styles=[X,Jt,k`
    :host {
      display: block;
    }
    div {
      display: flex;
      border: 1px solid var(--gac-edge);
      border-radius: 2px;
      background: var(--gac-paper);
    }
    button {
      flex: 1 1 0;
      min-width: 0;
      height: 44px;
      padding: 0 4px;
      font: 600 15px/1 var(--gac-label);
      letter-spacing: 0.03em;
      color: var(--gac-ink);
      background: none;
      border: 0;
      cursor: pointer;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      -webkit-tap-highlight-color: transparent;
    }
    button + button {
      border-left: 1px solid var(--gac-hair);
    }
    button:hover {
      background: color-mix(in srgb, var(--gac-paper) 88%, var(--gac-ink));
    }
    button[aria-checked="true"] {
      background: var(--gac-mw);
      color: var(--gac-mw-ink);
      box-shadow: inset 0 0 0 1px var(--gac-mw-case);
    }
    div[aria-disabled="true"] button {
      cursor: not-allowed;
      color: var(--gac-muted);
    }
  `];var Tt=class extends E{constructor(){super(),this.min=0,this.max=100,this.step=1,this.unit="",this.digits=0,this.pending=!1,this.disabled=!1}willUpdate(e){e.has("value")&&this._draft!==void 0&&this.value===this._draft&&(this._draft=void 0)}nudge(e){let t=this._draft??this.value??this.min,n=Math.min(this.max,Math.max(this.min,Math.round((t+e*this.step)/this.step)*this.step));n!==t&&(this._draft=n,window.clearTimeout(this.timer),this.timer=window.setTimeout(()=>{this.dispatchEvent(new CustomEvent("change",{detail:{value:n},bubbles:!0,composed:!0}))},1200))}disconnectedCallback(){super.disconnectedCallback(),window.clearTimeout(this.timer)}render(){let e=this._draft??this.value,t=e===void 0?"\u2013":this.format?this.format(e):e.toFixed(this.digits),n=this.disabled||this.pending;return d`<div class="box ${this.pending?"pending":""} ${this._draft!==void 0?"draft":""}"
      role="group" aria-label=${this.label}>
      <button aria-label="Decrease ${this.label}" ?disabled=${n||(e??this.min)<=this.min}
        @click=${()=>this.nudge(-1)}>${P("minus")}</button>
      <output aria-live="polite"><span>${t}${this.unit?d`<small>&nbsp;${this.unit}</small>`:p}</span></output>
      <button aria-label="Increase ${this.label}" ?disabled=${n||(e??this.max)>=this.max}
        @click=${()=>this.nudge(1)}>${P("plus")}</button>
    </div>`}};Tt.properties={value:{type:Number},min:{type:Number},max:{type:Number},step:{type:Number},unit:{},digits:{type:Number},label:{},pending:{type:Boolean},disabled:{type:Boolean},format:{attribute:!1},_draft:{state:!0}},Tt.styles=[X,Jt,k`
    :host {
      display: block;
    }
    .box {
      display: flex;
      align-items: stretch;
      height: 48px;
      border: 1px solid var(--gac-edge);
      border-radius: 2px;
      background: var(--gac-paper);
    }
    button {
      width: 48px;
      flex: none;
      display: grid;
      place-items: center;
      background: none;
      border: 0;
      color: var(--gac-ink);
      cursor: pointer;
      -webkit-tap-highlight-color: transparent;
      touch-action: manipulation;
    }
    button:hover:not(:disabled) {
      background: color-mix(in srgb, var(--gac-paper) 88%, var(--gac-ink));
    }
    button:disabled {
      color: var(--gac-muted);
      cursor: not-allowed;
      opacity: 0.5;
    }
    svg {
      width: 20px;
      height: 20px;
    }
    output {
      flex: 1;
      min-width: 0;
      display: grid;
      place-items: center;
      border-left: 1px solid var(--gac-hair);
      border-right: 1px solid var(--gac-hair);
      font: 600 22px/1 var(--gac-label);
      font-variant-numeric: tabular-nums;
      white-space: nowrap;
    }
    output small {
      font-size: 15px;
      font-weight: 500;
      color: var(--gac-muted);
    }
    .draft output {
      color: var(--gac-mw-case);
    }
  `];var Rt=class extends E{constructor(){super(),this.options=[],this.pending=!1}pick(e){this.pending||e===this.value||this.dispatchEvent(new CustomEvent("change",{detail:{value:e},bubbles:!0,composed:!0}))}stopAt(e){let t=this.renderRoot.querySelector(".stops").getBoundingClientRect(),n=Math.max(1,this.options.length);return Math.min(n-1,Math.max(0,Math.floor((e-t.left)/t.width*n)))}down(e){this.pending||e.button>0||!this.options.length||(e.currentTarget.setPointerCapture(e.pointerId),this._draft=this.stopAt(e.clientX))}move(e){this._draft!==void 0&&(this._draft=this.stopAt(e.clientX))}up(e){if(this._draft===void 0)return;let t=e.type==="pointerup"?this.options[this._draft]:void 0;this._draft=void 0,t&&this.pick(t.value)}key(e){let t=this.options.findIndex(a=>a.value===this.value),n=e.key==="ArrowRight"||e.key==="ArrowUp"?1:e.key==="ArrowLeft"||e.key==="ArrowDown"?-1:0;if(!n)return;e.preventDefault();let s=this.options[Math.min(this.options.length-1,Math.max(0,t+n))];s&&(this.pick(s.value),this.renderRoot.querySelectorAll("button")[this.options.indexOf(s)]?.focus())}render(){let e=this._draft??this.options.findIndex(s=>s.value===this.value),t=Math.max(1,this.options.length),n=e<0?0:(e+.5)/t*100;return d`<div class="stops ${this.pending?"pending":""}" role="radiogroup" aria-label=${this.label}
      aria-busy=${this.pending?"true":"false"} @pointerdown=${this.down} @pointermove=${this.move}
      @pointerup=${this.up} @pointercancel=${this.up} @keydown=${this.key}>
      <i class="road"></i><i class="driven" style="width:${n}%"></i>
      ${this.options.map((s,a)=>d`<button role="radio" aria-checked=${a===e?"true":"false"}
        class=${a<e?"passed":""} tabindex=${a===e||e<0&&a===0?0:-1}
        aria-label=${s.label} @click=${r=>{r.detail===0&&this.pick(s.value)}}
        ><i></i><span>${s.label}</span></button>`)}
    </div>`}};Rt.properties={options:{attribute:!1},value:{},pending:{type:Boolean},label:{},_draft:{state:!0}},Rt.styles=[X,k`
    :host {
      display: block;
    }
    .stops {
      position: relative;
      display: flex;
      touch-action: pan-y;
      user-select: none;
      -webkit-user-select: none;
    }
    .road {
      position: absolute;
      left: 0;
      right: 0;
      top: 13px;
      height: 7px;
      background: var(--gac-minor);
      box-shadow: inset 0 0 0 1px var(--gac-minor-case);
    }
    .driven {
      position: absolute;
      left: 0;
      top: 10px;
      height: 13px;
      background: var(--gac-mw);
      box-shadow: inset 0 0 0 2px var(--gac-mw-case);
      transition: width 200ms ease-out;
    }
    .pending .driven {
      background: var(--gac-water);
      box-shadow: none;
      outline: 1.5px dashed var(--gac-mw-case);
    }
    button {
      position: relative;
      flex: 1 1 0;
      min-width: 0;
      height: 52px;
      padding: 0;
      background: none;
      border: 0;
      cursor: pointer;
      color: var(--gac-muted);
      font: 600 13px/1 var(--gac-label);
      letter-spacing: 0.06em;
      text-transform: uppercase;
      -webkit-tap-highlight-color: transparent;
    }
    button i {
      position: absolute;
      left: 50%;
      top: 9px;
      width: 15px;
      height: 15px;
      margin-left: -7.5px;
      border-radius: 50%;
      background: var(--gac-minor);
      border: 1.5px solid var(--gac-minor-case);
    }
    button.passed i {
      border-color: var(--gac-mw-case);
    }
    button[aria-checked="true"] {
      color: var(--gac-ink);
    }
    button[aria-checked="true"] i {
      width: 19px;
      height: 19px;
      top: 7px;
      margin-left: -9.5px;
      border: 2px solid var(--gac-ink);
    }
    button span {
      position: absolute;
      left: 0;
      right: 0;
      bottom: 4px;
      white-space: nowrap;
      overflow: hidden;
    }
  `];var L=1440;function zn(i,e=!1){let t=(Math.round(i)%L+L)%L,n=Math.floor(t/60),s=String(t%60).padStart(2,"0");return e?`${n%12||12}:${s} ${n<12?"AM":"PM"}`:`${String(n).padStart(2,"0")}:${s}`}function qn(i,e){let t=i/60;return e?`${t%12||12}${t%24<12?"a":"p"}`:String(t).padStart(2,"0")}var Ht=class extends E{constructor(){super(),this.openEnded=!1,this.pending=!1,this.disabled=!1,this.step=5,this.startLabel="Start",this.stopLabel="Stop",this.twelve=!1,this._width=300}connectedCallback(){super.connectedCallback(),this.resizer=new ResizeObserver(e=>{let t=Math.round(e[0]?.contentRect.width??0);t>0&&(this._width=t)}),this.resizer.observe(this)}disconnectedCallback(){super.disconnectedCallback(),this.resizer?.disconnect()}willUpdate(e){(e.has("start")||e.has("stop"))&&this._draft&&!this._drag&&(this._draft.start===void 0||this._draft.start===this.start)&&(this._draft.stop===void 0||this._draft.stop===this.stop)&&(this._draft=void 0)}get value(){return{start:this._draft?.start??this.start,stop:this._draft?.stop??this.stop}}geometry(){let t=Math.max(200,this._width)-12;return{x0:12,x1:t,at:n=>12+n/L*(t-12)}}minutesAt(e){let t=this.renderRoot.querySelector("svg");if(!t)return 0;let n=t.getBoundingClientRect(),{x0:s,x1:a}=this.geometry(),r=(e-n.left-s)/(a-s),o=Math.min(L-this.step,Math.max(0,r*L));return Math.round(o/this.step)*this.step}emit(e,t){let{start:n,stop:s}=this.value;this.dispatchEvent(new CustomEvent(e,{detail:{start:n,stop:s,which:t},bubbles:!0,composed:!0}))}set(e,t){this.value[e]!==t&&(this._draft={...this._draft,[e]:t},this.emit("input",e))}down(e){if(this.disabled||e.button>0)return;let t=e.target,n=this.minutesAt(e.clientX),s=t.closest("[data-end]")?.dataset.end;if(!s){let{start:a,stop:r}=this.value,o=l=>l===void 0?1/0:Math.min(Math.abs(l-n),L-Math.abs(l-n));s=this.openEnded||o(a)<=o(r)?"start":"stop"}this._drag=s,e.currentTarget.setPointerCapture(e.pointerId),this.set(s,n),e.preventDefault()}move(e){this._drag&&this.set(this._drag,this.minutesAt(e.clientX))}up(){if(!this._drag)return;let e=this._drag;this._drag=void 0,this.emit("change",e)}key(e,t){if(this.disabled)return;let n={ArrowRight:this.step,ArrowUp:this.step,ArrowLeft:-this.step,ArrowDown:-this.step,PageUp:60,PageDown:-60},s=this.value[e]??0,a;t.key in n&&(a=(s+n[t.key]+L)%L),t.key==="Home"&&(a=0),t.key==="End"&&(a=L-this.step),a!==void 0&&(t.preventDefault(),this.set(e,a),this.emit("change",e))}render(){let{x0:e,x1:t,at:n}=this.geometry(),s=Math.max(200,this._width),a=18,{start:r,stop:o}=this.value,l=[];if(r!==void 0&&(o!==void 0||this.openEnded)){let c=this.openEnded?L:o;r===c?l.push([0,L]):r<c?l.push([r,c]):l.push([r,L],[0,c])}let h=(c,m,f)=>m===void 0?p:g`<g class="handle ${this._drag===c?"active":""}" data-end=${c} tabindex=${this.disabled?-1:0}
          role="slider" aria-label=${f} aria-valuemin="0" aria-valuemax=${L-this.step}
          aria-valuenow=${m} aria-valuetext=${zn(m,this.twelve)} aria-disabled=${this.disabled?"true":"false"}
          @keydown=${v=>this.key(c,v)}>
          <circle cx=${n(m)} cy=${a} r="16" fill="transparent"/>
          <circle class="ring" cx=${n(m)} cy=${a} r="11"/>
          <circle cx=${n(m)} cy=${a} r="7" fill="var(--gac-minor)" stroke="var(--gac-ink)" stroke-width="2"/>
        </g>`,u=(c,m)=>this.pending?g`<path d="M${n(c)} ${a}H${n(m)}" stroke="var(--gac-mw-case)" stroke-width="12" stroke-dasharray="6 4"/>
          <path d="M${n(c)} ${a}H${n(m)}" stroke="var(--gac-mw)" stroke-width="8" opacity="0.55"/>`:g`<path d="M${n(c)} ${a}H${n(m)}" stroke="var(--gac-mw-case)" stroke-width="14"/>
          <path d="M${n(c)} ${a}H${n(m)}" stroke="var(--gac-mw)" stroke-width="10"/>`;return d`<svg class=${this._drag?"dragging":""} width=${s} height="56" viewBox="0 0 ${s} 56"
      @pointerdown=${this.down} @pointermove=${this.move} @pointerup=${this.up} @pointercancel=${this.up}>
      <path d="M${e} ${a}H${t}" stroke="var(--gac-minor-case)" stroke-width="7"/>
      <path d="M${e} ${a}H${t}" stroke="var(--gac-minor)" stroke-width="5"/>
      ${l.map(([c,m])=>u(c,m))}
      ${Array.from({length:9},(c,m)=>m*180).map(c=>g`<path d="M${n(c)} ${a+12}v${c%360===0?7:4}"
        stroke="var(--gac-ink)"/>`)}
      ${[0,360,720,1080,1440].map(c=>g`<text class="tick" x=${n(c)} y="52" text-anchor="middle">${qn(c,this.twelve)}</text>`)}
      ${this.now!==void 0?g`<path d="M${n(this.now)-4} 0L${n(this.now)+4} 0L${n(this.now)} 6Z"
        fill="var(--gac-ink)"/>`:p}
      ${h("start",r,this.startLabel)}
      ${this.openEnded?p:h("stop",o,this.stopLabel)}
    </svg>`}};Ht.properties={start:{type:Number},stop:{type:Number},openEnded:{type:Boolean,attribute:"open-ended"},pending:{type:Boolean},disabled:{type:Boolean,reflect:!0},now:{type:Number},step:{type:Number},startLabel:{attribute:"start-label"},stopLabel:{attribute:"stop-label"},twelve:{type:Boolean},_width:{state:!0},_drag:{state:!0},_draft:{state:!0}},Ht.styles=[X,k`
    :host {
      display: block;
      user-select: none;
      -webkit-user-select: none;
    }
    svg {
      display: block;
      overflow: visible;
      touch-action: pan-y;
      cursor: pointer;
    }
    :host([disabled]) svg {
      cursor: not-allowed;
      opacity: 0.55;
    }
    .handle {
      cursor: grab;
      outline: none;
    }
    .dragging .handle {
      cursor: grabbing;
    }
    .handle .ring {
      fill: none;
      stroke: transparent;
      stroke-width: 3;
    }
    .handle:focus-visible .ring,
    .handle.active .ring {
      stroke: var(--gac-mw);
    }
    .tick {
      font: 600 12px var(--gac-label);
      fill: var(--gac-muted);
      letter-spacing: 0.06em;
    }
  `];var Lt=class extends E{constructor(){super(),this.options=[],this.pending=!1,this.disabled=!1,this._open=!1}pick(e){this._open=!1,e!==this.value&&this.dispatchEvent(new CustomEvent("change",{detail:{value:e},bubbles:!0,composed:!0})),this.renderRoot.querySelector(".current")?.focus()}key(e){let t=[...this.renderRoot.querySelectorAll("li button")],n=t.indexOf(e.target);e.key==="Escape"?(this._open=!1,this.renderRoot.querySelector(".current")?.focus()):(e.key==="ArrowDown"||e.key==="ArrowUp")&&(e.preventDefault(),t[(n+(e.key==="ArrowDown"?1:-1)+t.length)%t.length]?.focus())}render(){let e=this.options.find(t=>t.value===this.value);return d`<div class="${this._open?"open":""} ${this.pending?"pending":""}">
      <button class="current" aria-expanded=${this._open?"true":"false"} aria-label="${this.label}: ${e?.label??"not set"}" ?disabled=${this.disabled||this.pending}
        @click=${()=>this._open=!this._open}><span>${e?.label??"\u2013"}</span>${P("chevron")}</button>
      ${this._open?d`<ul role="radiogroup" aria-label=${this.label} @keydown=${this.key}>
        ${this.options.map(t=>d`<li><button role="radio" aria-checked=${t.value===this.value?"true":"false"}
          @click=${()=>this.pick(t.value)}>${t.label}</button></li>`)}
      </ul>`:p}
    </div>`}};Lt.properties={options:{attribute:!1},value:{},pending:{type:Boolean},disabled:{type:Boolean},label:{},_open:{state:!0}},Lt.styles=[X,Jt,k`
    :host {
      display: block;
    }
    .current {
      width: 100%;
      height: 44px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      padding: 0 12px;
      font: 600 16px/1 var(--gac-label);
      letter-spacing: 0.03em;
      color: var(--gac-ink);
      background: var(--gac-paper);
      border: 1px solid var(--gac-edge);
      border-radius: 2px;
      cursor: pointer;
    }
    .current svg {
      width: 18px;
      height: 18px;
      transition: transform 150ms ease-out;
    }
    .open .current svg {
      transform: rotate(90deg);
    }
    .current:disabled {
      cursor: not-allowed;
      color: var(--gac-muted);
    }
    ul {
      list-style: none;
      margin: 4px 0 0;
      padding: 0;
      border: 1px solid var(--gac-edge);
      border-radius: 2px;
      background: var(--gac-paper);
    }
    li + li {
      border-top: 1px solid var(--gac-hair);
    }
    li button {
      width: 100%;
      min-height: 44px;
      padding: 0 12px;
      text-align: left;
      font: 500 15px/1.2 var(--gac-text);
      color: var(--gac-ink);
      background: none;
      border: 0;
      cursor: pointer;
    }
    li button:hover {
      background: color-mix(in srgb, var(--gac-paper) 88%, var(--gac-ink));
    }
    li button[aria-checked="true"] {
      background: var(--gac-mw);
      color: var(--gac-mw-ink);
      font-weight: 600;
    }
  `];function Ze(){let i=(e,t)=>{customElements.get(e)||customElements.define(e,t)};i("gac-action",At),i("gac-switch",Ct),i("gac-segments",Et),i("gac-stepper",Tt),i("gac-stops",Rt),i("gac-day-range",Ht),i("gac-choice",Lt)}var tn=[{value:"hatch",label:"Hatchback"},{value:"saloon",label:"Saloon"},{value:"suv",label:"SUV"},{value:"coupe_suv",label:"Coup\xE9 SUV"},{value:"mpv",label:"MPV (sliding doors)"}],In=[[/\b(M6|M8|GN6|GN8|E8|E9|MPV)\b/i,"mpv"],[/\bHT\b|\bSSR\b|coup/i,"coupe_suv"],[/\bAION\s*E?S\b|\bGA[468]\b|\bEMPOW\b|\bHYPTEC\s*GT\b|saloon|sedan/i,"saloon"],[/\bUT\b|\bAION\s*Y\b|hatch/i,"hatch"]];function en(i){return In.find(([e])=>e.test(i))?.[1]??"suv"}var jn={hatch:{hwFront:40,hwRear:40,top:30,bottom:206,rFront:22,rRear:14,screen:[62,84],rear:[164,180]},saloon:{hwFront:39,hwRear:39,top:22,bottom:218,rFront:22,rRear:16,screen:[70,92],rear:[150,170],deck:!0},suv:{hwFront:43,hwRear:43,top:24,bottom:214,rFront:18,rRear:10,screen:[64,84],rear:[184,200],rails:!0},coupe_suv:{hwFront:43,hwRear:37,top:22,bottom:216,rFront:22,rRear:16,screen:[64,86],rear:[150,190]},mpv:{hwFront:45,hwRear:45,top:16,bottom:222,rFront:16,rRear:8,screen:[50,72],rear:[200,214],sliding:!0}},b=110,_e=1.12,te=118,ke=(i,e)=>[b+(i-b)*_e,te+(e-te)*_e];function Xe(i){let{hwFront:e,hwRear:t,top:n,bottom:s,rFront:a,rRear:r}=i;return`M${b-e+a} ${n}Q${b} ${n-5} ${b+e-a} ${n}Q${b+e} ${n} ${b+e} ${n+a}L${b+t} ${s-r}Q${b+t} ${s} ${b+t-r} ${s}Q${b} ${s+3} ${b-t+r} ${s}Q${b-t} ${s} ${b-t} ${s-r}L${b-e} ${n+a}Q${b-e} ${n} ${b-e+a} ${n}Z`}function U(i,e){let t=(e-i.top)/(i.bottom-i.top);return i.hwFront+(i.hwRear-i.hwFront)*Math.min(1,Math.max(0,t))}var pt="var(--gac-yellow)";function Je(i,e){return g`<path d="M${i-5} ${e+4.5}L${i} ${e-5}L${i+5} ${e+4.5}Z" fill=${pt}
    stroke="var(--gac-ink)" stroke-linejoin="round"/>`}function nn(i,e,t){let n=jn[i],[s,a]=n.screen,[r,o]=n.rear,l=Math.round((a+r)/2),h={front:[a-6,l],rear:[l,Math.min(r+6,l+(l-a)+6)]},u=n.top+(n.bottom-n.top)*.2,c=n.bottom-(n.bottom-n.top)*.19,m=($,T)=>{let R=U(n,$);return g`<rect x=${b+T*(R+1)-5} y=${$-14} width="10" height="28" rx="2.5" fill="var(--gac-ink)"/>`},f=[],v=($,T,R,H)=>{let[V,C]=ke($,T);f.push(g`<text class="plan-label" x=${V} y=${C} text-anchor=${H}>${R}</text>`)},B=($,T)=>f.push(Je(...ke($,T))),at=$=>{let[T,R]=$.split("_"),[H,V]=T==="front"?[a+2,l-2]:[l+2,r-2],C=R==="left"?-1:1,z=U(n,(H+V)/2),D=C<0?b-z+4:b+z-11,K=e.windows[$]===!0;if(K&&e.doors[$]!==!0){let $t=(H+V)/2;B(b+C*(z+7),$t),v(b+C*(z+14),$t+4,"WINDOW",C<0?"end":"start")}return g`<rect x=${D} y=${H} width="7" height=${Math.max(4,V-H)} fill=${K?pt:"var(--gac-glass)"}
      stroke="var(--gac-ink)" stroke-width="1"/>`},ft=$=>{let[T,R]=$.split("_"),[H,V]=h[T],C=R==="left"?-1:1,z=U(n,H),D=b+C*z;if(e.doors[$]!==!0)return g`<path d="M${D} ${V}h${-C*12}" stroke="var(--gac-ink)" stroke-width="1"/>`;let K=V-H;if(n.sliding&&T==="rear"){let le=n.bottom-n.rRear-6,de=Math.min(H+K*.45,le-K*.8),He=(de+le)/2;return B(D+C*16,He),v(D+C*24,He+4,"DOOR",C<0?"end":"start"),g`<rect x=${C<0?D-9:D+3} y=${de} width="6" height=${le-de}
        fill=${pt} stroke="var(--gac-ink)" stroke-width="1.2"/>`}let $t=38*Math.PI/180,jt=D+C*Math.sin($t)*K,Wt=H+Math.cos($t)*K;return v(jt+C*6,Wt+22,"DOOR","middle"),g`<g><path d="M${D} ${H}L${jt} ${Wt}" stroke="var(--gac-ink)" stroke-width="6.5"
      stroke-linecap="round"/><path d="M${D} ${H}L${jt} ${Wt}" stroke=${pt} stroke-width="4"
      stroke-linecap="round"/>${Je(jt+C*6,Wt+6)}</g>`},re=$=>(U(n,$)-12)*2,qt=($,T)=>{let R=re($)/2;return B(b+R+9,$+7),v(b+R+16,$+11,T,"start"),g`<rect x=${b-R} y=${$} width=${R*2} height="16" rx="2" fill=${pt}
      stroke="var(--gac-ink)" stroke-width="1.5"/>`},bt=e.boot?qt(n.bottom-1,"BOOT"):"",oe=e.bonnet?qt(n.top-15,"BONNET"):"",O=($,T,R,H,V,C="")=>{let z=H?T-R:T+R;return g`<path class=${C} d="M${$-R*.62} ${T}L${$} ${z}L${$+R*.62} ${T}Z" fill=${V}
      stroke="var(--gac-ink)" stroke-width="1" stroke-linejoin="round"/>`},I=e.lights??{},rt=n.top-3,A=n.bottom+3,j=e.boot?n.bottom+19:A,It=g`
    ${I.headlights||I.highBeam?[-1,1].map($=>I.highBeam?O(b+$*(n.hwFront-14),rt-1,15,!0,"var(--gac-lamp-high)","lamp-high"):O(b+$*(n.hwFront-14),rt,10,!0,"var(--gac-lamp)")):""}
    ${I.rearFog?O(b-n.hwRear*.4,j,10,!1,"var(--gac-lamp-high)"):""}
    ${I.indicators?[-1,1].flatMap($=>[O(b+$*(n.hwFront+1),n.top+9,9,!0,"var(--gac-yellow)","blink"),O(b+$*(n.hwRear+1),n.bottom-9,9,!1,"var(--gac-yellow)","blink")]):""}`,W=b-U(n,l)+12,ot=b+U(n,l)-12,Te=Math.min(42,(r-a)/2.2);if(e.sunroof){let $=ke(0,a+8+Te/2+4)[1];f.push(g`<text class="plan-label" x="218" y=${$} text-anchor="end">SUNROOF</text>`)}let Sn=e.sunroof===void 0?"":g`<rect x=${W+6} y=${a+8}
    width=${ot-W-12} height=${Te}
    fill=${e.sunroof?pt:"var(--gac-glass)"} stroke="var(--gac-ink)" stroke-width="1"/>`,vt=U(n,a),lt=U(n,r),Re=$=>g`<rect x=${b+$*(vt+4)-4} y=${s+2} width="8"
    height="6" rx="1" fill="var(--gac-body)" stroke="var(--gac-ink)"/>`,An=["front_left","rear_left","front_right","rear_right"].map(at),Cn=["front_left","rear_left","front_right","rear_right"].map(ft);return d`<svg class="plan" viewBox="0 -28 220 296" role="img" aria-label=${t}>
    <g transform="translate(${b} ${te}) scale(${_e}) translate(${-b} ${-te})">
    ${m(u,-1)}${m(u,1)}${m(c,-1)}${m(c,1)}
    ${bt}${oe}
    <path d=${Xe(n)} fill="var(--gac-body)" stroke="var(--gac-ink)" stroke-width="4.5"/>
    <path d=${Xe(n)} fill="none" stroke="var(--gac-body)" stroke-width="1.6"/>
    ${Re(-1)}${Re(1)}
    <g stroke="var(--gac-ink)" stroke-width="1">
      <path d="M${b-vt+10} ${s+4}Q${b} ${s-4} ${b+vt-10} ${s+4}
        L${b+vt-6} ${a}H${b-vt+6}Z" fill="var(--gac-glass)"/>
      <path d="M${b-lt+7} ${r}H${b+lt-7}L${b+lt-11} ${o}Q${b} ${o+4} ${b-lt+11} ${o}Z" fill="var(--gac-glass)"/>
      <path d="M${W} ${a}V${r}M${ot} ${a}V${r}" fill="none"/>
      ${n.deck?g`<path d="M${b-lt+10} ${o+14}H${b+lt-10}" fill="none"/>`:""}
      ${n.rails?g`<path d="M${W+3} ${a+6}V${r-6}M${ot-3} ${a+6}V${r-6}" stroke-width="2" stroke-linecap="round" fill="none"/>`:""}
      ${n.sliding?g`<path d="M${b-U(n,l)+2} ${l+4}V${r+4}M${b+U(n,l)-2} ${l+4}V${r+4}" stroke-dasharray="3 2" fill="none"/>`:""}
    </g>
    ${Sn}
    ${An}
    ${Cn}
    ${It}
    </g>
    ${f}
  </svg>`}var Wn=new Set(["unknown","unavailable",""]);function an(i,e,t,n,s){let a=i.formatEntityAttributeValue?.(e,t,n);return a&&a!==n?a:s}function w(i){return i!==void 0&&!Wn.has(i.state)}function _(i){if(!w(i))return;let e=Number(i.state);return Number.isFinite(e)?e:void 0}function x(i){if(w(i))return i.state==="on"}function Nt(i,e,t){i.dispatchEvent(new CustomEvent(e,{detail:t,bubbles:!0,composed:!0}))}function M(i,e){e&&Nt(i,"hass-more-info",{entityId:e})}function rn(i,e){history.pushState(null,"",e),Nt(i,"location-changed",{replace:!1})}function N(i,e,t=0){return e.toLocaleString(i.locale?.language??i.language??"en-GB",{minimumFractionDigits:t,maximumFractionDigits:t})}function ht(i){let e=i.locale?.time_format;if(e==="12")return!0;if(e==="24")return!1;let t=e==="system"?void 0:i.locale?.language??i.language;return new Intl.DateTimeFormat(t,{hour:"numeric"}).resolvedOptions().hour12===!0}function tt(i,e){return e===void 0?"\u2013\u2013:\u2013\u2013":new Date(2024,0,1,Math.floor(e/60)%24,e%60).toLocaleTimeString(i.locale?.language??i.language??"en-GB",{hour:"numeric",minute:"2-digit",hour12:ht(i)})}var sn=["sunday","monday","tuesday","wednesday","thursday","friday","saturday"];function on(i){let e=i.locale?.first_weekday??"language";if(sn.includes(e))return sn.indexOf(e);let t=i.locale?.language??i.language??"en";try{let n=new Intl.Locale(t),s=(n.getWeekInfo?.()??n.weekInfo)?.firstDay;if(s)return s%7}catch{}return/^en(-US)?$/i.test(t)?0:1}function Me(i,e,t){return new Date(2024,0,7+e).toLocaleDateString(i.locale?.language??i.language??"en-GB",{weekday:t})}function J(i,e){return e.toLocaleTimeString(i.locale?.language??"en-GB",{hour:"2-digit",minute:"2-digit",hour12:ht(i)})}function et(i,e,t=new Date){if(!e||Number.isNaN(e.getTime()))return"time unknown";let n=Math.round((t.getTime()-e.getTime())/1e3);if(n<-60)return`at ${J(i,e)}`;if(n<60)return"just now";let s=Math.floor(n/60);if(s<60)return`${s} min ago`;let a=Math.floor(s/60);if(a<24&&e.getDate()===t.getDate())return`${a} h ago`;let r=new Date(t);return r.setDate(t.getDate()-1),e.toDateString()===r.toDateString()?`yesterday ${J(i,e)}`:`${e.toLocaleDateString(i.locale?.language??i.language??"en-GB",{day:"numeric",month:"short",...e.getFullYear()!==t.getFullYear()?{year:"numeric"}:{}})}, ${J(i,e)}`}function ee(i){let e=Math.max(0,Math.round(i)),t=Math.floor(e/60),n=e%60;return t===0?`${n} min`:n===0?`${t} h`:`${t} h ${n} min`}function ne(i){if(!w(i))return;let e=new Date(i.state);return Number.isNaN(e.getTime())?void 0:e}var Ot="gac_connect";function ut(i){let e=new Set;for(let t of Object.values(i.entities??{}))t.platform===Ot&&t.device_id&&e.add(t.device_id);return[...e].map(t=>{let n=i.devices?.[t];return{id:t,name:n?.name_by_user||n?.name||"GAC vehicle"}}).sort((t,n)=>t.name.localeCompare(n.name))}var ln=new WeakMap;function Kn(i,e){let t=ln.get(i.entities);t||(t=new Map,ln.set(i.entities,t));let n=t.get(e);if(!n){n=new Map;for(let s of Object.values(i.entities))s.platform!==Ot||s.device_id!==e||!s.translation_key||n.set(`${s.entity_id.split(".")[0]}.${s.translation_key}`,s.entity_id);t.set(e,n)}return n}var Gn=[[/^unlock$/,"Unlock"],[/^lock$/,"Lock"],[/^aircon|^climate|^ac-/,"A/C"],[/^ventilate/,"Ventilation"],[/^tailgate-open/,"Open boot"],[/^tailgate-close/,"Close boot"],[/^window-open/,"Open windows"],[/^window-close/,"Close windows"],[/^sunroof-open/,"Open sunroof"],[/^sunroof-close/,"Close sunroof"],[/^horn/,"Sound horn"],[/^flash/,"Flash lights"],[/^steering/,"Steering wheel heat"],[/^seat-1/,"Driver seat"],[/^seat-2/,"Passenger seat"],[/^seat-/,"Rear seat"],[/^battery-precondition/,"Smart battery temp"],[/^antivirus/,"Sterilisation"],[/^fridge/,"Fridge"],[/^charge-now/,"Charge now"],[/^charge-resume/,"Scheduled charging"],[/^charge-window|^charge-schedule/,"Charge window"],[/^charger-unlock/,"Unlock connector"],[/^vehicle-power-off/,"Turn vehicle off"]];function Pt(i){return i?Gn.find(([e])=>e.test(i))?.[1]??i.replace(/-/g," ").replace(/^./,e=>e.toUpperCase()):"Command"}var Se={idle:"No command yet",sending:"Sending",pending:"Waiting for the car",awaiting_report:"Accepted; waiting for the car's report",confirmed:"Confirmed by the car",reported_success:"The car reported success",rejected:"Refused by the car",failed:"Request failed",timed_out:"Not confirmed in time",cancelled:"Cancelled",superseded:"Replaced by a newer request"};function nt(i){switch(i){case"sending":case"pending":case"awaiting_report":return"pending";case"confirmed":case"reported_success":return"ok";case"rejected":case"failed":return"refused";case"timed_out":return"unconfirmed";default:return"quiet"}}var se=class{constructor(e,t){this.hass=e;this.deviceId=t;let n=e.devices?.[t];this.name=n?.name_by_user||n?.name||"GAC vehicle",this.model=n?.model||n?.name||"",this.vin=n?.serial_number??void 0,this.keys=Kn(e,t)}get exists(){return this.keys.size>0}id(e){return this.keys.get(e)}has(e){return this.get(e)!==void 0}get(e){let t=this.keys.get(e),n=t?this.hass.states[t]:void 0;return n?.attributes.restored===!0?void 0:n}pending(e){return(this.get("sensor.last_command")?.attributes.pending_commands??[]).some(s=>e.some(a=>s.startsWith(a)))}lastFor(e){let t=this.get("sensor.last_command");if(!w(t))return;let n=t.attributes.command;if(!(!n||!e.some(s=>n.startsWith(s))))return{state:t.state,reason:st(t),at:t.attributes.requested_at?new Date(t.attributes.requested_at):void 0}}call(e,t,n,s={}){let a=this.id(n);return a?this.hass.callService(e,t,{entity_id:a,...s}).catch(()=>{}):Promise.resolve()}action(e,t){let n=this.vin?{vin:this.vin,...t}:t;return this.hass.callService(Ot,e,n).catch(()=>{})}};function st(i){if(!i)return;let e=i.attributes.reported_causes??[];return e.length?e.join(", "):i.attributes.refusal_reason??i.attributes.failure_reason??void 0}var dn=i=>`var(--gac-${i})`,cn=i=>`var(--gac-${i}-case)`;function Ae(i,e,t){return g`<path d="M${i} ${t}H${e}" stroke="var(--gac-minor-case)" stroke-width="7"/>
    <path d="M${i} ${t}H${e}" stroke="var(--gac-minor)" stroke-width="5"/>`}function pn(i,e,t,n){return g`<path d="M${i} ${t}H${e}" stroke=${cn(n)} stroke-width="14"/>
    <path d="M${i} ${t}H${e}" stroke=${dn(n)} stroke-width="10"/>`}function Yn(i,e,t,n){let s=[];for(let a=i-14;a<e+14;a+=14)s.push(`M${a} ${t-3}l3 3-3 3`);return g`<clipPath id=${n}><rect x=${i} y=${t-5} width=${Math.max(0,e-i)} height="10"/></clipPath>
    <g clip-path="url(#${n})"><path class="flow" d=${s.join("")} fill="none" stroke="var(--gac-minor)"
      stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" opacity="0.9"/></g>`}function hn(i){let e=Math.max(160,i.width),t=8,n=e-8,s=12,a=i.fraction===void 0?void 0:Math.min(1,Math.max(0,i.fraction)),r=a===void 0?void 0:t+a*(n-t),o=36,l;if(i.marker!==void 0&&r!==void 0){let u=r-t>132,c=u?(t+r)/2:Math.min(r+12,n-96),m=u?"middle":"start";l=g`
      <path d="M${t-5} ${o+8}L${t} ${o-4}L${t+5} ${o+8}Z" fill="var(--gac-ink)"/>
      <path d="M${r-5} ${o+8}L${r} ${o-4}L${r+5} ${o+8}Z" fill="var(--gac-ink)"/>
      ${u?g`<path d="M${t+9} ${o+3.5}H${c-62}M${c+62} ${o+3.5}H${r-9}"
        stroke="var(--gac-ink)" stroke-width="1"/>`:""}
      <text x=${c} y=${o+12} text-anchor=${m} class="road-text">
        <tspan class="road-lab">${i.markerLabel??""} </tspan><tspan class="road-num">${i.marker}</tspan><tspan
          class="road-unit"> ${i.markerUnit??""}</tspan></text>`}return d`<svg class="road" width=${e} height=${i.marker!==void 0?56:26} viewBox="0 0 ${e} ${i.marker!==void 0?56:26}" aria-hidden="true">
    ${Ae(t,n,s)}
    ${r!==void 0&&r>t?pn(t,r,s,i.tone):""}
    ${r!==void 0&&i.flowing?Yn(t,r-6,s,`${i.id}-flow`):""}
    ${l??""}
  </svg>`}function un(i){let e=Math.max(200,i.width),t=10,n=e-10,s=16,a=l=>t+l/1440*(n-t),r=[];i.start!==void 0&&i.stop!==void 0&&(i.start===i.stop?r.push([0,1440]):i.start<i.stop?r.push([i.start,i.stop]):r.push([i.start,1440],[0,i.stop]));let o=Array.from({length:9},(l,h)=>h*180);return d`<svg class="road" width=${e} height="50" viewBox="0 0 ${e} 50" aria-hidden="true">
    ${Ae(t,n,s)}
    ${r.map(([l,h])=>i.dashed?g`<path d="M${a(l)} ${s}H${a(h)}" stroke=${cn(i.tone)} stroke-width="12" stroke-dasharray="6 4"/>
        <path d="M${a(l)} ${s}H${a(h)}" stroke=${dn(i.tone)} stroke-width="8" opacity="0.55"/>`:pn(a(l),a(h),s,i.tone))}
    ${o.map(l=>g`<path d="M${a(l)} ${s+10}v${l%360===0?7:4}" stroke="var(--gac-ink)"/>`)}
    ${[0,360,720,1080,1440].map(l=>g`<text x=${a(l)} y="45" text-anchor="middle"
      class="road-tick">${String(l/60).padStart(2,"0")}</text>`)}
    ${i.now!==void 0?g`<path d="M${a(i.now)-4} 0L${a(i.now)+4} 0L${a(i.now)} 6Z"
      fill="var(--gac-ink)"/>`:""}
  </svg>`}function gn(i){let e=Math.max(200,i.width),t=12,n=e-12,s=14,a=m=>t+(Math.min(i.max,Math.max(i.min,m))-i.min)/(i.max-i.min)*(n-t),r=i.cabin!==void 0?a(i.cabin):void 0,o=i.target!==void 0?a(i.target):void 0,l=i.outside!==void 0?a(i.outside):void 0,h=l===void 0?void 0:Math.min(n-36,Math.max(t+36,l)),u=m=>h===void 0||Math.abs(h-m)>64,c="";if(r!==void 0&&o!==void 0&&Math.abs(o-r)>12){let m=Math.sign(o-r),f=o-m*9;c=i.running?g`<path d="M${r} ${s}H${f}" stroke="var(--gac-road-case)" stroke-width="12"/>
          <path d="M${r} ${s}H${f}" stroke="var(--gac-road)" stroke-width="8"/>
          <path d="M${o} ${s}L${o-m*12} ${s-9}V${s+9}Z" fill="var(--gac-road)" stroke="var(--gac-road-case)"
            stroke-width="1.5" stroke-linejoin="round"/>`:g`<path d="M${r} ${s}H${f}" stroke="var(--gac-road)" stroke-width="2" stroke-dasharray="5 4"/>
          <path d="M${o} ${s}L${o-m*11} ${s-7}V${s+7}Z" fill="none" stroke="var(--gac-road)" stroke-width="2"
            stroke-linejoin="round"/>`,c=g`${c}<path d="M${r} ${s-7}V${s+7}" stroke="var(--gac-ink)" stroke-width="2.5"/>`}else o!==void 0&&(c=g`<path d="M${o} ${s-8}V${s+8}" stroke="var(--gac-ink)" stroke-width="2.5"/>`);return d`<svg class="road" width=${e} height="52" viewBox="0 0 ${e} 52" aria-hidden="true">
    ${Ae(t,n,s)}
    ${c}
    ${l!==void 0?g`<path d="M${l-5} 36L${l} 25L${l+5} 36Z"
      fill="var(--gac-ink)"/><text x=${h} y="49" text-anchor="middle"
      class="road-tick">OUTSIDE ${Math.round(i.outside)}°</text>`:""}
    ${u(t)?g`<text x=${t} y="49" class="road-tick">${i.min}°</text>`:""}
    ${u(n)?g`<text x=${n} y="49" text-anchor="end" class="road-tick">${i.max}°</text>`:""}
  </svg>`}var mn=`
  .road { display: block; overflow: visible; }
  .road-text { font-family: var(--gac-label); fill: var(--gac-ink); }
  .road-lab { font-size: 12px; font-weight: 600; letter-spacing: 0.1em; fill: var(--gac-muted); }
  .road-num { font-size: 26px; font-weight: 600; font-variant-numeric: tabular-nums; }
  .road-unit { font-size: 15px; font-weight: 500; fill: var(--gac-muted); }
  .road-tick { font: 600 12px var(--gac-label); fill: var(--gac-muted); letter-spacing: 0.06em; }
  .plan-label { font: 600 12px var(--gac-label); fill: var(--gac-ink); letter-spacing: 0.06em; }
  .flow { animation: gac-flow 1.6s linear infinite; }
  .blink { animation: gac-blink 1s steps(1, end) infinite; }
  @keyframes gac-blink { 50% { opacity: 0.12; } }
  .lamp-high { filter: drop-shadow(0 0 2.5px rgba(255, 255, 255, 0.95)); }
  @keyframes gac-flow { to { transform: translateX(14px); } }
  @media (prefers-reduced-motion: reduce) { .flow, .blink { animation: none; } }
`;var Qn=[["Barlow Condensed",500],["Barlow Condensed",600],["Barlow Condensed",700],["Barlow",400],["Barlow",500]],Zn={latin:"U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD","latin-ext":"U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF"};function fn(i){if(document.getElementById("gac-connect-fonts")||document.querySelector('link[href*="family=Barlow"]'))return;let e=Qn.flatMap(([n,s])=>Object.entries(Zn).map(([a,r])=>{let o=`${n.toLowerCase().replace(" ","-")}-${a}-${s}-normal.woff2`;return`@font-face{font-family:"${n}";font-style:normal;font-weight:${s};font-display:swap;src:url(${new URL(`fonts/${o}`,i).href}) format("woff2");unicode-range:${r}}`})),t=document.createElement("style");t.id="gac-connect-fonts",t.textContent=e.join(`
`),document.head.append(t)}var bn=k`
  :host {
    --gac-land: #eaf0e2;
    --gac-paper: #f8faf4;
    --gac-water: #dce6ec;
    --gac-ink: #1e2421;
    --gac-muted: #535b56;
    --gac-hair: rgba(30, 36, 33, 0.2);
    --gac-edge: rgba(30, 36, 33, 0.34);
    --gac-mw: #2e6db4;
    --gac-mw-case: #1b3f6b;
    --gac-mw-ink: #ffffff;
    --gac-green: #1f8a4c;
    --gac-green-case: #145c33;
    --gac-red: #d2352b;
    --gac-red-case: #8e1f18;
    --gac-red-ink: #b02a21;
    --gac-yellow: #f2c230;
    --gac-yellow-case: #8a6a0a;
    --gac-minor: #ffffff;
    --gac-minor-case: #a9b4a3;
    --gac-road: #56625b;
    --gac-road-case: #2f3833;
    --gac-lamp: #f4f6f0;
    --gac-lamp-high: #ffffff;
    --gac-body: #f8faf4;
    --gac-glass: #dce6ec;
    --gac-label: "Barlow Condensed", "Arial Narrow", "Roboto Condensed", sans-serif;
    --gac-text: "Barlow", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    color-scheme: light;
  }
  :host([dark]) {
    --gac-land: #17201b;
    --gac-paper: #1f2a24;
    --gac-water: #1a2a35;
    --gac-ink: #e4ebe2;
    --gac-muted: #a4aea7;
    --gac-hair: rgba(228, 235, 226, 0.16);
    --gac-edge: rgba(228, 235, 226, 0.3);
    --gac-mw: #3f86d4;
    --gac-mw-case: #9cc4ef;
    --gac-mw-ink: #0c1a2b;
    --gac-green: #34a866;
    --gac-green-case: #9ad9b2;
    --gac-red: #e0493e;
    --gac-red-case: #f3a49d;
    --gac-red-ink: #f08a80;
    --gac-yellow: #f2c230;
    --gac-yellow-case: #f7dd8a;
    --gac-minor: #2b3731;
    --gac-minor-case: #4b5852;
    --gac-road: #aeb9b1;
    --gac-road-case: #dfe6dd;
    --gac-lamp: #d9ded6;
    --gac-lamp-high: #ffffff;
    --gac-body: #26322c;
    --gac-glass: #1f3442;
    color-scheme: dark;
  }
`,vn=k`
  :host {
    display: block;
  }
  * {
    box-sizing: border-box;
  }
  ha-card {
    display: block;
    background: var(--gac-land);
    color: var(--gac-ink);
    border: 1px solid var(--gac-hair);
    border-radius: 4px;
    box-shadow: none;
    overflow: hidden;
    font: 400 15px/1.35 var(--gac-text);
    container-type: inline-size;
    -webkit-font-smoothing: antialiased;
  }
  ::selection {
    background: var(--gac-mw);
    color: var(--gac-mw-ink);
  }
  .plate {
    height: 44px;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 0 16px;
    border-bottom: 1px solid var(--gac-hair);
  }
  .ref {
    width: 24px;
    height: 24px;
    flex: none;
    border: 1px solid var(--gac-ink);
    display: grid;
    place-items: center;
  }
  .ref svg {
    width: 16px;
    height: 16px;
  }
  .name {
    font: 700 22px/1 var(--gac-label);
    letter-spacing: 0.05em;
    text-transform: uppercase;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    min-width: 0;
  }
  .plate .lab {
    margin-left: auto;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 45%;
  }
  .lab {
    font: 600 12px/16px var(--gac-label);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--gac-muted);
  }
  .sec {
    padding: 12px 16px;
  }
  .sec + .sec {
    border-top: 1px solid var(--gac-hair);
  }
  .fig {
    font: 600 40px/1 var(--gac-label);
    font-variant-numeric: tabular-nums lining-nums;
    letter-spacing: 0.01em;
  }
  .fig small,
  .unit {
    font-size: 18px;
    font-weight: 500;
    color: var(--gac-muted);
    letter-spacing: 0.02em;
  }
  .num {
    font-family: var(--gac-label);
    font-variant-numeric: tabular-nums lining-nums;
  }
  .muted {
    color: var(--gac-muted);
  }
  .sr {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
    white-space: nowrap;
  }
  .fresh {
    min-height: 36px;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 0 6px 0 16px;
    border-top: 1px solid var(--gac-hair);
  }
  .fresh-info {
    flex: 1;
    min-width: 0;
    min-height: 36px;
    display: flex;
    align-items: center;
    gap: 6px;
    font: 400 13px/1.3 var(--gac-text);
    color: var(--gac-muted);
    text-align: left;
    cursor: pointer;
  }
  .refresh {
    flex: none;
    width: 36px;
    height: 36px;
    display: grid;
    place-items: center;
    padding: 0;
    color: var(--gac-muted);
    background: none;
    border: 0;
    border-radius: 2px;
    cursor: pointer;
  }
  .refresh:hover {
    color: var(--gac-ink);
    background: color-mix(in srgb, var(--gac-land) 85%, var(--gac-ink));
  }
  .refresh svg {
    width: 18px;
    height: 18px;
  }
  .refresh.reading svg {
    animation: gac-spin 1s linear infinite;
  }
  @keyframes gac-spin {
    to {
      transform: rotate(360deg);
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .refresh.reading svg {
      animation: none;
    }
  }
  .refresh:focus-visible,
  .tap:focus-visible {
    outline: 2px solid var(--gac-mw);
    outline-offset: -2px;
  }
  .tap {
    cursor: pointer;
    background: none;
    border: 0;
    padding: 0;
    color: inherit;
    font: inherit;
    text-align: inherit;
  }
  .mark {
    width: 12px;
    height: 12px;
    flex: none;
    display: inline-block;
    vertical-align: -1px;
  }
  .note {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    font-size: 14px;
    line-height: 1.4;
    margin: 0;
  }
  .note .mark {
    margin-top: 3px;
  }
  .note.refused {
    color: var(--gac-red-ink);
  }
  .duo {
    display: grid;
    grid-template-columns: 1fr 1fr;
  }
  .duo > * + * {
    border-left: 1px solid var(--gac-hair);
    padding-left: 16px;
  }
  .row {
    display: flex;
    align-items: center;
    gap: 12px;
    min-height: 48px;
  }
  .row + .row {
    border-top: 1px solid var(--gac-hair);
  }
  .row .what {
    flex: 1;
    min-width: 0;
  }
  .row .title {
    font-size: 15px;
    font-weight: 500;
  }
  .row .desc {
    font-size: 13px;
    color: var(--gac-muted);
    line-height: 1.35;
  }
  .head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 4px;
  }
  .grid3 {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
  }
  .grid2 {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
  }
  .empty {
    padding: 16px;
    font-size: 14px;
    color: var(--gac-muted);
  }
  .empty strong {
    display: block;
    color: var(--gac-ink);
    font: 600 18px/1.2 var(--gac-label);
    letter-spacing: 0.04em;
    text-transform: uppercase;
    margin-bottom: 4px;
  }
  @container (max-width: 330px) {
    .sec,
    .plate {
      padding-left: 12px;
      padding-right: 12px;
    }
    .fresh {
      padding-left: 12px;
    }
    .fig {
      font-size: 34px;
    }
    .grid3 {
      grid-template-columns: repeat(2, 1fr);
    }
  }
`;var S=class extends E{constructor(){super();this.readingSince=0;this.width=320}setConfig(t){if(!t||typeof t!="object")throw new Error("Invalid configuration");this.config={...t}}static getConfigElement(){return document.createElement("gac-card-editor")}static getStubConfig(t){let n=ut(t)[0];return n?{device:n.id}:{}}getCardSize(){return 6}getGridOptions(){return{columns:12,min_columns:6,rows:"auto"}}connectedCallback(){super.connectedCallback(),this.resizer=new ResizeObserver(t=>{let n=Math.round(t[0]?.contentRect.width??0);n>0&&Math.abs(n-this.width)>=1&&(this.width=n)}),this.resizer.observe(this),this.ticker=window.setInterval(()=>this.requestUpdate(),3e4)}disconnectedCallback(){super.disconnectedCallback(),this.resizer?.disconnect(),window.clearInterval(this.ticker)}willUpdate(t){t.has("hass")&&this.hass&&this.toggleAttribute("dark",this.hass.themes?.darkMode===!0)}get inner(){return Math.max(200,this.width-(this.width<=330?26:34))}get vehicle(){let t=this.hass;if(!t)return;let n=this.config?.device,s=(Array.isArray(n)?n[0]:n)||ut(t)[0]?.id;return s?new se(t,s):void 0}render(){if(!this.hass||!this.config)return p;let t=this.vehicle;return!t||!t.exists?d`<ha-card>
        ${this.plate(this.cardTitle,"")}
        <div class="empty"><strong>Choose your car</strong>
          No GAC Connect vehicle was found${this.config.device?" for the chosen car":""}. Edit the card and
          pick a car, or add the GAC Connect integration first.</div>
      </ha-card>`:d`<ha-card>
      ${this.plate(this.plateTitle(t),this.plateNote(t))}
      ${this.body(t)}
      ${this.freshness(t)}
    </ha-card>`}plateTitle(t){return this.cardTitle}plateNote(t){return t.name}plate(t,n){return d`<div class="plate"><span class="ref">${P(this.glyph)}</span>
      <span class="name" role="heading" aria-level="2">${t}</span>
      ${n?d`<span class="lab">${n}</span>`:p}</div>`}freshness(t){let n=this.hass,s=t.get("sensor.last_report"),a=ne(s),r=[],o,l=x(t.get("binary_sensor.online")),h=t.get("sensor.polling_status")?.state,u=t.get("sensor.data_freshness")?.state;if(l===!1?(o="fault",r.push("Offline")):h==="auth_required"?(o="fault",r.push("Sign in again")):h==="error"?(o="warn",r.push("Refresh failed")):h==="rate_limited"?(o="warn",r.push("Waiting for the request limit")):u==="stale"?(o="warn",r.push("Old report")):u==="clock_mismatch"?(o="warn",r.push("Report clock ahead")):h==="quiet_hours"&&(o="off",r.push("Quiet hours")),!o){let m=x(t.get("binary_sensor.charging")),f=x(t.get("binary_sensor.vehicle_power"));m?r.push("Charging"):f===!0?r.push("Switched on"):f===!1&&r.push("Parked")}r.push(w(s)?`Updated ${et(n,a)}`:"No report yet");let c=this.readingFrom!==void 0&&this.readingFrom===(s?.state??"")&&Date.now()-this.readingSince<2e4;return d`<div class="fresh">
      <button class="tap fresh-info" @click=${()=>M(this,t.id("sensor.last_report"))}>
        ${o?y(o):p}<span>${r.join(" \xB7 ")}</span></button>
      ${t.has("button.refresh")?d`<button class="refresh ${c?"reading":""}"
        aria-label="Read the car now" title="Read the car now" aria-busy=${c?"true":"false"}
        @click=${()=>this.readNow(t,s?.state??"")}>${P("refresh")}</button>`:p}
    </div>`}readNow(t,n){this.readingFrom=n,this.readingSince=Date.now(),this.requestUpdate(),window.setTimeout(()=>this.requestUpdate(),20100),t.call("button","press","button.refresh")}actionState(t,n,s,a=!1){if(a||t.pending(n))return"pending";let r=t.lastFor(n);return r&&nt(r.state)==="refused"&&r.at&&Date.now()-r.at.getTime()<12e4?"refused":s?"on":"idle"}commandNote(t,n){let s=t.get("sensor.last_command");if(!w(s))return p;let a=s.attributes.command;if(!a||!n.some(c=>a.startsWith(c)))return p;let r=s.attributes.requested_at?new Date(s.attributes.requested_at):void 0,o=nt(s.state);if(o!=="pending"&&(!r||Date.now()-r.getTime()>18e4))return p;let l=Pt(a),u={pending:["wait",s.state==="sending"?`${l}: sending`:`${l}: waiting for the car`],ok:["ok",`${l}: confirmed by the car`],refused:["fault",`${l} refused${st(s)?`: ${st(s)}`:""}`],unconfirmed:["warn",`${l}: not confirmed in time`]}[o];return u?d`<p class="note ${o}" role="status">${y(u[0])}<span>${u[1]}</span></p>`:p}};S.properties={hass:{attribute:!1},config:{state:!0},width:{state:!0}},S.styles=[bn,vn,Yt(mn)];var yn=[{value:"lock",label:"Lock and unlock"},{value:"climate",label:"A/C"},{value:"ventilation",label:"Ventilation"},{value:"boot",label:"Boot"},{value:"horn",label:"Sound horn"},{value:"lights",label:"Flash lights"},{value:"windows",label:"Windows"},{value:"sunroof",label:"Sunroof"},{value:"charge_now",label:"Charge now"},{value:"refresh",label:"Refresh"}],Xn=["lock","climate","ventilation","windows","boot","sunroof","horn","lights"],Jn=9,$n=30,Ce=["front_left","front_right","rear_left","rear_right"],wn={front_left:"Front left",front_right:"Front right",rear_left:"Rear left",rear_right:"Rear right"};function ts(i,e){return e?"green":i!==void 0&&i<=10?"red":i!==void 0&&i<=20?"yellow":"road"}function Ee(i,e,t,n){let s=_(e.get("sensor.soc")),a=e.get("sensor.range"),r=_(a),o=x(e.get("binary_sensor.charging"));return d`<div class="battery">
    <div class="head">
      <span class="lab">Battery</span>
      <button class="tap fig" @click=${()=>M(i,e.id("sensor.soc"))}
        aria-label="Battery ${s??"unknown"} per cent">${s!==void 0?Math.round(s):"\u2013"}<small>&nbsp;%</small></button>
    </div>
    ${hn({width:t,fraction:s===void 0?void 0:s/100,tone:ts(s,o),flowing:o===!0,id:n,marker:r!==void 0?N(i.hass,r):void 0,markerLabel:"RANGE",markerUnit:a?.attributes.unit_of_measurement??"km"})}
    ${r!==void 0?d`<span class="sr">Range ${Math.round(r)}
      ${a?.attributes.unit_of_measurement??"km"}</span>`:p}
  </div>`}var Vt=class extends S{constructor(){super(...arguments);this.cardTitle="Vehicle";this.glyph="car"}getCardSize(){return 11}plateTitle(t){return t.name}plateNote(){return"Vehicle"}body_style(t){return this.config.body??en(t.model)}planState(t){let n={},s={};for(let r of Ce)n[r]=x(t.get(`binary_sensor.${r}_door`)),s[r]=x(t.get(`binary_sensor.${r}_window`));let a=t.get("cover.sunroof");return{doors:n,windows:s,boot:x(t.get("binary_sensor.hatch_open"))??t.get("cover.tailgate")?.state==="open",bonnet:x(t.get("binary_sensor.hood_open")),sunroof:a?w(a)?a.state==="open":!1:void 0,lights:{headlights:x(t.get("binary_sensor.headlights")),highBeam:x(t.get("binary_sensor.high_beam")),rearFog:x(t.get("binary_sensor.rear_fog_light")),indicators:x(t.get("binary_sensor.turn_signal"))}}}openItems(t,n){let s=[],a=t.get("lock.doors"),r=x(t.get("binary_sensor.locked")),o=a&&w(a)?a.state==="locked":r===void 0?void 0:!r;a?.state==="open"?s.push(d`<li>${y("off")}Not locked</li>`):o!==void 0&&s.push(d`<li>${y(o?"ok":"off")}${o?"Locked":"Unlocked"}</li>`);let l=x(t.get("binary_sensor.anti_theft"));l!==void 0&&s.push(d`<li>${y(l?"ok":"off")}${l?"Alarm armed":"Alarm off"}</li>`);let h=Ce.filter(v=>n.doors[v]),u=Ce.filter(v=>n.windows[v]),c=[];h.length===4?c.push("All doors open"):h.forEach(v=>c.push(`${wn[v]} door open`)),n.boot&&c.push("Boot open"),n.bonnet&&c.push("Bonnet open"),n.sunroof&&c.push("Sunroof open"),u.length>1?c.push(`${u.length} windows open`):u.forEach(v=>c.push(`${wn[v]} window open`)),c.forEach(v=>s.push(d`<li>${y("warn")}${v}</li>`)),x(t.get("binary_sensor.brake_fluid"))&&s.push(d`<li>${y("fault")}Check brake fluid</li>`);let m=Object.values(n.doors).some(v=>v!==void 0)||n.boot!==void 0;!c.length&&m&&s.push(d`<li>${y("ok")}All closed</li>`);let f=n.lights??{};return f.indicators&&s.push(d`<li>${y("warn")}Indicators flashing</li>`),f.highBeam?s.push(d`<li>${y("lamp")}High beams on</li>`):f.headlights&&s.push(d`<li>${y("lamp")}Headlights on</li>`),f.rearFog&&s.push(d`<li>${y("lamp")}Rear fog light on</li>`),d`<ul class="status" aria-label="Car status">${s}</ul>`}tyres(t){let n=[1,2,3,4].map(o=>({i:o,pressure:t.get(`sensor.tyre_${o}_pressure`),temp:t.get(`sensor.tyre_${o}_temp`)})).filter(o=>o.pressure||o.temp);if(!n.length)return p;let s=Number(this.config.tyre_warning_kpa)||void 0,a={kPa:1,psi:6.894757,bar:100,Pa:.001,hPa:.1},r=n.find(o=>o.pressure)?.pressure?.attributes.unit_of_measurement;return d`<div class="sec">
      <div class="head"><span class="lab">Tyres</span>${r?d`<span class="lab">${r}</span>`:p}</div>
      <div class="tyres">
        ${n.map(({i:o,pressure:l,temp:h})=>{let u=_(l),c=_(h),m=a[l?.attributes.unit_of_measurement??"kPa"]??1,f=s!==void 0&&u!==void 0&&u*m<s,v=[u!==void 0?`${u} ${r??""}`:void 0,c!==void 0?`${c} ${h?.attributes.unit_of_measurement??"\xB0C"}`:void 0].filter(Boolean).join(", ");return d`<button class="tap" @click=${()=>M(this,(l??h)?.entity_id)}
            aria-label="Tyre ${o}: ${v||"no reading"}${f?", below your warning level":""}">
            <span class="lab">${f?y("fault"):p}Tyre ${o}</span>
            ${l?d`<span class="num ${f?"low":""}">${u===void 0?"\u2013":N(this.hass,u)}</span>`:p}
            ${h?d`<span class="heat">${c===void 0?"\u2013":N(this.hass,c)}${h.attributes.unit_of_measurement??"\xB0C"}</span>`:p}
          </button>`})}
      </div></div>`}actions(t){let n=Array.isArray(this.config.actions)?this.config.actions:Xn,s=[];for(let a of n){let r=this.action(t,a);if(r&&s.push(r),s.length===Jn)break}return s}cover(t,n,s,a,r,o){let l=t.get(s);if(!l)return;let h=l.state==="opening"||l.state==="closing",u=l.state==="open";return{key:n,icon:r,hold:!u,label:l.state==="opening"?"Opening\u2026":l.state==="closing"?"Closing\u2026":u?`Close ${a}`:`Open ${a}`,state:this.actionState(t,[o],!1,h),run:()=>t.call("cover",u?"close_cover":"open_cover",s)}}toggle(t,n,s,a,r,o){let l=t.get(s);if(!l)return;let h=l.state==="on";return{key:n,label:a,icon:r,state:w(l)?this.actionState(t,[o],h):"unavailable",run:()=>t.call("switch",h?"turn_off":"turn_on",s)}}press(t,n,s,a,r,o){if(t.get(s))return{key:n,label:a,icon:r,state:this.actionState(t,[o]),run:()=>t.call("button","press",s)}}horn(t,n){if(!t.get("button.horn"))return;let s=t.get("sensor.last_command"),a=s?.attributes.requested_at?new Date(s.attributes.requested_at).getTime():0,r=Date.now()-a;return s?.attributes.command==="horn-on"&&r<$n*1e3&&!["rejected","failed","cancelled"].includes(s.state)?(window.clearTimeout(this.hornTimer),this.hornTimer=window.setTimeout(()=>this.requestUpdate(),$n*1e3-r+100),{key:n,label:"Stop horn",icon:"horn",state:t.pending(["horn-off"])?"pending":"on",run:()=>t.action("send_command",{command:"horn-off"})}):{key:n,label:"Horn",icon:"horn",hold:!0,state:this.actionState(t,["horn"]),run:()=>t.call("button","press","button.horn")}}disconnectedCallback(){super.disconnectedCallback(),window.clearTimeout(this.hornTimer)}action(t,n){switch(n){case"lock":{let s=t.get("lock.doors");if(!s)return;let a=t.get("switch.allow_remote_unlock"),r=s.state==="locking"||s.state==="unlocking",o=s.state==="locked";return r?{key:n,label:s.state==="locking"?"Locking\u2026":"Unlocking\u2026",icon:"lock",state:"pending",run:()=>{}}:o&&a&&a.state!=="on"?{key:n,label:"Locked",icon:"lock",state:"unavailable",hint:"Remote unlocking is off. Turn it on in Settings to unlock from here.",run:()=>{}}:{key:n,label:o?"Unlock":"Lock",icon:o?"unlock":"lock",hold:o,state:this.actionState(t,["lock","unlock"]),run:()=>t.call("lock",o?"unlock":"lock","lock.doors")}}case"climate":return this.toggle(t,n,"switch.climate_power","A/C","ac","aircon");case"ventilation":return this.toggle(t,n,"switch.ventilation","Vent","vent","ventilate");case"lights":return this.toggle(t,n,"switch.lights","Lights","lights","flash");case"boot":return this.cover(t,n,"cover.tailgate","boot","boot","tailgate");case"windows":return this.cover(t,n,"cover.windows","windows","windows","window");case"sunroof":return this.cover(t,n,"cover.sunroof","sunroof","sunroof","sunroof");case"horn":return this.horn(t,n);case"refresh":return this.press(t,n,"button.refresh","Refresh","refresh","refresh");case"charge_now":return this.press(t,n,"button.charge_now","Charge now","bolt","charge-now");default:return}}body(t){let n=this.planState(t),s=this.body_style(t),a=t.get("sensor.cabin_temp"),r=t.get("sensor.outside_temp"),o=this.actions(t),l=typeof this.config.image=="string"&&this.config.image?this.config.image:void 0,h=(c,m,f=0,v=!1)=>m?d`<button
      class="tap ${v?"long":""}"
      @click=${()=>M(this,m.entity_id)}><span class="lab">${c}</span>
      <span class="num">${_(m)!==void 0?N(this.hass,_(m),f):"\u2013"}<span
        class="unit"> ${m.attributes.unit_of_measurement??""}</span></span></button>`:void 0,u=[h("Cabin",a),h("Outside",r),h("Odometer",t.get("sensor.odometer"),0,!0),h("Trip",t.get("sensor.trip_consumption"),1,!0)].filter(Boolean);return d`
      ${l?d`<img class="photo" src=${l} alt="${t.name}">`:p}
      ${t.has("sensor.soc")?d`<div class="sec">${Ee(this,t,this.inner,"veh")}</div>`:p}
      <div class="sec">
        <div class="car">
          ${nn(s,n,`Plan view of ${t.name}`)}
          <div class="side">
            ${this.openItems(t,n)}
            ${u.length?d`<div class="temps">${u}</div>`:p}
          </div>
        </div>
      </div>
      ${this.tyres(t)}
      ${o.length?d`<div class="sec actions">
        <div class="grid3">
          ${o.map(c=>d`<gac-action .label=${c.label} .icon=${c.icon} .state=${c.state}
            .hold=${c.hold??!1} .hint=${c.hint??""} @activate=${c.run}></gac-action>`)}
        </div>
        ${this.commandNote(t,["lock","unlock","aircon","ventilate","tailgate","window","sunroof","horn","flash","charge-now"])}
      </div>`:p}
    `}};Vt.styles=[...S.styles,k`
    .battery .head {
      align-items: flex-end;
      margin-bottom: 2px;
    }
    .battery .fig {
      font-size: 48px;
    }
    .photo {
      display: block;
      width: 100%;
      height: 148px;
      object-fit: cover;
      border-bottom: 1px solid var(--gac-hair);
    }
    .car {
      display: grid;
      grid-template-columns: minmax(170px, 200px) 1fr;
      gap: 0 16px;
      align-items: stretch;
    }
    .plan {
      display: block;
      width: 100%;
      height: auto;
    }
    .side {
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 12px;
      min-width: 0;
      border-left: 1px solid var(--gac-hair);
      padding-left: 16px;
    }
    .status {
      list-style: none;
      margin: 0;
      padding: 4px 0 0;
      display: flex;
      flex-direction: column;
      gap: 8px;
      font-size: 14px;
      line-height: 1.3;
    }
    .status li {
      display: flex;
      align-items: flex-start;
      gap: 7px;
    }
    .status .mark {
      margin-top: 2px;
    }
    .temps {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px 8px;
      border-top: 1px solid var(--gac-hair);
      padding-top: 10px;
    }
    .temps button {
      display: flex;
      flex-direction: column;
      gap: 2px;
      min-width: 0;
    }
    .temps .num {
      font-size: 22px;
      font-weight: 600;
      line-height: 1.05;
      overflow-wrap: anywhere;
    }
    .temps .unit {
      font-size: 13px;
    }
    /* Odometer and trip: a full-width row each, so their longer values keep the unit beside them. */
    .temps .long {
      grid-column: 1 / -1;
      flex-direction: row;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: baseline;
      column-gap: 8px;
    }
    .temps .long .num {
      font-size: 17px;
    }
    .temps .long .unit {
      font-size: 12px;
    }
    .tyres {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      margin-top: 6px;
    }
    .tyres button {
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: 2px;
      padding: 2px 0 2px 10px;
      border-left: 1px solid var(--gac-hair);
    }
    .tyres button:first-child {
      border-left: 0;
      padding-left: 0;
    }
    .tyres .num {
      font-size: 24px;
      font-weight: 600;
      line-height: 1;
    }
    .tyres .low {
      color: var(--gac-red-ink);
    }
    .tyres .heat {
      font: 500 14px/1.2 var(--gac-label);
      font-variant-numeric: tabular-nums;
      color: var(--gac-muted);
    }
    .tyres .lab {
      display: flex;
      align-items: center;
      gap: 4px;
    }
    .actions .note {
      margin-top: 10px;
    }
    @container (max-width: 380px) {
      .car {
        grid-template-columns: 1fr;
      }
      .plan {
        max-width: 230px;
        margin: 0 auto;
      }
      .side {
        border-left: 0;
        padding-left: 0;
        margin-top: 8px;
      }
      .status {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 6px 12px;
      }
    }
  `];var xn={device:"Car",body:"Body style for the drawing",image:"Photo of your car (optional)",tyre_warning_kpa:"Warn below this tyre pressure (optional)",actions:"Actions"},es={device:"The car this card shows. For another car, add another card.",body:"Automatic follows the car's model name.",image:"A picture you supply, for example /local/my-car.jpg. It shows above the drawing.",tyre_warning_kpa:"The car reports pressures but no limit; leave empty for no warning.",actions:"Shown when the car has them, up to six."},gt=class extends E{setConfig(e){this.config=e}get onlyCar(){let e=this.hass?ut(this.hass):[];return e.length===1?e[0].id:void 0}schema(){let e=this.onlyCar?[]:[{name:"device",required:!0,selector:{device:{filter:{integration:Ot}}}}];return this.config?.type==="custom:gac-vehicle-card"&&e.push({name:"body",selector:{select:{mode:"dropdown",options:[{value:"auto",label:"Automatic"},...tn]}}},{name:"image",selector:{text:{}}},{name:"tyre_warning_kpa",selector:{number:{min:100,max:400,step:5,mode:"box",unit_of_measurement:"kPa"}}},{name:"actions",selector:{select:{multiple:!0,mode:"list",options:yn}}}),e}changed(e){let t={...e.detail.value};for(let s of Object.keys(t))(t[s]===""||t[s]===void 0||s==="body"&&t[s]==="auto")&&delete t[s];let n=this.onlyCar;Nt(this,"config-changed",{config:{...t,...n?{device:n}:{},type:this.config?.type}})}render(){if(!this.hass||!this.config)return p;if(customElements.get("ha-form"))return d`<ha-form .hass=${this.hass} .data=${{body:"auto",...this.config}} .schema=${this.schema()}
        .computeLabel=${t=>xn[t.name]??t.name}
        .computeHelper=${t=>es[t.name]}
        @value-changed=${this.changed}></ha-form>`;let e=ut(this.hass);return e.length<2?p:d`<label for="device">${xn.device}</label>
      <select id="device" @change=${t=>Nt(this,"config-changed",{config:{...this.config,device:t.target.value}})}>
        ${e.map(t=>d`<option value=${t.id} ?selected=${t.id===this.config?.device}>${t.name}</option>`)}
      </select>`}};gt.properties={hass:{attribute:!1},config:{state:!0}},gt.styles=k`
    select {
      width: 100%;
      height: 48px;
      font: inherit;
    }
    label {
      display: block;
      margin-bottom: 4px;
    }
  `;var ns={charging_stopped:["Charging stopped with the cable in","warn"],left_unlocked:["Left unlocked","warn"],left_open:["Left open","warn"],window_left_open:["Window left open","warn"],sterilisation_finished:["Sterilisation finished","ok"],battery_temp_finished:["Smart battery temp finished","ok"]},ss={waiting:["Starting","wait"],ok:["Normal","ok"],quiet_hours:["Quiet","off","Quiet hours"],rate_limited:["Held","warn","Waiting for the request limit"],error:["Failed","fault"],auth_required:["Sign in","fault","Reconfigure to sign in again"]};function it(i){return i.replace(/_/g," ").replace(/^./,e=>e.toUpperCase())}function is(i){return/fault|fail|anti_theft|intrusion|stopped|low|left_in/.test(i)?"fault":/finished|done|complete/.test(i)?"ok":"warn"}var Dt=class extends S{constructor(){super(...arguments);this.cardTitle="Activity";this.glyph="activity";this.events=[]}getCardSize(){return 10}disconnectedCallback(){super.disconnectedCallback(),this.stopHistory()}connectedCallback(){super.connectedCallback(),this.subscribedTo&&(this.subscribedTo=void 0,this.requestUpdate())}stopHistory(){this.unsubscribe?.then(t=>t()).catch(()=>{}),this.unsubscribe=void 0}updated(t){super.updated(t);let n=this.vehicle;if(!n||!this.hass)return;let s=["event.car_alert","event.gac_alert"].map(o=>n.id(o)).filter(Boolean),a=s.join(",");if(!s.length||a===this.subscribedTo)return;this.stopHistory(),this.subscribedTo=a,this.events=[];let r=new Date(Date.now()-48*36e5).toISOString();this.unsubscribe=this.hass.connection.subscribeMessage(o=>this.onHistory(o),{type:"history/stream",entity_ids:s,start_time:r,minimal_response:!1,no_attributes:!1,significant_changes_only:!1}),this.unsubscribe.catch(()=>{})}onHistory(t){let n=this.vehicle;if(!n)return;let s=n.id("event.car_alert"),a=[];for(let[o,l]of Object.entries(t.states??{}))for(let h of l){let u=new Date(h.s),c=h.a?.event_type;if(!(!c||Number.isNaN(u.getTime())))if(o===s){let[m,f]=ns[c]??[it(c),"warn"],v=h.a?.windows;a.push({at:u,title:m,kind:f,detail:v?.length?v.map(it).join(", "):"Car alert"})}else a.push({at:u,title:it(c),kind:is(c),detail:"GAC alert"})}let r=new Map([...this.events,...a].map(o=>[`${o.at.getTime()}|${o.title}`,o]));this.events=[...r.values()].sort((o,l)=>l.at.getTime()-o.at.getTime()).slice(0,20),this.requestUpdate()}commandStops(t){return(t?.attributes.recent_commands??[]).map(s=>{let a={ok:"ok",refused:"fault",unconfirmed:"warn",pending:"wait",quiet:"off"},r=t?.attributes.command===s.command&&t?.attributes.requested_at===s.requested_at,o=nt(s.state)==="refused"?r?st(t):s.failure_reason:void 0;return{at:new Date(s.requested_at),title:Pt(s.command),kind:a[nt(s.state)],detail:`${Se[s.state]??it(s.state)}${o?`: ${o}`:""}`}})}health(t){let n=x(t.get("binary_sensor.online")),s=t.get("sensor.data_freshness"),a=t.get("sensor.last_report"),r=t.get("sensor.polling_status"),[o,l,h]=w(r)?ss[r.state]??[it(r.state),"off"]:["Unknown","off"],u=r?.state==="error"?r.attributes.last_error_reason:h,c=s?.state,m=c==="recent"?"ok":c==="stale"||c==="clock_mismatch"?"warn":"off",f=c==="recent"?"Recent":c==="stale"?"Old":c==="clock_mismatch"?"Clock ahead":"Unknown";return d`<div class="sec">
      <div class="health">
        <button class="tap" @click=${()=>M(this,t.id("binary_sensor.online"))}>
          <span class="lab">Car</span>
          <span class="value">${y(n===!1?"fault":n?"ok":"off")}${n===!1?"Offline":n?"Online":"Unknown"}</span>
        </button>
        <button class="tap" @click=${()=>M(this,t.id("sensor.last_report"))}>
          <span class="lab">Report</span>
          <span class="value">${y(m)}${f}</span>
          <span class="when">${w(a)?et(this.hass,ne(a)):"none yet"}</span>
        </button>
        <button class="tap" @click=${()=>M(this,r?.entity_id)}>
          <span class="lab">Polling</span>
          <span class="value">${y(l)}${o}</span>
          ${u?d`<span class="when">${u}</span>`:p}
        </button>
      </div>
    </div>`}lastCommand(t){if(!w(t)||t.state==="idle")return p;let n=nt(t.state),s={ok:"ok",refused:"fault",unconfirmed:"warn",pending:"wait",quiet:"off"},a=n==="refused"?st(t):void 0,r=t.attributes.requested_at?new Date(t.attributes.requested_at):void 0;return d`<div class="sec last">
      <div class="head"><span class="lab">Last command</span>
        <span class="lab">${r?et(this.hass,r):""}</span></div>
      <button class="tap what" @click=${()=>M(this,t.entity_id)}>${Pt(t.attributes.command)}
      </button>
      <p class="note ${n}">${y(s[n])}<span>${Se[t.state]??it(t.state)}${a?`: ${a}`:""}</span></p>
    </div>`}timeline(t){let n=this.hass,s=new Date().toDateString();return d`<div class="sec">
      <div class="head"><span class="lab">Last 48 hours</span></div>
      ${t.length?d`<ol>${t.map(a=>d`<li>
        <time datetime=${a.at.toISOString()}>${a.at.toDateString()===s?J(n,a.at):et(n,a.at)}</time>
        <span class="route">${y(a.kind)}</span>
        <div class="stop"><div class="title">${a.title}</div>
          ${a.detail?d`<div class="detail">${a.detail}</div>`:p}</div>
      </li>`)}</ol>`:d`<p class="note">${y("off")}<span>No commands or alerts yet. Car alerts appear here
        when charging stops, or the car is left unlocked or open.</span></p>`}
    </div>`}readings(t){let n=[["sensor.aux_voltage","12V battery",1],["sensor.odometer","Odometer",0],["sensor.trip_consumption","Trip consumption",1],["sensor.pm25","Cabin PM2.5",0]].filter(([a])=>t.has(a)),s=t.get("sensor.last_gac_alert");return!n.length&&!s?p:d`<div class="sec readings">
      ${n.map(([a,r,o])=>{let l=t.get(a),h=_(l);return d`<button class="tap" @click=${()=>M(this,l?.entity_id)}><span>${r}</span>
          <span class="num">${h===void 0?"\u2013":N(this.hass,h,o)}<span class="unit">
            ${l?.attributes.unit_of_measurement??""}</span></span></button>`})}
      ${s?d`<button class="tap" @click=${()=>M(this,s.entity_id)}><span>Last GAC alert</span>
        <span class="alert"><span class="num" style="font-size:15px">${w(s)?s.attributes.title||it(s.state):"\u2013"}</span>${s.attributes.created?d`<span class="when">${et(this.hass,new Date(s.attributes.created))}</span>`:p}</span>
      </button>`:p}
    </div>`}body(t){let n=t.get("sensor.last_command"),s=[...this.commandStops(n),...this.events].filter(a=>!Number.isNaN(a.at.getTime())&&Date.now()-a.at.getTime()<48*36e5).sort((a,r)=>r.at.getTime()-a.at.getTime()).slice(0,8);return d`
      ${this.health(t)}
      ${this.lastCommand(n)}
      ${this.timeline(s)}
      ${this.readings(t)}
    `}};Dt.styles=[...S.styles,k`
    .health {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
    }
    .health > button {
      display: flex;
      flex-direction: column;
      gap: 4px;
      padding: 0 8px 0 12px;
      border-left: 1px solid var(--gac-hair);
      min-width: 0;
    }
    .health > button:first-child {
      border-left: 0;
      padding-left: 0;
    }
    .health .value {
      display: flex;
      align-items: center;
      gap: 6px;
      font: 600 17px/1.15 var(--gac-label);
      letter-spacing: 0.02em;
    }
    .health .when {
      font-size: 13px;
      color: var(--gac-muted);
    }
    .refresh {
      margin-top: 12px;
    }
    .last .what {
      font: 600 20px/1.2 var(--gac-label);
      letter-spacing: 0.02em;
    }
    .last .note {
      margin-top: 6px;
    }
    ol {
      list-style: none;
      margin: 4px 0 0;
      padding: 0;
    }
    li {
      display: grid;
      grid-template-columns: 64px 22px 1fr;
      gap: 0 10px;
      min-height: 46px;
    }
    li time {
      padding-top: 2px;
      font: 600 14px/1.2 var(--gac-label);
      font-variant-numeric: tabular-nums;
      color: var(--gac-muted);
      text-align: right;
    }
    .route {
      position: relative;
    }
    .route::before {
      content: "";
      position: absolute;
      left: 7px;
      width: 8px;
      top: 0;
      bottom: 0;
      background: var(--gac-minor);
      box-shadow: inset 1px 0 0 var(--gac-minor-case), inset -1px 0 0 var(--gac-minor-case);
    }
    li:first-child .route::before {
      top: 9px;
    }
    li:last-child .route::before {
      bottom: auto;
      height: 10px;
    }
    .route .mark {
      position: absolute;
      left: 3px;
      top: 2px;
      width: 16px;
      height: 16px;
      background: var(--gac-land);
    }
    .stop {
      padding-bottom: 12px;
      min-width: 0;
    }
    .stop .title {
      font-weight: 500;
      line-height: 1.3;
    }
    .stop .detail {
      font-size: 13px;
      color: var(--gac-muted);
      line-height: 1.35;
    }
    .readings {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 0 12px;
    }
    .readings > button {
      display: contents;
    }
    .readings span {
      padding: 8px 0;
      border-top: 1px solid var(--gac-hair);
    }
    .readings > button:first-child span {
      border-top: 0;
    }
    .readings .num {
      font-size: 18px;
      font-weight: 600;
      text-align: right;
    }
    .readings .alert {
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 2px;
      text-align: right;
    }
    .readings .alert span {
      padding: 0;
      border: 0;
    }
    .readings .alert .when {
      font-size: 13px;
      color: var(--gac-muted);
    }
    .readings > button:focus-visible span {
      outline: 2px solid var(--gac-mw);
      outline-offset: -2px;
    }
  `];var ie=[["mon","Mon",1],["tue","Tue",2],["wed","Wed",3],["thu","Thu",4],["fri","Fri",5],["sat","Sat",6],["sun","Sun",0]],kn={unrestricted:"Whenever plugged in",scheduled:"Scheduled charging",not_set:"Not set, won't charge",not_reported:"Not reported"};function ae(i){if(typeof i!="string")return;let e=/^(\d{1,2}):(\d{2})/.exec(i);return e?Number(e[1])*60+Number(e[2]):void 0}function as(i){return i===void 0?"\u2013\u2013:\u2013\u2013":`${String(Math.floor(i/60)).padStart(2,"0")}:${String(i%60).padStart(2,"0")}`}var Ut=class extends S{constructor(){super(...arguments);this.cardTitle="Charging";this.glyph="plug"}getCardSize(){return 12}statusBlock(t){if(!t.has("binary_sensor.plugged")&&!t.has("binary_sensor.charging"))return p;let n=x(t.get("binary_sensor.plugged")),s=x(t.get("binary_sensor.charging")),a=_(t.get("sensor.charge_power")),r=_(t.get("sensor.charge_time")),o=t.get("sensor.charge_schedule"),l=s?"ok":n?"info":"off",h=s?"Charging":n?"Plugged in":n===!1?"Not plugged in":"Plug unknown",u=r!==void 0&&s?ee(r):void 0,c=x(t.get("binary_sensor.charger_locked")),m=n&&c!==void 0?c?"Connector released":"Connector locked":void 0;return d`<div class="sec duo state">
      <button class="tap" @click=${()=>M(this,t.id("binary_sensor.charging"))}>
        <span class="lab">${y(l)}${h}</span>
        ${s&&a!==void 0?d`<span class="fig">${N(this.hass,a,a<10?1:0)}<small>&nbsp;kW</small></span>`:d`<span class="fig muted">${s?"\u2013":n?"Waiting":"\u2013"}</span>`}
        ${m?d`<span class="when">${m}</span>`:p}
      </button>
      <button class="tap" @click=${()=>M(this,t.id(s?"sensor.charge_time":"sensor.charge_schedule"))}>
        <span class="lab">${s?"Time left":"Schedule"}</span>
        ${s?d`<span class="fig">${u?this.splitDuration(u):"\u2013"}</span>`:d`<span class="fig" style="font-size:22px;margin-top:6px">${w(o)?kn[o.state]??o.state:"\u2013"}</span>`}
      </button>
    </div>`}splitDuration(t){return t.split(" ").map(n=>/^\d+$/.test(n)?d`${n}`:d`<small>&nbsp;${n}&nbsp;</small>`)}cells(t){if(!x(t.get("binary_sensor.charging")))return p;let s=[["Current","sensor.charge_current",0],["Voltage","sensor.charge_voltage",0]].filter(([,a])=>t.has(a));return s.length?d`<div class="sec cells" style="grid-template-columns:repeat(${s.length},1fr)">${s.map(([a,r,o])=>{let l=t.get(r),h=_(l);return d`<button class="tap" @click=${()=>M(this,l?.entity_id)}>
        <span class="lab">${a}</span>
        <span class="num">${h===void 0?"\u2013":N(this.hass,h,o)}<span
          class="unit">&nbsp;${l?.attributes.unit_of_measurement??""}</span></span></button>`})}</div>`:p}battery(t){let n=t.get("sensor.battery_temp"),s=t.get("switch.precondition_battery");if(!n&&!s)return p;let a=_(n),r=s?.state==="on";return d`<div class="sec">
      ${n?d`<button class="tap row" @click=${()=>M(this,n.entity_id)}>
        <div class="what"><div class="title">Battery temperature</div></div>
        <span class="num reading">${a===void 0?"\u2013":N(this.hass,a)}<span class="unit">&nbsp;${n.attributes.unit_of_measurement??"\xB0C"}</span></span></button>`:p}
      ${s?d`<div class="row"><div class="what"><div class="title">Smart battery temp</div>
        <div class="desc">Warms or cools the battery for charging or driving, for up to 1.5 hours.</div></div>
        <gac-switch label="Smart battery temp" .checked=${r} .pending=${t.pending(["battery-precondition"])}
          ?disabled=${!w(s)}
          @change=${()=>t.call("switch",r?"turn_off":"turn_on","switch.precondition_battery")}>
        </gac-switch></div>`:p}
      ${this.commandNote(t,["battery-precondition"])}
    </div>`}stopped(t){let n=t.get("event.car_alert");if(!w(n)||n.attributes.event_type!=="charging_stopped")return p;if(x(t.get("binary_sensor.charging"))||x(t.get("binary_sensor.plugged"))===!1)return p;let s=new Date(n.state);return Number.isNaN(s.getTime())||Date.now()-s.getTime()>6*36e5?p:d`<div class="sec"><p class="note">${y("warn")}<span>Charging stopped at ${J(this.hass,s)}
      with the cable still in.</span></p></div>`}sendTimes(t,n){let s=n[n.which];s!==void 0&&t.call("time","set_value",`time.charge_window_${n.which}`,{time:`${as(s)}:00`})}schedule(t){let n=t.get("sensor.charge_schedule"),s=t.get("time.charge_window_start"),a=t.get("time.charge_window_stop");if(!n&&!s)return p;let r=s!==void 0&&a!==void 0,o=ae(n?.attributes.reported_start),l=ae(n?.attributes.reported_stop),h=r?ae(s.state):o,u=r?ae(a.state):l,c=this.live?.start??h,m=this.live?.stop??u,f=t.get("switch.charge_window_until_soc"),v=f?.state==="on",B=n?.state==="unrestricted",at=new Date,ft=ie.map(([A])=>t.get(`switch.charge_window_${A}`)),re=on(this.hass),qt=[0,1,2,3,4,5,6].map(A=>ie.findIndex(([,,j])=>j===(re+A)%7)),bt=ie.filter((A,j)=>ft[j]?.state==="on").map(([,A])=>A),oe=bt.length===7?"Every day":bt.length?bt.join(", "):"One time",O=n?.attributes.reported_days,I=r&&n&&!B&&(h!==o||!v&&u!==l||O!==void 0&&O!=="Not reported"&&O.replace(/\s/g,"")!==oe.replace(/\s/g,"")),rt=t.pending(["charge-window","charge-schedule"]);return d`<div class="sec schedule">
      <div class="head"><span class="lab">${r?"Charging window":"Reported window"}</span>
        <span class="lab">${w(n)?kn[n.state]??"":""}</span></div>
      <div class="window" aria-live="polite">${B&&!r?"Any time":`${tt(this.hass,c)} \u2013 ${v?"charge limit":tt(this.hass,m)}`}</div>
      ${r?d`<gac-day-range .start=${h} .stop=${u} ?open-ended=${v}
          ?twelve=${ht(this.hass)}
          .now=${at.getHours()*60+at.getMinutes()} ?pending=${rt}
          start-label="Charging starts" stop-label="Charging stops"
          @input=${A=>{this.live={start:A.detail.start,stop:A.detail.stop},this.requestUpdate()}}
          @change=${A=>{this.live=void 0,this.sendTimes(t,A.detail)}}>
        </gac-day-range>`:un({width:this.inner,tone:B?"green":"road",start:B?0:h,stop:B?0:v?void 0:u,now:at.getHours()*60+at.getMinutes(),dashed:rt})}
      ${r?d`
        ${ft.some(A=>A)?d`<div class="days" role="group" aria-label="Repeat on">
          ${qt.map(A=>{let[j,,It]=ie[A],W=ft[A];if(!W)return p;let ot=W.state==="on";return d`<button aria-pressed=${ot?"true":"false"} aria-label=${Me(this.hass,It,"long")}
              @click=${()=>t.call("switch",ot?"turn_off":"turn_on",`switch.charge_window_${j}`)}>${Me(this.hass,It,"short")}</button>`})}
        </div>`:p}
        ${f?d`<div class="row">
          <div class="what"><div class="title">Stop at charge limit</div>
            <div class="desc">Stops at the car's own target level instead of a stop time.</div></div>
          <gac-switch .checked=${v} label="Stop at charge limit" @change=${()=>t.call("switch",v?"turn_off":"turn_on","switch.charge_window_until_soc")}></gac-switch>
        </div>`:p}
        ${I?d`<p class="note differs">${y("info")}<span>The car has ${tt(this.hass,o)} – ${tt(this.hass,l)}, ${O}. Send to
          change it.</span></p>`:p}
        ${t.has("button.send_charge_window")?d`<gac-action class="send" label=${rt?"Sending\u2026":"Send window to car"} icon="check" .state=${this.actionState(t,["charge-window","charge-schedule"])} @activate=${()=>t.call("button","press","button.send_charge_window")}>
          </gac-action>`:p}
      `:d`<p class="note">${y("off")}<span>${O??"Days not reported"}</span></p>`}
    </div>`}actions(t){let n=t.get("switch.charging"),s=[];if(t.has("button.charge_now")){let r=x(t.get("binary_sensor.charging"))===!0,o=this.actionState(t,["charge-now"]);s.push(d`<gac-action label=${r?"Charging":"Charge now"} icon="bolt"
        .state=${r&&o!=="pending"?"unavailable":o}
        hint=${r?"The car is charging.":"Charges whenever plugged in and switches the schedule off."}
        @activate=${()=>!r&&t.call("button","press","button.charge_now")}></gac-action>`)}if(t.has("button.charger_unlock")){let r=x(t.get("binary_sensor.plugged")),o=x(t.get("binary_sensor.charger_locked")),l=this.actionState(t,["charger-unlock"]),[h,u,c]=r===!1?["Release cable","No cable is plugged in.",!1]:o===!0?["Cable released","The connector is unlocked; the cable can be pulled out.",!1]:["Release cable","Unlocks the charging connector so the cable can be pulled out. This stops charging.",!0];s.push(d`<gac-action label=${h} icon="connector" .hold=${c}
        .state=${c||l==="pending"?l:"unavailable"} hint=${u}
        @activate=${()=>c&&t.call("button","press","button.charger_unlock")}></gac-action>`)}let a=n?d`<div class="row">
      <div class="what"><div class="title">Use charging schedule</div>
        <div class="desc">Off charges whenever the car is plugged in.</div></div>
      <gac-switch .checked=${n.state==="on"} label="Use charging schedule"
        .pending=${t.pending(["charge-resume","charge-now"])}
        @change=${()=>t.call("switch",n.state==="on"?"turn_off":"turn_on","switch.charging")}>
      </gac-switch></div>`:p;return!s.length&&!n?p:d`<div class="sec">
      ${a}
      ${s.length?d`<div class="grid2" style="margin-top:${n?8:0}px">${s}</div>`:p}
      ${this.commandNote(t,["charge-now","charge-resume","charge-window","charge-schedule","charger-unlock"])}
    </div>`}body(t){return d`
      ${this.statusBlock(t)}
      ${t.has("sensor.soc")?d`<div class="sec">${Ee(this,t,this.inner,"chg")}</div>`:p}
      ${this.stopped(t)}
      ${this.cells(t)}
      ${this.battery(t)}
      ${this.schedule(t)}
      ${this.actions(t)}
    `}};Ut.styles=[...S.styles,k`
    .state .lab {
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .state .fig {
      margin-top: 6px;
    }
    .state .fig small + small {
      margin-left: 0;
    }
    .battery .fig {
      font-size: 32px;
    }
    .cells {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
    }
    .cells > button {
      display: flex;
      flex-direction: column;
      gap: 2px;
      padding-left: 12px;
      border-left: 1px solid var(--gac-hair);
    }
    .cells > button:first-child {
      padding-left: 0;
      border-left: 0;
    }
    .state .when {
      display: block;
      margin-top: 6px;
      font-size: 13px;
      color: var(--gac-muted);
    }
    .reading {
      font-size: 22px;
      font-weight: 600;
    }
    button.row {
      width: 100%;
    }
    .cells .num {
      font-size: 22px;
      font-weight: 600;
    }
    .window {
      font: 600 30px/1 var(--gac-label);
      font-variant-numeric: tabular-nums;
      letter-spacing: 0.01em;
      margin: 2px 0 6px;
    }
    .schedule .head .lab:last-child {
      color: var(--gac-ink);
    }
    .days {
      display: grid;
      grid-template-columns: repeat(7, 1fr);
      gap: 4px;
      margin-top: 10px;
    }
    .days button {
      height: 44px;
      padding: 0;
      font: 600 14px/1 var(--gac-label);
      letter-spacing: 0.04em;
      color: var(--gac-muted);
      background: none;
      border: 1px solid var(--gac-hair);
      border-radius: 2px;
      cursor: pointer;
    }
    .days button[aria-pressed="true"] {
      background: var(--gac-mw);
      border-color: var(--gac-mw-case);
      color: var(--gac-mw-ink);
    }
    .days button:focus-visible {
      outline: 2px solid var(--gac-mw);
      outline-offset: 1px;
    }
    .days button:disabled {
      cursor: wait;
      opacity: 0.6;
    }
    .send {
      margin-top: 10px;
    }
    .differs {
      margin-top: 10px;
    }
    .row gac-switch {
      margin-right: -6px;
    }
  `];var rs={off:"Off",heat_cool:"On",fan_only:"Fan only",heat:"Heat",cool:"Cool",auto:"Auto",dry:"Dry"},_n={heating:["Max heat","Starts the A/C in Auto at the highest target."],cooling:["Max cool","Starts the A/C in Auto at the lowest target."]};function mt(i){return i.replace(/_/g," ").replace(/^./,e=>e.toUpperCase())}var os=[["switch.recirculation","Recirculation","On recirculates cabin air; off draws fresh air. Changes while the A/C runs.","aircon"],["switch.sterilisation","Sterilisation","Hot-air cabin clean for 30 minutes. Car off, locked, windows shut.","antivirus"],["switch.ventilation","Ventilation","Lowers the windows 2\u20133 cm and runs fresh air.","ventilate"]],Bt=class extends S{constructor(){super(...arguments);this.cardTitle="Climate";this.glyph="climate"}getCardSize(){return 12}temperatures(t,n){let s=t.get("sensor.cabin_temp");if(!s&&!n)return p;let a=_(s)??(n?Number(n.attributes.current_temperature):void 0),r=_(t.get("sensor.outside_temp")),o=n?.attributes.temperature,l=Number(n?.attributes.min_temp??16),h=Number(n?.attributes.max_temp??32),u=Number(n?.attributes.target_temp_step??.5),c=w(n)&&n.state!=="off",m=s?.attributes.unit_of_measurement??"\xB0C";return d`<div class="sec">
      <div class="duo temps">
        <button class="tap" @click=${()=>M(this,s?.entity_id??n?.entity_id)}>
          <span class="lab">Cabin</span>
          <span class="fig">${a!==void 0&&Number.isFinite(a)?N(this.hass,a,0):"\u2013"}<small>&nbsp;${m}</small></span>
        </button>
        ${n?d`<div><span class="lab">Target</span>
          <gac-stepper .value=${o} .min=${l} .max=${h} .step=${u} .digits=${u<1?1:0}
            unit=${m} label="target temperature" .pending=${t.pending(["aircon-temperature"])}
            ?disabled=${!w(n)}
            @change=${f=>t.call("climate","set_temperature","climate.climate",{temperature:f.detail.value})}></gac-stepper></div>`:p}
      </div>
      ${n?gn({width:this.inner,min:l,max:h,cabin:a!==void 0&&Number.isFinite(a)?a:void 0,target:o,outside:r,running:c}):p}
    </div>`}power(t,n){let s=t.get("switch.climate_power"),a=t.get("number.ac_minutes");if(!n&&!s)return p;let r=t.pending(["aircon"]),o=n?.attributes.hvac_modes??[],l=n?.attributes.preset_modes??[],h=_(a);return d`<div class="sec stack">
      <div class="head"><span class="lab">A/C</span></div>
      ${n&&o.length?d`<gac-segments label="A/C mode" .value=${n.state} .pending=${r}
        ?disabled=${!w(n)} .options=${o.map(u=>({value:u,label:rs[u]??mt(u)}))}
        @change=${u=>t.call("climate","set_hvac_mode","climate.climate",{hvac_mode:u.detail.value})}></gac-segments>`:s?d`<div class="row"><div class="what"><div class="title">A/C</div></div>
          <gac-switch label="A/C" .checked=${s.state==="on"} .pending=${r}
            @change=${()=>t.call("switch",s.state==="on"?"turn_off":"turn_on","switch.climate_power")}>
          </gac-switch></div>`:p}
      ${l.length?d`<div class="presets">${l.map(u=>d`<gac-action
        label=${_n[u]?.[0]??mt(u)} hint=${_n[u]?.[1]??""}
        icon=${/heat/i.test(u)?"sterilise":"climate"}
        .state=${n?.attributes.preset_mode===u?"on":r?"pending":"idle"}
        @activate=${()=>t.call("climate","set_preset_mode","climate.climate",{preset_mode:u})}>
        </gac-action>`)}</div>`:p}
      ${a?d`<div class="field"><span class="lab">Run time per remote start</span>
        <gac-stepper .value=${h} .min=${Number(a.attributes.min??1)}
          .max=${Number(a.attributes.max??60)} .step=${Number(a.attributes.step??1)}
          unit=${a.attributes.unit_of_measurement??"min"} label="run time"
          @change=${u=>t.call("number","set_value","number.ac_minutes",{value:u.detail.value})}></gac-stepper></div>`:p}
    </div>`}airflow(t,n){if(!n)return p;let s=n.attributes.fan_modes??[],a=n.attributes.swing_modes??[];if(!s.length&&!a.length)return p;let r=t.pending(["aircon"]);return d`<div class="sec">
      ${s.length?d`<div class="field"><span class="lab">Fan</span>
        <gac-stops label="Fan speed" .value=${n.attributes.fan_mode} .pending=${r}
          .options=${s.map(o=>({value:o,label:mt(o)}))}
          @change=${o=>t.call("climate","set_fan_mode","climate.climate",{fan_mode:o.detail.value})}></gac-stops></div>`:p}
      ${a.length?d`<div class="field"><span class="lab">Airflow</span>
        <gac-choice label="Airflow" .value=${n.attributes.swing_mode} .pending=${r}
          .options=${a.map(o=>({value:o,label:an(this.hass,n,"swing_mode",o,mt(o))}))}
          @change=${o=>t.call("climate","set_swing_mode","climate.climate",{swing_mode:o.detail.value})}></gac-choice></div>`:p}
    </div>`}seats(t){let n=[["select.seat_1_ventilation","Driver seat","seat-1"],["select.seat_2_ventilation","Passenger seat","seat-2"]].filter(([a])=>t.has(a)),s=t.get("switch.steering_heat");return!n.length&&!s?p:d`<div class="sec">
      ${n.map(([a,r,o])=>{let l=t.get(a);return d`<div class="field"><span class="lab">${r} ventilation</span>
          <gac-segments label="${r} ventilation" .value=${l.state} .pending=${t.pending([o])}
            ?disabled=${!w(l)}
            .options=${(l.attributes.options??[]).map(h=>({value:h,label:mt(h)}))}
            @change=${h=>t.call("select","select_option",a,{option:h.detail.value})}>
          </gac-segments></div>`})}
      ${s?d`<div class="row" style="margin-top:${n.length?8:0}px">
        <div class="what"><div class="title">Steering wheel heat</div></div>
        <gac-switch label="Steering wheel heat" .checked=${s.state==="on"} .pending=${t.pending(["steering"])}
          @change=${()=>t.call("switch",s.state==="on"?"turn_off":"turn_on","switch.steering_heat")}>
        </gac-switch></div>`:p}
    </div>`}extras(t){let n=os.filter(([s])=>t.has(s));return n.length?d`<div class="sec">${n.map(([s,a,r,o])=>{let l=t.get(s),h=l.state==="on";return d`<div class="row"><div class="what"><div class="title">${a}</div>
        <div class="desc">${r}</div></div>
        <gac-switch label=${a} .checked=${h} .pending=${t.pending([o])} ?disabled=${!w(l)}
          @change=${()=>t.call("switch",h?"turn_off":"turn_on",s)}></gac-switch></div>`})}</div>`:p}fridge(t){let n=t.get("switch.fridge"),s=t.get("select.fridge_mode"),a=t.get("number.fridge_temperature");if(!n&&!s)return p;let r=t.pending(["fridge"]),o=_(t.get("sensor.fridge_time_left"));return d`<div class="sec">
      <div class="row"><div class="what"><div class="title">Fridge</div>
        ${o!==void 0?d`<div class="desc">${ee(o)} left</div>`:p}</div>
        ${n?d`<gac-switch label="Fridge" .checked=${n.state==="on"} .pending=${r}
          @change=${()=>t.call("switch",n.state==="on"?"turn_off":"turn_on","switch.fridge")}>
        </gac-switch>`:p}</div>
      ${s?d`<gac-segments label="Fridge mode" .value=${s.state} .pending=${r}
        .options=${(s.attributes.options??[]).map(l=>({value:l,label:mt(l)}))}
        @change=${l=>t.call("select","select_option","select.fridge_mode",{option:l.detail.value})}></gac-segments>`:p}
      ${a?d`<div class="field" style="margin-top:8px"><gac-stepper .value=${_(a)}
        .min=${Number(a.attributes.min??0)} .max=${Number(a.attributes.max??20)}
        .step=${Number(a.attributes.step??1)} unit=${a.attributes.unit_of_measurement??"\xB0C"}
        label="fridge temperature" .pending=${r}
        @change=${l=>t.call("number","set_value","number.fridge_temperature",{value:l.detail.value})}></gac-stepper></div>`:p}
    </div>`}body(t){let n=t.get("climate.climate"),s=this.commandNote(t,["aircon","seat-","steering","antivirus","ventilate","fridge"]),a=[this.temperatures(t,n),this.power(t,n),this.airflow(t,n),this.seats(t),this.extras(t),this.fridge(t)].filter(r=>r!==p);return a.length?d`${a}${s!==p?d`<div class="sec">${s}</div>`:p}`:d`<div class="empty"><strong>No climate controls</strong>This car reports no cabin temperature or
        climate controls to Home Assistant.</div>`}};Bt.styles=[...S.styles,k`
    .temps {
      align-items: end;
      margin-bottom: 6px;
    }
    .temps .lab {
      display: block;
      margin-bottom: 6px;
    }
    gac-segments + .presets,
    .stack > * + * {
      margin-top: 8px;
    }
    .presets {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }
    .field + .field {
      margin-top: 12px;
    }
    .field .lab {
      display: block;
      margin-bottom: 6px;
    }
    .row gac-switch {
      margin-right: -6px;
    }
    @container (max-width: 380px) {
      .temps {
        grid-template-columns: 1fr;
        gap: 10px;
      }
      .temps > * + * {
        border-left: 0;
        padding-left: 0;
      }
    }
  `];function Mn(i,e,t){return`${Math.abs(i).toFixed(5)}\xB0 ${i>=0?e:t}`}var Ft=class extends S{constructor(){super(...arguments);this.cardTitle="Location";this.glyph="pin";this.loading=!1}getCardSize(){return 9}coordinates(t){if(!w(t))return;let n=Number(t.attributes.latitude),s=Number(t.attributes.longitude);return Number.isFinite(n)&&Number.isFinite(s)&&t.attributes.latitude!==null?[n,s]:void 0}updated(t){super.updated(t);let n=this.vehicle,s=n?.id("device_tracker.location");if(!(s&&this.coordinates(n?.get("device_tracker.location")))||!s)return;let r=this.hass?.themes?.darkMode===!0;if(this.map&&this.mapFor===s&&this.mapDark===r){this.map.hass=this.hass,this.sizeCar(this.map);return}this.loadMap(s,r)}async loadMap(t,n){if(this.loading)return;let s=window.loadCardHelpers;if(s){this.loading=!0;try{let r=await(await s()).createCardElement({type:"map",entities:[{entity:t,label_mode:"icon"}],default_zoom:15,aspect_ratio:"16:11",theme_mode:n?"dark":"light",hours_to_show:0});r.hass=this.hass,this.map=r,this.sizeCar(r),this.mapFor=t,this.mapDark=n,this.requestUpdate()}finally{this.loading=!1}}}async sizeCar(t){await t.updateComplete,t.shadowRoot?.querySelector("ha-map")?.style.setProperty("--mdc-icon-size","30px")}blankTile(){return d`<svg class="off-map" viewBox="0 0 320 180" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <rect width="320" height="180" fill="var(--gac-land)"/>
      <path d="M0 0H320M0 60H320M0 120H320M80 0V180M160 0V180M240 0V180" stroke="var(--gac-hair)"/>
      <path d="M-10 132C60 120 110 70 180 74S280 40 330 30" fill="none" stroke="var(--gac-minor-case)"
        stroke-width="9"/>
      <path d="M-10 132C60 120 110 70 180 74S280 40 330 30" fill="none" stroke="var(--gac-minor)" stroke-width="6"/>
      <circle cx="160" cy="90" r="22" fill="none" stroke="var(--gac-ink)" stroke-width="1.5" stroke-dasharray="4 4"/>
      <path d="M154 90h12M160 84v12" stroke="var(--gac-ink)" stroke-width="1.5"/>
    </svg>`}trackingRows(t){let n=[["switch.track_parked","When parked","Shows where the car is while it is switched off."],["switch.track_moving","When switched on","Follows the car while it is switched on."]].filter(([s])=>t.has(s));return n.length?d`<div class="sec"><div class="head"><span class="lab">Track location</span></div>
      ${n.map(([s,a,r])=>{let o=t.get(s)?.state==="on";return d`<div class="row"><div class="what"><div class="title">${a}</div>
          <div class="desc">${r}</div></div>
          <gac-switch label="Track location ${a.toLowerCase()}" .checked=${o}
            @change=${()=>t.call("switch",o?"turn_off":"turn_on",s)}></gac-switch></div>`})}</div>`:p}body(t){let n=t.get("device_tracker.location"),s=this.coordinates(n),a=x(t.get("binary_sensor.vehicle_power")),r=t.get("switch.track_parked")?.state==="on",o=t.get("switch.track_moving")?.state==="on";if(!s){let c=a===!1&&!r&&o||a===!0&&!o&&r;return d`<div class="map">${this.blankTile()}</div>
        <div class="empty"><strong>${c?"Hidden for now":"Location is off"}</strong>
          ${c?a?"Tracking is on only while the car is parked.":"Tracking is on only while the car is switched on.":n?"Turn on tracking below to see the car on the map. Positions already recorded stay in Home Assistant's history.":"This car has no location entity. Turn on tracking below."}
        </div>
        ${this.trackingRows(t)}`}let l=n.state,h=l==="home"?"Home":l==="not_home"?"Away from home":l,u=!window.loadCardHelpers;return d`
      <div class="map">${this.map??(u?this.demoMap():p)}</div>
      <div class="sec">
        <button class="tap" @click=${()=>M(this,n.entity_id)}>
          <div class="place">${h}</div>
          <div class="coords">${Mn(s[0],"N","S")} · ${Mn(s[1],"E","W")}</div>
        </button>
        <p class="note" style="margin-top:10px">${y(a?"info":"ok")}<span>${a?"Switched on":"Parked"}${n.attributes.gps_accuracy?` \xB7 within ${Math.round(n.attributes.gps_accuracy)} m`:""}</span></p>
      </div>
      ${this.trackingRows(t)}`}demoMap(){return d`<svg class="off-map" style="height:220px" viewBox="0 0 320 220" preserveAspectRatio="xMidYMid slice"
      role="img" aria-label="Demo map">
      <rect width="320" height="220" fill="var(--gac-land)"/>
      <path d="M250 0C230 50 262 90 236 140S250 200 240 220H320V0Z" fill="var(--gac-water)"/>
      <path d="M0 150C70 140 120 120 170 120S260 96 330 60" fill="none" stroke="var(--gac-mw-case)" stroke-width="12"/>
      <path d="M0 150C70 140 120 120 170 120S260 96 330 60" fill="none" stroke="var(--gac-mw)" stroke-width="8"/>
      <path d="M96 -10C104 60 118 120 136 230" fill="none" stroke="var(--gac-red-case)" stroke-width="9"/>
      <path d="M96 -10C104 60 118 120 136 230" fill="none" stroke="var(--gac-red)" stroke-width="6"/>
      <path d="M-10 60H200M30 -10V230M190 40V230" fill="none" stroke="var(--gac-minor-case)" stroke-width="6"/>
      <path d="M-10 60H200M30 -10V230M190 40V230" fill="none" stroke="var(--gac-minor)" stroke-width="4"/>
      <g transform="translate(136 72) scale(1.15)" fill="var(--gac-ink)">
        <path d="M5,11L6.5,6.5H17.5L19,11M17.5,16A1.5,1.5 0 0,1 16,14.5A1.5,1.5 0 0,1 17.5,13A1.5,1.5 0 0,1 19,14.5A1.5,1.5 0 0,1 17.5,16M6.5,16A1.5,1.5 0 0,1 5,14.5A1.5,1.5 0 0,1 6.5,13A1.5,1.5 0 0,1 8,14.5A1.5,1.5 0 0,1 6.5,16M18.92,6C18.72,5.42 18.16,5 17.5,5H6.5C5.84,5 5.28,5.42 5.08,6L3,12V20A1,1 0 0,0 4,21H5A1,1 0 0,0 6,20V19H18V20A1,1 0 0,0 19,21H20A1,1 0 0,0 21,20V12L18.92,6Z"/>
      </g>
    </svg><span class="demo-tag">Demo map</span>`}};Ft.styles=[...S.styles,k`
    .map {
      position: relative;
      border-bottom: 1px solid var(--gac-hair);
      --ha-card-border-radius: 0;
      --ha-card-border-width: 0;
      --ha-card-box-shadow: none;
      /* One car on the map needs no name bubble: the marker is just the car, in the theme's text
         colour (light on a dark theme, dark on a light one), with a shadow to lift it off the map. */
      --ha-marker-background: transparent;
      --ha-marker-border-width: 0;
      --ha-marker-color: transparent;
      --ha-marker-size: 40px;
      --ha-cluster-shadow: drop-shadow(0 0 2px var(--gac-land)) drop-shadow(0 1px 3px rgba(0, 0, 0, 0.35));
      min-height: 220px;
      background: var(--gac-water);
    }
    .map > * {
      display: block;
    }
    .place {
      font: 700 28px/1.05 var(--gac-label);
      letter-spacing: 0.03em;
      text-transform: uppercase;
    }
    .coords {
      margin-top: 6px;
      font: 500 16px/1.2 var(--gac-label);
      font-variant-numeric: tabular-nums;
      letter-spacing: 0.04em;
      color: var(--gac-muted);
    }
    .demo-tag {
      position: absolute;
      left: 10px;
      bottom: 8px;
      font: 600 12px/1 var(--gac-label);
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--gac-muted);
      background: var(--gac-land);
      padding: 3px 6px;
    }
    .off-map {
      display: block;
      width: 100%;
      height: 180px;
    }
    .row gac-switch {
      margin-right: -6px;
    }
  `];var ls=[["Remote permissions",[["switch.allow_remote_unlock","Remote unlocking","Lets the Vehicle card and the Doors lock unlock the car.",!0],["switch.allow_charger_unlock","Release charging cable","Shows Release cable on the Charging card. It stops charging.",!0],["switch.allow_vehicle_shutdown","Remote shutdown","Shows Turn vehicle off below.",!0]]],["Location",[["switch.track_parked","Track when parked","Shows the position while the car is switched off."],["switch.track_moving","Track when switched on","Follows the car while it is switched on."]]],["Alerts and push",[["switch.allow_account_alerts","GAC account alerts","Refreshes GAC's alert list every 10 minutes. Signing in with the official app prevents GAC alerts from appearing here."],["switch.allow_plaintext_push","Unencrypted push","Faster command results through GAC's push feed, whose login and topic names travel unencrypted.",!0]]]],ds=[{value:"automatic",label:"Auto"},{value:"always",label:"Always"},{value:"omit",label:"Omit"}];function cs(i){return i<60?`${i} s`:i%60===0?`${i/60} min`:`${Math.floor(i/60)} min ${i%60} s`}var zt=class extends S{constructor(){super(...arguments);this.cardTitle="Settings";this.glyph="settings";this.entitiesOpen=!1;this.filter=""}getCardSize(){return 14}toggles(t,n,s){let a=s.filter(([r])=>t.has(r));return a.length?d`<div class="sec"><div class="head"><span class="lab">${n}</span></div>
      ${a.map(([r,o,l,h])=>{let u=t.get(r),c=u.state==="on";return d`<div class="row"><div class="what"><div class="title">${o}</div><div class="desc">${l}</div>
          </div><gac-switch label=${o} .checked=${c} ?hold-on=${h===!0} ?disabled=${!w(u)}
            @change=${()=>t.call("switch",c?"turn_off":"turn_on",r)}></gac-switch></div>`})}</div>`:p}polling(t){let n=t.get("number.polling_interval"),s=t.get("switch.quiet_hours"),a=t.get("time.quiet_hours_start"),r=t.get("time.quiet_hours_end");if(!n&&!s)return p;let o=s?.state==="on",l=(f=a)=>{let v=w(f)?/^(\d{1,2}):(\d{2})/.exec(f.state):null;return v?Number(v[1])*60+Number(v[2]):void 0},h=f=>f===void 0?"\u2013\u2013:\u2013\u2013":`${String(Math.floor(f/60)).padStart(2,"0")}:${String(f%60).padStart(2,"0")}`,u=f=>tt(this.hass,f),c=this.quietLive?.start??l(a),m=this.quietLive?.stop??l(r);return d`<div class="sec"><div class="head"><span class="lab">Polling</span></div>
      ${n?d`<div class="field"><div class="title" style="margin-bottom:6px">Read the car every</div>
        <gac-stepper .value=${_(n)} .min=${Number(n.attributes.min??60)}
          .max=${Number(n.attributes.max??3600)} .step=${60} .format=${cs} label="poll interval"
          @change=${f=>t.call("number","set_value","number.polling_interval",{value:f.detail.value})}></gac-stepper></div>`:p}
      ${s?d`<div class="row" style="margin-top:4px"><div class="what"><div class="title">Quiet hours</div>
        <div class="desc">No polling ${a&&r?`from ${u(c)} until ${u(m)}`:"at night"}.</div>
        </div>
        <gac-switch label="Quiet hours" .checked=${o}
          @change=${()=>t.call("switch",o?"turn_off":"turn_on","switch.quiet_hours")}></gac-switch>
      </div>`:p}
      ${a&&r?d`<gac-day-range .start=${l(a)} .stop=${l(r)} ?disabled=${!o}
        ?twelve=${ht(this.hass)}
        start-label="Quiet hours start" stop-label="Quiet hours end"
        @input=${f=>{this.quietLive={start:f.detail.start,stop:f.detail.stop},this.requestUpdate()}}
        @change=${f=>{this.quietLive=void 0;let v=f.detail.which;t.call("time","set_value",`time.quiet_hours_${v==="start"?"start":"end"}`,{time:`${h(f.detail[v])}:00`})}}></gac-day-range>`:p}
    </div>`}vehicleActions(t){let n=t.has("button.refresh_capabilities"),s=t.has("button.vehicle_power_off");return!n&&!s?p:d`<div class="sec"><div class="head"><span class="lab">Vehicle</span></div>
      <div class="grid2">
        ${n?d`<gac-action label="Re-read equipment" icon="refresh"
          hint="Reads the car's capability list again, for example after a software update."
          .state=${this.actionState(t,["capabilities"])}
          @activate=${()=>t.call("button","press","button.refresh_capabilities")}></gac-action>`:p}
        ${s?d`<gac-action label="Turn car off" icon="power" hold hint="Switches the car off."
          .state=${this.actionState(t,["vehicle-power-off"])}
          @activate=${()=>t.call("button","press","button.vehicle_power_off")}></gac-action>`:p}
      </div>
      ${this.commandNote(t,["vehicle-power-off"])}
    </div>`}entities(t){let n=t.get("sensor.entity_choices");if(!n)return p;let s=n.attributes.entities??{},a=new Set(n.attributes.always_show??[]),r=new Set(n.attributes.omit??[]),o=this.filter.trim().toLowerCase(),l=Object.entries(s).filter(([h,u])=>!o||u.toLowerCase().includes(o)||h.includes(o));return d`<div class="sec">
      <details ?open=${this.entitiesOpen} @toggle=${h=>{this.entitiesOpen=h.target.open,this.requestUpdate()}}>
        <summary><span class="lab">Entity choices</span><span class="muted" style="font-size:14px">${w(n)&&Number(n.state)>0?`${n.state} set`:"all automatic"}</span>${P("chevron")}</summary>
        ${this.entitiesOpen?d`
          <p class="note">${y("info")}<span>Auto follows the car's capability list. Each change reloads GAC
            Connect for a few seconds.</span></p>
          <input type="search" placeholder="Filter entities" aria-label="Filter entities" .value=${this.filter}
            @input=${h=>{this.filter=h.target.value,this.requestUpdate()}}>
          ${l.map(([h,u])=>d`<div class="entity"><div class="title">${u}</div>
            <gac-segments label=${u} .options=${ds}
              .value=${a.has(h)?"always":r.has(h)?"omit":"automatic"}
              @change=${c=>t.action("set_entity_visibility",{entity:h,visibility:c.detail.value})}>
            </gac-segments></div>`)}`:p}
      </details>
    </div>`}body(t){return d`
      ${ls.map(([n,s])=>this.toggles(t,n,s))}
      ${this.polling(t)}
      ${this.vehicleActions(t)}
      ${this.entities(t)}
      <div class="sec"><button class="link" @click=${()=>rn(this,`/config/devices/device/${t.deviceId}`)}>Device page and diagnostics${P("chevron")}</button></div>
    `}};zt.styles=[...S.styles,k`
    .row gac-switch {
      margin-right: -6px;
    }
    input {
      height: 44px;
      width: 100%;
      padding: 0 10px;
      color: var(--gac-ink);
      background: var(--gac-paper);
      border: 1px solid var(--gac-edge);
      border-radius: 2px;
    }
    input[type="search"] {
      font: 400 15px/1 var(--gac-text);
      margin-bottom: 8px;
    }
    input:focus-visible,
    summary:focus-visible,
    .link:focus-visible {
      outline: 2px solid var(--gac-mw);
      outline-offset: 1px;
    }
    input:disabled {
      color: var(--gac-muted);
      border-style: dotted;
    }
    .field + .field,
    .grid2 {
      margin-top: 8px;
    }
    .field .lab {
      display: block;
      margin-bottom: 6px;
    }
    summary {
      display: flex;
      align-items: center;
      gap: 8px;
      min-height: 44px;
      cursor: pointer;
      list-style: none;
    }
    summary::-webkit-details-marker {
      display: none;
    }
    summary svg,
    .link svg {
      width: 18px;
      height: 18px;
      margin-left: auto;
      transition: transform 150ms ease-out;
    }
    details[open] summary svg {
      transform: rotate(90deg);
    }
    .entity {
      padding: 8px 0;
      border-top: 1px solid var(--gac-hair);
    }
    .entity .title {
      font-size: 14px;
      margin-bottom: 6px;
    }
    .link {
      display: flex;
      align-items: center;
      gap: 8px;
      width: 100%;
      min-height: 44px;
      padding: 0;
      background: none;
      border: 0;
      color: var(--gac-ink);
      font: 600 15px/1 var(--gac-label);
      letter-spacing: 0.08em;
      text-transform: uppercase;
      cursor: pointer;
    }
  `];var ps=[["gac-vehicle-card",Vt,"GAC Vehicle","Battery, range, what is open on the car, and quick actions."],["gac-climate-card",Bt,"GAC Climate","Cabin temperature, A/C, fan, seats and comfort features."],["gac-charging-card",Ut,"GAC Charging","Charging state, Charge now and the charging window."],["gac-location-card",Ft,"GAC Location","Where the car is, and location tracking."],["gac-activity-card",Dt,"GAC Activity","Connection, commands and alerts over the last two days."],["gac-settings-card",zt,"GAC Settings","Permissions, tracking, polling and entity choices."]];fn(import.meta.url);Ze();customElements.get("gac-card-editor")||customElements.define("gac-card-editor",gt);var hs=window.customCards??=[];for(let[i,e,t,n]of ps)customElements.get(i)||(customElements.define(i,e),hs.push({type:i,name:t,description:n,preview:!0,documentationURL:"https://github.com/wattferry/ha-gac-connect#dashboard-cards"}));
/*! Bundled license information:

@lit/reactive-element/css-tag.js:
  (**
   * @license
   * Copyright 2019 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

@lit/reactive-element/reactive-element.js:
lit-html/lit-html.js:
lit-element/lit-element.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

lit-html/is-server.js:
  (**
   * @license
   * Copyright 2022 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)
*/
