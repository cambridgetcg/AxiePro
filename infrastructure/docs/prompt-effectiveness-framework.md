# Prompt Effectiveness Assessment Framework
## A Systematic Standard for Evaluating Codebase Exploration Prompts

---

## 1. Assessment Workflow

### Phase 1: Pre-Execution Setup
```
┌─────────────────────────────────────────────────────────────┐
│  STEP 1: Define Assessment Context                          │
├─────────────────────────────────────────────────────────────┤
│  □ Identify the codebase scope (files, modules, systems)    │
│  □ Define the exploration objective (understand, debug, etc)│
│  □ Establish baseline knowledge (what do we already know?)  │
│  □ Set time/token budget for the exploration                │
│  □ Identify ground truth (if available) for validation      │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 2: Categorize the Prompt                              │
├─────────────────────────────────────────────────────────────┤
│  Prompt Type:                                               │
│  □ Discovery (what exists?)                                 │
│  □ Tracing (how does X flow to Y?)                          │
│  □ Analysis (what patterns/issues exist?)                   │
│  □ Alignment (does X match purpose Y?)                      │
│  □ Diagnostic (why is X failing?)                           │
│  □ Comparative (how does X differ from Y?)                  │
└─────────────────────────────────────────────────────────────┘
```

### Phase 2: Execution & Observation
```
┌─────────────────────────────────────────────────────────────┐
│  STEP 3: Execute Prompt                                     │
├─────────────────────────────────────────────────────────────┤
│  □ Record start time / token count                          │
│  □ Execute prompt against codebase                          │
│  □ Document tools/agents used                               │
│  □ Capture raw output                                       │
│  □ Record end time / final token count                      │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 4: Immediate Observations                             │
├─────────────────────────────────────────────────────────────┤
│  □ Did it complete without errors?                          │
│  □ Did it require follow-up questions?                      │
│  □ Were the right files/modules examined?                   │
│  □ Did it produce structured output?                        │
└─────────────────────────────────────────────────────────────┘
```

### Phase 3: Systematic Evaluation
```
┌─────────────────────────────────────────────────────────────┐
│  STEP 5: Apply Rating Rubric (see Section 2)                │
├─────────────────────────────────────────────────────────────┤
│  Rate each of the 10 assessment attributes (1-5 scale)      │
│  Document evidence for each rating                          │
│  Calculate composite scores                                 │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 6: Validation & Calibration                           │
├─────────────────────────────────────────────────────────────┤
│  □ Verify claims against actual code                        │
│  □ Check for hallucinations/inaccuracies                    │
│  □ Compare with ground truth (if available)                 │
│  □ Assess practical utility of insights                     │
└─────────────────────────────────────────────────────────────┘
```

