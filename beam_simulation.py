"""
Beam Mechanics Simulator -- SFD & BMD Analysis  (PyQt5 Edition)
================================================================
A complete engineering simulation for Shear Force Diagram (SFD) and
Bending Moment Diagram (BMD) of a simply supported beam.

Supports:
  - Point loads (single concentrated force)
  - Uniformly Distributed Loads (UDL)
  - Combined loading (point + UDL simultaneously)
  - Real-time interactive sliders and material selector
  - Animated loading sequence (QTimer-based, non-blocking)
  - Bending stress and safety factor analysis

Engineering Formulae Used:
  - Equilibrium:  SFy = 0,  SM_A = 0
  - Shear Force:  V(x) = R_A - P*H(x-a) - w*x
  - Bending Moment: M(x) = R_A*x - P*<x-a> - w*x^2/2
  - Bending Stress: sigma = M*y / I   (y = D/2 for extreme fibre)
  - Moment of Inertia (circular): I = pi*D^4 / 64
"""

import sys
import numpy as np

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QSlider, QPushButton, QRadioButton,
    QButtonGroup, QFrame, QSizePolicy, QSpacerItem,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.patches import Polygon

# ---------------------------------------------------------------------------
# COLOR CONSTANTS
# ---------------------------------------------------------------------------
BG_MAIN  = '#0a0a0a'
BG_PANEL = '#0d0d0d'
BG_CARD  = '#111111'
BORDER   = '#2a2a2a'
BORDER2  = '#1e1e1e'
AMBER    = '#E8A838'
BLUE     = '#4FC3F7'
TEXT1    = '#F5F5F5'
TEXT2    = '#9E9E9E'
GREEN    = '#66BB6A'
RED      = '#EF5350'

# ---------------------------------------------------------------------------
# QSS STYLESHEET
# ---------------------------------------------------------------------------
STYLESHEET = """
QMainWindow, QWidget {
    background-color: #0a0a0a;
    color: #F5F5F5;
    font-family: 'Courier New', monospace;
}
QSlider::groove:horizontal {
    height: 3px;
    background: #1e1e1e;
    border-radius: 2px;
    margin: 0px;
}
QSlider::handle:horizontal {
    background: #E8A838;
    width: 14px;
    height: 14px;
    margin: -6px 0px;
    border-radius: 7px;
}
QSlider::sub-page:horizontal {
    background: #E8A838;
    border-radius: 2px;
}
QPushButton {
    background: transparent;
    border: 1px solid #E8A838;
    color: #E8A838;
    font-family: 'Courier New';
    font-weight: bold;
    padding: 7px 16px;
    border-radius: 3px;
    font-size: 10px;
    min-width: 120px;
}
QPushButton:hover {
    background: rgba(232, 168, 56, 0.12);
}
QPushButton:disabled {
    border-color: #444;
    color: #444;
}
QPushButton#resetBtn {
    border-color: #EF5350;
    color: #EF5350;
}
QPushButton#resetBtn:hover {
    background: rgba(239, 83, 80, 0.12);
}
QRadioButton {
    color: #9E9E9E;
    font-size: 9px;
    font-family: 'Courier New';
    spacing: 5px;
}
QRadioButton:checked {
    color: #F5F5F5;
}
QRadioButton::indicator {
    width: 11px;
    height: 11px;
    border-radius: 6px;
    border: 1px solid #555;
    background: transparent;
}
QRadioButton::indicator:checked {
    background: #E8A838;
    border-color: #E8A838;
}
"""


# ---------------------------------------------------------------------------
# MATPLOTLIB CANVAS WIDGET
# ---------------------------------------------------------------------------
class MplCanvas(FigureCanvasQTAgg):
    """Reusable matplotlib canvas for embedding in Qt layouts."""

    def __init__(self, width=8, height=2.5):
        self.fig = Figure(figsize=(width, height), facecolor=BG_PANEL)
        self.fig.subplots_adjust(left=0.07, right=0.97, top=0.86, bottom=0.18)
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setStyleSheet(f"background-color: {BG_PANEL}; border: none;")


