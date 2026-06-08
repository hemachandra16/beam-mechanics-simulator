"""
Beam Mechanics Simulator - Flask Backend
=========================================
Provides /calculate and /explain endpoints for the Electron frontend.
All engineering calculations are performed here using NumPy.
"""

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import numpy as np
import json
import os

app = Flask(__name__)
CORS(app)

# Groq client — initialised lazily so server starts even without key
_groq_client = None
_DEFAULT_GROQ_KEY = ""

def get_groq_client():
    global _groq_client
    if _groq_client is None:
        try:
            from groq import Groq
            key = os.environ.get("GROQ_API_KEY", _DEFAULT_GROQ_KEY)
            if key:
                _groq_client = Groq(api_key=key)
        except Exception:
            pass
    return _groq_client

MATERIALS = {
    'Steel':    {'yield_mpa': 250, 'color': '#4FC3F7'},
    'Aluminum': {'yield_mpa': 270, 'color': '#E8A838'},
    'Timber':   {'yield_mpa': 40,  'color': '#66BB6A'},
}


@app.route('/ping')
def ping():
    return 'ok'


@app.route('/calculate', methods=['POST'])
def calculate():
    """
    Main calculation endpoint.
    Receives beam parameters, returns reactions, SFD, BMD, and stress data.

    Engineering formulae:
        Reactions (equilibrium):
            R_B = (P * a + w * L^2 / 2) / L
            R_A = P + w * L - R_B

        Shear force (Heaviside step):
            V(x) = R_A - w*x - P * H(x - a)

        Bending moment (Macaulay bracket):
            M(x) = R_A*x - w*x^2/2 - P * max(x - a, 0)

        Bending stress (circular cross-section):
            I = pi * D^4 / 64
            sigma = M_max * (D/2) / I
    """
    d = request.json
    L   = float(d['L'])
    P   = float(d['P'])
    a   = float(d['a'])
    w   = float(d['w'])
    D   = float(d['D']) / 1000.0   # mm -> m
    mat = d['material']
    a   = min(a, L)

    # Insert exact load position so Heaviside/Macaulay activate at precisely x=a
    x  = np.sort(np.unique(np.append(np.linspace(0, L, 500), [a])))

    # Reactions from equilibrium
    R_B = (P * a + w * L**2 / 2.0) / L
    R_A = P + w * L - R_B

    # Shear force: V(x) = R_A - w*x - P*H(x-a)
    V = R_A - w * x - P * (x >= a).astype(float)

    # Bending moment: M(x) = R_A*x - w*x^2/2 - P*<x-a>
    M = R_A * x - w * x**2 / 2.0 - P * np.maximum(x - a, 0.0)

    # Stress calculation
    I = np.pi * D**4 / 64.0
    y = D / 2.0
    M_max = float(np.max(np.abs(M)))

    if I > 0 and M_max > 0:
        sigma_pa  = M_max * y / I
        sigma_mpa = sigma_pa / 1e6
    else:
        sigma_pa  = 0.0
        sigma_mpa = 0.0

    yield_mpa = MATERIALS[mat]['yield_mpa']
    FOS  = yield_mpa / sigma_mpa if sigma_mpa > 0 else 999.0
    safe = sigma_mpa < yield_mpa

    # Critical failure point
    idx_crit = int(np.argmax(np.abs(M)))
    x_crit   = float(x[idx_crit])

    # Indian structural convention: BMD drawn on tension face.
    # For a simply supported beam, sagging is positive → tension at bottom → plot below baseline.
    # We negate M for display only; M_max (absolute) is unchanged for stress calculation.
    M_display = (-M).tolist()

    return jsonify({
        'x':          x.tolist(),
        'V':          V.tolist(),
        'M':          M_display,          # negated for Indian convention display
        'R_A':        round(R_A, 2),
        'R_B':        round(R_B, 2),
        'V_max':      round(float(np.max(V)), 2),
        'V_min':      round(float(np.min(V)), 2),
        'M_max':      round(M_max, 2),    # always positive absolute value
        'sigma_mpa':  round(sigma_mpa, 3),
        'yield_mpa':  yield_mpa,
        'FOS':        round(FOS, 2),
        'safe':       safe,
        'x_crit':     round(x_crit, 3),
        'L': L, 'P': P, 'a': a, 'w': w,
        'D_mm': D * 1000.0, 'material': mat,
    })


@app.route('/explain', methods=['POST'])
def explain():
    """
    AI explanation endpoint using Groq streaming.
    Sends the simulation results to a language model and streams back
    a step-by-step engineering explanation.
    """
    d = request.json
    client = get_groq_client()

    if client is None:
        def err_stream():
            yield f"data: {json.dumps({'text': 'Groq API key not set. Set GROQ_API_KEY environment variable to enable AI explanations.'})}\n\n"
            yield "data: [DONE]\n\n"
        return Response(err_stream(), mimetype='text/event-stream')

    prompt = f"""You are writing a SHORT step-by-step calculation sheet for a beam mechanics simulation. Use ONLY the exact values provided below. Do NOT invent or change any numbers.

GIVEN VALUES:
- Beam Length (L) = {d['L']} m
- Point Load (P) = {d['P']} N at x = {d['a']} m
- UDL (w) = {d['w']} N/m across full span
- Diameter (D) = {d['D_mm']} mm
- Material = {d['material']} (yield = {d['yield_mpa']} MPa)

CALCULATED RESULTS (use these exact numbers):
- R_A = {d['R_A']} N
- R_B = {d['R_B']} N
- V_max = {d['V_max']} N
- M_max = {d['M_max']} N*m at x = {d['x_crit']} m
- sigma_max = {d['sigma_mpa']} MPa
- FOS = {d['FOS']}
- Status = {"SAFE" if d['safe'] else "FAIL"}

Write your response in this EXACT format with these numbered sections. Keep each section 2-3 lines max:

**1. Reactions R_A and R_B**
Show the equilibrium equations, plug in values, state R_A and R_B.

**2. Shear Force (SFD)**
State where the jumps occur and the max/min shear values.

**3. Bending Moment (BMD)**
State where M_max occurs and its value.

**4. Bending Stress**
Show sigma = M*y/I formula, plug in D={d['D_mm']}mm, state sigma result.

**5. Safety Check**
Compare sigma vs yield, state FOS, say if SAFE or FAIL.

RULES:
- Use ONLY the exact numbers given above, do not recalculate
- No LaTeX, use plain text formulas like: R_B = (P*a + w*L^2/2) / L
- Total response MUST be under 200 words
- Be direct, no filler phrases like "Let me explain" or "Great question"
- Use ** for bold section headers only"""

    def stream():
        try:
            resp = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_completion_tokens=1200,
                stream=True,
            )
            for chunk in resp:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield f"data: {json.dumps({'text': delta.content})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'text': f'Error: {str(e)}'})}\n\n"
        yield "data: [DONE]\n\n"

    return Response(stream(), mimetype='text/event-stream')


if __name__ == '__main__':
    app.run(port=5000, debug=False)
