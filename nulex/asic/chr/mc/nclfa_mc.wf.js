// Monte-Carlo Vt-mismatch reliability harness for the composed NCL full-adder (nclfa).
// Runs kvt=1..4 in parallel (N=200 .SAMPLING MC each), then FOUR perspective-diverse
// adversarial verifiers, then a synthesis stage that writes RESULTS_nclfa.md.
//
// Reusable: pass paths via args ->  Workflow({scriptPath:'.../nclfa_mc.wf.js',
//   args:{sp:'/abs/scratch-dir', mc:'/abs/path/to/this/mc/dir'}}).
// Prerequisites (see mc/README.md / RESULTS_nclfa.md):
//   - the PyMS-fixed Xyce (PSP103 via .hdl) at XYCE, PYMS_DIR installed.
//   - a PRE-WARMED shared .so cache at <sp>/mc_shared_hdl and <sp>/mc_shared_vae
//     (build every device geometry once under PYMS_CALLBACK_PARAMS=DELVTO) so the
//     .SAMPLING runs are build-free and race-free (read-only shared cache).
//   - the corrected deck mc_nclfa.cir, which includes nclfa_mc.sp (threads kvt DOWN
//     to every TH-gate instance). The kvt-scaling verifier below guards against the
//     regression where an un-threaded kvt silently pins every level at nominal.
export const meta = {
  name: 'nclfa-mc',
  description: 'Monte-Carlo Vt-mismatch reliability of the composed NCL full-adder block (nclfa), kvt=1..4 + adversarial verification',
  phases: [
    {title:'Sweep',    detail:'kvt=1..4 in parallel: N=200 .SAMPLING MC, functional yield + completion latency'},
    {title:'Verify',   detail:'perspective-diverse adversarial checks: truth-table, raw-data recount, NCL protocol, kvt-scaling'},
    {title:'Synthesize', detail:'aggregate yields+latency, fold in verifier verdicts, write RESULTS_nclfa.md'},
  ],
}
const SP = (typeof args === 'object' && args && args.sp) || '/tmp/nclfa_mc';
const MC = (typeof args === 'object' && args && args.mc) || '/usr/local/src/mylex/nulex/asic/chr/mc';
const ENV = `export XYCE=/usr/local/src/xyce-build/src/Xyce PYMS_DIR=/usr/local/share/xyce/PyMS PYMS_CALLBACK_PARAMS=DELVTO PYMS_CACHE=${SP}/mc_shared_hdl PYMS_VAE_CACHE=${SP}/mc_shared_vae`

const KVT_SCHEMA = { type:'object', additionalProperties:false, properties:{
  kvt:{type:'number'}, functional:{type:'integer'}, total:{type:'integer'}, yield_pct:{type:'number'},
  latency_mean_ps:{type:'number'}, latency_sd_ps:{type:'number'}, latency_min_ps:{type:'number'}, latency_max_ps:{type:'number'},
  worst_measures:{type:'string'}, notes:{type:'string'} },
  required:['kvt','functional','total','yield_pct','latency_mean_ps','latency_sd_ps','notes'] }

function kvtPrompt(k){ return `Run ONE Monte-Carlo mismatch level of the composed NCL full-adder (nclfa) and report structured results. Work autonomously.

The nominal FA is already verified correct on all 8 (A,B,Cin) vectors. Your job: the MC run at kvt=${k}.

ENVIRONMENT — paste before the Xyce run:
${ENV}
Working dir (EXACT path — a later verifier reads it): mkdir -p ${SP}/wf_nclfa/k${k} && cd ${SP}/wf_nclfa/k${k}

STEPS:
1. Copy the deck + expected map and set kvt=${k}:
     sed 's/\\.param kvt=[0-9.]*/.param kvt=${k}/' ${MC}/mc_nclfa.cir > mc_nclfa.cir
     cp ${MC}/mc_nclfa.cir.expected.json mc_nclfa.cir.expected.json
   (The deck includes nclfa_mc.sp which threads kvt down to the gates; it already has
    numsamples=200, SAMPLE_TYPE=MC, SEED=1, and 60 per-device AGAUSS DELVTO. Cache is pre-warmed.)
2. Run: $XYCE mc_nclfa.cir > mc.log 2>&1   (generous timeout ~900s; build-free but transient-heavy)
   Confirm the log shows "Number of unique random parameters = 60" and "End of Xyce".
3. Analyze: python3 ${MC}/analyze_fa.py "$PWD/mc_nclfa.cir"
   (functional = every DATA-phase output rail matches the FA dual-rail codeword AND every
   final-NULL output returns LOW/RTZ; plus completion-latency tvalid stats.)

Return KVT_SCHEMA JSON: kvt=${k}, functional, total (=200), yield_pct, latency_{mean,sd,min,max}_ps,
worst_measures (the wrong-output tally or '' if none), notes. Do NOT fabricate; if the run failed,
set functional=0 and explain.`
}

