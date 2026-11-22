# =============================================================================
# styles.py — Single source of truth for OsdagBridge report formatting
# -----------------------------------------------------------------------------
# Every layout rule, colour, spacing value and table style used by the report
# generator lives here. Chapter files and report_generator.py import from this
# module; nothing formatting-related should be hardcoded elsewhere.
# =============================================================================

# ── 1. Document / page geometry ──────────────────────────────────────────────
DOC_CLASS      = "report"
DOC_FONT_PT    = "12pt"
DOC_PAPER      = "a4paper"
LINE_STRETCH   = 1.15

PAGE = {
    "left": "1in", "right": "1in", "top": "1in",
    # Reserve explicit room for header/footer so table rows can never run into
    # them (fix for footer overlap, e.g. row "G4" on p.30).
    "bottom": "1.15in",
    "headheight": "16pt",
    "headsep": "14pt",
    "footskip": "34pt",
}

# ── 2. Colour palette ────────────────────────────────────────────────────────
COLORS = {                       # name -> hex (no '#')
    "osdagGreen": "91B014",
    "osdagDark":  "5E7409",
    "tableHead":  "EAF1CF",
    "tableAlt":   "F7F9EE",
    "passGreen":  "2E7D32",
    "failRed":    "C62828",
}
PRIMARY = "osdagGreen"

# ── 3. Table layout ──────────────────────────────────────────────────────────
TABLE = {
    "tabcolsep": "6pt",
    "arraystretch": "1.12",
    "arrayrulewidth": "0.5pt",
    "extrarowheight": "0.6pt",
    "LTpre": "0pt",
    "LTpost": "6pt",
    "needspace_lines": 10,         # break to a new page if fewer lines remain
    "row_skip": r"\\[6pt]",       # row terminator used by chapter tables
    "head_bg": "tableHead",       # header-row shading
}

# ── 4. Header / footer ───────────────────────────────────────────────────────
FOOTER_LEFT = r"Osdag $|$ FOSSEE $|$ Indian Institute of Technology Bombay"
FOOTER_RIGHT = r"Page \thepage\ of \pageref{LastPage}"
RULE_WIDTH = "1pt"

# ── 5. Chart style (matplotlib) ──────────────────────────────────────────────
CHART = {
    "dpi": 200,
    "figsize": (6.4, 3.6),
    "pass_color": "#" + COLORS["osdagGreen"],
    "fail_color": "#" + COLORS["failRed"],
    "threshold_color": "red",
    "threshold_ls": "--",
    "font_size": 9,
    "include_width": r"0.85\textwidth",
}

# ── 6. Live-load table column specs ──────────────────────────────────────────
LL_TABLE_SPEC = r"|L{2.8cm}|C{2.0cm}|C{1.9cm}|C{2.5cm}|C{1.8cm}|C{2.2cm}|"


