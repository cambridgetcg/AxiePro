# Prompt Effectiveness Assessor

A standardized tool for evaluating codebase exploration prompts across Claude Code instances.

## Overview

This tool provides a systematic framework for assessing the effectiveness of prompts used for codebase exploration, debugging, and analysis. It implements a 10-attribute rating system with weighted scoring to enable objective comparison and optimization of prompts.

## Quick Start

### CLI Usage

```bash
# Create a new assessment interactively
python src/assessor.py new ARCH-001

# Rate an existing assessment
python src/assessor.py rate assessments/ARCH-001_2025-01-20.json

# View scores
python src/assessor.py score assessments/ARCH-001_2025-01-20.json

# Generate markdown report
python src/assessor.py report assessments/ARCH-001_2025-01-20.json

# Compare multiple prompts
python src/assessor.py compare assessments/v1.json assessments/v2.json

# View assessment history
python src/assessor.py history

# Get benchmark statistics
python src/assessor.py benchmark
```

### Programmatic Usage (in Claude Code)

```python
from tools.prompt_assessor.src.claude_integration import quick_assess, inline_assess

# Quick assessment with all ratings
result = quick_assess(
    prompt_id="ARCH-001",
    prompt_text="Analyze the architecture of this codebase...",
    codebase="MyProject",
    ratings={
        "comprehension_depth": 4.5,
        "coverage_breadth": 4.0,
        "accuracy": 4.5,
        "actionability": 4.0,
        "bridging_capability": 4.5,
        "domain_alignment": 4.0,
        "clarity_structure": 4.5,
        "efficiency": 3.5,
        "gap_detection": 4.0,
        "reproducibility": 4.0
    },
    tokens_used=8500,
    execution_time=3.0
)

# Inline assessment with abbreviated codes
summary = inline_assess(
    prompt_text="Your prompt here",
    output_summary="What the prompt produced",
    cd=4.5, cb=4.0, ac=4.5, at=4.0, bc=4.5,
    da=4.0, cs=4.5, ef=3.5, gd=4.0, rp=4.0,
    codebase="MyProject"
)
print(summary)
```

## The 10 Assessment Attributes

| Code | Attribute | Weight | Description |
|------|-----------|--------|-------------|
| **CD** | Comprehension Depth | 15% | How deeply the prompt penetrates understanding |
| **CB** | Coverage Breadth | 12% | How much relevant territory is explored |
| **AC** | Accuracy | 15% | Correctness of claims (verified against code) |
| **AT** | Actionability | 12% | Whether insights lead to concrete actions |
| **BC** | Bridging Capability | 10% | Ability to connect disparate system parts |
| **DA** | Domain Alignment | 10% | Relevance to application's core purpose |
| **CS** | Clarity & Structure | 8% | Organization and readability of output |
| **EF** | Efficiency | 8% | Value gained vs resources (tokens) spent |
| **GD** | Gap Detection | 5% | Identifying what's missing or incomplete |
| **RP** | Reproducibility | 5% | Consistency across multiple executions |

## Rating Scale

Each attribute is rated 1-5:

| Score | Level | Meaning |
|-------|-------|---------|
| **5** | Excellent | Exceeds expectations in every way |
| **4** | Good | Meets expectations with minor gaps |
| **3** | Adequate | Acceptable but room for improvement |
| **2** | Below Average | Significant gaps or issues |
| **1** | Poor | Fails to meet basic requirements |

## Grade Scale

| Grade | Score Range | Interpretation |
|-------|-------------|----------------|
| **A** | 4.5 - 5.0 | Excellent - Use as template |
| **A-** | 4.0 - 4.49 | Very Good - Minor refinements needed |
| **B+** | 3.5 - 3.99 | Good - Some improvements needed |
| **B** | 3.0 - 3.49 | Adequate - Notable gaps |
| **C+** | 2.5 - 2.99 | Below Average - Significant rework |
| **C** | 2.0 - 2.49 | Poor - Major revision needed |
| **F** | < 2.0 | Ineffective - Redesign from scratch |

## Directory Structure

```
prompt-assessor/
├── README.md                 # This file
├── CLAUDE.md                 # Claude Code specific instructions
├── config/
│   └── attributes.yaml       # Attribute definitions and rubrics
├── src/
│   ├── assessor.py           # Main assessment engine
│   └── claude_integration.py # Programmatic interface
├── templates/
│   └── assessment-template.json  # Empty assessment template
└── assessments/              # Saved assessment files
    └── *.json
```

## Workflow

### 1. Pre-Execution
- Define assessment context (codebase, objective)
- Categorize the prompt (discovery, tracing, analysis, etc.)
- Set token/time budget

### 2. Execution
- Run the prompt against the codebase
- Record execution metrics (time, tokens)
- Capture output

### 3. Rating
- Rate each of the 10 attributes (1-5)
- Provide evidence for ratings
- Calculate composite score

### 4. Optimization
- Identify lowest-scoring attributes
- Refine prompt to address weaknesses
- Re-test and compare

## Best Practices

### Writing Effective Prompts

1. **Be Specific**: Include file paths, module names, specific questions
2. **Set Scope**: Define boundaries to improve efficiency
3. **Request Structure**: Ask for tables, diagrams, categorized output
4. **Include Domain Context**: Mention the application's purpose
5. **Specify Depth**: Indicate whether you want overview or deep-dive

### Common Optimization Patterns

| Issue | Solution | Expected Impact |
|-------|----------|-----------------|
| Low Efficiency | Add token budget ("< 5000 tokens") | +0.5 EF |
| Low Bridging | Add "trace end-to-end flow" | +0.5 BC |
| Low Actionability | Add "provide code snippets" | +0.5 AT |
| Low Domain Alignment | Include domain checklist | +0.5 DA |

## Configuration

Edit `config/attributes.yaml` to:
- Adjust attribute weights
- Customize rubric descriptions
- Add domain-specific criteria

## Integration with Claude Code

This tool is designed to work seamlessly within Claude Code sessions:

1. **During Exploration**: After running an exploration prompt, assess its effectiveness
2. **Prompt Iteration**: Compare v1 vs v2 of a prompt to measure improvement
3. **Team Standards**: Establish baseline scores for acceptable prompts
4. **Documentation**: Generate reports for prompt libraries

## Example Assessment

```
## Prompt Assessment: ARCH-001

**Grade: A-** | **Score: 4.20/5.00** (84%)

### Attribute Scores
CD ██████████████████░░ 4.5  Comprehension Depth
CB ████████████████░░░░ 4.0  Coverage Breadth
AC ██████████████████░░ 4.5  Accuracy
AT ████████████████░░░░ 4.0  Actionability
BC ██████████████████░░ 4.5  Bridging Capability
DA ████████████████░░░░ 4.0  Domain Alignment
CS ██████████████████░░ 4.5  Clarity & Structure
EF ██████████████░░░░░░ 3.5  Efficiency
GD ████████████████░░░░ 4.0  Gap Detection
RP ████████████████░░░░ 4.0  Reproducibility

### Recommendations
1. Add token budget to improve efficiency
2. Include domain-specific checklist
3. Request code snippets for actionability
```

## License

Internal tool for Claude Code prompt optimization.

---

*Version 1.0.0 | Created 2025-01-20*