phase('Sweep')
const sweep = await parallel([1,2,3,4].map(k => () =>
  agent(kvtPrompt(k), {label:`nclfa:kvt${k}`, phase:'Sweep', schema:KVT_SCHEMA})))
const kvts = sweep.filter(Boolean)
log(`swept ${kvts.length}/4 kvt levels`)

phase('Verify')
const VERIFY_SCHEMA = { type:'object', additionalProperties:false, properties:{
  lens:{type:'string'}, verdict:{type:'string'}, detail:{type:'string'} },
  required:['lens','verdict','detail'] }

const vTruth = `ADVERSARIAL VERIFIER — TRUTH-TABLE lens. Independently derive the correct dual-rail
truth of the NCL full-adder and CONFIRM (or refute) the expected-output map used to score the MC.
Read /usr/local/src/ldx/asic/cells/nclfa.sp (coH=TH23(aH,bH,ciH); coL=TH23(aL,bL,ciL);
sH=TH34W2(coL,aH,bH,ciH) with the FIRST/weight-2 input = coL; sL=TH34W2(coH,aL,bL,ciL)). Using
TH23="assert when >=2 of 3 inputs high" and TH34W2="assert when 2*first+rest>=3", derive
sH,sL,coH,coL for all 8 (A,B,Cin) dual-rail DATA vectors (A=1 -> aH=1,aL=0). Compare against
${MC}/mc_nclfa.cir.expected.json (measure d<i>_{sh,sl,coh,col}; vector index i = A*4+B*2+Cin), and
confirm Sum=A^B^Cin, Cout=maj(A,B,Cin). Return VERIFY_SCHEMA: lens='truth-table', verdict 'pass'
iff expected.json matches your derivation for all 8 vectors (and RTZ=all-LOW), else 'fail'; detail
= per-vector agreement + any mismatch.`

const vRaw = `ADVERSARIAL VERIFIER — RAW-DATA lens. Independently recompute the kvt=4 functional yield
WITHOUT using analyze_fa.py. Read ${SP}/wf_nclfa/k4/mc_nclfa.cir.mt0..mt199 and the expected map
${MC}/mc_nclfa.cir.expected.json. Own parser: a sample is functional iff for every measure in
expected.json the value is on the correct side of VDD/2 with margin (expected 'H' => V>0.72,
expected 'L' => V<0.48). Count functional out of the .mt files present and compare to the kvt=4
sweep agent's reported functional/total. Return VERIFY_SCHEMA: lens='raw-data', verdict 'pass' iff
your count matches (and total=200), else 'fail'; detail = your count, files seen, discrepancy.`

const vProto = `ADVERSARIAL VERIFIER — NCL-PROTOCOL lens. Read ${MC}/mc_nclfa.cir. Verify: (1) every
input-rail PWL is 0 during NULL phases and each DATA phase asserts EXACTLY ONE rail of each of the
3 input pairs (aH/aL,bH/bL,ciH/ciL); (2) a NULL phase separates every pair of consecutive DATA
phases (TH hysteresis reset); (3) the .measure set + expected.json cover all 8 DATA vectors' four
outputs plus a final-NULL RTZ check on all four outputs. Return VERIFY_SCHEMA: lens='protocol',
verdict 'pass' iff all three hold, else 'fail'; detail = what you confirmed + any violation.`

