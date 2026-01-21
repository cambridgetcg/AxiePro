# Claude Code Integration Guide

## Quick Reference for Prompt Assessment

This document provides instructions for using the Prompt Effectiveness Assessor within Claude Code sessions.

---

## Inline Assessment (Fastest Method)

After running any exploration prompt, use this template to assess it:

```python
# Copy and adapt this assessment block

ASSESSMENT = {
    "prompt_id": "PROMPT-ID-HERE",
    "codebase": "PROJECT-NAME",
    "prompt_text": """
    Your prompt text here...
    """,
    "ratings": {
        "comprehension_depth": 4.0,    # CD: How deep is understanding?
        "coverage_breadth": 4.0,        # CB: How much territory covered?
        "accuracy": 4.0,                # AC: Are claims correct?
        "actionability": 4.0,           # AT: Can you act on insights?
        "bridging_capability": 4.0,     # BC: Does it connect parts?
        "domain_alignment": 4.0,        # DA: Relevant to app purpose?
        "clarity_structure": 4.0,       # CS: Well organized output?
        "efficiency": 4.0,              # EF: Good value vs tokens?
        "gap_detection": 4.0,           # GD: Identifies what's missing?
        "reproducibility": 4.0          # RP: Consistent results?
    },
    "tokens_used": 5000,
    "execution_time_minutes": 2.0
}

# Calculate score
weights = {"comprehension_depth": 0.15, "coverage_breadth": 0.12, "accuracy": 0.15,
           "actionability": 0.12, "bridging_capability": 0.10, "domain_alignment": 0.10,
           "clarity_structure": 0.08, "efficiency": 0.08, "gap_detection": 0.05,
           "reproducibility": 0.05}

score = sum(ASSESSMENT["ratings"][k] * weights[k] for k in weights)
grade = "A" if score >= 4.5 else "A-" if score >= 4.0 else "B+" if score >= 3.5 else "B" if score >= 3.0 else "C"

print(f"Score: {score:.2f}/5.00 | Grade: {grade}")
```

---

## Assessment Workflow

### Step 1: Run Your Exploration Prompt
Execute any codebase exploration prompt using Task agents or direct tools.

### Step 2: Quick Mental Checklist
Rate each attribute (1-5) as you review the output:

```
□ CD (15%): Did I understand WHY code is structured this way?
□ CB (12%): Did it examine all relevant files?
□ AC (15%): Are all claims verifiable in the code?
□ AT (12%): Can I immediately act on these insights?
□ BC (10%): Did it connect different parts of the system?
□ DA (10%): Is it relevant to what the app does?
□ CS (8%):  Is the output well-organized?
□ EF (8%):  Was this worth the tokens spent?
□ GD (5%):  Did it identify what's missing?
□ RP (5%):  Would I get the same results again?
```

### Step 3: Record Assessment
Create assessment file:

```bash
# Option A: Interactive CLI
python tools/prompt-assessor/src/assessor.py new MY-PROMPT-001

# Option B: Direct JSON
# Copy template from tools/prompt-assessor/templates/assessment-template.json
# Fill in ratings and save to tools/prompt-assessor/assessments/
```

### Step 4: Generate Report
```bash
python tools/prompt-assessor/src/assessor.py report assessments/MY-PROMPT-001.json
```

---

## Quick Rating Guide

### Comprehension Depth (CD) - 15%
| Score | Indicator |
|-------|-----------|
| 5 | Explains architectural rationale, edge cases, implicit assumptions |
| 4 | Understands interactions and trade-offs |
| 3 | Knows what code does, follows data flow |
| 2 | Surface-level file/function descriptions |
| 1 | Just lists files |

### Coverage Breadth (CB) - 12%
| Score | Indicator |
|-------|-----------|
| 5 | All relevant files, config, tests, infra |
| 4 | Primary modules + most dependencies |
| 3 | Main components for the query |
| 2 | Only obvious files |
| 1 | 1-2 files, no connections |

### Accuracy (AC) - 15%
| Score | Indicator |
|-------|-----------|
| 5 | 100% verifiable, zero hallucinations |
| 4 | 95%+ correct, minor issues |
| 3 | 85-95% correct, core is sound |
| 2 | 70-85% correct, needs verification |
| 1 | Major hallucinations |

### Actionability (AT) - 12%
| Score | Indicator |
|-------|-----------|
| 5 | Specific file:line changes provided |
| 4 | Clear steps to implement |
| 3 | Direction but needs investigation |
| 2 | Vague suggestions |
| 1 | Descriptive only |

### Bridging Capability (BC) - 10%
| Score | Indicator |
|-------|-----------|
| 5 | Full data flow across all layers |
| 4 | Cross-module dependency mapping |
| 3 | Adjacent component connections |
| 2 | Isolated understanding |
| 1 | No connections made |

