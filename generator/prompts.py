
# Промпты для генерации и рефайнмента CodeQL правил


GENERATION_PROMPT = """You are an expert CodeQL developer specializing in C/C++ security analysis.

Your task is to generate a CodeQL rule to detect the following vulnerability:

CWE ID: {cwe_id}
CWE Name: {cwe_name}

{context}

IMPORTANT REQUIREMENTS:
1. Output MUST be a single valid CodeQL query (.ql file)
2. Start with 'import cpp'
3. Include 'from ... where ... select ...' query
4. Do NOT include markdown, backticks or explanations
5. Output ONLY raw QL code, nothing else
6. Code must be compilable by CodeQL compiler
7. Include comments explaining the detection logic

QL Syntax reminders:
- Import: import cpp
- Use: from <var> where <condition> select <result>
- Use getEnclosingFunction() for function context
- Use DataFlow for taint tracking
- Use string concatenation: "text1" + "text2"

Generate the complete CodeQL rule now (code only, no explanation):"""

REFINEMENT_PROMPT = """You are an expert CodeQL developer. Your task is to improve an existing CodeQL rule based on its performance metrics.

CWE ID: {cwe_id}
CWE Name: {cwe_name}

Current Rule:
```
{current_rule}
```

Current Metrics:
- Precision (TP/(TP+FP)): {precision:.1%}
- Recall (TP/(TP+FN)): {recall:.1%}
- Specificity (TN/(TN+FP)): {specificity:.1%}

Target Metrics:
- Precision: {target_precision:.1%}
- Recall: {target_recall:.1%}
- Specificity: {target_specificity:.1%}

Performance Analysis:
{analysis}

Feedback:
{feedback}

IMPORTANT REQUIREMENTS:
1. Output ONLY the improved, compilable CodeQL code
2. Do NOT include markdown blocks, backticks or explanations
3. Maintain syntactic correctness
4. Make minimal but impactful improvements
5. Do not break existing functionality

Improvement Strategy:
{strategy}

Generate the improved CodeQL rule now (code only, no explanation):"""


def get_generation_prompt(cwe_id: str, cwe_name: str, context: str = "") -> str:
    # Подготовить промпт для генерации правила
    ctx = context if context else "Focus on C/C++ implementation specifics and common attack patterns."
    return GENERATION_PROMPT.format(
        cwe_id=cwe_id,
        cwe_name=cwe_name,
        context=ctx
    )


def get_refinement_prompt(
    cwe_id: str,
    cwe_name: str,
    current_rule: str,
    metrics: dict,
    target_metrics: dict,
    feedback: str = ""
) -> str:
    # Подготовить промпт для рефайнмента правила
    
    analysis = _analyze_metrics(metrics, target_metrics)
    strategy = _get_refinement_strategy(metrics, target_metrics)
    
    return REFINEMENT_PROMPT.format(
        cwe_id=cwe_id,
        cwe_name=cwe_name,
        current_rule=current_rule,
        precision=metrics.get("precision", 0),
        recall=metrics.get("recall", 0),
        specificity=metrics.get("specificity", 0),
        target_precision=target_metrics.get("precision", 0.7),
        target_recall=target_metrics.get("recall", 0.6),
        target_specificity=target_metrics.get("specificity", 0.8),
        analysis=analysis,
        feedback=feedback if feedback else "No additional feedback",
        strategy=strategy
    )


def _analyze_metrics(current: dict, target: dict) -> str:
    # Анализ разницы между текущими и целевыми метриками
    analysis = []
    
    precision = current.get("precision", 0)
    recall = current.get("recall", 0)
    specificity = current.get("specificity", 0)
    
    target_precision = target.get("precision", 0.7)
    target_recall = target.get("recall", 0.6)
    target_specificity = target.get("specificity", 0.8)
    
    if precision < target_precision:
        gap = (target_precision - precision) * 100
        analysis.append(
            f"  Precision gap: {gap:.0f}% below target\n"
            "   Issue: Too many false positives\n"
            "   Action: Add more restrictive conditions"
        )
    
    if recall < target_recall:
        gap = (target_recall - recall) * 100
        analysis.append(
            f"  Recall gap: {gap:.0f}% below target\n"
            "   Issue: Missing true vulnerabilities\n"
            "   Action: Broaden pattern matching"
        )
    
    if specificity < target_specificity:
        analysis.append(
            f"  Specificity below target\n"
            "   Issue: Poor non-vulnerable case handling\n"
            "   Action: Improve filtering logic"
        )
    
    return "\n".join(analysis) if analysis else "Metrics are close to target"


def _get_refinement_strategy(current: dict, target: dict) -> str:
    # Получить стратегию рефайнмента
    precision = current.get("precision", 0)
    recall = current.get("recall", 0)
    target_precision = target.get("precision", 0.7)
    target_recall = target.get("recall", 0.6)
    
    if precision < 0.6 and recall < 0.5:
        return (
            "Both metrics are critically low. Consider:\n"
            "1. Completely rewrite pattern matching logic\n"
            "2. Review the condition structure\n"
            "3. Add missing vulnerability patterns"
        )
    
    if precision < target_precision:
        return (
            "Focus on reducing false positives:\n"
            "1. Add stricter type checking\n"
            "2. Filter out safe API calls\n"
            "3. Improve boundary condition checks\n"
            "4. Add more specific pattern matching"
        )
    
    if recall < target_recall:
        return (
            "Focus on improving detection coverage:\n"
            "1. Add alternative vulnerability patterns\n"
            "2. Broaden type matching\n"
            "3. Include indirect function calls\n"
            "4. Handle edge cases better"
        )
    
    return (
        "Make incremental refinements:\n"
        "1. Fine-tune existing conditions\n"
        "2. Add missing edge cases\n"
        "3. Optimize pattern matching"
    )
