# =============================================================================
# longtable_utils.py — repeat column headers on every page of every longtable
# -----------------------------------------------------------------------------
# The chapter files emit longtables whose first row is a header row but never
# declare \endfirsthead / \endhead, so continuation pages have no headers.
# `add_repeating_headers()` rewrites each longtable once, centrally, so chapter
# code stays unchanged and every table gets:
#   * caption + header on the first page          (\endfirsthead)
#   * "Table X.Y (continued)" + header on each    (\endhead)
#     following page
#   * "Continued on next page" foot               (\endfoot / \endlastfoot)
# =============================================================================
import re
from osdagbridge.core.reports.styles import TABLE

NEED = ""   # no forced page-break rule: it conflicts with longtable first-page logic
_BEGIN = re.compile(r"\\begin\{longtable\}(\[[^\]]*\])?")


def _match_brace(s: str, i: int) -> int:
    """s[i] == '{' → index of its matching '}' (or -1)."""
    depth = 0
    for j in range(i, len(s)):
        c = s[j]
        if c == "\\":
            continue
        if c == "{" and (j == 0 or s[j - 1] != "\\"):
            depth += 1
        elif c == "}" and (j == 0 or s[j - 1] != "\\"):
            depth -= 1
            if depth == 0:
                return j
    return -1


def count_columns(spec: str) -> int:
    """Number of real columns in a tabular column spec (ignores |, >{..}, <{..}, @{..})."""
    n, i = 0, 0
    while i < len(spec):
        c = spec[i]
        if c in "><@!":
            j = spec.find("{", i)
            i = _match_brace(spec, j) + 1
            continue
        if c in "pmbLCRX":
            n += 1
            if i + 1 < len(spec) and spec[i + 1] == "{":
                i = _match_brace(spec, i + 1)
        elif c in "clr":
            n += 1
        i += 1
    return n


def _find_row_end(s: str, start: int) -> int:
    """Index just after the first top-level '\\\\' (plus optional [..]) from start."""
    depth, i = 0, start
    while i < len(s) - 1:
        c = s[i]
        if c == "\\" and s[i + 1] == "\\" and depth == 0:
            j = i + 2
            m = re.match(r"\s*\[[^\]]*\]", s[j:])
            return j + (m.end() if m else 0)
        if c == "\\":
            i += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    return -1


def _rewrite(block_head: str, spec: str, body: str) -> str:
    """body = everything between the column spec and \\end{longtable}."""
    if r"\endhead" in body or r"\endfirsthead" in body:
        return None

    m = re.match(r"(\s*)(\\caption(?:\[[^\]]*\])?\s*)", body)
    caption = ""
    rest = body
    if m:
        cstart = m.start(2)
        brace = body.find("{", m.end(2) - 1 if body[m.end(2) - 1] == "{" else m.end(2) - 0)
        # locate the caption's argument group
        k = body.find("{", cstart + len(r"\caption"))
        end = _match_brace(body, k)
        if end < 0:
            return None
        caption = body[cstart:end + 1]
        rest = body[end + 1:]
        rest = re.sub(r"^\s*\\\\(\[[^\]]*\])?", "", rest)   # drop an existing \\ after caption

    m2 = re.match(r"\s*\\hline\s*", rest)
    if not m2:
        return None
    hstart = m2.end()
    hend = _find_row_end(rest, hstart)
    if hend < 0:
        return None
    header = rest[hstart:hend].strip()
    if r"\textbf" not in header or r"\multirow" in header:
        return None            # first row is data, not a header — leave table alone
    after = rest[hend:]
    after = re.sub(r"^\s*\\hline", "", after, count=1)   # header's closing \hline (re-added below)

    n = count_columns(spec)
    label = r"Table~\thetable\ (continued)" if caption else r"(continued from previous page)"
    cont = (r"\multicolumn{%d}{l}{\small\textit{%s}} \\" % (n, label))
    foot = (r"\multicolumn{%d}{r}{\small\textit{Continued on next page}} \\" % n)
    first = (caption + r"\\" + "\n" if caption else "")
    out = (
        NEED + block_head + "{" + spec + "}\n"
        + first
        + r"\hline" + "\n" + header + "\n" + r"\hline" + "\n"
        + r"\endfirsthead" + "\n"
        + cont + "\n" + r"\hline" + "\n" + header + "\n" + r"\hline" + "\n"
        + r"\endhead" + "\n"
        + after.lstrip("\n")
    )
    return out


def _fix_caption(body: str) -> str:
    """A longtable \\caption must be followed by \\\\ ; without it LaTeX raises
    'Misplaced \\noalign' on the next \\hline. Add it where missing."""
    m = re.match(r"(\s*)\\caption(\[[^\]]*\])?\s*\{", body)
    if not m:
        return body
    k = m.end() - 1
    end = _match_brace(body, k)
    if end < 0 or re.match(r"\s*\\\\", body[end + 1:]):
        return body
    return body[:end + 1] + "\\\\" + body[end + 1:]


def add_repeating_headers(tex: str) -> str:
    """Return tex with \\endfirsthead/\\endhead blocks added to every longtable."""
    out, pos = [], 0
    for m in _BEGIN.finditer(tex):
        if m.start() < pos:
            continue
        spec_open = m.end()
        if spec_open >= len(tex) or tex[spec_open] != "{":
            continue
        spec_close = _match_brace(tex, spec_open)
        end_tag = tex.find(r"\end{longtable}", spec_close)
        if spec_close < 0 or end_tag < 0:
            continue
        spec = tex[spec_open + 1:spec_close]
        body = tex[spec_close + 1:end_tag]
        new = _rewrite(m.group(0), spec, body)
        out.append(tex[pos:m.start()])
        if new is None:
            out.append(NEED + tex[m.start():spec_close + 1] + _fix_caption(body))
        else:
            out.append(new)
        pos = end_tag
    out.append(tex[pos:])
    return "".join(out)