# ---------------------------------------------------------------------------
# MAIN SIMULATOR WINDOW
# ---------------------------------------------------------------------------
class BeamSimulator(QMainWindow):
    """
    Simulates a simply supported beam under point load and/or UDL.
    Computes support reactions, SFD, BMD, bending stress, and checks safety.
    """

    MATERIALS = {
        'Steel':    250.0,
        'Aluminum': 270.0,
        'Timber':    40.0,
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Beam Mechanics Simulator -- SFD & BMD Analysis')
        self.setFixedSize(1400, 850)

        # -- Animation state --
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._anim_step)
        self.anim_step_count = 0
        self.anim_target = 0

        # -- Build everything --
        self._build_ui()

        # -- Initial draw --
        self.update_all()

    # ===================================================================
    #  BUILD UI
    # ===================================================================

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ROW 1 — Title bar
        root.addWidget(self._build_title_bar())

        # ROW 2 — Main content (plots + right panel)
        main_row = QHBoxLayout()
        main_row.setSpacing(0)
        main_row.setContentsMargins(0, 0, 0, 0)

        # Left: plots
        plots_widget = QWidget()
        plots_widget.setStyleSheet(f"background-color: {BG_MAIN};")
        plots_layout = QVBoxLayout(plots_widget)
        plots_layout.setContentsMargins(4, 4, 0, 4)
        plots_layout.setSpacing(2)

        self.canvas_beam = MplCanvas(width=8, height=1.8)
        self.canvas_beam.setFixedHeight(170)
        self.ax_beam = self.canvas_beam.ax
        plots_layout.addWidget(self.canvas_beam)

        self.canvas_sfd = MplCanvas(width=8, height=2.5)
        self.canvas_sfd.setSizePolicy(QSizePolicy.Expanding,
                                      QSizePolicy.Expanding)
        self.ax_sfd = self.canvas_sfd.ax
        plots_layout.addWidget(self.canvas_sfd, stretch=1)

        self.canvas_bmd = MplCanvas(width=8, height=2.5)
        self.canvas_bmd.setSizePolicy(QSizePolicy.Expanding,
                                      QSizePolicy.Expanding)
        self.ax_bmd = self.canvas_bmd.ax
        plots_layout.addWidget(self.canvas_bmd, stretch=1)

        main_row.addWidget(plots_widget, stretch=1)

        # Right: inputs panel
        main_row.addWidget(self._build_inputs_panel())

        main_container = QWidget()
        main_container.setLayout(main_row)
        root.addWidget(main_container, stretch=1)

        # ROW 3 — Results strip
        root.addWidget(self._build_results_strip())

        # ROW 4 — Controls bar
        root.addWidget(self._build_controls_bar())

    # -------------------------------------------------------------------
    def _build_title_bar(self):
        bar = QWidget()
        bar.setFixedHeight(44)
        bar.setStyleSheet(
            f"background-color: {BG_CARD}; "
            f"border-bottom: 1px solid {BORDER};"
        )
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(14, 0, 14, 0)

        title = QLabel('BEAM MECHANICS SIMULATOR')
        title.setFont(QFont('Courier New', 14, QFont.Bold))
        title.setStyleSheet(f"color: {TEXT1}; border: none;")

        subtitle = QLabel('SFD & BMD Analysis | Simply Supported Beam')
        subtitle.setFont(QFont('Courier New', 9))
        subtitle.setStyleSheet("color: #555555; border: none;")
        subtitle.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(subtitle)
        return bar

    # -------------------------------------------------------------------
    def _build_inputs_panel(self):
        panel = QFrame()
        panel.setFixedWidth(210)
        panel.setStyleSheet(
            f"QFrame#inputsPanel {{ background: {BG_PANEL}; "
            f"border-left: 1px solid {BORDER}; }}"
        )
        panel.setObjectName('inputsPanel')

        vbox = QVBoxLayout(panel)
        vbox.setContentsMargins(10, 10, 10, 10)
        vbox.setSpacing(6)

        header = QLabel('INPUTS')
        header.setFont(QFont('Courier New', 9, QFont.Bold))
        header.setStyleSheet(f"color: {AMBER}; border: none;")
        vbox.addWidget(header)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {BORDER}; border: none;")
        vbox.addWidget(sep)

        def make_card(key_text):
            card = QFrame()
            card.setStyleSheet(
                f"background: {BG_CARD}; border: 1px solid {BORDER2}; "
                f"border-radius: 3px;"
            )
            row = QHBoxLayout(card)
            row.setContentsMargins(8, 5, 8, 5)
            row.setSpacing(4)

            key_lbl = QLabel(key_text)
            key_lbl.setFont(QFont('Courier New', 8))
            key_lbl.setStyleSheet(f"color: {TEXT2}; border: none;")

            val_lbl = QLabel('--')
            val_lbl.setFont(QFont('Courier New', 8, QFont.Bold))
            val_lbl.setStyleSheet(f"color: {BLUE}; border: none;")
            val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            row.addWidget(key_lbl)
            row.addWidget(val_lbl, stretch=1)
            return card, val_lbl

        card_l, self.inp_L = make_card('L')
        card_p, self.inp_P = make_card('P')
        card_udl, self.inp_UDL = make_card('UDL')
        card_d, self.inp_D = make_card('D')
        card_mat, self.inp_mat = make_card('Material')

        for c in [card_l, card_p, card_udl, card_d, card_mat]:
            vbox.addWidget(c)

        vbox.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Minimum,
                                       QSizePolicy.Expanding))
        return panel

    # -------------------------------------------------------------------
    def _build_results_strip(self):
        strip = QWidget()
        strip.setFixedHeight(68)
        strip.setStyleSheet(
            f"background-color: {BG_PANEL}; "
            f"border-top: 1px solid {BORDER};"
        )

        layout = QHBoxLayout(strip)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(4)

        def make_metric_card(header_text):
            card = QFrame()
            card.setStyleSheet(
                f"background: {BG_CARD}; border: 1px solid {BORDER2}; "
                f"border-radius: 3px;"
            )
            vbox = QVBoxLayout(card)
            vbox.setContentsMargins(6, 4, 6, 4)
            vbox.setSpacing(1)

            hdr = QLabel(header_text)
            hdr.setFont(QFont('Courier New', 7))
            hdr.setStyleSheet(f"color: {TEXT2}; border: none;")
            hdr.setAlignment(Qt.AlignCenter)

            val = QLabel('--')
            val.setFont(QFont('Courier New', 11, QFont.Bold))
            val.setStyleSheet(f"color: {AMBER}; border: none;")
            val.setAlignment(Qt.AlignCenter)

            vbox.addWidget(hdr)
            vbox.addWidget(val)
            return card, val

        c1, self.res_RA   = make_metric_card('R_A')
        c2, self.res_RB   = make_metric_card('R_B')
        c3, self.res_Vmax = make_metric_card('V_max')
        c4, self.res_Mmax = make_metric_card('M_max')

        for c in [c1, c2, c3, c4]:
            layout.addWidget(c, stretch=1)

        # Stress card (wider)
        stress_card = QFrame()
        stress_card.setStyleSheet(
            f"background: {BG_CARD}; border: 1px solid {BORDER2}; "
            f"border-radius: 3px;"
        )
        self._stress_card = stress_card
        stress_layout = QHBoxLayout(stress_card)
        stress_layout.setContentsMargins(12, 6, 12, 6)
        stress_layout.setSpacing(12)

        self.res_sigma = QLabel('sigma: -- MPa')
        self.res_sigma.setFont(QFont('Courier New', 9, QFont.Bold))
        self.res_sigma.setStyleSheet(f"color: {BLUE}; border: none;")

        self.res_yield = QLabel('yield: -- MPa')
        self.res_yield.setFont(QFont('Courier New', 9))
        self.res_yield.setStyleSheet(f"color: {TEXT2}; border: none;")

        self.res_fos = QLabel('FOS: --')
        self.res_fos.setFont(QFont('Courier New', 9, QFont.Bold))
        self.res_fos.setStyleSheet(f"color: {BLUE}; border: none;")

        self.res_safety = QLabel('[SAFE]')
        self.res_safety.setFont(QFont('Courier New', 10, QFont.Bold))
        self.res_safety.setStyleSheet(f"color: {GREEN}; border: none;")

        for w in [self.res_sigma, self.res_yield, self.res_fos,
                  self.res_safety]:
            stress_layout.addWidget(w)

        layout.addWidget(stress_card, stretch=2)
        return strip

    # -------------------------------------------------------------------
    def _build_controls_bar(self):
        bar = QWidget()
        bar.setFixedHeight(185)
        bar.setStyleSheet(
            f"background-color: {BG_PANEL}; "
            f"border-top: 2px solid {BORDER};"
        )

        outer = QHBoxLayout(bar)
        outer.setContentsMargins(10, 8, 10, 8)
        outer.setSpacing(0)

        # -- LEFT: Sliders --
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(5)

        def make_slider_row(row, label_text, smin, smax, sdef):
            lbl = QLabel(label_text)
            lbl.setFont(QFont('Courier New', 8))
            lbl.setStyleSheet(f"color: {TEXT2}; border: none;")
            lbl.setFixedWidth(115)
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            grid.addWidget(lbl, row, 0)

            slider = QSlider(Qt.Horizontal)
            slider.setMinimum(smin)
            slider.setMaximum(smax)
            slider.setValue(sdef)
            slider.setSingleStep(1)
            grid.addWidget(slider, row, 1)

            val_lbl = QLabel('')
            val_lbl.setFont(QFont('Courier New', 9, QFont.Bold))
            val_lbl.setStyleSheet(f"color: {BLUE}; border: none;")
            val_lbl.setFixedWidth(75)
            val_lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            grid.addWidget(val_lbl, row, 2)

            return slider, val_lbl

        self.sl_L,   self.lbl_L   = make_slider_row(0, 'Beam Length',  100, 1000, 500)
        self.sl_P,   self.lbl_P   = make_slider_row(1, 'Point Load',     0, 2000, 1000)
        self.sl_pos, self.lbl_pos = make_slider_row(2, 'Load Position',  0,  500, 200)
        self.sl_udl, self.lbl_udl = make_slider_row(3, 'UDL Intensity',  0,  500, 200)
        self.sl_dia, self.lbl_dia = make_slider_row(4, 'Diameter',      20,  200, 100)

        # Connect sliders
        self.sl_L.valueChanged.connect(self.update_pos_slider_max)
        self.sl_L.valueChanged.connect(self.update_all)
        self.sl_P.valueChanged.connect(self.update_all)
        self.sl_pos.valueChanged.connect(self.update_all)
        self.sl_udl.valueChanged.connect(self.update_all)
        self.sl_dia.valueChanged.connect(self.update_all)

        slider_widget = QWidget()
        slider_widget.setLayout(grid)
        slider_widget.setStyleSheet("border: none;")
        outer.addWidget(slider_widget, stretch=1)

        # -- SEPARATOR --
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setFixedWidth(1)
        sep.setStyleSheet(f"background-color: {BORDER}; border: none;")
        sep.setContentsMargins(0, 4, 0, 4)
        outer.addWidget(sep)

        # -- RIGHT: Material + Buttons --
        right = QVBoxLayout()
        right.setContentsMargins(14, 0, 0, 0)
        right.setSpacing(8)

        mat_label = QLabel('MATERIAL')
        mat_label.setFont(QFont('Courier New', 8, QFont.Bold))
        mat_label.setStyleSheet(f"color: {AMBER}; border: none;")
        right.addWidget(mat_label)

        self.rb_steel  = QRadioButton('Steel   (250 MPa)')
        self.rb_alum   = QRadioButton('Aluminum (270 MPa)')
        self.rb_timber = QRadioButton('Timber  ( 40 MPa)')
        self.rb_steel.setChecked(True)

        self.mat_group = QButtonGroup(self)
        self.mat_group.addButton(self.rb_steel, 0)
        self.mat_group.addButton(self.rb_alum, 1)
        self.mat_group.addButton(self.rb_timber, 2)

        for rb in [self.rb_steel, self.rb_alum, self.rb_timber]:
            rb.setStyleSheet("border: none;")
            rb.toggled.connect(self.update_all)
            right.addWidget(rb)

        right.addSpacerItem(QSpacerItem(0, 6, QSizePolicy.Minimum,
                                        QSizePolicy.Fixed))

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_animate = QPushButton('>> ANIMATE')
        self.btn_animate.clicked.connect(self.start_animate)

        self.btn_reset = QPushButton('RESET')
        self.btn_reset.setObjectName('resetBtn')
        self.btn_reset.clicked.connect(self.reset_all)

        btn_row.addWidget(self.btn_animate)
        btn_row.addWidget(self.btn_reset)
        right.addLayout(btn_row)

        right.addStretch()

        right_widget = QWidget()
        right_widget.setFixedWidth(200)
        right_widget.setLayout(right)
        right_widget.setStyleSheet("border: none;")
        outer.addWidget(right_widget)

        return bar

    # ===================================================================
    #  GET VALUES FROM UI
    # ===================================================================

    def get_values(self):
        """Read all slider/radio state and return a dict of float values."""
        L = self.sl_L.value() / 100.0
        P = float(self.sl_P.value())
        a = self.sl_pos.value() / 100.0
        a = min(a, L)  # safety clamp
        w = float(self.sl_udl.value())
        D = self.sl_dia.value() / 1000.0

        if self.rb_steel.isChecked():
            mat = 'Steel'
            yield_str = 250e6
        elif self.rb_alum.isChecked():
            mat = 'Aluminum'
            yield_str = 270e6
        else:
            mat = 'Timber'
            yield_str = 40e6

        return {
            'L': L, 'P': P, 'a': a, 'w': w, 'D': D,
            'mat': mat, 'yield_str': yield_str,
            'yield_MPa': yield_str / 1e6,
        }

    # ===================================================================
    #  ENGINEERING CALCULATIONS
    # ===================================================================

    def calculate(self, vals):
        """
        Run all engineering calculations and return a results dict.

        Reactions (static equilibrium):
            R_B = (P * a + w * L^2 / 2) / L
            R_A = P + w * L - R_B

        Shear force (Heaviside step):
            V(x) = R_A - w*x - P * H(x - a)

        Bending moment (Macaulay bracket):
            M(x) = R_A*x - w*x^2/2 - P * <x - a>

        Bending stress (circular cross-section):
            I = pi * D^4 / 64
            sigma = M_max * (D/2) / I
        """
        L = vals['L']
        P = vals['P']
        a = vals['a']
        w = vals['w']
        D = vals['D']
        yield_str = vals['yield_str']

        # Insert exact load position so Heaviside/Macaulay activate at precisely x=a
        x = np.sort(np.unique(np.append(np.linspace(0, L, 1000), [a])))

        # -- Reactions --
        R_B = (P * a + w * L**2 / 2.0) / L
        R_A = P + w * L - R_B

        # -- Shear force at each x --
        V = R_A - w * x - P * (x >= a).astype(float)

        # -- Bending moment at each x --
        M = R_A * x - w * x**2 / 2.0 - P * np.maximum(x - a, 0.0)

        # -- Bending stress --
        I = np.pi * D**4 / 64.0
        y = D / 2.0
        M_max_abs = np.max(np.abs(M))

        if I > 0 and M_max_abs > 0:
            sigma = M_max_abs * y / I        # Pascals
            sigma_MPa = sigma / 1e6
            FOS = yield_str / sigma
        else:
            sigma = 0.0
            sigma_MPa = 0.0
            FOS = 9999.0

        safe = sigma < yield_str

        V_max = np.max(V)
        V_min = np.min(V)

        return {
            'x': x, 'V': V, 'M': M,
            'R_A': R_A, 'R_B': R_B,
            'V_max': V_max, 'V_min': V_min,
            'M_max': M_max_abs,
            'sigma_MPa': sigma_MPa,
            'yield_MPa': vals['yield_MPa'],
            'FOS': FOS,
            'safe': safe,
        }

    # ===================================================================
    #  POSITION SLIDER MAX UPDATE
    # ===================================================================

    def update_pos_slider_max(self):
        """Keep Load Position slider max in sync with Beam Length."""
        new_max = self.sl_L.value()
        self.sl_pos.setMaximum(new_max)
        if self.sl_pos.value() > new_max:
            self.sl_pos.setValue(new_max // 2)

    # ===================================================================
    #  MASTER UPDATE
    # ===================================================================

    def update_all(self):
        """Recalculate everything and update all UI elements."""
        vals = self.get_values()
        results = self.calculate(vals)

        # -- Draw all 3 canvases --
        self.draw_beam(vals, results)
        self.draw_sfd(vals, results)
        self.draw_bmd(vals, results)

        # -- Update inputs panel --
        self.inp_L.setText(f"{vals['L']:.1f} m")
        self.inp_P.setText(f"{vals['P']:.0f} N @ {vals['a']:.1f} m")
        self.inp_UDL.setText(f"{vals['w']:.0f} N/m")
        self.inp_D.setText(f"{vals['D']*1000:.0f} mm")
        self.inp_mat.setText(vals['mat'])

        # -- Update slider value labels --
        self.lbl_L.setText(f"{vals['L']:.1f} m")
        self.lbl_P.setText(f"{vals['P']:.0f} N")
        self.lbl_pos.setText(f"{vals['a']:.1f} m")
        self.lbl_udl.setText(f"{vals['w']:.0f} N/m")
        self.lbl_dia.setText(f"{vals['D']*1000:.0f} mm")

        # -- Update results strip --
        self.res_RA.setText(f"{results['R_A']:.1f} N")
        self.res_RB.setText(f"{results['R_B']:.1f} N")
        self.res_Vmax.setText(f"{max(abs(results['V_max']), abs(results['V_min'])):.1f} N")
        self.res_Mmax.setText(f"{results['M_max']:.1f} N*m")
        self.res_sigma.setText(f"sigma: {results['sigma_MPa']:.2f} MPa")
        self.res_yield.setText(f"yield: {results['yield_MPa']:.0f} MPa")
        self.res_fos.setText(f"FOS: {results['FOS']:.2f}")

        if results['safe']:
            self.res_safety.setText('[SAFE]')
            self.res_safety.setStyleSheet(
                f"color: {GREEN}; font-weight: bold; border: none;")
            self._stress_card.setStyleSheet(
                f"background: {BG_CARD}; border: 1px solid {BORDER2}; "
                f"border-radius: 3px;")
        else:
            overshoot = (results['sigma_MPa'] / results['yield_MPa'] - 1) * 100
            self.res_safety.setText(f'[FAIL] +{overshoot:.1f}%')
            self.res_safety.setStyleSheet(
                f"color: {RED}; font-weight: bold; border: none;")
            self._stress_card.setStyleSheet(
                f"background: #1a0808; border: 1px solid {RED}; "
                f"border-radius: 3px;")

    # ===================================================================
    #  COMMON AXES SETUP
    # ===================================================================

    def _setup_ax(self, ax, fig):
        """Apply common dark theme to a matplotlib axes."""
        ax.clear()
        ax.set_facecolor(BG_PANEL)
        ax.tick_params(colors=TEXT2, labelsize=7)
        ax.xaxis.label.set_color(TEXT2)
        ax.yaxis.label.set_color(TEXT2)
        for sp in ax.spines.values():
            sp.set_color(BORDER)
            sp.set_linewidth(0.8)
        ax.grid(color=BORDER2, alpha=0.5, linestyle='--', linewidth=0.5)
        fig.patch.set_facecolor(BG_PANEL)

    # ===================================================================
    #  DRAW BEAM DIAGRAM
    # ===================================================================

    def draw_beam(self, vals, results):
        """Draw the beam schematic with supports, loads, and labels."""
        ax = self.ax_beam
        fig = self.canvas_beam.fig
        self._setup_ax(ax, fig)
        ax.grid(False)

        L = vals['L']
        P = vals['P']
        a = vals['a']
        w = vals['w']
        R_A = results['R_A']
        R_B = results['R_B']

        ax.set_xlim(-0.05 * L, 1.05 * L)
        ax.set_ylim(-0.5, 1.5)
        ax.axis('off')

        # Beam line
        ax.plot([0, L], [0.5, 0.5], color=BLUE, linewidth=5,
                solid_capstyle='round', zorder=5)

        # Support triangles at x=0 and x=L
        tw = 0.08 * L
        for xpos in [0, L]:
            tri = Polygon(
                [[xpos - tw, 0.3], [xpos + tw, 0.3], [xpos, 0.5]],
                closed=True, facecolor=AMBER, edgecolor=AMBER,
                linewidth=1.0, zorder=6,
            )
            ax.add_patch(tri)

        # UDL arrows
        if w > 0:
            n_arrows = min(20, max(8, int(L * 3)))
            xs = np.linspace(0.02 * L, 0.98 * L, n_arrows)
            for xi in xs:
                ax.annotate('', xy=(xi, 0.5), xytext=(xi, 1.1),
                            arrowprops=dict(arrowstyle='->', color=BLUE,
                                            lw=1.0), zorder=4)
            ax.plot([0.02 * L, 0.98 * L], [1.1, 1.1],
                    color=BLUE, linewidth=1.5, zorder=4)
            ax.text(L / 2, 1.25, f'UDL = {w:.0f} N/m', ha='center',
                    color=BLUE, fontsize=8, fontfamily='Courier New')

        # Point load arrow
        if P > 0:
            ax.annotate('', xy=(a, 0.5), xytext=(a, 0.95),
                        arrowprops=dict(arrowstyle='->', color=RED,
                                        lw=2.0), zorder=7)
            ax.text(a, 1.0, f'P = {P:.0f} N', ha='center',
                    color=RED, fontsize=8, fontfamily='Courier New')

        # Support labels and reactions
        ax.text(0, 0.2, f'A\nR_A={R_A:.1f}N', ha='center',
                color=AMBER, fontsize=7, fontfamily='Courier New')
        ax.text(L, 0.2, f'B\nR_B={R_B:.1f}N', ha='center',
                color=AMBER, fontsize=7, fontfamily='Courier New')
        ax.text(L / 2, 0.05, f'L = {L:.1f} m', ha='center',
                color=TEXT2, fontsize=7, fontfamily='Courier New')

        ax.set_title('Beam Diagram', loc='left', color=AMBER,
                     fontsize=8, fontweight='bold', pad=4,
                     fontfamily='Courier New')

        self.canvas_beam.draw()

    # ===================================================================
    #  DRAW SFD
    # ===================================================================

    def draw_sfd(self, vals, results):
        """Draw the Shear Force Diagram with dual-color fill."""
        ax = self.ax_sfd
        fig = self.canvas_sfd.fig
        self._setup_ax(ax, fig)

        x = results['x']
        V = results['V']
        L = vals['L']

        ax.fill_between(x, V, 0, where=(V >= 0),
                        color=BLUE, alpha=0.3, interpolate=True)
        ax.fill_between(x, V, 0, where=(V < 0),
                        color=RED, alpha=0.25, interpolate=True)
        ax.plot(x, V, color=BLUE, linewidth=1.2, zorder=5)
        ax.axhline(0, color=TEXT2, linewidth=0.5, linestyle='--')

        # V_max annotation
        idx_max = np.argmax(V)
        ax.annotate(
            f'V_max = {V[idx_max]:.1f} N',
            xy=(x[idx_max], V[idx_max]),
            xytext=(x[idx_max] + 0.05 * L, V[idx_max]),
            color=TEXT1, fontsize=7, fontfamily='Courier New',
            bbox=dict(boxstyle='round,pad=0.3', facecolor=BG_CARD,
                      edgecolor=AMBER, alpha=0.9),
            arrowprops=dict(arrowstyle='->', color=AMBER, lw=0.8),
        )

        # V_min annotation -- flip if near right edge
        idx_min = np.argmin(V)
        if x[idx_min] > 0.75 * L:
            xoffset = -0.15 * L
            ha = 'right'
        else:
            xoffset = 0.05 * L
            ha = 'left'
        ax.annotate(
            f'V_min = {V[idx_min]:.1f} N',
            xy=(x[idx_min], V[idx_min]),
            xytext=(x[idx_min] + xoffset, V[idx_min]),
            ha=ha, color=TEXT1, fontsize=7, fontfamily='Courier New',
            bbox=dict(boxstyle='round,pad=0.3', facecolor=BG_CARD,
                      edgecolor=RED, alpha=0.9),
            arrowprops=dict(arrowstyle='->', color=RED, lw=0.8),
        )

        ax.set_xlabel('Position (m)', fontsize=7, fontfamily='Courier New')
        ax.set_ylabel('Shear Force (N)', fontsize=7, fontfamily='Courier New')
        ax.set_title('Shear Force Diagram (SFD)', loc='left',
                     color=AMBER, fontsize=8, fontweight='bold', pad=4,
                     fontfamily='Courier New')

        self.canvas_sfd.draw()

    # ===================================================================
    #  DRAW BMD
    # ===================================================================

    def draw_bmd(self, vals, results):
        """Draw the Bending Moment Diagram with green fill.

        Follows Indian structural convention: sagging moments (positive)
        are plotted BELOW the baseline (tension face is at the bottom).
        The annotation label still shows the true positive M_max value.
        """
        ax = self.ax_bmd
        fig = self.canvas_bmd.fig
        self._setup_ax(ax, fig)

        x = results['x']
        M = results['M']
        L = vals['L']

        # Indian convention: negate for display so sagging appears below zero
        M_disp = -M

        ax.fill_between(x, M_disp, 0, color=GREEN, alpha=0.3)
        ax.plot(x, M_disp, color=GREEN, linewidth=1.5, zorder=5)
        ax.axhline(0, color=TEXT2, linewidth=0.5, linestyle='--')

        # M_max annotation — label shows positive value, dot plotted at -M[idx]
        idx = np.argmax(np.abs(M))
        ax.plot(x[idx], M_disp[idx], 'o', color=BLUE, markersize=5, zorder=10)
        ax.axvline(x[idx], color=TEXT2, linewidth=0.5, linestyle='--',
                   alpha=0.5)
        ax.annotate(
            f'M_max = {M[idx]:.1f} N*m\n@ x = {x[idx]:.2f} m',
            xy=(x[idx], M_disp[idx]),
            xytext=(x[idx] + 0.05 * L, M_disp[idx] * 0.85),
            color=TEXT1, fontsize=7, fontfamily='Courier New',
            bbox=dict(boxstyle='round,pad=0.3', facecolor=BG_CARD,
                      edgecolor=AMBER, alpha=0.9),
            arrowprops=dict(arrowstyle='->', color=AMBER, lw=0.8),
        )

        ax.set_xlabel('Position (m)', fontsize=7, fontfamily='Courier New')
        ax.set_ylabel('Moment (N·m)  [Indian conv: sagging ↓]',
                      fontsize=7, fontfamily='Courier New')
        ax.set_title('Bending Moment Diagram (BMD)', loc='left',
                     color=AMBER, fontsize=8, fontweight='bold', pad=4,
                     fontfamily='Courier New')

        self.canvas_bmd.draw()

    # ===================================================================
    #  ANIMATE
    # ===================================================================

    def start_animate(self):
        """Begin animation: ramp point load from 0 to current value."""
        if self.anim_timer.isActive():
            return
        self.anim_target = self.sl_P.value()
        self.anim_step_count = 0
        self.sl_P.setValue(0)
        self.btn_animate.setEnabled(False)
        self.anim_timer.start(25)

    def _anim_step(self):
        """Single animation tick called by QTimer."""
        self.anim_step_count += 1
        steps = 45
        val = int(self.anim_target * self.anim_step_count / steps)
        self.sl_P.setValue(val)
        if self.anim_step_count >= steps:
            self.anim_timer.stop()
            self.sl_P.setValue(self.anim_target)
            self.btn_animate.setEnabled(True)

    # ===================================================================
    #  RESET
    # ===================================================================

    def reset_all(self):
        """Reset all controls to default values."""
        self.sl_L.setValue(500)
        self.sl_P.setValue(1000)
        self.sl_pos.setValue(200)
        self.sl_udl.setValue(200)
        self.sl_dia.setValue(100)
        self.rb_steel.setChecked(True)
        self.update_all()


# =======================================================================
#  ENTRY POINT
# =======================================================================

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setStyleSheet(STYLESHEET)
    window = BeamSimulator()
    window.resize(1400, 850)
    window.show()
    sys.exit(app.exec_())
