/* Cruscotto territoriale della dashboard MACTEE (modalita' "Cruscotto" del calcolo).
   Stesso calcolo e stessa grafica di MACTEE_Cruscotto_DB.html, ma con i dati del database della
   dashboard (GET /api/cruscotto/dati) al posto del DB WTCED e dell'export MACTEE:
   impianti con coordinate e anno di dismissione (e loro fonti), masse per macrocomponente,
   composizioni, trasformazioni dei processi, prodotti.
   Generato da build_cz.py a partire da cruscotto_template.html; codice isolato in una funzione
   per non toccare i nomi globali della dashboard. Espone solo window.Cruscotto. */
(function(){
"use strict";
const $=s=>document.querySelector(s);
const esc=s=>String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
const TECHS=[['FOTOVOLTAICO','Fotovoltaico','var(--pv)','#E0A83E'],['EOLICO','Eolico','var(--eol)','#2E8B8B'],['BESS','BESS','var(--bess)','#6E5AA8']];
const TCOL=Object.fromEntries(TECHS.map(t=>[t[0],t[3]])), TLAB=Object.fromEntries(TECHS.map(t=>[t[0],t[1]]));
const SCN=['minimo','medio','massimo'];
const COLS=['recupero_pct_min','recupero_pct','recupero_pct_max'];
const ROTTAMI=[[/^rottame_Cu/i,'Cu'],[/^rottame_Al/i,'Al'],[/^rottame_acciaio/i,'Fe']];
const PROXY=[[/COPPER|(^|[-_])CU($|[-_])/i,{Cu:100}],[/ALUMIN/i,{Al:100}],[/STEEL|CAST_IRON|(^|[-_])IRON($|[-_])/i,{Fe:98}]];
const MASSE_ATOMICHE={Li:6.94,Fe:55.845,Co:58.933,Ni:58.693,Mn:54.938,Cu:63.546,Al:26.982};
const ELNOMI={Ag:'Argento',Al:'Alluminio',As:'Arsenico',B:'Boro',Ba:'Bario',Be:'Berillio',Bi:'Bismuto',C:'Carbonio',Ca:'Calcio',Cd:'Cadmio',Ce:'Cerio',Cl:'Cloro',Co:'Cobalto',Cr:'Cromo',Cu:'Rame',Dy:'Disprosio',F:'Fluoro',Fe:'Ferro',Ga:'Gallio',Ge:'Germanio',H:'Idrogeno',In:'Indio',K:'Potassio',La:'Lantanio',Li:'Litio',Mg:'Magnesio',Mn:'Manganese',Mo:'Molibdeno',N:'Azoto',Na:'Sodio',Nb:'Niobio',Nd:'Neodimio',Ni:'Nichel',O:'Ossigeno',P:'Fosforo',Pb:'Piombo',Pr:'Praseodimio',S:'Zolfo',Sb:'Antimonio',Se:'Selenio',Si:'Silicio',Sn:'Stagno',Sr:'Stronzio',Tb:'Terbio',Te:'Tellurio',Ti:'Titanio',V:'Vanadio',W:'Tungsteno',Zn:'Zinco',Zr:'Zirconio'};

const S={sc:1, techs:new Set(TECHS.map(t=>t[0])), el:'Cu', y0:null, y1:null, sel:{mode:'all',provs:new Set(),circle:null,rect:null},
  proxy:true, cum:false, size:'C', site:null, sort:['C',-1]};
let DATA=null, PM=new Map(), ENG=null, SITES=[]; const RES=new Map();
const t1=new Intl.NumberFormat('it-IT',{maximumFractionDigits:1}), t0=new Intl.NumberFormat('it-IT',{maximumFractionDigits:0}), t2=new Intl.NumberFormat('it-IT',{maximumFractionDigits:2});
const T=kg=>{const t=kg/1000; return !t?'0':Math.abs(t)>=100?t0.format(t):Math.abs(t)>=1?t1.format(t):Math.abs(t)>=0.01?t2.format(t):'<0,01';};
const EUR=v=>v>=1e9?t1.format(v/1e9)+' Mld €':v>=1e6?t1.format(v/1e6)+' M€':v>=1e3?t0.format(v/1e3)+' k€':t0.format(v)+' €';
const pct=(a,b)=>b>0?t1.format(a/b*100)+' %':'–';

/* ================= motore di recupero (dati del database) ================= */
function buildEngine(){
  const comp=new Map(), fonte=new Map(), nomi=new Map();
  const put=(mid,el,v,src)=>{ let m=comp.get(mid); if(!m){m=new Map();comp.set(mid,m);fonte.set(mid,src);} m.set(el,v); };
  for(const [mid,els] of Object.entries(DATA.composizione)) for(const [el,v] of Object.entries(els)) put(mid,el,+v,'DB');
  for(const [mid,nm] of DATA.materiali) nomi.set(mid,nm||'');
  if(S.proxy) for(const [mid,nm] of nomi){ if(comp.has(mid)) continue; const t=mid+' '+nm;
    for(const [rx,fr] of PROXY) if(rx.test(t)){ for(const [el,v] of Object.entries(fr)) put(mid,el,v,'proxy'); break; } }
  const am={...MASSE_ATOMICHE}, fatt=new Map(), price=new Map(), cat=new Map();
  const prod=DATA.prodotti;
  for(const r of prod) if(r.elemento_confronto&&r.prodotto===r.elemento_confronto&&r.peso_molare) am[r.prodotto]=+r.peso_molare;
  for(const r of prod){ const el=r.elemento_confronto;
    if(el) fatt.set(r.prodotto,[el,(r.prodotto===el||!r.peso_molare||!am[el])?1:(+r.parametro_equivalenza||1)*am[el]/(+r.peso_molare)]);
    else for(const [rx,e] of ROTTAMI) if(rx.test(String(r.prodotto))){ fatt.set(r.prodotto,[e,1]); break; }
    if(el&&r.prodotto===el){ price.set(el,+r.prezzo_attuale_eur_kg||0); cat.set(el,r.categoria||''); } }
  const testa=new Map(DATA.processi.map(p=>[p.id_processo,p]));
  const proc=new Map();
  for(const [pid,mid,tipo,prodotto,a,b,c] of DATA.trasformazioni){
    const h=testa.get(pid); if(!h) continue;
    const key=h.tipologia+'|'+h.macro_componente; let K=proc.get(key); if(!K){K=new Map();proc.set(key,K);}
    let P=K.get(pid); if(!P){P={pid,tec:h.tecnica||'',sub:h.sotto_tecnologia||'',mats:new Map(),resa:new Map()};K.set(pid,P);}
    let M=P.mats.get(mid); if(!M){M=new Map();P.mats.set(mid,M);}
    if(tipo!=='prodotto'||!fatt.has(prodotto)) continue;
    const [el,f]=fatt.get(prodotto); let v=M.get(el); if(!v){v=[0,0,0];M.set(el,v);}
    [a,b,c].forEach((x,i)=>{ if(x!=null) v[i]+=(+x)*f; });
  }
  // resa elementare media del processo: recuperato / contenuto, sui materiali del processo con composizione nota
  for(const K of proc.values()) for(const P of K.values()){
    const num=new Map(), den=new Map();
    for(const [mid,M] of P.mats){ const cm=comp.get(mid); if(!cm) continue;
      for(const [el,fr] of cm){ if(!(fr>0)) continue; den.set(el,(den.get(el)||0)+fr/100);
        let n=num.get(el); if(!n){n=[0,0,0];num.set(el,n);} const y=M.get(el); if(y) for(let i=0;i<3;i++) n[i]+=y[i]; } }
    for(const [el,d] of den) P.resa.set(el,num.get(el).map(x=>Math.min(1,x/d)));
  }
  ENG={comp,fonte,proc,price,cat}; RES.clear();
}
function plantRes(idm){
  if(RES.has(idm)) return RES.get(idm);
  const pm=PM.get(idm), out=new Map(); if(!pm){RES.set(idm,out);return out;}
  const byMacro=new Map(); for(const r of pm.rows){ let a=byMacro.get(r.macro_componente); if(!a){a=[];byMacro.set(r.macro_componente,a);} a.push(r); }
  for(const [macro,rows] of byMacro){
    const K=ENG.proc.get(pm.tip+'|'+macro);
    const Ps=K?[...K.values()].filter(P=>!pm.sub||!P.sub||P.sub===pm.sub):[];
    const acc=new Map();
    for(const r of rows){
      const cm=ENG.comp.get(r.material_id), src=ENG.fonte.get(r.material_id);
      const els=new Set(cm?cm.keys():[]);
      for(const P of Ps){ const M=P.mats.get(r.material_id); if(M) for(const el of M.keys()) els.add(el); }
      for(const el of els){
        const c=r.massa_kg*((cm&&cm.get(el))||0)/100;
        let a=acc.get(el); if(!a){a={C:0,per:Ps.map(()=>[0,0,0]),src:{},u:Ps.map(()=>[0,0,0])};acc.set(el,a);}
        a.C+=c; if(c&&src) a.src[src]=(a.src[src]||0)+c;
        Ps.forEach((P,j)=>{ const M=P.mats.get(r.material_id);
          if(M){ const y=M.get(el); if(y) for(let i=0;i<3;i++){ a.per[j][i]+=r.massa_kg*y[i]; if(!cm) a.u[j][i]+=r.massa_kg*y[i]; } }
          else if(c){ const rs=P.resa.get(el); if(rs) for(let i=0;i<3;i++) a.per[j][i]+=c*rs[i]; } });
      }
    }
    for(const [el,a] of acc){
      let o=out.get(el); if(!o){o={C:0,r:[0,0,0],nop:0,src:{},mac:[],u:0};out.set(el,o);}
      o.C+=a.C; for(const k in a.src) o.src[k]=(o.src[k]||0)+a.src[k];
      if(!Ps.length){ o.nop+=a.C; o.mac.push({macro,C:a.C,r:[0,0,0],procs:[],nop:a.C}); continue; }
      // le rese min/max del foglio processi non sono sempre ordinate: estremi su processi e livelli
      const r=[Math.min(...a.per.map(v=>Math.min(...v))), a.per.reduce((s,v)=>s+v[1],0)/a.per.length, Math.max(...a.per.map(v=>Math.max(...v)))];
      for(let i=0;i<3;i++) o.r[i]+=r[i];
      o.u+=a.u.reduce((s,v)=>s+v[1],0)/a.u.length;   // recupero nominale da materiali senza composizione
      o.mac.push({macro,C:a.C,r,procs:Ps.map((P,j)=>({pid:P.pid,tec:P.tec,v:a.per[j]})),nop:0});
    }
  }
  RES.set(idm,out); return out;
}
const ZERO={C:0,r:[0,0,0],nop:0,src:{},mac:[],u:0};
const resOf=(s,el)=>plantRes(s.idm).get(el)||ZERO;

/* ================= geografia ================= */
const LAT0=41.0, KX=Math.cos(LAT0*Math.PI/180), SC=100;      // 1 grado di latitudine = 100 unità
const prj=(lon,lat)=>[lon*KX*SC,-lat*SC];
const KM_PER_UNIT=111.32/SC;
let PROV=[], BB=[0,0,1,1];
function initProvince(PROVINCE){
  PROV=PROVINCE.map(p=>{ const rings=p.rings.map(r=>r.map(([lo,la])=>prj(lo,la)));
    let big=rings[0]; for(const r of rings) if(r.length>big.length) big=r;
    const c=big.reduce((a,[x,y])=>[a[0]+x/big.length,a[1]+y/big.length],[0,0]);
    return {sigla:p.sigla,nome:p.nome,rings,c,d:rings.map(r=>'M'+r.map(([x,y])=>x.toFixed(2)+','+y.toFixed(2)).join('L')+'Z').join('')}; });
  BB=(()=>{let a=[1e9,1e9,-1e9,-1e9]; for(const p of PROV) for(const r of p.rings) for(const [x,y] of r){a[0]=Math.min(a[0],x);a[1]=Math.min(a[1],y);a[2]=Math.max(a[2],x);a[3]=Math.max(a[3],y);} return a;})();
}
function inRing(x,y,r){ let ins=false; for(let i=0,j=r.length-1;i<r.length;j=i++){ const [xi,yi]=r[i],[xj,yj]=r[j]; if(((yi>y)!==(yj>y))&&(x<(xj-xi)*(y-yi)/(yj-yi)+xi)) ins=!ins; } return ins; }
function provOf(x,y){ for(const p of PROV){ let ins=false; for(const r of p.rings) if(inRing(x,y,r)) ins=!ins; if(ins) return p.sigla; } return null; }

/* ================= impianti e siti dal database ================= */
function buildSites(){
  PM=new Map(); SITES=[];
  const imps=DATA.impianti, mc=DATA.macro_componenti, mat=DATA.materiali;
  imps.forEach(i=>PM.set(i.id_imp,{idm:i.id_imp,name:i.nome,tip:i.tipologia,sub:i.sotto_tecnologia||'',rows:[]}));
  for(const [ii,mi,ti,kg] of DATA.masse){ const p=PM.get(imps[ii].id_imp);
    p.rows.push({macro_componente:mc[mi],material_id:mat[ti][0],material:mat[ti][1],massa_kg:kg}); }
  for(const i of imps){
    const s={sid:i.id_imp,nome:i.nome,tip:i.tipologia,sub:i.sotto_tecnologia||'',idm:i.id_imp,n:1,lat:i.lat,lon:i.lon,
      srcC:i.lat==null?'non disponibili':(i.fonte_coordinate||'database'),dism:i.anno_dismissione,srcY:i.fonte_anno||'database'};
    if(s.lat!=null&&s.lon!=null){ const [x,y]=prj(s.lon,s.lat); s.x=x; s.y=y; s.prov=provOf(x,y); }
    SITES.push(s);
  }
}

/* ================= selezione ================= */
function inSel(s){
  const m=S.sel;
  if(m.mode==='prov') return m.provs.size?m.provs.has(s.prov):true;
  if(m.mode==='circle'&&m.circle){ const c=m.circle; return (s.x-c.x)**2+(s.y-c.y)**2<=c.r*c.r; }
  if(m.mode==='rect'&&m.rect){ const r=m.rect; return s.x>=Math.min(r.x0,r.x1)&&s.x<=Math.max(r.x0,r.x1)&&s.y>=Math.min(r.y0,r.y1)&&s.y<=Math.max(r.y0,r.y1); }
  return true;
}
const inPeriod=s=>s.dism!=null&&s.dism>=S.y0&&s.dism<=S.y1;
const selected=()=>SITES.filter(s=>S.techs.has(s.tip)&&inSel(s));
function selText(){
  const m=S.sel;
  if(m.mode==='prov') return m.provs.size?'Province: '+[...m.provs].map(sg=>PROV.find(p=>p.sigla===sg).nome).join(', '):'Toccare una o più province sulla mappa.';
  if(m.mode==='circle') return m.circle?`Cerchio di raggio ${t1.format(m.circle.r*KM_PER_UNIT)} km`:'Trascinare sulla mappa dal centro verso il bordo.';
  if(m.mode==='rect') return m.rect?`Rettangolo di ${t0.format(Math.abs(m.rect.x1-m.rect.x0)*KM_PER_UNIT)} × ${t0.format(Math.abs(m.rect.y1-m.rect.y0)*KM_PER_UNIT)} km`:'Trascinare sulla mappa per disegnare il rettangolo.';
  return 'Tutti gli impianti della regione.';
}


/* ================= controlli ================= */
function updateYears(){
  const ys=SITES.map(s=>s.dism).filter(v=>v!=null);
  const lo=Math.min(2025,...ys), hi=Math.max(2050,...ys);
  const opts=[]; for(let y=lo;y<=hi;y++) opts.push(y);
  const f=$('#yFrom'), t=$('#yTo');
  if(S.y0==null||S.y0<lo) S.y0=Math.max(lo,2025); if(S.y1==null||S.y1>hi) S.y1=hi; if(S.y0>S.y1) S.y0=S.y1;
  f.innerHTML=opts.map(y=>`<option${y===S.y0?' selected':''}>${y}</option>`).join('');
  t.innerHTML=opts.map(y=>`<option${y===S.y1?' selected':''}>${y}</option>`).join('');
}
function fillControls(){
  const els=new Map();
  for(const p of PM.values()) for(const [el,o] of plantRes(p.idm)) if(o.C>0||o.r[2]>0) els.set(el,(els.get(el)||0)+o.C);
  const list=[...els].sort((a,b)=>b[1]-a[1]).map(x=>x[0]);
  if(!list.includes(S.el)) S.el=list.includes('Cu')?'Cu':list[0]||'Cu';
  $('#elF').innerHTML=list.map(el=>`<option value="${el}"${el===S.el?' selected':''}>${esc(ELNOMI[el]||el)} (${el})</option>`).join('');
  $('#proxyF').checked=S.proxy;
}
function stateLines(){
  const test=SITES.filter(s=>s.srcC==='prova').length, nc=SITES.filter(s=>s.x==null).length;
  $('#dataState').innerHTML=`<b>${SITES.length}</b> impianti dal database · ${test} con coordinate di prova${nc?` · ${nc} senza coordinate`:''}<br>${DATA.trasformazioni.length} trasformazioni di ${DATA.processi.length} processi`;
}

/* ================= calcolo della selezione ================= */
function compute(){
  const sel=selected(), el=S.el, sc=S.sc;
  const per=sel.filter(inPeriod);
  const years=[]; for(let y=S.y0;y<=S.y1;y++) years.push(y);
  const yi=new Map(years.map((y,i)=>[y,i]));
  const byT={}; for(const [t] of TECHS) byT[t]=years.map(()=>0);
  const rec=[0,1,2].map(()=>years.map(()=>0));
  const tot={C:0,r:[0,0,0],nop:0,src:{},n:0,nT:{},sites:[],noYear:0,u:0};
  for(const s of sel){ if(s.dism==null) tot.noYear++; }
  for(const s of per){
    const o=resOf(s,el), k=s.n, i=yi.get(s.dism);
    byT[s.tip][i]+=o.C*k; for(let j=0;j<3;j++) rec[j][i]+=o.r[j]*k;
    tot.C+=o.C*k; for(let j=0;j<3;j++) tot.r[j]+=o.r[j]*k; tot.nop+=o.nop*k; tot.u+=o.u*k;
    for(const q in o.src) tot.src[q]=(tot.src[q]||0)+o.src[q]*k;
    tot.n++; tot.nT[s.tip]=(tot.nT[s.tip]||0)+1;
  }
  // metalli
  const els=new Map();
  for(const s of per) for(const [e,o] of plantRes(s.idm)){ let a=els.get(e); if(!a){a={C:0,R:0};els.set(e,a);} a.C+=o.C*s.n; a.R+=o.r[sc]*s.n; }
  // macro componente x processo
  const mp=new Map();
  for(const s of per){ const o=resOf(s,el); for(const m of o.mac){
    const k=s.tip+'|'+m.macro; let a=mp.get(k); if(!a){a={tip:s.tip,macro:m.macro,C:0,r:[0,0,0],nop:0,procs:new Map()};mp.set(k,a);}
    a.C+=m.C*s.n; a.nop+=m.nop*s.n; for(let j=0;j<3;j++) a.r[j]+=m.r[j]*s.n;
    for(const p of m.procs){ let b=a.procs.get(p.pid); if(!b){b={pid:p.pid,tec:p.tec,v:[0,0,0]};a.procs.set(p.pid,b);} for(let j=0;j<3;j++) b.v[j]+=p.v[j]*s.n; } } }
  return {sel,per,years,byT,rec,tot,els,mp};
}

/* ================= disegno ================= */
let D=null;
function render(){
  if(!PM.size||!$('#warns')||!$('#scSeg')) return;
  document.querySelectorAll('#scSeg button').forEach(b=>b.setAttribute('aria-pressed',String(+b.dataset.sc===S.sc)));
  document.querySelectorAll('#selSeg button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.m===S.sel.mode)));
  $('#selNote').textContent=selText();
  $('#techF').innerHTML=TECHS.map(([t,l,c])=>`<button data-t="${t}" aria-pressed="${S.techs.has(t)}"><span class="dot" style="background:${c}"></span>${l}<span class="n">${SITES.filter(s=>s.tip===t).length}</span></button>`).join('');
  if($('#elF').value!==S.el) $('#elF').value=S.el;
  stateLines();
  D=compute();
  renderWarns(); renderKpis(); renderMap(); renderDetail(); renderChart(); renderTiles(); renderMP(); renderSites();
  $('#foot').innerHTML=`Contenuto = massa del materiale × frazione dell'elemento (tabella materiali del database${S.proxy?', poi proxy dal nome per i materiali generici senza composizione':''}). Recuperabile = rese delle trasformazioni dei processi (righe prodotto) per i materiali previsti dal processo; per gli altri materiali del macro componente si applica la resa elementare media del processo. Scenari: minimo e massimo sono gli estremi tra i processi applicabili e i livelli di resa (min, nominale, max), il medio è la media dei processi alla resa nominale. Prodotti in forma di composto (es. Li₂CO₃) convertiti in elemento con la stechiometria; i rottami di rame, alluminio e acciaio valgono come Cu, Al e Fe.`;
}
function renderWarns(){
  const w=[];
  const test=SITES.filter(s=>String(s.srcC).startsWith('prova')).length;
  if(test) w.push(`${test} siti su ${SITES.length} hanno coordinate di prova (fonte_coordinate = prova nella tabella impianti), assegnate a caso dentro la regione: la distribuzione geografica serve solo a provare il sistema.`);
  if(D.tot.u>0) w.push(`${T(D.tot.u)} t di ${ELNOMI[S.el]||S.el} recuperabili (scenario medio) vengono da materiali che i processi trattano come fonte di ${S.el} ma che nel DB non hanno composizione: il dato non è verificabile${D.tot.r[1]>D.tot.C?' e porta il recuperabile sopra il contenuto':''}.`);
  if(D.tot.noYear) w.push(`${D.tot.noYear} siti selezionati non hanno un anno di dismissione e restano fuori dai totali.`);
  $('#warns').innerHTML=w.map(x=>`<div class="warnbox">${esc(x)}</div>`).join('');
}
function kpi(k,v,u,s,cls=''){ return `<div class="kpi ${cls}"><div class="k">${k}</div><div class="v">${v}${u?` <small>${u}</small>`:''}</div><div class="s">${s}</div></div>`; }
function renderKpis(){
  const t=D.tot, el=S.el, nm=ELNOMI[el]||el;
  const serie=D.years.map((y,i)=>D.rec[S.sc][i]); let pk=-1,pv=0; serie.forEach((v,i)=>{if(v>pv){pv=v;pk=i;}});
  const price=ENG.price.get(el)||0;
  const srcTot=Object.values(t.src).reduce((a,b)=>a+b,0)||1;
  $('#kpis').innerHTML=[
    kpi(`${nm} contenuto`,T(t.C),'t',`${t.n} impianti in dismissione ${S.y0}–${S.y1}`),
    kpi(`${nm} recuperabile · ${SCN[S.sc]}`,T(t.r[S.sc]),'t',`intervallo ${T(t.r[0])}–${T(t.r[2])} t`,'accent'),
    kpi('Resa complessiva',pct(t.r[S.sc],t.C),'','recuperabile / contenuto'),
    kpi('Valore stimato',price?EUR(t.r[S.sc]*price):'–','',price?`a ${t2.format(price)} €/kg (tabella prodotti)`:'prezzo non disponibile','accent'),
    kpi('Impianti selezionati',t0.format(t.n),'',TECHS.map(([k,l])=>`${l} ${t.nT[k]||0}`).join(' · ')),
    kpi('Anno di picco',pk>=0?D.years[pk]:'–','',pk>=0?`${T(pv)} t recuperabili nell'anno`:'nessun recupero nel periodo'),
    kpi('Contenuto senza processo',T(t.nop),'t',`${pct(t.nop,t.C)} del contenuto: macrocomponenti senza processo`,t.nop>0?'warn':''),
    kpi('Composizione da proxy',pct(t.src.proxy||0,srcTot),'',`database ${pct(t.src.DB||0,srcTot)}`,(t.src.proxy||0)>0?'warn':''),
  ].join('');
}
let VB=null;
function renderMap(){
  const svg=$('#map'), pad=12, w=BB[2]-BB[0]+2*pad, h=BB[3]-BB[1]+2*pad;
  VB=[BB[0]-pad,BB[1]-pad,w,h];
  svg.setAttribute('viewBox',VB.join(' '));
  svg.classList.toggle('draw',S.sel.mode==='circle'||S.sel.mode==='rect');
  const el=S.el, z=S.size==='C'?(o=>o.C):(o=>o.r[S.sc]);
  const MS=SITES.filter(s=>s.x!=null), vals=MS.map(s=>z(resOf(s,el))*s.n); const vmax=Math.max(1,...vals);
  const selSet=new Set(D.per.map(s=>s.sid)), rmax=w/42;
  let g=PROV.map(p=>`<path class="prov${S.sel.mode==='prov'&&S.sel.provs.has(p.sigla)?' sel':''}" data-prov="${p.sigla}" d="${p.d}"><title>${esc(p.nome)}</title></path>`).join('');
  g+=PROV.map(p=>`<text class="plab" x="${p.c[0].toFixed(1)}" y="${p.c[1].toFixed(1)}" text-anchor="middle" style="font-size:${(w/60).toFixed(1)}px">${p.sigla}</text>`).join('');
  const order=MS.map((s,i)=>[s,vals[i]]).sort((a,b)=>b[1]-a[1]);
  g+=order.map(([s,v])=>{ const r=Math.max(w/260,rmax*Math.sqrt(v/vmax)); const on=selSet.has(s.sid)&&S.techs.has(s.tip);
    return `<circle class="pt${on?'':' off'}${String(s.srcC).startsWith('prova')?' test':''}" data-sid="${esc(s.sid)}" cx="${s.x.toFixed(2)}" cy="${s.y.toFixed(2)}" r="${r.toFixed(2)}" fill="${TCOL[s.tip]}" fill-opacity="${v>0?.78:.25}" style="stroke-width:${(w/900).toFixed(2)}"><title>${esc(s.nome)} · ${TLAB[s.tip]} · dismissione ${s.dism??'n.d.'}\n${ELNOMI[el]||el}: ${T(resOf(s,el).C*s.n)} t contenute, ${T(resOf(s,el).r[S.sc]*s.n)} t recuperabili (${SCN[S.sc]})\nCoordinate: ${s.srcC}</title></circle>`; }).join('');
  g+=`<g id="shape">${shapeSvg()}</g>`;
  svg.innerHTML=g;
  $('#mapSub').textContent=`${ELNOMI[el]||el}: area dei cerchi proporzionale al metallo ${S.size==='C'?'contenuto':'recuperabile'} · ${D.per.length} impianti nella selezione e nel periodo`;
  $('#mapLeg').innerHTML=TECHS.map(([t,l,c])=>`<span><i style="background:${c}"></i>${l}</span>`).join('')+`<span><i style="background:#fff;border:1.5px dashed #888"></i>bordo tratteggiato = coordinate di prova</span><span><i style="background:#ccc;opacity:.4"></i>fuori selezione o periodo</span>`;
}
function shapeSvg(){
  const m=S.sel;
  if(m.mode==='circle'&&m.circle) return `<circle class="shape" cx="${m.circle.x}" cy="${m.circle.y}" r="${m.circle.r}"/>`;
  if(m.mode==='rect'&&m.rect){ const r=m.rect; return `<rect class="shape" x="${Math.min(r.x0,r.x1)}" y="${Math.min(r.y0,r.y1)}" width="${Math.abs(r.x1-r.x0)}" height="${Math.abs(r.y1-r.y0)}"/>`; }
  return '';
}
function renderDetail(){
  const el=S.el, nm=ELNOMI[el]||el;
  const s=S.site&&SITES.find(x=>x.sid===S.site);
  if(s){
    const o=resOf(s,el), k=s.n;
    $('#detTitle').textContent=s.nome;
    $('#detSub').innerHTML=`${TLAB[s.tip]}${s.sub?' · '+esc(s.sub):''} · ${k} ${k===1?'unità':'unità'} · ${s.prov||'fuori regione'} · dismissione ${s.dism??'n.d.'} <span class="tag">${esc(s.srcY)}</span>`;
    const rows=o.mac.slice().sort((a,b)=>b.C-a.C).map(m=>`<tr><td>${esc(m.macro)}${m.procs.length?'':' <span class="tag test">senza processo</span>'}</td><td class="n">${T(m.C*k)}</td><td class="n">${T(m.r[0]*k)}</td><td class="n">${T(m.r[1]*k)}</td><td class="n">${T(m.r[2]*k)}</td></tr>`
      +m.procs.map(p=>`<tr class="sub"><td>↳ ${esc(p.pid)} · ${esc(p.tec)}</td><td></td><td class="n" colspan="3">${T(p.v[0]*k)} · ${T(p.v[1]*k)} · ${T(p.v[2]*k)}</td></tr>`).join('')).join('');
    $('#detail').innerHTML=`<div class="qual" style="margin-bottom:8px"><span>Coordinate</span><span>${s.lat==null?'non disponibili':s.lat.toFixed(4).replace('.',',')+'; '+s.lon.toFixed(4).replace('.',',')} <span class="tag${String(s.srcC).startsWith('prova')?' test':''}">${esc(s.srcC)}</span></span>
      <span>${nm} contenuto</span><b>${T(o.C*k)} t</b><span>Recuperabile min · medio · max</span><b>${T(o.r[0]*k)} · ${T(o.r[1]*k)} · ${T(o.r[2]*k)} t</b></div>
      <div class="scroll" style="max-height:300px"><table class="tbl"><thead><tr><th>Macro componente / processo</th><th class="n">Contenuto t</th><th class="n">Min</th><th class="n">Medio</th><th class="n">Max</th></tr></thead><tbody>${rows||'<tr><td colspan="5">Nessuna quantità per questo metallo.</td></tr>'}</tbody></table></div>
      <button class="sbtn full" id="detclose">Torna alla selezione</button>`;
    return;
  }
  const t=D.tot;
  $('#detTitle').textContent='Selezione';
  $('#detSub').textContent=selText();
  const srcTot=Object.values(t.src).reduce((a,b)=>a+b,0)||1;
  const bar=(parts)=>`<div class="bar">${parts.map(([v,c])=>`<i style="width:${(v*100).toFixed(1)}%;background:${c}"></i>`).join('')}</div>`;
  const provRows=PROV.map(p=>{ const ss=D.per.filter(s=>s.prov===p.sigla); const c=ss.reduce((a,s)=>a+resOf(s,el).C*s.n,0), r=ss.reduce((a,s)=>a+resOf(s,el).r[S.sc]*s.n,0); return [p,ss.length,c,r]; }).filter(x=>x[1]);
  $('#detail').innerHTML=`<div class="qual">
     <span>${nm} contenuto</span><b>${T(t.C)} t</b>
     <span>Recuperabile min · medio · max</span><b>${T(t.r[0])} · ${T(t.r[1])} · ${T(t.r[2])} t</b>
     <span>Contenuto in macro componenti senza processo</span><b>${T(t.nop)} t</b>
     ${bar([[(t.C-t.nop)/(t.C||1),'var(--green2)'],[t.nop/(t.C||1),'var(--gold)']])}
     <span>Composizione: database · proxy</span><b>${pct(t.src.DB||0,srcTot)} · ${pct(t.src.proxy||0,srcTot)}</b>
     ${bar([[(t.src.DB||0)/srcTot,'var(--green2)'],[(t.src.MACTEE||0)/srcTot,'#7FA894'],[(t.src.proxy||0)/srcTot,'var(--gold)']])}
   </div>
   <table class="tbl" style="margin-top:6px"><thead><tr><th>Provincia</th><th class="n">Impianti</th><th class="n">Contenuto t</th><th class="n">Recuperabile t</th></tr></thead>
   <tbody>${provRows.map(([p,n,c,r])=>`<tr class="click" data-prov="${p.sigla}"><td>${esc(p.nome)}</td><td class="n">${n}</td><td class="n">${T(c)}</td><td class="n">${T(r)}</td></tr>`).join('')||'<tr><td colspan="4">Nessun impianto nella selezione e nel periodo.</td></tr>'}</tbody></table>
   <p class="note">Toccare un impianto sulla mappa o nella tabella in basso per vederne il dettaglio per macro componente e processo.</p>`;
}
function niceScale(v){ if(v<=0) return 1; const e=Math.pow(10,Math.floor(Math.log10(v))), f=v/e; return (f<=1?1:f<=2?2:f<=2.5?2.5:f<=5?5:10)*e; }
function renderChart(){
  const yrs=D.years, n=yrs.length, W=900,H=300,pl=62,pr=14,pt=14,pb=32, pw=W-pl-pr, ph=H-pt-pb;
  const techs=TECHS.map(t=>t[0]).filter(t=>S.techs.has(t));
  const cumf=a=>{let s=0;return a.map(v=>s+=v);};
  const byT=Object.fromEntries(techs.map(t=>[t,S.cum?cumf(D.byT[t]):D.byT[t]]));
  const rec=D.rec.map(a=>S.cum?cumf(a):a);
  const stack=yrs.map((_,i)=>techs.reduce((a,t)=>a+byT[t][i],0));
  const maxV=niceScale(Math.max(1,...stack,...rec[2])/1000)*1000;
  const bw=pw/n, x=i=>pl+i*bw, y=v=>pt+ph-v/maxV*ph;
  let g='';
  for(let k=0;k<=4;k++){ const v=maxV*k/4; g+=`<line x1="${pl}" x2="${W-pr}" y1="${y(v)}" y2="${y(v)}" stroke="#E8EAE4"/><text x="${pl-8}" y="${y(v)+4}" text-anchor="end" font-size="11" fill="#6C7C73">${T(v)} t</text>`; }
  yrs.forEach((yr,i)=>{ let base=0; for(const t of techs){ const v=byT[t][i]; if(v>0) g+=`<rect x="${(x(i)+bw*.14).toFixed(1)}" y="${y(base+v).toFixed(1)}" width="${(bw*.72).toFixed(1)}" height="${(y(base)-y(base+v)).toFixed(1)}" fill="${TCOL[t]}" fill-opacity=".55"/>`; base+=v; } });
  const cx=i=>x(i)+bw/2;
  const band=rec[2].map((v,i)=>`${cx(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ')+' '+rec[0].map((v,i)=>`${cx(i).toFixed(1)},${y(v).toFixed(1)}`).reverse().join(' ');
  g+=`<polygon points="${band}" fill="#B5651D" fill-opacity=".16"/>`;
  [0,1,2].forEach(j=>{ g+=`<polyline points="${rec[j].map((v,i)=>`${cx(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ')}" fill="none" stroke="#B5651D" stroke-width="${j===S.sc?2.6:1.1}" ${j===S.sc?'':'stroke-dasharray="4 3"'}/>`; });
  const step=n>30?5:n>14?2:1;
  yrs.forEach((yr,i)=>{ if(yr%step===0) g+=`<text x="${cx(i).toFixed(1)}" y="${H-10}" text-anchor="middle" font-size="11" fill="#6C7C73">${yr}</text>`; });
  yrs.forEach((yr,i)=>{ const tip=techs.map(t=>`${TLAB[t]}: ${T(byT[t][i])} t contenute`).join('\n');
    g+=`<rect x="${x(i).toFixed(1)}" y="${pt}" width="${bw.toFixed(1)}" height="${ph}" fill="transparent"><title>${yr}${S.cum?' (cumulato)':''}\n${tip}\nRecuperabile: min ${T(rec[0][i])} · medio ${T(rec[1][i])} · max ${T(rec[2][i])} t</title></rect>`; });
  $('#proj').innerHTML=`<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" style="width:100%;height:100%;font-family:Inter">${g}</svg>`;
  $('#projSub').textContent=`${ELNOMI[S.el]||S.el} per anno di dismissione${S.cum?', valori cumulati':''} · ${S.y0}–${S.y1} · barre: contenuto per tecnologia · linee: recuperabile (continua = scenario ${SCN[S.sc]})`;
  $('#projLeg').innerHTML=techs.map(t=>`<span><i style="background:${TCOL[t]};opacity:.6"></i>${TLAB[t]} · contenuto</span>`).join('')+`<span><i style="background:#B5651D;height:3px"></i>recuperabile, scenario ${SCN[S.sc]}</span><span><i style="background:#B5651D;opacity:.2"></i>intervallo minimo–massimo</span>`;
}
function renderTiles(){
  const cc={critico:'var(--critico)',strategico:'var(--strategico)',utile:'var(--utile)'};
  const list=[...D.els].filter(([,a])=>a.C>0||a.R>0).sort((a,b)=>(b[1].R-a[1].R)||(b[1].C-a[1].C));
  $('#tiles').innerHTML=list.map(([el,a])=>{ const c=cc[ENG.cat.get(el)]||'#C9D0C8';
    return `<button class="tile" data-el="${el}" aria-pressed="${el===S.el}" title="${esc(ELNOMI[el]||el)}${a.R>a.C*1.0001?' – recuperabile superiore al contenuto: rese dei processi su materiali senza composizione nel database':''}"><span class="cat" style="background:${c}"></span><div class="sym" style="color:${cc[ENG.cat.get(el)]?c:'var(--ink)'}">${el}</div><div class="val">${T(a.R)} t</div><div class="val2">su ${T(a.C)} t${a.R>a.C*1.0001?' ⚠':''}</div></button>`; }).join('')||'<p class="note">Nessun metallo nella selezione.</p>';
}
function renderMP(){
  const rows=[...D.mp.values()].sort((a,b)=>b.C-a.C);
  $('#mpSub').textContent=`${ELNOMI[S.el]||S.el}, impianti nella selezione e nel periodo, in tonnellate · per processo: min · nominale · max`;
  const tr=rows.map(a=>`<tr><td><span class="tdot" style="background:${TCOL[a.tip]}"></span>${esc(a.macro)}${a.procs.size?'':' <span class="tag test">senza processo</span>'}</td><td class="n">${T(a.C)}</td><td class="n">${T(a.r[0])}</td><td class="n">${T(a.r[1])}</td><td class="n">${T(a.r[2])}</td></tr>`
    +[...a.procs.values()].map(p=>`<tr class="sub"><td>↳ ${esc(p.pid)} · ${esc(p.tec)}</td><td></td><td class="n" colspan="3">${T(p.v[0])} · ${T(p.v[1])} · ${T(p.v[2])}</td></tr>`).join('')).join('');
  const t=D.tot;
  $('#mptable').innerHTML=`<table class="tbl"><thead><tr><th>Macro componente</th><th class="n">Contenuto</th><th class="n">Min</th><th class="n">Medio</th><th class="n">Max</th></tr></thead><tbody>${tr}<tr class="tot"><td>Totale</td><td class="n">${T(t.C)}</td><td class="n">${T(t.r[0])}</td><td class="n">${T(t.r[1])}</td><td class="n">${T(t.r[2])}</td></tr></tbody></table>`;
}
function siteRows(){
  return D.per.map(s=>{ const o=resOf(s,S.el); return {s,C:o.C*s.n,r0:o.r[0]*s.n,r1:o.r[1]*s.n,r2:o.r[2]*s.n,nop:o.nop*s.n,u:o.u*s.n}; });
}
function renderSites(){
  const [k,dir]=S.sort; const rows=siteRows();
  const val=r=>k==='nome'?r.s.nome:k==='tip'?r.s.tip:k==='dism'?(r.s.dism??0):k==='prov'?(r.s.prov||''):r[k];
  rows.sort((a,b)=>{const x=val(a),y=val(b); return (typeof x==='string'?x.localeCompare(y,'it'):x-y)*dir;});
  $('#stSub').textContent=`${rows.length} impianti · ${ELNOMI[S.el]||S.el} in tonnellate · toccare una riga per il dettaglio`;
  const th=(key,l,n)=>`<th data-sort="${key}" class="${n?'n':''}">${l}${S.sort[0]===key?(S.sort[1]>0?' ▲':' ▼'):''}</th>`;
  $('#sitetable').innerHTML=`<table class="tbl"><thead><tr>${th('nome','Impianto')}${th('tip','Tipologia')}${th('prov','Prov.')}${th('dism','Dismissione',1)}<th>Fonti</th>${th('C','Contenuto',1)}${th('r0','Min',1)}${th('r1','Medio',1)}${th('r2','Max',1)}${th('nop','Senza processo',1)}${th('u','Da materiali senza comp.',1)}</tr></thead><tbody>${
    rows.slice(0,600).map(r=>`<tr class="click${S.site===r.s.sid?' hl':''}" data-sid="${esc(r.s.sid)}"><td>${esc(r.s.nome)}${r.s.n!==1?` <span class="tag">× ${r.s.n}</span>`:''}</td><td><span class="tdot" style="background:${TCOL[r.s.tip]}"></span>${TLAB[r.s.tip]}${r.s.sub?' · '+esc(r.s.sub):''}</td><td>${r.s.prov||'–'}</td><td class="n">${r.s.dism??'–'}</td><td><span class="tag${String(r.s.srcC).startsWith('prova')?' test':''}">coord. ${esc(r.s.srcC)}</span> <span class="tag${/prova/.test(r.s.srcY)?' test':''}">${esc(r.s.srcY)}</span></td><td class="n">${T(r.C)}</td><td class="n">${T(r.r0)}</td><td class="n">${T(r.r1)}</td><td class="n">${T(r.r2)}</td><td class="n">${T(r.nop)}</td><td class="n">${r.u>0?T(r.u):'–'}</td></tr>`).join('')}</tbody></table>`;
}


/* ================= esportazione ================= */
async function exportXlsx(){
  if(!D) return;
  await caricaXLSX();
  const el=S.el, wb=XLSX.utils.book_new(), r3=v=>Math.round(v*1000)/1000;
  const imp=D.per.map(s=>{ const o=resOf(s,el); return {id_sito:s.sid,nome:s.nome,tipologia:s.tip,sotto_tecnologia:s.sub||'',id_imp:s.idm,n_unita:s.n,provincia:s.prov||'',lat:s.lat,lon:s.lon,fonte_coordinate:s.srcC,
    anno_esercizio:s.cod??null,anno_dismissione:s.dism,fonte_anno:s.srcY,elemento:el,contenuto_kg:r3(o.C*s.n),recuperabile_min_kg:r3(o.r[0]*s.n),recuperabile_medio_kg:r3(o.r[1]*s.n),recuperabile_max_kg:r3(o.r[2]*s.n),contenuto_senza_processo_kg:r3(o.nop*s.n),recuperabile_medio_da_materiali_senza_composizione_kg:r3(o.u*s.n)}; });
  XLSX.utils.book_append_sheet(wb,XLSX.utils.json_to_sheet(imp),'Impianti_selezionati');
  let c=[0,0,0,0];
  const serie=D.years.map((y,i)=>{ const row={anno:y}; let tot=0; for(const [t,l] of TECHS){ row['contenuto_'+t+'_kg']=r3(D.byT[t][i]); tot+=D.byT[t][i]; }
    row.contenuto_totale_kg=r3(tot); ['min','medio','max'].forEach((n,j)=>row['recuperabile_'+n+'_kg']=r3(D.rec[j][i]));
    c[0]+=tot; for(let j=0;j<3;j++) c[j+1]+=D.rec[j][i]; row.contenuto_cumulato_kg=r3(c[0]); ['min','medio','max'].forEach((n,j)=>row['recuperabile_'+n+'_cumulato_kg']=r3(c[j+1])); return row; });
  XLSX.utils.book_append_sheet(wb,XLSX.utils.json_to_sheet(serie),'Serie_annuale');
  const mp=[];
  for(const a of [...D.mp.values()].sort((x,y)=>y.C-x.C)){
    mp.push({tipologia:a.tip,macro_componente:a.macro,id_processo:'(scenario)',tecnica:a.procs.size?'':'nessun processo applicabile',contenuto_kg:r3(a.C),recuperabile_min_kg:r3(a.r[0]),recuperabile_medio_kg:r3(a.r[1]),recuperabile_max_kg:r3(a.r[2])});
    for(const p of a.procs.values()) mp.push({tipologia:a.tip,macro_componente:a.macro,id_processo:p.pid,tecnica:p.tec,contenuto_kg:null,recuperabile_min_kg:r3(p.v[0]),recuperabile_medio_kg:r3(p.v[1]),recuperabile_max_kg:r3(p.v[2])});
  }
  XLSX.utils.book_append_sheet(wb,XLSX.utils.json_to_sheet(mp),'Macro_processi_recupero');
  const met=[...D.els].filter(([,a])=>a.C>0||a.R>0).sort((a,b)=>b[1].R-a[1].R).map(([e,a])=>({elemento:e,nome:ELNOMI[e]||e,categoria:ENG.cat.get(e)||'',contenuto_kg:r3(a.C),['recuperabile_'+SCN[S.sc]+'_kg']:r3(a.R)}));
  XLSX.utils.book_append_sheet(wb,XLSX.utils.json_to_sheet(met),'Metalli_selezione');
  const siti=SITES.map(s=>({id_sito:s.sid,nome:s.nome,tipologia:s.tip,id_imp:s.idm,n_unita:s.n,lat:s.lat,lon:s.lon,anno_esercizio:s.cod??null,anno_dismissione:s.dismImp??null,fonte_coordinate:s.srcC,fonte_anno:s.srcY}));
  XLSX.utils.book_append_sheet(wb,XLSX.utils.json_to_sheet(siti),'Siti');
  const note=[['Cruscotto recupero MPCS – risultati della selezione'],[],['Fonte','database della dashboard MACTEE (impianti, macrocomponenti, materiali, processi, prodotti)'],['Siti',`${SITES.length} impianti, ${SITES.filter(s=>s.srcC==='prova').length} con coordinate di prova`],
    ['Metallo',`${ELNOMI[el]||el} (${el})`],['Periodo di dismissione',`${S.y0}–${S.y1}`],['Tecnologie',[...S.techs].map(t=>TLAB[t]).join(', ')],['Selezione geografica',selText()],['Scenario visualizzato',SCN[S.sc]],
    ['Proxy composizione',S.proxy?'attivo':'non attivo'],[],
    ['Masse','Tabella macro (macrocomponenti di livello 1 per impianto).'],
    ['Contenuto','massa del materiale × frazione dell\'elemento; composizione dalla tabella materiali'+(S.proxy?', poi proxy da nome per i materiali generici non risolti (rame Cu 100 %, alluminio Al 100 %, acciaio/ghisa Fe 98 %)':'')+'.'],
    ['Recuperabile','Rese delle trasformazioni dei processi (righe prodotto) per i materiali previsti dal processo; per gli altri materiali del macro componente resa elementare media del processo (recuperato/contenuto sui materiali del processo con composizione nota). Composti convertiti in elemento con la stechiometria (parametro_equivalenza, peso_molare); rottami di Cu, Al e acciaio = Cu, Al, Fe.'],
    ['Scenari','Per ogni macro componente: minimo = valore più basso tra processi applicabili e livelli di resa; medio = media dei processi alla resa nominale; massimo = valore più alto. recupero_pct_min non è sempre minore di recupero_pct_max.'],
    ['Anno di dismissione','anno_dismissione della tabella impianti (la fonte è in fonte_anno).'],
    ['Senza processo','Contenuto di macrocomponenti senza processi: non recuperato.']];
  const ws=XLSX.utils.aoa_to_sheet(note); ws['!cols']=[{wch:26},{wch:120}];
  XLSX.utils.book_append_sheet(wb,ws,'Note');
  const d=new Date(), z=n=>String(n).padStart(2,'0');
  XLSX.writeFile(wb,`Cruscotto_recupero_${el}_${d.getFullYear()}${z(d.getMonth()+1)}${z(d.getDate())}_${z(d.getHours())}${z(d.getMinutes())}.xlsx`);
  toast('Esportazione completata');
}

/* ================= utilità ================= */
function toast(t){const el=$('#toast');if(!el)return;el.textContent=t;el.classList.add('show');clearTimeout(toast.t);toast.t=setTimeout(()=>el.classList.remove('show'),2800);}
function caricaXLSX(){
  if(window.XLSX) return Promise.resolve();
  return new Promise((ok,ko)=>{ const sc=document.createElement('script'); sc.src='/assets/vendor/xlsx.full.min.js'; sc.onload=ok; sc.onerror=()=>ko(new Error('SheetJS non caricato')); document.head.appendChild(sc); });
}

/* ================= interfaccia ================= */
const ASIDE=`
    <div class="fgroup"><div class="h">Scenario di recupero</div>
      <div class="cz-seg" id="scSeg" role="group" aria-label="Scenario"><button data-sc="0">Minimo</button><button data-sc="1" aria-pressed="true">Medio</button><button data-sc="2">Massimo</button></div></div>
    <div class="fgroup"><div class="h">Tecnologia</div><div class="tech" id="techF"></div></div>
    <div class="fgroup"><div class="h">Metallo</div><select id="elF"></select>
      <div class="note">Si può scegliere anche toccando una casella nel riquadro dei metalli.</div></div>
    <div class="fgroup"><div class="h">Periodo di dismissione</div>
      <div class="yrrow"><select id="yFrom"></select><span>–</span><select id="yTo"></select></div></div>
    <div class="fgroup"><div class="h">Selezione geografica</div>
      <div class="btnrow" id="selSeg"><button class="sbtn" data-m="all" aria-pressed="true">Tutta la regione</button><button class="sbtn" data-m="prov">Province</button><button class="sbtn" data-m="circle">Cerchio</button><button class="sbtn" data-m="rect">Rettangolo</button></div>
      <div class="note" id="selNote">Tutti gli impianti della regione.</div></div>
    <div class="fgroup"><div class="h">Composizione</div>
      <label class="chk"><input type="checkbox" id="proxyF" checked><span>Proxy per i materiali generici senza composizione nel database (rame → Cu 100 %, alluminio → Al 100 %, acciaio e ghisa → Fe 98 %)</span></label></div>
    <div class="fgroup"><div class="h">Dati</div><div class="status" id="dataState"></div>
      <button class="sbtn full" id="reloadF">Ricarica dal database</button>
      <button class="sbtn full" id="expbtn">Esporta XLSX</button></div>`;
const MAIN=`
    <div id="warns"></div>
    <div class="kpis" id="kpis"></div>
    <div class="grid2">
      <div class="panel"><div class="head"><div><h3>Impianti sul territorio</h3><p class="sub" id="mapSub"></p></div>
        <div class="toggle" id="sizeSeg"><button data-z="C" aria-pressed="true">Contenuto</button><button data-z="R">Recuperabile</button></div></div>
        <svg id="map" role="img" aria-label="Mappa degli impianti"></svg><div class="maplegend" id="mapLeg"></div></div>
      <div class="panel"><div class="head"><div><h3 id="detTitle">Selezione</h3><p class="sub" id="detSub"></p></div></div><div id="detail" class="detail"></div></div>
    </div>
    <div class="panel"><div class="head"><div><h3>Disponibilità nel tempo</h3><p class="sub" id="projSub"></p></div>
      <div class="toggle" id="cumSeg"><button data-c="0" aria-pressed="true">Per anno</button><button data-c="1">Cumulata</button></div></div>
      <div class="chartbox" id="proj"></div><div class="legend" id="projLeg"></div></div>
    <div class="grid2">
      <div class="panel"><div class="head"><div><h3>Metalli nella selezione</h3><p class="sub">Recuperabile nello scenario scelto e contenuto, in tonnellate; tocca per cambiare metallo</p></div></div>
        <div class="tiles" id="tiles"></div>
        <div class="legend"><span><i style="background:var(--critico)"></i>Critico</span><span><i style="background:var(--strategico)"></i>Strategico</span><span><i style="background:var(--utile)"></i>Utile</span><span><i style="background:#C9D0C8"></i>Non classificato</span></div></div>
      <div class="panel"><div class="head"><div><h3>Recupero per macrocomponente e processo</h3><p class="sub" id="mpSub"></p></div></div><div class="scroll" id="mptable"></div></div>
    </div>
    <div class="panel"><div class="head"><div><h3>Impianti selezionati</h3><p class="sub" id="stSub"></p></div></div><div class="scroll" id="sitetable"></div></div>
    <p class="footer" id="foot"></p>
    <div class="toast" id="toast" role="status"></div>`;

function bindEvents(){
/* ================= interazione con la mappa ================= */
function svgPt(ev){ const svg=$('#map'), p=svg.createSVGPoint(); p.x=ev.clientX; p.y=ev.clientY; const q=p.matrixTransform(svg.getScreenCTM().inverse()); return [q.x,q.y]; }
let drag=null;
$('#map').addEventListener('pointerdown',ev=>{
  const m=S.sel.mode;
  if(m==='circle'||m==='rect'){ const [x,y]=svgPt(ev); drag={x,y}; if(m==='circle') S.sel.circle={x,y,r:0}; else S.sel.rect={x0:x,y0:y,x1:x,y1:y}; $('#map').setPointerCapture(ev.pointerId); ev.preventDefault(); }
});
$('#map').addEventListener('pointermove',ev=>{
  if(!drag) return; const [x,y]=svgPt(ev);
  if(S.sel.mode==='circle') S.sel.circle.r=Math.hypot(x-drag.x,y-drag.y); else { S.sel.rect.x1=x; S.sel.rect.y1=y; }
  $('#shape').innerHTML=shapeSvg(); $('#selNote').textContent=selText();
});
$('#map').addEventListener('pointerup',ev=>{
  if(drag){ const tiny=S.sel.mode==='circle'?S.sel.circle.r<1:Math.abs(S.sel.rect.x1-S.sel.rect.x0)<1;
    drag=null; if(tiny){ if(S.sel.mode==='circle') S.sel.circle=null; else S.sel.rect=null; const t=ev.target.closest('[data-sid]'); if(t){ S.site=t.dataset.sid; } }
    S.site=tiny?S.site:null; render(); return; }
  const pt=ev.target.closest('[data-sid]'); if(pt){ S.site=pt.dataset.sid; render(); return; }
  const pv=ev.target.closest('[data-prov]');
  if(pv&&S.sel.mode==='prov'){ const sg=pv.dataset.prov; S.sel.provs.has(sg)?S.sel.provs.delete(sg):S.sel.provs.add(sg); S.site=null; render(); }
  else if(pv&&S.sel.mode==='all'){ S.sel.mode='prov'; S.sel.provs=new Set([pv.dataset.prov]); S.site=null; render(); }
});

/* ================= eventi ================= */
$('#scSeg').addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;S.sc=+b.dataset.sc;render();});
$('#techF').addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;const t=b.dataset.t; if(S.techs.has(t)){ if(S.techs.size>1) S.techs.delete(t); } else S.techs.add(t); render();});
$('#elF').addEventListener('change',e=>{S.el=e.target.value;render();});
$('#tiles').addEventListener('click',e=>{const b=e.target.closest('.tile');if(!b)return;S.el=b.dataset.el;render();});
$('#yFrom').addEventListener('change',e=>{S.y0=+e.target.value;if(S.y1<S.y0){S.y1=S.y0;$('#yTo').value=S.y1;}render();});
$('#yTo').addEventListener('change',e=>{S.y1=+e.target.value;if(S.y0>S.y1){S.y0=S.y1;$('#yFrom').value=S.y0;}render();});
$('#selSeg').addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;const m=b.dataset.m; if(m===S.sel.mode&&m!=='all'){ S.sel.provs.clear(); S.sel.circle=null; S.sel.rect=null; } S.sel.mode=m; S.site=null; render();});
$('#sizeSeg').addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;S.size=b.dataset.z;document.querySelectorAll('#sizeSeg button').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));render();});
$('#cumSeg').addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;S.cum=b.dataset.c==='1';document.querySelectorAll('#cumSeg button').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));renderChart();});
$('#proxyF').addEventListener('change',e=>{ S.proxy=e.target.checked; buildEngine(); fillControls(); render(); });
$('#detail').addEventListener('click',e=>{ if(e.target.id==='detclose'){ S.site=null; render(); return; } const tr=e.target.closest('tr[data-prov]'); if(tr){ S.sel.mode='prov'; S.sel.provs=new Set([tr.dataset.prov]); render(); } });
$('#sitetable').addEventListener('click',e=>{ const th=e.target.closest('th[data-sort]'); if(th){ const k=th.dataset.sort; S.sort=[k,S.sort[0]===k?-S.sort[1]:(['nome','tip','prov'].includes(k)?1:-1)]; renderSites(); return; }
  const tr=e.target.closest('tr[data-sid]'); if(tr){ S.site=S.site===tr.dataset.sid?null:tr.dataset.sid; render(); window.scrollTo({top:0,behavior:'smooth'}); } });