### Domain Alignment (DA) - 10%
| Score | Indicator |
|-------|-----------|
| 5 | Every insight relates to app's mission |
| 4 | Frames findings in business context |
| 3 | Technical but limited "why it matters" |
| 2 | Generic, any-codebase analysis |
| 1 | Irrelevant focus |

### Clarity & Structure (CS) - 8%
| Score | Indicator |
|-------|-----------|
| 5 | Perfect hierarchy, tables, scannable |
| 4 | Clear with minor inconsistencies |
| 3 | Has structure but messy |
| 2 | Scattered information |
| 1 | Stream of consciousness |

### Efficiency (EF) - 8%
| Score | Indicator |
|-------|-----------|
| 5 | < 1500 tokens per score point |
| 4 | 1500-2000 tokens per score point |
| 3 | 2000-2500 tokens per score point |
| 2 | 2500-3500 tokens per score point |
| 1 | > 3500 tokens per score point |

### Gap Detection (GD) - 5%
| Score | Indicator |
|-------|-----------|
| 5 | Proactively lists missing features, security gaps, tech debt |
| 4 | Significant gaps with impact assessment |
| 3 | Obvious gaps mentioned |
| 2 | Only explicit TODOs found |
| 1 | No gaps identified |

### Reproducibility (RP) - 5%
| Score | Indicator |
|-------|-----------|
| 5 | Same core insights every run |
| 4 | Consistent with minor variation |
| 3 | Main conclusions similar |
| 2 | Different conclusions per run |
| 1 | Wildly variable |

---

## Prompt Improvement Patterns

### Low Efficiency (< 3.5)
**Add constraints:**
```
Analyze X in under 5000 tokens. Focus on files > 100 lines.
Use tables instead of prose. Skip obvious information.
```

### Low Bridging (< 3.5)
**Add tracing:**
```
Trace the complete data flow from [input] to [output].
Show how changes in module A affect B, C, D.
Map all cross-module dependencies.
```

### Low Actionability (< 3.5)
**Request specifics:**
```
Provide specific file:line references for each finding.
Include code snippets for recommended changes.
List exact commands to run.
```

### Low Domain Alignment (< 3.5)
**Add context:**
```
This is a [domain] application for [purpose].
Evaluate against these domain requirements: [list].
Use domain terminology: [terms].
```

### Low Gap Detection (< 3.5)
**Explicitly request:**
```
Identify what's missing vs [standard/requirements].
List technical debt markers (TODOs, FIXMEs, etc).
Flag security gaps and missing error handling.
```

---

## Score Calculation Formula

```
Total Score = Σ (Attribute_Score × Weight)

Where weights are:
  CD: 0.15, CB: 0.12, AC: 0.15, AT: 0.12, BC: 0.10
  DA: 0.10, CS: 0.08, EF: 0.08, GD: 0.05, RP: 0.05

Grade Thresholds:
  A:  4.50 - 5.00
  A-: 4.00 - 4.49
  B+: 3.50 - 3.99
  B:  3.00 - 3.49
  C+: 2.50 - 2.99
  C:  2.00 - 2.49
  F:  0.00 - 1.99
```

---

## Example: Complete Assessment

```markdown
## Assessment: ARCH-001

**Prompt:** "Analyze the AxiePro codebase architecture..."
**Codebase:** AxiePro
**Tokens:** 8,500 | **Time:** 3 min

### Ratings
| Attr | Score | Evidence |
|------|-------|----------|
| CD | 4.5 | Explained async patterns, DI, lifespan management |
| CB | 4.0 | 90% files covered, missed some scripts |
| AC | 4.5 | All paths verified, no hallucinations |
| AT | 4.0 | Clear entry points, could navigate immediately |
| BC | 4.5 | Full data flow diagram provided |
| DA | 4.0 | Mentioned Axie domain but didn't deep-dive |
| CS | 4.5 | Great tables and hierarchy |
| EF | 3.5 | Some redundancy, could be 30% shorter |
| GD | 4.0 | Found WebSocket handlers missing |
| RP | 4.0 | Core findings would repeat |

### Score: 4.20/5.00 | Grade: A-

### Improvements
1. Add "Be concise, max 6000 tokens" → +0.5 EF
2. Add "Evaluate against Axie analytics requirements" → +0.3 DA
```

---

## File Locations

```
tools/prompt-assessor/
├── src/assessor.py           # CLI tool
├── src/claude_integration.py # Programmatic API
├── config/attributes.yaml    # Full rubric definitions
├── templates/               # JSON templates
└── assessments/             # Saved assessments
```

---

*Use this guide to systematically improve your codebase exploration prompts.*