### Phase 4: Optimization Loop
```
┌─────────────────────────────────────────────────────────────┐
│  STEP 7: Identify Improvement Opportunities                 │
├─────────────────────────────────────────────────────────────┤
│  □ Which attributes scored lowest?                          │
│  □ What was missing from the output?                        │
│  □ What was included but not useful?                        │
│  □ How could the prompt be more specific?                   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 8: Iterate & Re-assess                                │
├─────────────────────────────────────────────────────────────┤
│  □ Refine prompt based on findings                          │
│  □ Re-execute and re-rate                                   │
│  □ Compare scores to previous iteration                     │
│  □ Document what changes improved which attributes          │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Assessment Attributes & Rating Rubric

### Overview: The 10 Assessment Dimensions

| # | Attribute | Abbreviation | Weight | What It Measures |
|---|-----------|--------------|--------|------------------|
| 1 | Comprehension Depth | **CD** | 15% | How deeply the prompt penetrates understanding |
| 2 | Coverage Breadth | **CB** | 12% | How much relevant territory is explored |
| 3 | Accuracy | **AC** | 15% | Correctness of claims and findings |
| 4 | Actionability | **AT** | 12% | Whether insights lead to concrete actions |
| 5 | Bridging Capability | **BC** | 10% | Ability to connect disparate components |
| 6 | Domain Alignment | **DA** | 10% | Relevance to application's core purpose |
| 7 | Clarity & Structure | **CS** | 8% | Organization and readability of output |
| 8 | Efficiency | **EF** | 8% | Value gained vs resources spent |
| 9 | Gap Detection | **GD** | 5% | Ability to identify what's missing |
| 10 | Reproducibility | **RP** | 5% | Consistency across multiple executions |

---

### Attribute 1: Comprehension Depth (CD)
*How deeply does the prompt help understand the code?*

| Score | Level | Criteria |
|-------|-------|----------|
| **5** | Expert | Reveals non-obvious insights, architectural rationale, edge cases, and implicit assumptions. Could explain to a senior engineer. |
| **4** | Proficient | Understands component interactions, design patterns, and trade-offs. Identifies why code is structured this way. |
| **3** | Competent | Grasps what code does and how pieces connect. Can follow data flow but may miss subtle dependencies. |
| **2** | Basic | Surface-level understanding. Identifies files and functions but not their deeper purpose or interactions. |
| **1** | Superficial | Only describes obvious structure. Lists files without understanding their relationships. |

**Evidence Markers:**
- [5] "The service uses read-through caching because write frequency is low but read latency is critical"
- [3] "Data flows from API to service to database"
- [1] "There is a file called database.py"

---

### Attribute 2: Coverage Breadth (CB)
*How much of the relevant codebase does it explore?*

| Score | Level | Criteria |
|-------|-------|----------|
| **5** | Comprehensive | Examines all relevant files, cross-module dependencies, configuration, tests, and infrastructure. No significant blind spots. |
| **4** | Thorough | Covers primary modules and most dependencies. May miss peripheral concerns (tests, docs, scripts). |
| **3** | Adequate | Examines main components relevant to the query. Misses some secondary files or cross-cutting concerns. |
| **2** | Partial | Focuses on obvious files only. Misses important dependencies or related modules. |
| **1** | Narrow | Examines 1-2 files without exploring connections or dependencies. |

**Measurement Method:**
```
Coverage % = (Relevant files examined / Total relevant files) × 100

Relevance is determined by:
- Direct imports/dependencies
- Shared data structures
- Configuration that affects behavior
- Tests that validate functionality
```

---

### Attribute 3: Accuracy (AC)
*Are the claims and findings correct?*

| Score | Level | Criteria |
|-------|-------|----------|
| **5** | Verified | All claims are verifiable against code. No hallucinations. Technical details are precise. |
| **4** | Reliable | Minor inaccuracies that don't affect conclusions. 95%+ claims are correct. |
| **3** | Mostly Correct | Some inaccuracies present but core understanding is sound. 85-95% accurate. |
| **2** | Mixed | Significant errors mixed with correct information. Requires verification. 70-85% accurate. |
| **1** | Unreliable | Major hallucinations or misunderstandings. Cannot be trusted without full verification. <70% accurate. |

**Validation Process:**
```
For each factual claim:
1. Locate the referenced file/line
2. Verify the claim matches actual code
3. Check for omitted context that changes meaning
4. Confirm technical terminology is used correctly

