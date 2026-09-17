"""
PE6201 · A2 scaffold — CONFIGURATION
====================================================================
THIS IS THE VENDOR-NEUTRAL BLOCK THE BRIEF ASKS FOR (D5).

Everything that knows which model you are using lives here and in
backend_live.py, and nowhere else. Switching model is changing a string.

    BACKEND = "scripted"   free, deterministic, no key, no network.
                           THIS MUST BE THE DEFAULT IN WHAT YOU SUBMIT.
                           A marker clones your repository and runs it
                           this way. If it does not run, D5(a) fails and
                           Technical Execution is capped.

    BACKEND = "live"       real model through OpenRouter. Costs money.
                           Only D5(b) - your model battery - needs this.

The guardrail checklist (D3b), the reproducible run (D5a) and the two
failure reproductions (D7) ALL run scripted. Only the battery is live.
====================================================================
"""
import os
import sys

# ─────────────────────────────────────────────────────────────────────
# THE THREE STRINGS. Change these, change nothing else.
# ─────────────────────────────────────────────────────────────────────
BACKEND = "scripted"          # "scripted" | "live"

MODEL = "openai/gpt-4o-mini"  # only used when BACKEND == "live"
BASE_URL = "https://openrouter.ai/api/v1"

# Your key never goes in this file. Put it in the environment:
#     export OPENROUTER_API_KEY="sk-or-..."
# In Colab:  os.environ["OPENROUTER_API_KEY"] = "sk-or-..."
API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

# ─────────────────────────────────────────────────────────────────────
# WHICH PROBLEM. "A" = claims first response, "B" = referral coordination.
# ─────────────────────────────────────────────────────────────────────
PROBLEM = "A"

# ─────────────────────────────────────────────────────────────────────
# WHICH TOOL-DESCRIPTOR VERSION (D2b). This is the ONLY thing that
# differs between the two arms of the descriptor experiment.
#
#   "v2"  tools.DESCRIPTORS - what we argue for. THE COMMITTED DEFAULT.
#         check_coverage also returns `required_document` in this arm.
#   "v1"  descriptors_v1.py - FROZEN 2026-09-17, the control arm.
#         Member 6 runs this on the SAME MODEL Member 1 uses for v2;
#         change the model as well and the comparison measures nothing.
#
# "v1" and "v2" are the same number of bytes, so the stale-bytecode trap
# below applies to this setting exactly as it does to PROBLEM.
# ─────────────────────────────────────────────────────────────────────
PROMPT_VERSION = "v2"

# ─────────────────────────────────────────────────────────────────────
# GUARDRAIL LIMITS (D3a). These are the code layer. Set them from
# EVIDENCE, not from a round number - see D7. If your median run is 4
# turns and your worst legitimate run is 7, a cap of 8 is defensible
# and a cap of 30 is decoration.
# ─────────────────────────────────────────────────────────────────────
MAX_TURNS = 8                 # step cap
MAX_TOKENS_PER_RUN = 60000    # budget ceiling
AUTONOMY = "confirm"          # "suggest" | "confirm" | "act"
#   suggest  - the agent proposes; a human does everything
#   confirm  - the agent does everything EXCEPT the irreversible step,
#              which waits for a yes. THE GATE GOES IN FRONT OF THE
#              IRREVERSIBLE STEP, not in front of the agent.
#   act      - the agent completes the irreversible step itself

# ─────────────────────────────────────────────────────────────────────
# WHERE THE DATA IS. The scaffold ships in its own folder, so it looks
# for the reference data next door. If you moved things, set the
# environment variable A2_DATA instead of editing this.
# ─────────────────────────────────────────────────────────────────────
HERE = os.path.dirname(os.path.abspath(__file__))

_CANDIDATES = [
    os.environ.get("A2_DATA", ""),
    os.path.join(HERE, "..", "A2_reference_data"),
    os.path.join(HERE, "A2_reference_data"),
    os.path.join(HERE, "..", "fixtures"),
    os.path.join(HERE, ".."),
]


def data_root():
    """Find the folder that holds data_A/ and data_B/.

    Fails LOUDLY with instructions rather than returning something wrong.
    A silent wrong path here is exactly the failure the data guide warns
    about: your tools return nothing and the run still looks fine.
    """
    for c in _CANDIDATES:
        if c and os.path.isdir(os.path.join(c, "data_A")) \
             and os.path.isdir(os.path.join(c, "data_B")):
            return os.path.abspath(c)
    raise SystemExit(
        "\n  Could not find the reference data.\n"
        "  I looked for a folder containing BOTH data_A/ and data_B/ in:\n"
        + "".join("    %s\n" % os.path.abspath(c) for c in _CANDIDATES if c)
        + "\n  Fix it either way:\n"
        "    1. put A2_reference_data/ next to this scaffold folder, or\n"
        "    2. export A2_DATA=/path/to/A2_reference_data\n")


