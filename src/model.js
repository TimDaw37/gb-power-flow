// GB zonal power-flow model. Pure functions; works in browser and node.
(function (root) {
  const ZONES = ['_P','_N','_F','_G','_M','_D','_E','_B','_A','_K','_L','_H','_C','_J'];
  // Indicative inter-zone transfer paths. Weight ~ rough transfer capability (GW), used as susceptance.
  const LINKS = [
    ['_P','_N',4.5,'B4 (SSEN–SPT)'], ['_N','_F',3.4,'B6 east (Eccles–Stella)'], ['_N','_G',3.4,'B6 west (Gretna–Harker)'],
    ['_N','_D',2.2,'Western HVDC Link'], ['_F','_G',1.5,'Cumbria–Tyne'], ['_F','_M',6,'Teesside–Yorkshire'],
    ['_G','_M',4,'Pennine crossings'], ['_G','_D',6,'Cheshire / Merseyside'], ['_G','_E',4,'North West–Midlands'],
    ['_D','_E',3,'N Wales–Midlands'], ['_M','_B',8,'Trent valley'], ['_B','_E',6,'East–West Midlands'],
    ['_B','_A',4,'East Midlands–East Anglia'], ['_E','_H',3,'Midlands–Thames valley'], ['_E','_L',2,'Midlands–South West'],
    ['_E','_K',1.5,'Midlands–South Wales'], ['_K','_L',3,'Severn crossings'], ['_L','_H',3,'Wessex'],
    ['_H','_C',4,'West London'], ['_H','_J',3,'South coast'], ['_J','_C',4,'South London'],
    ['_A','_C',6,'North & East London'], ['_A','_J',3,'Thames estuary']];
  // Indicative share of GB electricity demand by DNO area (~TWh/yr, sub-national consumption statistics, rounded).
  const DEMAND = {_A:30,_B:23,_C:36,_D:12,_E:23,_F:12,_G:19,_H:27,_J:20,_K:10,_L:13,_M:23,_N:15,_P:7};
  // Indicative share of embedded (distribution-connected) capacity by area.
  const EMB_SOLAR = {_A:15,_B:10,_C:1.5,_D:4,_E:7,_F:2.5,_G:4,_H:13,_J:7,_K:7,_L:16,_M:5,_N:4,_P:2};
  const EMB_WIND  = {_A:6,_B:4,_C:0,_D:6,_E:2,_F:7,_G:5,_H:1,_J:1,_K:6,_L:5,_M:7,_N:25,_P:25};
  const norm = o => { const s = Object.values(o).reduce((a,b)=>a+b,0); const r={}; for (const k in o) r[k]=o[k]/s; return r; };
  const DS = norm(DEMAND), ES = norm(EMB_SOLAR), EW = norm(EMB_WIND);

  function fuelGroup(f, name) {
    const n = (name||'').toLowerCase();
    if (/bess|battery|storage/.test(n)) return 'Storage';
    if (/solar/.test(n)) return 'Solar';
    switch (f) {
      case 'BATTERY': return 'Storage';
      case 'SOLAR': return 'Solar';
      case 'WIND': return 'Wind';
      case 'CCGT': case 'OCGT': return 'Gas';
      case 'NUCLEAR': return 'Nuclear';
      case 'BIOMASS': return 'Biomass';
      case 'PS': case 'NPSHYD': return 'Hydro';
    }
    if (/ wf|wind|offshore/.test(n)) return 'Wind';
    return 'Other';
  }

  // Level of a piecewise-linear notification at time t (ms).
  function levelAt(recs, t) {
    for (const r of recs) {
      const a = Date.parse(r.timeFrom), b = Date.parse(r.timeTo);
      if (t >= a && t <= b) return b > a ? r.levelFrom + (r.levelTo - r.levelFrom) * (t - a) / (b - a) : r.levelTo;
    }
    return null;
  }

  // Inputs: geo (precomputed), fuelinst (latest 5-min records), pn, boa (arrays), emb {wind, solar}, t (ms)
  function compute(geo, d) {
    const t = d.t;
    const plants = {}; for (const p of geo.plants) plants[p[0]] = p;
    const byUnit = {}; for (const r of d.pn) (byUnit[r.bmUnit] ||= []).push(r);
    const acc = {}; for (const r of d.boa) (acc[r.bmUnit] ||= []).push(r);
    const units = [];
    let posSum = 0, unlocated = 0; const supDem = {};
    for (const u in byUnit) {
      if (u.startsWith('I_')) continue;              // interconnectors taken from FUELINST
      let v = levelAt(byUnit[u], t);
      const a = (acc[u] || []).filter(r => t >= Date.parse(r.timeFrom) && t <= Date.parse(r.timeTo));
      if (a.length) { const r = a.reduce((x, y) => y.acceptanceNumber > x.acceptanceNumber ? y : x); const lv = levelAt([r], t); if (lv != null) v = lv; }
      if (v == null || v === 0) continue;
      const p = plants[u], z = p ? p[3] : geo.gsp[u];
      if (!z) { if (v > 0) unlocated += v; continue; }
      if (!p && v < 0) { supDem[z] = (supDem[z]||0) - v; continue; }   // supplier demand BMUs: regional demand shape
      units.push({ u, v, z, x: p && p[1], y: p && p[2], fuel: fuelGroup(p ? p[4] : '', p ? p[5] : ''), name: p ? p[5] : u });
      if (v > 0) posSum += v;
    }
    // National totals from FUELINST (metered, 5-min)
    const fi = {}; for (const r of d.fuelinst) fi[r.fuelType] = r.generation;
    let genTotal = 0, icNet = 0;
    for (const k in fi) { if (k.startsWith('INT')) icNet += fi[k]; else genTotal += fi[k]; }
    const scale = posSum > 0 ? genTotal / (posSum + unlocated) : 1;
    // Zone balances
    const Z = {}; for (const z of ZONES) Z[z] = { gen: 0, charge: 0, ic: 0, embW: 0, embS: 0, demand: 0, src: {}, fuel: {} };
    const addSrc = (zz, key, fuel, mw) => { zz.src[key] = (zz.src[key]||0) + mw; zz.fuel[fuel] = (zz.fuel[fuel]||0) + mw; };
    for (const x of units) {
      if (x.v > 0) { x.mw = x.v * scale; Z[x.z].gen += x.mw; addSrc(Z[x.z], x.z, x.fuel, x.mw); }
      else { x.mw = x.v; Z[x.z].charge += -x.v; }
    }
    // spread unlocated output pro rata to located generation
    if (unlocated > 0) { const tot = ZONES.reduce((s,z)=>s+Z[z].gen,0); for (const z of ZONES) { const add = unlocated*scale*Z[z].gen/tot; Z[z].gen += add; addSrc(Z[z], z, 'Other', add); } }
    const ics = geo.ics.map(c => ({ ...c, mw: fi[c.key] || 0 }));
    for (const c of ics) { if (c.mw > 0) { Z[c.zone].ic += c.mw; addSrc(Z[c.zone], c.key, 'Imports', c.mw); } else Z[c.zone].charge += -c.mw; }
    for (const z of ZONES) {
      Z[z].embW = d.emb.wind * EW[z]; Z[z].embS = d.emb.solar * ES[z];
      if (Z[z].embW) addSrc(Z[z], z, 'Wind', Z[z].embW);
      if (Z[z].embS) addSrc(Z[z], z, 'Solar', Z[z].embS);
    }
    // Demand: everything produced or imported is consumed somewhere (losses folded in), spread by indicative shares
    const supply = ZONES.reduce((s, z) => s + Z[z].gen + Z[z].ic + Z[z].embW + Z[z].embS, 0);
    const sinks  = ZONES.reduce((s, z) => s + Z[z].charge, 0);   // storage charging + exports
    const demand = supply - sinks;
    const sd = Object.values(supDem).reduce((a,b)=>a+b,0);
    const shares = sd > 5000 ? norm(Object.fromEntries(ZONES.map(z => [z, supDem[z]||0]))) : DS;
    for (const z of ZONES) { Z[z].demand = demand * shares[z]; Z[z].net = Z[z].gen + Z[z].ic + Z[z].embW + Z[z].embS - Z[z].charge - Z[z].demand; }
    // DC power flow: B theta = P, slack = last zone
    const n = ZONES.length, idx = Object.fromEntries(ZONES.map((z, i) => [z, i]));
    const Bm = Array.from({ length: n }, () => new Array(n).fill(0));
    for (const [a, b, w] of LINKS) { const i = idx[a], j = idx[b]; Bm[i][i] += w; Bm[j][j] += w; Bm[i][j] -= w; Bm[j][i] -= w; }
    const m = n - 1, A = Bm.slice(0, m).map((r, i) => [...r.slice(0, m), Z[ZONES[i]].net]);
    for (let c = 0; c < m; c++) {
      let p = c; for (let r = c + 1; r < m; r++) if (Math.abs(A[r][c]) > Math.abs(A[p][c])) p = r;
      [A[c], A[p]] = [A[p], A[c]];
      for (let r = 0; r < m; r++) if (r !== c) { const f = A[r][c] / A[c][c]; for (let k = c; k <= m; k++) A[r][k] -= f * A[c][k]; }
    }
    const theta = ZONES.map((z, i) => i < m ? A[i][m] / A[i][i] : 0);
    const flows = LINKS.map(([a, b, w, label]) => { const f = w * (theta[idx[a]] - theta[idx[b]]); return { a, b, label, mw: f }; });
    // Proportional-sharing flow tracing (flows are acyclic in DC: follow decreasing theta)
    const order = ZONES.map((z, i) => i).sort((i, j) => theta[j] - theta[i]);
    const mix = {}, fmix = {};
    for (const i of order) {
      const z = ZONES[i], src = { ...Z[z].src }, fu = { ...Z[z].fuel };
      for (const f of flows) {
        let from = null, mw = 0;
        if (f.b === z && f.mw > 0) { from = f.a; mw = f.mw; } else if (f.a === z && f.mw < 0) { from = f.b; mw = -f.mw; }
        if (!from) continue;
        for (const k in mix[from]) src[k] = (src[k]||0) + mw * mix[from][k];
        for (const k in fmix[from]) fu[k] = (fu[k]||0) + mw * fmix[from][k];
      }
      const s = Object.values(src).reduce((a,b)=>a+b,0) || 1, sf = Object.values(fu).reduce((a,b)=>a+b,0) || 1;
      mix[z] = {}; for (const k in src) mix[z][k] = src[k] / s;
      fmix[z] = {}; for (const k in fu) fmix[z][k] = fu[k] / sf;
    }
    // National fuel mix from FUELINST
    const nat = {};
    const G = { WIND:'Wind', CCGT:'Gas', OCGT:'Gas', NUCLEAR:'Nuclear', BIOMASS:'Biomass', PS:'Hydro', NPSHYD:'Hydro', COAL:'Other', OIL:'Other', OTHER:'Other' };
    for (const k in fi) { if (k.startsWith('INT')) continue; const g = G[k] || 'Other'; nat[g] = (nat[g]||0) + fi[k]; }
    nat.Wind = (nat.Wind||0) + d.emb.wind; nat.Solar = (nat.Solar||0) + d.emb.solar;
    return { demandSource: sd > 5000 ? 'live' : 'static', zones: Z, flows, ics, units, theta, mix, fmix, nat, demand, icNet, genTotal, scale, unlocated };
  }
  const api = { ZONES, LINKS, compute, fuelGroup };
  if (typeof module !== 'undefined') module.exports = api; else root.GBFlow = api;
})(this);
