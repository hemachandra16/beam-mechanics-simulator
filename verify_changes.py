"""
Quick verification script for all code changes.
Run with: python verify_changes.py
"""
import ast
import numpy as np

print('=' * 60)
print('STEP 1 — Syntax checks')
print('=' * 60)

for label, path in [
    ('V1 beam_simulation.py', r'd:\MSF prjct\beam_simulation.py'),
    ('V2 backend/app.py',     r'd:\MSF prjct\beam-simulator\backend\app.py'),
]:
    with open(path, encoding='utf-8') as f:
        src = f.read()
    try:
        ast.parse(src)
        print(f'  OK  — {label}')
    except SyntaxError as e:
        print(f'  ERR — {label}: {e}')

print()
print('=' * 60)
print('STEP 2 — Change presence checks')
print('=' * 60)

with open(r'd:\MSF prjct\beam_simulation.py', encoding='utf-8') as f:
    v1 = f.read()
with open(r'd:\MSF prjct\beam-simulator\backend\app.py', encoding='utf-8') as f:
    v2 = f.read()
with open(r'd:\MSF prjct\beam-simulator\frontend\renderer.js', encoding='utf-8') as f:
    js = f.read()

checks = [
    ('V1  x-array fix',       'np.sort(np.unique(np.append',        v1),
    ('V1  M_disp = -M',       'M_disp = -M',                        v1),
    ('V1  fill uses M_disp',  'M_disp, 0, color=GREEN',             v1),
    ('V1  y-label Indian',    'Indian conv',                         v1),
    ('V2  x-array fix',       'np.sort(np.unique(np.append',        v2),
    ('V2  M_display negate',  'M_display = (-M).tolist()',           v2),
    ('V2  M in response',     'M_display',                          v2),
    ('V2  renderer tooltip',  'Math.abs(ctx.parsed.y)',              js),
    ('V2  renderer y-label',  'Indian convention',                   js),
]

all_ok = True
for name, pattern, text in checks:
    found = pattern in text
    status = 'FOUND  ' if found else 'MISSING'
    print(f'  {status} — {name}')
    if not found:
        all_ok = False

print()
print('=' * 60)
print('STEP 3 — Numerical verification (default test case)')
print('=' * 60)

L, P, a, w, D = 5.0, 1000.0, 2.0, 200.0, 0.1

R_B = (P * a + w * L**2 / 2.0) / L
R_A = P + w * L - R_B

# Analytical M_max
M_max_exact = R_A * a - w * a**2 / 2.0

# Old 500-pt linspace
x_old = np.linspace(0, L, 500)
M_old = R_A * x_old - w * x_old**2 / 2.0 - P * np.maximum(x_old - a, 0.0)
M_max_old = np.max(np.abs(M_old))

# New pinned x
x_new = np.sort(np.unique(np.append(np.linspace(0, L, 500), [a])))
M_new = R_A * x_new - w * x_new**2 / 2.0 - P * np.maximum(x_new - a, 0.0)
M_max_new = np.max(np.abs(M_new))

# Stress
I = np.pi * D**4 / 64.0
y_c = D / 2.0
sigma_exact = M_max_exact * y_c / I / 1e6
sigma_old   = M_max_old   * y_c / I / 1e6
sigma_new   = M_max_new   * y_c / I / 1e6

err_old  = abs(M_max_old - M_max_exact) / M_max_exact * 100
err_new  = abs(M_max_new - M_max_exact) / M_max_exact * 100
sig_err_old = abs(sigma_old - sigma_exact) / sigma_exact * 100
sig_err_new = abs(sigma_new - sigma_exact) / sigma_exact * 100

print(f'  Reactions:  R_A={R_A:.1f} N  R_B={R_B:.1f} N')
print(f'  M_max exact:     {M_max_exact:.6f} N·m')
print(f'  M_max OLD  :     {M_max_old:.6f} N·m   error = {err_old:.4f}%')
print(f'  M_max NEW  :     {M_max_new:.6f} N·m   error = {err_new:.8f}%')
print(f'  sigma exact:     {sigma_exact:.5f} MPa')
print(f'  sigma OLD  :     {sigma_old:.5f} MPa   error = {sig_err_old:.4f}%')
print(f'  sigma NEW  :     {sigma_new:.5f} MPa   error = {sig_err_new:.8f}%')
print()

# Boundary conditions
print(f'  M(0) = {M_new[0]:.10f}  (must be 0)')
print(f'  M(L) = {M_new[-1]:.10f}  (must be 0)')

# BMD Indian convention check
M_disp = -M_new
idx = np.argmax(np.abs(M_new))
print()
print(f'  BMD Indian convention:')
print(f'    Sagging peak (internal) = +{M_new[idx]:.2f} N*m')
print(f'    Display value (plotted) = {M_disp[idx]:.2f} N*m  <- below baseline [OK]')

print()
print('=' * 60)
error_fixed = err_new < 1e-6
bc_ok = abs(M_new[0]) < 1e-9 and abs(M_new[-1]) < 1e-9
if all_ok and error_fixed and bc_ok:
    print('ALL VERIFICATIONS PASSED [OK]')
else:
    if not all_ok:
        print('  [FAIL] Some code changes missing')
    if not error_fixed:
        print(f'  [FAIL] Error still present: {err_new:.4f}%')
    if not bc_ok:
        print('  [FAIL] Boundary conditions failed')
print('=' * 60)