# ─────────────────────────────────────────────────────────────────────
# PRICES, US dollars per MILLION tokens. Section 7 of the brief.
#
# KEYED BY MODEL, on purpose. Six of us run six different models against
# the same harness, and the scaffold's own rule is that switching model
# is changing one string. With a single hardcoded pair, changing that
# string left everyone else's price in place and the cost column came out
# confidently wrong - the exact failure D6 is marked on, and one that
# looks like a result rather than a mistake.
#
# Read from openrouter.ai/api/v1/models on 17 September 2026 by
# docs/evidence/refresh_prices.py. Re-run it before quoting these; if a
# price moved, the script says so and this table is what it corrects.
# ─────────────────────────────────────────────────────────────────────
PRICES = {
    "openai/gpt-4o-mini":                       (0.150, 0.600),
    "qwen/qwen3.8-flash":                        (0.150, 0.470),
    "meta-llama/llama-3.3-70b-instruct":         (0.100, 0.320),
    "mistralai/mistral-small-3.2-24b-instruct":  (0.094, 0.250),
    "deepseek/deepseek-chat":                    (0.257, 1.029),
}

# What an unlisted model falls back to. Deliberately not a real price:
# it is high enough to be noticed in a cost table rather than blend in.
_FALLBACK = (1.000, 3.000)


def prices():
    """(in, out) per million tokens for the model currently configured."""
    if MODEL in PRICES:
        return PRICES[MODEL]
    if BACKEND == "live":
        sys.stderr.write(
            "\n  PRICE NOT ON FILE for %r.\n"
            "  Costs are being computed at the placeholder US$%.3f/%.3f and\n"
            "  are WRONG. Add your model to PRICES in config.py - the real\n"
            "  numbers are one call away:\n"
            "      python3 docs/evidence/refresh_prices.py\n\n"
            % ((MODEL,) + _FALLBACK))
    return _FALLBACK


PRICE_IN, PRICE_OUT = prices()


def _stale_bytecode_warning():
    """Detect Python reusing an out-of-date __pycache__ copy of THIS file.

    WHY THIS EXISTS. Changing PROBLEM = "B" to "A" edits one character and
    leaves the file the SAME SIZE. If the edit lands in the same second as
    the last run, Python's staleness check - (source mtime, source size) -
    sees no change and silently reuses the compiled copy. You edit the
    file, run it, and get the OLD value with no error at all.

    That happened during development of this scaffold, so it will happen
    to you. It is also a small lesson in its own right: the most expensive
    bugs are the ones that produce a confident, wrong, unremarkable answer.

    The fix is `rm -rf __pycache__`, or in a notebook, restart the kernel.
    """
    import re
    try:
        src = open(os.path.join(HERE, "config.py"), encoding="utf-8").read()
    except OSError:
        return ""
    out = []
    for name, live in (("PROBLEM", PROBLEM), ("BACKEND", BACKEND),
                       ("PROMPT_VERSION", PROMPT_VERSION)):
        m = re.search(r'^%s\s*=\s*"([^"]*)"' % name, src, re.M)
        if m and m.group(1) != live:
            out.append("%s is %r in config.py but %r in memory"
                       % (name, m.group(1), live))
    if not out:
        return ""
    return ("\n  !! STALE BYTECODE - PYTHON IS IGNORING YOUR EDIT !!\n"
            + "".join("     %s\n" % o for o in out)
            + "     fix:  rm -rf __pycache__      (in a notebook: restart the kernel)\n")


def summary():
    """One line, printed at the top of every run, so you always know
    which backend produced the numbers you are looking at.

    It also carries the stale-bytecode check, because this line is the
    one place every entry point already prints."""
    where = "FREE, deterministic" if BACKEND == "scripted" else "LIVE - this costs money"
    model = "(no model)" if BACKEND == "scripted" else MODEL
    line = ("BACKEND=%s  %s  |  PROBLEM=%s  |  prompt=%s  |  model=%s  |  "
            "cap=%d turns  |  autonomy=%s"
            % (BACKEND, where, PROBLEM, PROMPT_VERSION, model,
               MAX_TURNS, AUTONOMY))
    return line + _stale_bytecode_warning()
