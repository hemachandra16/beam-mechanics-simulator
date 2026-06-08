# PROJECT CONTEXT FILE — Beam Mechanics Simulator
# (Paste this into ChatGPT and ask it to write your report section)

---

## What This Project Is

I built a **Beam Mechanics Simulator** using **Python** with the **Matplotlib** and **NumPy** libraries.
It is a desktop application with a full graphical user interface (GUI) built using **PyQt5**.
The tool simulates the structural behaviour of a **Simply Supported Beam (SSB)** under various loading conditions.

This is NOT a web app or a paid software tool — it is a completely original simulation
coded from scratch in Python using free, open-source libraries (Matplotlib, NumPy, PyQt5).
Matplotlib is a Python plotting library (similar to MATLAB's plotting capability) and
NumPy handles all the numerical/engineering calculations.

---

## What Type of Simulation This Is

The simulation performs **Structural / Beam Mechanics Analysis**, specifically:

- **Shear Force Diagram (SFD)** — shows how shear force varies along the beam length
- **Bending Moment Diagram (BMD)** — shows how bending moment varies along the beam length
- **Bending Stress Analysis** — calculates the maximum bending stress at the critical section
- **Safety Factor Check** — compares calculated stress against the material's yield strength

The BMD follows the **Indian structural engineering convention**:
sagging moments are drawn **below** the baseline (on the tension face), which matches
what is taught in Indian engineering textbooks and universities.

---

## What Loads the Beam Can Handle

The simulator supports three loading scenarios:

1. **Point Load only** — a single concentrated force at any position along the beam
2. **UDL only** — a Uniformly Distributed Load spread across the full span of the beam
3. **Combined Loading** — both a point load AND a UDL simultaneously (most realistic case)

---

## What Inputs the User Can Change (All via Sliders — Real-Time)

| Input | Range | Unit |
|-------|-------|------|
| Beam Length (L) | 1.0 m to 10.0 m | metres |
| Point Load (P) | 0 to 2000 | Newtons (N) |
| Load Position (a) | 0 to L | metres from left support |
| UDL Intensity (w) | 0 to 500 | N/m |
| Beam Diameter (D) | 20 to 200 | millimetres (circular cross-section) |
| Material | Steel / Aluminum / Timber | (changes yield strength) |

Every time any slider is moved, ALL diagrams and results update **instantly in real time**.

---

## What the Software Calculates and Displays

### Engineering Results (shown on screen)
- **R_A** — Reaction force at left support A (Newtons)
- **R_B** — Reaction force at right support B (Newtons)
- **V_max** — Maximum shear force along the beam (Newtons)
- **M_max** — Maximum bending moment (Newton-metres), with exact location shown
- **σ_max (sigma)** — Maximum bending stress at the critical section (MPa)
- **σ_yield** — Yield strength of the selected material (MPa)
- **FOS** — Factor of Safety (yield strength ÷ actual stress)
- **SAFE / FAIL** status — automatically determined

### Visual Diagrams (plotted live)
1. **Beam Diagram** — shows the beam with support triangles, UDL arrows, point load arrow,
   reaction labels (R_A, R_B), and beam length dimension
2. **SFD (Shear Force Diagram)** — positive shear in blue fill, negative shear in red fill,
   annotated with V_max and V_min values
3. **BMD (Bending Moment Diagram)** — green fill, plotted below baseline (Indian convention),
   annotated with M_max value and exact position

---

## Material Options and Their Yield Strengths

| Material | Yield Strength |
|----------|---------------|
| Steel | 250 MPa |
| Aluminum | 270 MPa |
| Timber | 40 MPa |

---

## What Happens When the Beam Fails

If the calculated bending stress exceeds the yield strength of the selected material:
- The safety badge turns red and shows **[FAIL]**
- A **crack symbol** appears on the beam diagram at the exact failure point
- A **STRUCTURAL FAILURE** warning flashes on screen
- The exact location of failure (x coordinate) is shown

---

## Engineering Formulas the Software Uses

These are standard textbook formulas for a simply supported beam:

**Reactions (from Static Equilibrium):**
- R_B = (P × a + w × L² / 2) / L
- R_A = P + w × L − R_B

**Shear Force at any point x:**
- V(x) = R_A − w×x − P × H(x − a)
  where H is the Heaviside step function (activates at the load position)

**Bending Moment at any point x:**
- M(x) = R_A×x − w×x²/2 − P × ⟨x − a⟩
  where ⟨x − a⟩ is the Macaulay bracket (zero before load, active after)

**Bending Stress (circular cross-section):**
- I = π × D⁴ / 64   (Second Moment of Area)
- σ = M_max × (D/2) / I

**Factor of Safety:**
- FOS = σ_yield / σ_max

---

## Verified Test Case (Confirmed Correct by Hand)

**Inputs used:**
- Beam Length = 5 m
- Point Load = 1000 N at 2 m from A
- UDL = 200 N/m over full span
- Diameter = 100 mm (circular cross-section)
- Material = Steel (yield = 250 MPa)

**Results (software output matches hand calculation exactly):**

| Quantity | Value |
|----------|-------|
| R_A | 1100.0 N |
| R_B | 900.0 N |
| Maximum Shear | 1100.0 N (at support A) |
| Maximum Moment | 1800.0 N·m (at x = 2.0 m) |
| Maximum Bending Stress | 18.33 MPa |
| Factor of Safety | 13.64 |
| Status | SAFE |

---

## What Makes This Simulation Useful / Educational

1. **Real-time interactivity** — the user can move ANY slider and see how the SFD and BMD
   shape changes instantly. This builds intuition about how load position, span length,
   and load intensity affect beam behaviour.

2. **Combined loading** — most textbook examples only show one load type at a time.
   This simulator handles both point load and UDL simultaneously, which is more realistic.

3. **Safety analysis built-in** — the simulation does not just draw diagrams; it goes further
   and tells the engineer whether the beam is safe for the selected material and cross-section.
   This is relevant to real engineering design.

4. **Indian BMD convention** — follows the standard taught in Indian universities where
   sagging moments are plotted below the baseline (on the tension side of the beam).

5. **Multiple materials** — the user can instantly compare how Steel, Aluminum, and Timber
   perform under the same loading conditions.

6. **Animate feature** — the software can animate the point load ramping up from zero to
   the selected value, showing how diagrams evolve progressively as load increases.

7. **Exact numerical accuracy** — the simulation pins the load position exactly in the
   numerical array, so there is zero discretisation error in M_max and stress calculation.

---

## What Software/Libraries Were Used (V1 — Highlighted Version)

- **Python** — programming language
- **NumPy** — all engineering calculations (array-based, fast, accurate)
- **Matplotlib** — all plot rendering (SFD, BMD, beam diagram)
- **PyQt5** — graphical user interface (window, sliders, radio buttons, buttons)
- Packaged as a **standalone .exe** — no installation of Python required to run

This is comparable to what MATLAB does for engineering simulation,
but built entirely with free Python libraries.

---

## What This Project Demonstrates (for Report Context)

- Application of static equilibrium (ΣF = 0, ΣM = 0) to a real structural problem
- Shear force and bending moment diagram construction using standard beam theory
- Macaulay's method for writing beam equations as continuous functions
- Flexure formula (σ = My/I) applied to circular cross-sections
- Engineering safety analysis using Factor of Safety
- Real-time software simulation as a learning and design tool
- Python as a capable engineering computation environment

---
