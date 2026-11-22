# =============================================================================
# charts.py — programmatic charts for the OsdagBridge design report
#   * Utilization-Ratio bar charts  (Section 5.5)
#   * Material quantity bar charts  (Chapter 7)
# Images are saved into a temporary directory during report generation and
# embedded in LaTeX with a figure environment. All look-and-feel values come
# from styles.CHART.
# =============================================================================
import os
import re
import logging

from osdagbridge.core.reports.styles import CHART

logger = logging.getLogger(__name__)

# element → keyword prefixes found in the Table 5.22 row labels
UR_GROUPS = [
    ("Steel Plate Girders", ("Girder",)),
    ("Concrete Deck Slab",  ("Deck", "Crack Width", "Transverse Shear")),
    ("Cross Bracing",       ("Cross Bracing",)),
    ("End Diaphragms",      ("End Diaphragm",)),
]


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": CHART["font_size"], "axes.spines.top": False,
                         "axes.spines.right": False})
    return plt


def parse_ur(cell):
    """'\\textcolor{red}{1.12}' | '0.85' | '---' → float or None."""
    if cell is None:
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", re.sub(r"\\[a-zA-Z]+", "", str(cell)))
    try:
        return float(m.group()) if m else None
    except ValueError:
        return None


def group_for(label):
    for name, prefixes in UR_GROUPS:
        if any(str(label).startswith(p) for p in prefixes):
            return name
    return None


def _clean(label):
    return re.sub(r"\\[a-zA-Z]+\{?|[{}]", "", str(label)).replace("---", "-").strip()


def _threshold(ax, xmax):
    ax.axhline(1.0, color=CHART["threshold_color"], linestyle=CHART["threshold_ls"],
               linewidth=1.4, label="UR = 1.0 (limit)")
    ax.set_xlim(-0.6, xmax)


def _save(fig, out_dir, name):
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, name + ".png")
    fig.savefig(path, dpi=CHART["dpi"], bbox_inches="tight")
    _plt().close(fig)
    return path.replace("\\", "/")


def render_ur_charts(records, out_dir):
    """records: list of (row_label, ur_cell). Returns {name: png_path}."""
    plt = _plt()
    rows = []
    for label, cell in records:
        ur, grp = parse_ur(cell), group_for(label)
        if ur is not None and grp:
            rows.append((grp, _clean(label), ur))
    if not rows:
        return {}
    order = [n for n, _ in UR_GROUPS]
    rows.sort(key=lambda r: order.index(r[0]))      # keep checks of one element together
    paths = {}

    # (a) governing UR per primary element
    gov = []
    for name, _ in UR_GROUPS:
        vals = [r[2] for r in rows if r[0] == name]
        if vals:
            gov.append((name, max(vals)))
    fig, ax = plt.subplots(figsize=CHART["figsize"])
    colors = [CHART["pass_color"] if v <= 1.0 else CHART["fail_color"] for _, v in gov]
    bars = ax.bar([g[0].replace(" ", "\n", 1) for g in gov], [g[1] for g in gov],
                  color=colors, width=0.55)
    for b, (_, v) in zip(bars, gov):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.03, f"{v:.2f}", ha="center", fontsize=CHART["font_size"],
                bbox=dict(facecolor="white", edgecolor="none", pad=1.2))
    _threshold(ax, len(gov) - 0.4)
    ax.set_ylabel("Utilization Ratio (Demand / Capacity)")
    ax.set_ylim(0, max(1.15, max(v for _, v in gov) * 1.15))
    ax.set_title("Governing Utilization Ratio by Primary Element")
    ax.legend(loc="upper right", frameon=False)
    paths["ur_overall"] = _save(fig, out_dir, "ur_overall")

    # (b) every individual check, coloured by element
    palette = ["#4C6EF5", "#F59F00", "#12B886", "#AE3EC9"]
    fig, ax = plt.subplots(figsize=(CHART["figsize"][0] + 1.0, CHART["figsize"][1] + 0.9))
    xs = list(range(len(rows)))
    cols = [palette[[g for g, _ in UR_GROUPS].index(r[0])] if r[2] <= 1.0 else CHART["fail_color"]
            for r in rows]
    ax.bar(xs, [r[2] for r in rows], color=cols, width=0.7)
    for x, r in zip(xs, rows):
        ax.text(x, r[2] + 0.03, f"{r[2]:.2f}", ha="center", fontsize=CHART["font_size"] - 2,
                bbox=dict(facecolor="white", edgecolor="none", pad=0.8))
    ax.set_xticks(xs)
    ax.set_xticklabels([r[1] for r in rows], rotation=60, ha="right", fontsize=CHART["font_size"] - 2)
    _threshold(ax, len(rows) - 0.4)
    ax.set_ylabel("Utilization Ratio")
    ax.set_ylim(0, max(1.15, max(r[2] for r in rows) * 1.15))
    ax.set_title("Utilization Ratio of Individual Design Checks")
    from matplotlib.patches import Patch
    handles = [Patch(color=palette[i], label=n) for i, (n, _) in enumerate(UR_GROUPS)
               if any(r[0] == n for r in rows)]
    ax.legend(handles=handles + ax.get_legend_handles_labels()[0][:1], loc="upper right",
              frameon=False, fontsize=CHART["font_size"] - 1)
    paths["ur_checks"] = _save(fig, out_dir, "ur_checks")
    return paths