Accuracy % = (Verified correct claims / Total verifiable claims) × 100
```

---

### Attribute 4: Actionability (AT)
*Do the insights lead to concrete actions?*

| Score | Level | Criteria |
|-------|-------|----------|
| **5** | Immediately Actionable | Provides specific steps, file paths, code changes, or commands. Can act right now. |
| **4** | Clearly Actionable | Identifies what needs to be done with enough detail to plan implementation. |
| **3** | Directionally Actionable | Points toward areas needing work but requires further investigation to act. |
| **2** | Vaguely Actionable | General suggestions without specific guidance on implementation. |
| **1** | Not Actionable | Descriptive only. No clear path from insight to action. |

**Evidence Markers:**
- [5] "Fix by changing line 23 of database.py: replace `settings.database_url` with `settings.get_database_url()`"
- [3] "The caching layer needs optimization"
- [1] "The system has some complexity"

---

### Attribute 5: Bridging Capability (BC)
*Does it connect different parts of the system?*

| Score | Level | Criteria |
|-------|-------|----------|
| **5** | Full Integration View | Maps complete data/control flow across all layers. Explains how frontend, backend, database, and infrastructure interact. |
| **4** | Cross-Module Connections | Identifies dependencies between modules and how changes propagate. Understands shared contracts. |
| **3** | Adjacent Connections | Connects immediately related components but may miss indirect dependencies. |
| **2** | Isolated Understanding | Understands individual components but not how they fit together. |
| **1** | Siloed | Each component analyzed in isolation with no connection to others. |

**Assessment Questions:**
- Does it trace data from source to destination across boundaries?
- Does it identify shared interfaces/contracts between components?
- Does it explain how a change in A would affect B, C, D?
- Does it connect code to infrastructure to configuration?

---

### Attribute 6: Domain Alignment (DA)
*How relevant is the output to the application's purpose?*

| Score | Level | Criteria |
|-------|-------|----------|
| **5** | Purpose-Driven | Every insight relates to the application's core mission. Uses domain language. Identifies purpose-specific gaps. |
| **4** | Domain-Aware | Understands the domain and frames technical findings in business context. |
| **3** | Domain-Adjacent | Technical accuracy but limited connection to why this matters for the application. |
| **2** | Domain-Agnostic | Generic technical analysis that could apply to any codebase. |
| **1** | Domain-Irrelevant | Focuses on aspects unrelated to application purpose. |

**For AxiePro specifically:**
- Does it understand this is an Axie Infinity analytics platform?
- Does it evaluate features against what Axie traders need?
- Does it use correct domain terminology (genes, purity, floor price, breeding)?
- Does it identify domain-specific gaps (missing game mechanics)?

---

### Attribute 7: Clarity & Structure (CS)
*Is the output well-organized and easy to understand?*

| Score | Level | Criteria |
|-------|-------|----------|
| **5** | Exemplary | Logical hierarchy, consistent formatting, clear headings, tables where appropriate, easy to scan and deep-dive. |
| **4** | Well-Organized | Clear structure with some minor inconsistencies. Information is findable. |
| **3** | Adequate | Has structure but could be better organized. Some effort needed to extract information. |
| **2** | Disorganized | Information is present but scattered. Requires significant effort to parse. |
| **1** | Chaotic | Stream of consciousness. No clear structure. Difficult to extract useful information. |

**Structural Elements to Assess:**
- Headings and hierarchy
- Use of tables for comparative data
- Code blocks for technical details
- Bullet points for lists
- Summary/TL;DR sections
- Consistent formatting

---

### Attribute 8: Efficiency (EF)
*What value was gained relative to resources spent?*

| Score | Level | Criteria |
|-------|-------|----------|
| **5** | Highly Efficient | Maximum insight with minimal tokens/time. No redundancy. Every word adds value. |
| **4** | Efficient | Good value-to-cost ratio. Minor redundancy or unnecessary exploration. |
| **3** | Acceptable | Reasonable efficiency. Some wasted effort on irrelevant areas. |
| **2** | Inefficient | Significant resources spent on low-value exploration. Could have been more targeted. |
| **1** | Wasteful | Excessive tokens/time for minimal insight. Major inefficiencies. |

**Measurement:**
```
Efficiency Score = (Insight Value Score × 20) / (Tokens Used / 1000)

Where Insight Value = Average of other attribute scores
Normalized to 1-5 scale

Example:
- High insight (4.0 avg) with 5K tokens = (4.0 × 20) / 5 = 16 → Score 5
- Medium insight (3.0 avg) with 15K tokens = (3.0 × 20) / 15 = 4 → Score 3
- Low insight (2.0 avg) with 20K tokens = (2.0 × 20) / 20 = 2 → Score 1
```

---

### Attribute 9: Gap Detection (GD)
*Does it identify what's missing or incomplete?*

| Score | Level | Criteria |
|-------|-------|----------|
| **5** | Proactive Gap Analysis | Systematically identifies missing features, incomplete implementations, technical debt, and security gaps without being asked. |
| **4** | Good Gap Awareness | Identifies significant gaps and explains their impact. |
| **3** | Some Gap Detection | Mentions obvious gaps but may miss subtle ones. |
| **2** | Reactive Only | Only identifies gaps when explicitly present (TODO comments, empty functions). |
| **1** | Gap Blind | Does not identify any missing elements even when significant gaps exist. |

**Gap Categories:**
- Missing features (vs domain requirements)
- Missing error handling
- Missing tests
- Missing documentation
- Missing security controls
- Missing observability
- Technical debt markers

---

### Attribute 10: Reproducibility (RP)
*Are results consistent across multiple executions?*

| Score | Level | Criteria |
|-------|-------|----------|
| **5** | Highly Reproducible | Same prompt yields same core insights every time. Minor variation in wording only. |
| **4** | Mostly Reproducible | Core findings consistent with some variation in depth or organization. |
| **3** | Moderately Reproducible | Main conclusions similar but significant variation in supporting details. |
| **2** | Inconsistent | Different runs yield different conclusions or miss different areas. |
| **1** | Unreproducible | Results vary wildly between executions. Cannot rely on any single run. |

**Testing Method:**
```
1. Execute same prompt 3 times
2. Compare outputs for:
   - Core findings (should match)
   - File coverage (should be similar)
   - Technical claims (should be identical)
   - Recommendations (should align)