$('#expbtn').addEventListener('click',()=>exportXlsx().catch(e=>toast('Esportazione non riuscita: '+e.message)));
$('#reloadF').addEventListener('click',()=>monta($('#czAside'),$('#czMain'),true));
}

let PROVINCE_CACHE=null;
async function monta(asideBox, mainEl, forza){
  asideBox.innerHTML=`<div id="czAside" class="cz">${ASIDE}</div>`;
  mainEl.innerHTML=`<div id="czMain" class="cz"><div class="empty-state">Lettura dei dati dal database…</div></div>`;
  try{
    if(!PROVINCE_CACHE) PROVINCE_CACHE=await (await fetch('/assets/puglia_province.json')).json();
    initProvince(PROVINCE_CACHE);
    const r=await fetch('/api/cruscotto/dati'); if(!r.ok) throw new Error((await r.json().catch(()=>({}))).detail||r.statusText);
    DATA=await r.json();
  }catch(e){ $('#czMain').innerHTML=`<div class="empty-state">Dati del cruscotto non disponibili: ${esc(e.message)}</div>`; return; }
  buildSites(); buildEngine();
  if(S.site&&!SITES.some(s=>s.sid===S.site)) S.site=null;
  $('#czMain').innerHTML=MAIN;
  bindEvents(); updateYears(); fillControls(); render();
  if(forza) toast('Dati ricaricati dal database');
}
window.Cruscotto={monta:(asideBox,mainEl)=>monta(asideBox,mainEl,false)};
})();
