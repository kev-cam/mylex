# PSP103 Xyce plugin rebuild via PyMS — progress + the remaining ABI wall

The gold `--spice` path of `../characterize_th.py` needs a Xyce with the SG13G2
PSP103 device. This is the rebuild of that device via PyMS (share/xyce/PyMS/vae).
It gets the model to **compile, load, and register** in the stock Xyce; a C++
RTTI/plugin-ABI segfault at device-instance creation is the remaining blocker.

## What now works

1. **PyMS codegen fixes** (`codegen_pyms.patch`, applied to
   `/usr/local/share/xyce/PyMS/vae/codegen.py`) — two systematic bugs that broke
   PSP103 (and would break any complex model):
   - **multi-char operator splitting**: the emitter produced `= =`, `& &`, `| |`,
     `! =`, `> =`, `< =` (space-separated) — 1200+ malformed operators. Fixed by
     un-splitting in `_translate_expr`.
   - **if/else declaration scoping**: assignments inside branches were emitted as
     `double X = ...` (block-scoped), so X was undeclared after the block — the
     bulk of ~500 "not declared" errors. Fixed by hoisting every `double X = ...`
     to one declaration at function top + plain assignment (`_hoist_decls`).
   Result: PSP103 codegen errors 2723 → 9.
2. **Model-specific cleanup** (`build_eval.py` post-process) — the last 9 errors are
   PSP103's noise + AC-small-signal, irrelevant to large-signal transient delay:
   `ddx(...)` (AC OP-output derivatives, ×100), `ddt(...)` residuals, `I(noise)`
   probes, `V[-1]` (noise nodes at index −1 → OOB), malformed noise-op contribs.
   Nulled with stubs. `psp103_eval.so` (vae_eval + vae_jacobian) then **compiles**.
3. **The device plugin** (`N_DEV_PYMS_PSP103VA.C` from `xyce_device_gen.py` +
   `pyms_plugin_register.C`, which exports the `registerOpenDevices` entry point
   that `Xyce -plugin` dlsym's — the generator only emits a namespaced
   `registerDevice` + a load constructor, which `-plugin` does not call) **compiles
   and loads**: `SG13G2_NMOS`/`PMOS` bind and the full 782-parameter model card
   parses.

## The remaining blocker

`th22.sp` then reaches "Setting up topology" and **segfaults in
`DeviceMgr::addDeviceInstance` → `Xyce::operator<(type_index,…)` →
`type_info::before`** — a C++ RTTI/`type_index` mismatch at device-instance
creation. Not resolved by: linking `-lXyceLib`, using only the matching
`/usr/local/include` headers, `-fvisibility=default`, single registration, or
`LD_PRELOAD`. This is a plugin-ABI incompatibility between the PyMS-generated
`DeviceMaster<Traits>` and this `libXyceLib` build — it needs the exact Xyce
plugin build recipe (`buildxyceplugin.sh` flags / the matching Xyce dev
toolchain), which isn't present here.

## Reproduce

    # 1. apply the codegen fixes
    patch /usr/local/share/xyce/PyMS/vae/codegen.py < codegen_pyms.patch
    # 2. build the eval .so (preprocess+parse+codegen ~140s, then g++)
    python3 build_eval.py && <post-process per build_eval notes> && g++ -O1 -shared -fPIC psp103_eval.cpp -o psp103_eval.so
    # 3. build the device plugin (matching headers only!)
    g++ -O1 -shared -fPIC -I/usr/local/include -I<pyms_cache> \
        N_DEV_PYMS_PSP103VA.C pyms_plugin_register.C -L/usr/local/lib -lXyceLib -o psp103_plugin.so
    # 4. run (segfaults at topology — the ABI wall)
    VAE_SO_PATH=$PWD/psp103_eval.so Xyce -plugin $PWD/psp103_plugin.so ../th22_char.cir