3. Calculate consistency score
```

---

## 3. Scoring Methodology

### 3.1 Individual Prompt Score Calculation

```
Weighted Score = Σ (Attribute Score × Weight)

Example:
┌──────────────────┬───────┬────────┬──────────────────┐
│ Attribute        │ Score │ Weight │ Weighted         │
├──────────────────┼───────┼────────┼──────────────────┤
│ Comprehension    │ 4     │ 0.15   │ 0.60             │
│ Coverage         │ 3     │ 0.12   │ 0.36             │
│ Accuracy         │ 5     │ 0.15   │ 0.75             │
│ Actionability    │ 4     │ 0.12   │ 0.48             │
│ Bridging         │ 3     │ 0.10   │ 0.30             │
│ Domain Alignment │ 4     │ 0.10   │ 0.40             │
│ Clarity          │ 4     │ 0.08   │ 0.32             │
│ Efficiency       │ 3     │ 0.08   │ 0.24             │
│ Gap Detection    │ 4     │ 0.05   │ 0.20             │
│ Reproducibility  │ 4     │ 0.05   │ 0.20             │
├──────────────────┼───────┼────────┼──────────────────┤
│ TOTAL            │       │ 1.00   │ 3.85 / 5.00      │
└──────────────────┴───────┴────────┴──────────────────┘

Final Score: 3.85 (77% effectiveness)
Grade: B+
```

### 3.2 Grade Scale

| Score Range | Grade | Interpretation |
|-------------|-------|----------------|
| 4.5 - 5.0 | A | Excellent - Use as template |
| 4.0 - 4.49 | A- | Very Good - Minor refinements |
| 3.5 - 3.99 | B+ | Good - Some improvements needed |
| 3.0 - 3.49 | B | Adequate - Notable gaps |
| 2.5 - 2.99 | C+ | Below Average - Significant rework |
| 2.0 - 2.49 | C | Poor - Major revision needed |
| < 2.0 | F | Ineffective - Redesign from scratch |

### 3.3 Attribute Profile Visualization

```
Prompt: "Analyze the architecture..."

CD ████████████████░░░░ 4.0  Comprehension Depth
CB ████████████░░░░░░░░ 3.0  Coverage Breadth
AC ████████████████████ 5.0  Accuracy
AT ████████████████░░░░ 4.0  Actionability
BC ████████████░░░░░░░░ 3.0  Bridging Capability
DA ████████████████░░░░ 4.0  Domain Alignment
CS ████████████████░░░░ 4.0  Clarity & Structure
EF ████████████░░░░░░░░ 3.0  Efficiency
GD ████████████████░░░░ 4.0  Gap Detection
RP ████████████████░░░░ 4.0  Reproducibility
   ─────────────────────
   0    1    2    3    4    5
```

---

## 4. Assessment Template

### Prompt Assessment Record

```markdown
# Prompt Assessment: [Prompt Name/ID]

## Metadata
- **Date:** YYYY-MM-DD
- **Codebase:** [Project name]
- **Prompt Category:** [Discovery/Tracing/Analysis/Alignment/Diagnostic/Comparative]
- **Assessor:** [Name]
- **Execution Time:** [X minutes]
- **Tokens Used:** [X,XXX]

## Prompt Text
```
[Full prompt text here]
```

## Execution Summary
- **Files Examined:** [List key files]
- **Tools Used:** [Grep, Read, Task agents, etc.]
- **Errors/Issues:** [Any problems during execution]

## Attribute Ratings

| Attribute | Score | Evidence |
|-----------|-------|----------|
| Comprehension Depth | X/5 | [Specific evidence] |
| Coverage Breadth | X/5 | [Specific evidence] |
| Accuracy | X/5 | [Verification results] |
| Actionability | X/5 | [Example actions identified] |
| Bridging Capability | X/5 | [Connections made] |
| Domain Alignment | X/5 | [Domain relevance] |
| Clarity & Structure | X/5 | [Organization quality] |
| Efficiency | X/5 | [Value vs cost] |
| Gap Detection | X/5 | [Gaps identified] |
| Reproducibility | X/5 | [Consistency assessment] |

