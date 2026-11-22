# =============================================================================
# loads_tables.py — Chapter 3 live-load tables (vehicle LL and footway LL)
# Vehicle rows follow exactly the vehicles ticked in the UI (Additional Inputs
# → Loading tab); footway load is a separate table. Column layout comes from
# styles.LL_TABLE_SPEC.
# =============================================================================
from osdagbridge.core.utils.common import (
    KEY_LL_CUSTOM_VEHICLES, KEY_LL_FOOTPATH_PRESSURE_MODE, KEY_LL_FOOTPATH_PRESSURE_VALUE,
    KEY_LL_IRC_70R_BOGIE, KEY_LL_IRC_70R_TRACKED, KEY_LL_IRC_70R_WHEELED,
    KEY_LL_IRC_AA_TRACKED, KEY_LL_IRC_AA_WHEELED, KEY_LL_IRC_CLASS_A,
    KEY_LL_IRC_CLASS_FATIGUE, KEY_LL_IRC_CLASS_SV, KEY_SPAN,
)
from osdagbridge.core.reports.report_utils import _tex
from osdagbridge.core.reports.styles import LL_TABLE_SPEC, TABLE

NA = "---"
BRAKING_ECCENTRICITY_M = "1.2"      # IRC 6 Cl. 211.2: braking force acts 1.2 m above road surface

# (UI key, display name, total load in kN or None if not fixed by the standard,
#  impact clause family 'A' | 'AA' | None, braking considered?)
# Total loads are the standard IRC 6 train/vehicle weights; None → shown as '---'.
_VEHICLES = [
    (KEY_LL_IRC_CLASS_A,       "Class A",               554.0,  "A",  True),
    (KEY_LL_IRC_70R_WHEELED,   "Class 70R (Wheeled)",   1000.0, "AA", True),
    (KEY_LL_IRC_70R_TRACKED,   "Class 70R (Tracked)",   700.0,  "AA", True),
    (KEY_LL_IRC_70R_BOGIE,     "Class 70R (Bogie)",     None,   "AA", True),
    (KEY_LL_IRC_AA_WHEELED,    "Class AA (Wheeled)",    400.0,  "AA", True),
    (KEY_LL_IRC_AA_TRACKED,    "Class AA (Tracked)",    700.0,  "AA", True),
    (KEY_LL_IRC_CLASS_SV,      "Class SV",              None,   None, False),
    (KEY_LL_IRC_CLASS_FATIGUE, "Class Fatigue",         None,   None, False),
]


def _span(input_dict):
    try:
        return float(input_dict.get(KEY_SPAN))
    except (TypeError, ValueError):
        return None


def _impact(family, span, irc6):
    if family is None or span is None:
        return NA
    try:
        im = (irc6.cl_208_2_impact_factor(span) if family == "A"
              else irc6.cl_208_3_impact_factor(span))
        return f"{1.0 + im:.3f}"
    except Exception:
        return NA


def _carriageway_width(input_dict):
    """Find the carriageway width by scanning the input keys (no dependence on KEY_ names)."""
    import re
    for k, v in input_dict.items():
        kl = str(k).lower()
        if "carriageway" in kl:
            m = re.search(r"\d+(?:\.\d+)?", str(v))
            if m:
                return float(m.group())
    return None


def _braking_kN(input_dict, irc6):
    """IRC 6 Cl. 211.2 braking force (function returns tonnes) -> kN."""
    try:
        width = _carriageway_width(input_dict)
        lanes = irc6.table_6(width)
        if isinstance(lanes, dict):
            lanes = lanes.get("design_lanes")
        t = irc6.cl_211_2_braking_force(int(lanes))
        return f"{t * 9.81:.1f}"
    except Exception as exc:       # shown in the console so a failure is never silent
        keys = [k for k in input_dict if any(w in str(k).lower() for w in ("carriage", "width", "lane"))]
        print(f"[BRAKING-DEBUG] could not compute braking force: {exc!r}; width={_carriageway_width(input_dict)!r}; keys={keys}")
        return NA