const vScale = `ADVERSARIAL VERIFIER — KVT-SCALING lens. Confirm the swept parameter (kvt) ACTUALLY
reaches the DUT and scales the mismatch. This closes the gap that once let a hierarchical sweep
silently run EVERY level at nominal (a cell's subckt-local '.param kvt=1' shadowed the top-level
kvt because the composed block did not thread it down — every kvt produced byte-identical output).
Read the per-sample measure files the sweep agents wrote, per level:
  ${SP}/wf_nclfa/k1/mc_nclfa.cir.mt*  ${SP}/wf_nclfa/k2/...  k3/...  ${SP}/wf_nclfa/k4/mc_nclfa.cir.mt*
Verify BOTH, with your own bash/python (do not trust the sweep agents' self-reported numbers):
(1) VARIATION REACHES THE DUT: for several sample indices (e.g. 0,3,50,150) confirm
    k1/mc_nclfa.cir.mt<i> is NOT byte-identical to k4/mc_nclfa.cir.mt<i>. If ALL sampled indices
    are identical across k1 vs k4, kvt is inert (not threading to the devices) -> verdict 'fail'.
(2) SPREAD SCALES WITH kvt: from the .mt files compute the population std-dev of the completion
    latency 'tvalid' at each kvt; confirm it INCREASES with kvt (k4 sd clearly > k1 sd). A flat sd
    across levels means the sweep does nothing -> verdict 'fail'.
Return VERIFY_SCHEMA: lens='kvt-scaling', verdict 'pass' iff BOTH hold, else 'fail'; detail = the
k1-vs-k4 per-index diff outcome, the per-kvt tvalid sd values, and whether sd is monotone in kvt.`

const verdicts = (await parallel([
  () => agent(vTruth, {label:'verify:truth',   phase:'Verify', schema:VERIFY_SCHEMA}),
  () => agent(vRaw,   {label:'verify:raw',     phase:'Verify', schema:VERIFY_SCHEMA}),
  () => agent(vProto, {label:'verify:proto',   phase:'Verify', schema:VERIFY_SCHEMA}),
  () => agent(vScale, {label:'verify:scaling', phase:'Verify', schema:VERIFY_SCHEMA}),
])).filter(Boolean)

phase('Synthesize')
const synth = await agent(
`SYNTHESIS — write the NCL full-adder MC reliability report. Inputs:
kvt sweep results (JSON): ${JSON.stringify(kvts,null,1)}
adversarial verdicts (JSON, four lenses incl. kvt-scaling): ${JSON.stringify(verdicts,null,1)}

The nclfa is a composed dual-rail NCL block (2x TH23 carry + 2x TH34W2 sum, Fant form), 60
transistors, each with independent per-device Pelgrom DELVTO=AGAUSS. Write ${MC}/RESULTS_nclfa.md:
title; one-paragraph methodology (dual-rail NULL/DATA over all 8 vectors; functional = all outputs
correct codeword + RTZ; 60 independent per-device DELVTO via th23_mc/th34w2_mc + PyMS callback;
kvt threaded down by nclfa_mc.sp; Xyce .SAMPLING N=200 x kvt=1..4; completion latency tvalid on the
deepest carry->sum path); a kvt vs yield vs latency (mean+-sd,min,max) table; the FOUR-lens
adversarial-verification summary; and findings (functional robustness under mismatch; how latency
sd AND mean scale with kvt vs single cells). Factual, sourced only from the JSON. Return JSON:
{headline, results_md_written:bool, anomalies:[...], all_verifiers_pass:bool}.`,
  {label:'synthesize', phase:'Synthesize', schema:{ type:'object', additionalProperties:false,
    properties:{ headline:{type:'string'}, results_md_written:{type:'boolean'},
      anomalies:{type:'array',items:{type:'string'}}, all_verifiers_pass:{type:'boolean'} },
    required:['headline','results_md_written','anomalies','all_verifiers_pass'] }})

return { kvts, verdicts, synth }
