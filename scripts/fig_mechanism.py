"""Figure 1 of the camera-ready: (a) any-turn vs final-turn detection under last/full;
(b) reconstructed operating points (FPR vs pooled CDR) at every filter strength.
All numbers are copied from results_public/ (per_decision_final_turn.csv,
table2_commercial_ci.csv, strength_curve.csv). Run from the paper directory:  python scripts/fig_mechanism.py  (writes fig_mechanism.pdf)
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

plt.rcParams.update({
    "pdf.fonttype": 42, "ps.fonttype": 42,          # TrueType, no Type 3 (IEEE PDF eXpress)
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Nimbus Roman", "DejaVu Serif"],
    "font.size": 7.5, "axes.labelsize": 7.5, "xtick.labelsize": 7, "ytick.labelsize": 7,
    "axes.linewidth": 0.6, "xtick.major.width": 0.5, "ytick.major.width": 0.5,
})
BLUE, ORANGE = "#2a78d6", "#eb6834"     # validated adjacent pair: last / full
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e1e0d9"

# ---- (a) any-turn vs final-turn attack detection: (last, full) ---------------
A = [  # product, any-turn (last, full), final-turn (last, full)
    ("Bedrock",            (0.670, 0.591), (0.375, 0.561)),
    ("Model Armor",        (0.781, 0.637), (0.413, 0.540)),
    ("Azure Text",         (0.113, 0.113), (0.025, 0.086)),
    ("Prompt Shields",     (0.000, 0.001), (0.000, 0.000)),
    ("Qwen3Guard (ref)",   (0.325, 0.293), (0.102, 0.257)),
]
# ---- (b) operating points: strength -> ((FPR,CDR) last, (FPR,CDR) full) -------
B = {
    "Bedrock":     ("o", [("HIGH", (0.142, 0.670), (0.130, 0.591)),
                          ("MED",  (0.112, 0.620), (0.104, 0.533)),
                          ("LOW",  (0.080, 0.521), (0.069, 0.427))]),
    "Model Armor": ("s", [("LOW+", (0.421, 0.781), (0.220, 0.637)),
                          ("MED+", (0.044, 0.286), (0.033, 0.266)),
                          ("HIGH", (0.015, 0.075), (0.016, 0.071))]),
    "Azure Text":  ("^", [("sev. 2", (0.018, 0.113), (0.015, 0.113)),
                          ("sev. 4", (0.006, 0.035), (0.005, 0.035)),
                          ("sev. 6", (0.003, 0.008), (0.004, 0.009))]),
}

fig, (ax, bx) = plt.subplots(2, 1, figsize=(3.45, 3.3),
                             gridspec_kw={"height_ratios": [1.0, 1.15], "hspace": 0.5})
for a in (ax, bx):
    for s in ("top", "right"):
        a.spines[s].set_visible(False)
    a.spines["left"].set_color("#c3c2b7"); a.spines["bottom"].set_color("#c3c2b7")
    a.tick_params(colors=MUTED, length=2.5)
    a.grid(axis="x", color=GRID, linewidth=0.5); a.set_axisbelow(True)

# (a) dumbbells ----------------------------------------------------------------
ys, labels = [], []
for i, (name, anyt, fin) in enumerate(A):
    base = (len(A) - 1 - i) * 1.0
    for k, (row, (l, f)) in enumerate((("any turn", anyt), ("final turn", fin))):
        y = base + (0.18 if k == 0 else -0.18)
        ax.plot([l, f], [y, y], color="#c3c2b7", linewidth=1.2, zorder=1, solid_capstyle="round")
        ax.scatter([l], [y], s=22, color=BLUE, zorder=3, linewidths=0)
        ax.scatter([f], [y], s=22, color=ORANGE, zorder=3, linewidths=0)
        ax.text(-0.015, y, row, ha="right", va="center", fontsize=6, color=MUTED)
        ys.append(y); labels.append("")
    ax.text(-0.175, base, name, ha="right", va="center", fontsize=7, color=INK)
ax.set_yticks([]); ax.set_xlim(0, 0.85); ax.set_ylim(-0.6, len(A) - 0.4)
ax.set_xlabel("attack detection rate", color=MUTED, labelpad=1.5)
ax.set_title("(a) any-turn vs. single-decision detection", loc="left", fontsize=7.5, color=INK, pad=4)
ax.legend(handles=[Line2D([], [], marker="o", color=BLUE, linestyle="", markersize=4.5, label="last"),
                   Line2D([], [], marker="o", color=ORANGE, linestyle="", markersize=4.5, label="full")],
          loc="lower right", frameon=False, fontsize=6.5, handletextpad=0.3, borderaxespad=0.2)

# (b) operating points ---------------------------------------------------------
for name, (mk, pts) in B.items():
    for lab, (fl, cl), (ff, cf) in pts:
        bx.plot([fl, ff], [cl, cf], color="#c3c2b7", linewidth=1.0, zorder=1)
        bx.scatter([fl], [cl], marker=mk, s=26, color=BLUE, zorder=3, linewidths=0)
        bx.scatter([ff], [cf], marker=mk, s=26, color=ORANGE, zorder=3, linewidths=0)
        if name == "Bedrock":
            bx.text(fl + 0.012, cl + 0.015, lab, fontsize=6, color=MUTED, va="bottom")
        elif name == "Model Armor":
            if lab == "LOW+":
                bx.text(fl - 0.012, cl + 0.015, lab, fontsize=6, color=MUTED, ha="right", va="bottom")
            elif lab == "MED+":
                bx.text(fl + 0.012, cl - 0.02, lab, fontsize=6, color=MUTED, va="top")
            else:
                bx.text(fl + 0.045, cl - 0.005, lab, fontsize=6, color=MUTED, va="center")
bx.text(0.19, 0.44, "Bedrock  (●)", fontsize=6.5, color=INK)
bx.text(0.235, 0.745, "Model Armor  (■)", fontsize=6.5, color=INK)
bx.annotate("Azure Text  (▲)\nsev. 2 / 4 / 6", xy=(0.02, 0.10), xytext=(0.12, 0.21),
            fontsize=6.5, color=INK, va="center",
            arrowprops=dict(arrowstyle="-", color="#898781", linewidth=0.6))
bx.set_xlim(0, 0.5); bx.set_ylim(0, 0.85)
bx.set_xlabel("benign false-positive rate", color=MUTED, labelpad=1.5)
bx.set_ylabel("pooled attack detection", color=MUTED, labelpad=2)
bx.grid(axis="y", color=GRID, linewidth=0.5)
bx.set_title("(b) operating points per filter strength (last → full)", loc="left",
             fontsize=7.5, color=INK, pad=4)

fig.subplots_adjust(left=0.355, right=0.985, top=0.95, bottom=0.075)
fig.savefig("fig_mechanism.pdf"); fig.savefig("fig_mechanism_preview.png", dpi=200)
print("wrote fig_mechanism.pdf")