def preamble_packages() -> str:
    """LaTeX package block + global length settings (built from the values above)."""
    colors = "\n".join(
        r"\definecolor{%s}{HTML}{%s}" % (k, v) for k, v in COLORS.items()
    )
    g = PAGE
    t = TABLE
    return r"""
\documentclass[%(font)s,%(paper)s]{%(cls)s}

\usepackage[a4paper, left=%(left)s, right=%(right)s, top=%(top)s, bottom=%(bottom)s,
            headheight=%(headheight)s, headsep=%(headsep)s, footskip=%(footskip)s]{geometry}
\usepackage{graphicx}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{booktabs}
\usepackage{array}
\usepackage{tabularx}
\usepackage{float}
\usepackage{fancyhdr}
\usepackage[hidelinks]{hyperref}
\usepackage[table]{xcolor}
\usepackage{setspace}
\usepackage{enumitem}
\usepackage{caption}
\captionsetup{labelfont=bf, justification=raggedright, singlelinecheck=false, format=plain}
\usepackage{subcaption}
\usepackage{multirow}
\usepackage{colortbl}
\usepackage{longtable}
\setlength{\LTleft}{\fill}
\setlength{\LTright}{\fill}
\usepackage{titlesec}
\usepackage{titletoc}
\usepackage{lastpage}
\usepackage{makecell}
\usepackage{etoolbox}
\usepackage{needspace}

\numberwithin{table}{chapter}
\numberwithin{figure}{chapter}
\setlength{\tabcolsep}{%(tabcolsep)s}
\renewcommand{\arraystretch}{%(arraystretch)s}
\setlength{\LTpre}{%(LTpre)s}
\setlength{\LTpost}{%(LTpost)s}
\setlength{\arrayrulewidth}{%(arrayrulewidth)s}
\setlength{\extrarowheight}{%(extrarowheight)s}

%% Keep tables off the footer: break first if too little room remains.
\BeforeBeginEnvironment{table}{\needspace{%(ns)d\baselineskip}}
%% Table rows stay intact; ragged bottom avoids stretched spacing.
\AtBeginEnvironment{longtable}{\raggedbottom}

%(colors)s
""" % dict(
        font=DOC_FONT_PT, paper=DOC_PAPER, cls=DOC_CLASS,
        left=g["left"], right=g["right"], top=g["top"], bottom=g["bottom"],
        headheight=g["headheight"], headsep=g["headsep"], footskip=g["footskip"],
        tabcolsep=t["tabcolsep"], arraystretch=t["arraystretch"],
        LTpre=t["LTpre"], LTpost=t["LTpost"],
        arrayrulewidth=t["arrayrulewidth"], extrarowheight=t["extrarowheight"],
        ns=t["needspace_lines"], colors=colors,
    )


def pagestyles(pn: str, jn: str, rd: str, rv: str) -> str:
    """Header/footer page styles (main, plain share one definition; firstpage differs)."""
    body = r"""
  \fancyhf{}
  \fancyhead[L]{%(pn)s $|$ %(jn)s}
  \fancyhead[R]{%(rd)s $|$ %(rv)s}
  \fancyfoot[L]{%(fl)s}
  \fancyfoot[R]{%(fr)s}
  \renewcommand{\headrule}{\color{%(pc)s}\hrule width\headwidth height %(rw)s \vspace{2pt}}
  \renewcommand{\footrule}{%%
    \ifbool{hasSDonPage}{%%
      \vspace{-20pt}%%
      \hbox to \headwidth{\textcolor{black}{\footnotesize\textit{* Software default value}}\hfil}%%
      \vspace{4pt}%%
    }{%%
      \vspace{-8pt}%%
    }%%
    \color{%(pc)s}\hrule width\headwidth height %(rw)s \vspace{6pt}%%
  }
""" % dict(pn=pn, jn=jn, rd=rd, rv=rv, fl=FOOTER_LEFT, fr=FOOTER_RIGHT,
           pc=PRIMARY, rw=RULE_WIDTH)
    first = r"""
\fancypagestyle{firstpage}{
  \fancyhf{}
  \renewcommand{\headrulewidth}{0pt}
  \fancyfoot[L]{%s}
  \fancyfoot[R]{%s}
  \renewcommand{\footrule}{\vspace{-8pt}\color{%s}\hrule width\headwidth height %s \vspace{6pt}}
}
""" % (FOOTER_LEFT, FOOTER_RIGHT, PRIMARY, RULE_WIDTH)
    return (r"\fancypagestyle{main}{" + body + "}\n"
            r"\fancypagestyle{plain}{" + body + "}\n" + first)


def custom_commands() -> str:
    return r"""
\pagestyle{main}
\setstretch{%s}

\newcommand{\placeholder}[1]{\textit{\textless #1\textgreater}}
\newcommand{\todo}[1]{\colorbox{yellow}{TODO: #1}}
\newcolumntype{L}[1]{>{\raggedright\arraybackslash}p{#1}}
\newcolumntype{C}[1]{>{\centering\arraybackslash}p{#1}}
\newcolumntype{R}[1]{>{\raggedleft\arraybackslash}p{#1}}

\newcommand{\sdstar}{\textsuperscript{*}}
\newbool{hasSDonPage}
\boolfalse{hasSDonPage}
\newcommand{\markSD}{\global\booltrue{hasSDonPage}}
\renewcommand{\sdstar}{\textsuperscript{*}\markSD{}}
\AddToHook{shipout/before}{\global\boolfalse{hasSDonPage}}
""" % LINE_STRETCH