def _num(v):
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None


def render_material_charts(inputs, out_dir):
    """Uses the BOQ keys produced by boq_generator.calculate_material_quantities."""
    plt = _plt()
    paths = {}

    # (a) structural steel tonnage
    g = _num(inputs.get("steel_girders_wt_total"))
    br = [_num(inputs.get(f"bracing_{k}_wt_total")) for k in ("top", "bot", "diag")]
    br_sum = sum(x for x in br if x is not None) if any(x is not None for x in br) else None
    ed = _num(inputs.get("end_diaphragm_wt_total"))
    items = [("Girders", g), ("Cross Bracing", br_sum), ("End Diaphragms", ed)]
    if any(v is not None for _, v in items):
        fig, ax = plt.subplots(figsize=CHART["figsize"])
        vals = [v if v is not None else 0 for _, v in items]
        bars = ax.bar([n for n, _ in items], vals, color=CHART["pass_color"], width=0.55)
        top = max(vals) or 1
        for b, (_, v) in zip(bars, items):
            ax.text(b.get_x() + b.get_width() / 2, (v or 0) + top * 0.02,
                    f"{v:.2f}" if v is not None else "N.A.", ha="center", fontsize=CHART["font_size"])
        ax.set_ylabel("Structural Steel (MT)")
        ax.set_ylim(0, top * 1.18)
        ax.set_title("Structural Steel Tonnage")
        paths["mat_steel"] = _save(fig, out_dir, "mat_steel")

    # (b) concrete volume vs reinforcement weight (different units → two panels)
    cv, rw = _num(inputs.get("concrete_deck_vol_total")), _num(inputs.get("rebar_deck_wt_total"))
    if cv is not None or rw is not None:
        fig, (a1, a2) = plt.subplots(1, 2, figsize=CHART["figsize"])
        for ax, val, lab, unit, col in ((a1, cv, "Concrete (Deck Slab)", "Volume (m$^3$)", "#868E96"),
                                        (a2, rw, "Reinforcement Steel", "Weight (MT)", CHART["pass_color"])):
            ax.bar([lab], [val or 0], color=col, width=0.5)
            ax.text(0, (val or 0) * 1.02, f"{val:.2f}" if val is not None else "N.A.",
                    ha="center", va="bottom", fontsize=CHART["font_size"])
            ax.set_ylabel(unit)
            ax.set_ylim(0, (val or 1) * 1.2)
        fig.suptitle("Concrete Volume vs. Reinforcement Steel Weight")
        fig.tight_layout()
        paths["mat_concrete_rebar"] = _save(fig, out_dir, "mat_concrete_rebar")
    return paths


def figure_tex(rel_path, caption, width=None):
    """PyLaTeX-free figure environment (kept consistent with the rest of the report)."""
    return (r"\begin{figure}[H]" "\n" r"\centering" "\n"
            r"\includegraphics[width=" + (width or CHART["include_width"]) + "]{" + rel_path + "}\n"
            r"\caption{" + caption + "}\n" r"\end{figure}" "\n")