## Composite Score
- **Weighted Score:** X.XX / 5.00
- **Percentage:** XX%
- **Grade:** [A/B/C/F]

## Strengths
1. [What worked well]
2. [What worked well]

## Weaknesses
1. [What needs improvement]
2. [What needs improvement]

## Optimization Recommendations
1. [Specific change to improve]
2. [Specific change to improve]

## Comparison to Previous Version
| Attribute | Previous | Current | Change |
|-----------|----------|---------|--------|
| [Attr] | X.X | X.X | +/-X.X |

---
```

---

## 5. Benchmark Scores: AxiePro Prompt Evaluation

### Prompts Tested Against AxiePro Codebase

| Prompt | CD | CB | AC | AT | BC | DA | CS | EF | GD | RP | **Total** | **Grade** |
|--------|----|----|----|----|----|----|----|----|----|----|-----------|-----------|
| Architecture Discovery | 4.5 | 4.0 | 4.5 | 4.0 | 4.5 | 4.0 | 4.5 | 3.5 | 4.0 | 4.0 | **4.18** | **A-** |
| Data Model Alignment | 4.0 | 4.5 | 4.5 | 4.5 | 3.5 | 5.0 | 4.0 | 4.0 | 5.0 | 4.0 | **4.30** | **A-** |
| API Integration Mapping | 4.0 | 4.5 | 4.0 | 4.0 | 4.0 | 4.0 | 4.5 | 3.5 | 4.5 | 4.0 | **4.08** | **A-** |
| Infrastructure Assessment | 4.5 | 4.0 | 4.5 | 4.0 | 4.0 | 4.5 | 4.5 | 4.0 | 4.0 | 4.0 | **4.23** | **A-** |

### Attribute Analysis Across All Prompts

```
                        Avg Score   Assessment
Comprehension Depth     4.25 ████████████████▓░░░  Strong
Coverage Breadth        4.25 ████████████████▓░░░  Strong
Accuracy                4.38 █████████████████▓░░  Very Strong
Actionability           4.13 ████████████████▒░░░  Strong
Bridging Capability     4.00 ████████████████░░░░  Good
Domain Alignment        4.38 █████████████████▓░░  Very Strong
Clarity & Structure     4.38 █████████████████▓░░  Very Strong
Efficiency              3.75 ███████████████░░░░░  Adequate (needs work)
Gap Detection           4.38 █████████████████▓░░  Very Strong
Reproducibility         4.00 ████████████████░░░░  Good
```

### Key Insights

**Strongest Attributes (≥4.25):**
- Accuracy (4.38) - Prompts produced verifiable, correct findings
- Domain Alignment (4.38) - Well-aligned with Axie analytics purpose
- Clarity (4.38) - Output was well-structured
- Gap Detection (4.38) - Effectively identified missing components

**Weakest Attribute (<4.0):**
- Efficiency (3.75) - Some prompts explored too broadly, spending tokens on less relevant areas

**Improvement Focus:**
1. Add scope constraints to improve efficiency
2. Add explicit bridging instructions for cross-system analysis
3. Request reproducibility markers (deterministic file lists)

---

## 6. Continuous Improvement Process

### Monthly Prompt Review Cycle

```
Week 1: Collect prompt usage data
        ├── Which prompts were used most?
        ├── Which prompts needed follow-up?
        └── Which prompts produced actionable results?

Week 2: Re-assess top 5 prompts
        ├── Run assessment workflow
        ├── Compare to previous scores
        └── Identify regression or improvement

Week 3: Optimize underperforming prompts
        ├── Refine prompts scoring < 4.0
        ├── A/B test variations
        └── Document what changes helped

Week 4: Update prompt library
        ├── Archive ineffective prompts
        ├── Promote high-performing prompts
        └── Document lessons learned
```

### Version Control for Prompts

```
prompts/
├── v1/
│   ├── architecture-discovery.md
│   └── assessment-scores.json
├── v2/
│   ├── architecture-discovery.md  (refined)
│   └── assessment-scores.json
└── current/ → v2/  (symlink to latest)
```

---

*Framework Version: 1.0 | Created: 2025-01-20*