def vehicle_rows(input_dict, irc6):
    """List of 6-tuples of already-escaped strings, one per vehicle selected in the UI."""
    span = _span(input_dict)
    brake = _braking_kN(input_dict, irc6)
    rows = []
    for key, name, total, fam, braking in _VEHICLES:
        if not input_dict.get(key):
            continue
        rows.append((name, f"{total:.0f}" if total else NA, _impact(fam, span, irc6),
                     "Yes" if braking else "No",
                     brake if braking else NA,
                     BRAKING_ECCENTRICITY_M if braking else NA))
    custom = input_dict.get(KEY_LL_CUSTOM_VEHICLES)
    if isinstance(custom, list):
        for c in custom:
            if isinstance(c, dict) and c.get("name"):
                tl = c.get("total_load") or c.get("total_load_kN")
                rows.append((_tex(c["name"]), _tex(tl) if tl else NA, NA, NA, NA, NA))
            elif isinstance(c, str) and c:
                rows.append((_tex(c), NA, NA, NA, NA, NA))
    return rows


def vehicle_ll_table(input_dict, irc6):
    """Short table (<= ~10 rows) -> plain table float; avoids longtable page-edge quirks."""
    rows = vehicle_rows(input_dict, irc6)
    if not rows:
        body = r"\multicolumn{6}{|c|}{No vehicle live load selected} \\" + "\n\\hline"
    else:
        body = "\n".join(" & ".join(r) + r" \\[6pt]" + "\n\\hline" for r in rows)
    head = (
        r"\textbf{Vehicle} & \textbf{Total Load (kN)} & \textbf{Impact Factor} & "
        r"\multicolumn{3}{c|}{\textbf{Braking Load}} \\" "\n"
        r"\cline{4-6}" "\n"
        r" & & & \textbf{Considered?} & \textbf{Value (kN)} & \textbf{Eccentricity (m)} \\" "\n"
        r"\hline"
    )
    return (
        r"\vspace{1em}" "\n"
        r"\begin{table}[H]" "\n" r"\centering" "\n"
        r"\caption{\textbf{Live Loads (LL) --- Vehicle Loading}}" "\n"
        r"\begin{tabular}{" + LL_TABLE_SPEC + "}\n"
        r"\hline" "\n" + head + "\n" + body + "\n"
        r"\end{tabular}" "\n" r"\end{table}" "\n"
        r"\noindent\textit{Note: Vehicles listed are those selected in the Loading tab of Additional Inputs. "
        r"Impact factor = $1 + I$ per IRC 6 Cl. 208; braking force per IRC 6 Cl. 211.2 acts at the "
        r"eccentricity shown above the road surface. `---' = not applicable / not specified.}" "\n"
    )


def footway_ll_table(input_dict, irc6):
    mode = str(input_dict.get(KEY_LL_FOOTPATH_PRESSURE_MODE, "") or "")
    val = input_dict.get(KEY_LL_FOOTPATH_PRESSURE_VALUE, "")
    if mode.strip().lower() in ("as per irc 6", "as per irc6", "automatic"):
        try:
            value, ref = f"{irc6.cl_206_1_footway_load():.3f}", "IRC 6 Cl. 206.1"
        except Exception:
            value, ref = NA, "IRC 6 Cl. 206.1"
    elif val not in (None, ""):
        value, ref = _tex(val), "User-defined"
    else:
        value, ref = NA, NA
    spec = r"|L{4.8cm}|C{2.6cm}|C{2.2cm}|L{3.6cm}|"
    return (
        r"\vspace{1em}" "\n"
        r"\begin{table}[H]" "\n" r"\centering" "\n"
        r"\caption{\textbf{Live Loads (LL) --- Footway Loading}}" "\n"
        r"\begin{tabular}{" + spec + "}\n"
        r"\hline" "\n"
        r"\textbf{Parameter} & \textbf{Value} & \textbf{Unit} & \textbf{Basis} \\" "\n" r"\hline" "\n"
        r"Footpath pressure mode & " + (_tex(mode) or NA) + r" & --- & --- \\[6pt]" "\n" r"\hline" "\n"
        r"Footway live load intensity & " + value + r" & kN/m\textsuperscript{2} & " + ref + r" \\[6pt]" "\n"
        r"\hline" "\n"
        r"\end{tabular}" "\n" r"\end{table}" "\n"
    )
