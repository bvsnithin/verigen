"""
prompt_builder.py
=================
Constructs the LLM prompt for SystemVerilog Assertion (SVA) generation.

Pipeline:
    User RTL  -->  retriever (top-k similar examples)  -->  prompt template
                                                                  |
                                                         inject as few-shot
                                                                  |
                                                          send to LLM (Step 4)

Usage:
    source venv/bin/activate
    python prompt_builder.py
"""

from sentence_transformers import SentenceTransformer

from .retriever import MODEL_NAME, load_index, retrieve

# ─────────────────────────────────────────────────────────────
# PROMPT COMPONENTS
# ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are an expert hardware verification engineer specializing in \
SystemVerilog Assertions (SVA).

Your job is to read a block of SystemVerilog RTL code and generate \
correct, complete SVA property blocks that fully cover the logic.

RULES:
1. Generate one `property ... endproperty` block for every logical branch \
(if, else if, else, each case arm, and default).
2. Use the overlapping implication operator `|->` to link the condition \
to the expected assignment.
3. For synchronous RTL (non-blocking assignments `<=`): prefix each property \
with `@(posedge <clock>)` or `@(negedge <clock>)`.
4. Nest conditions correctly: inner `if` conditions must include the outer \
condition in the antecedent using `&&`.
5. Cover the `else` / `default` branch using the negation `!` of all \
prior conditions.
6. Property names must be PascalCase and descriptive.

REASONING STEP:
Before writing the final structure, you MUST output an <analysis> block where you \
break the RTL down like a verification engineer:
<analysis>
  <timing>Specify if synchronous or combinational, and clock name</timing>
  <conditions>List the if/else conditions</conditions>
  <branches>List the case/assignment branches</branches>
</analysis>

OUTPUT FORMAT:
Your final output MUST follow this exact structure after the analysis block:

<analysis>...</analysis>

1. Assertions
```systemverilog
property <PropertyName>;
  ...
endproperty
```

## Explanation
Briefly explain what each assertion checks.

## Edge Cases Covered
List the edge cases (e.g., reset, default assignments, mutual exclusion).
"""


def generate_mock_reasoning(code: str) -> str:
    """Synthesize a mock structural reasoning block for few-shot examples."""
    has_sync = "posedge" in code or "negedge" in code or "<=" in code
    has_if = "if " in code or "if(" in code
    has_case = "case" in code
    
    analysis = "  <timing>" + ("Synchronous" if has_sync else "Combinational") + "</timing>\n"
    
    cond_text = "Analyzed if/else structural conditions" if has_if else "No explicit if conditions"
    branch_text = "Analyzed case branches" if has_case else ("Analyzed else branches" if "else" in code else "Direct assignments analyzed")
    
    analysis += f"  <conditions>{cond_text}</conditions>\n"
    analysis += f"  <branches>{branch_text}</branches>\n"
    
    return f"<analysis>\n{analysis}</analysis>"


def format_few_shot_example(index: int, code: str, assertion: str) -> str:
    """
    Format a single retrieved example as a labelled few-shot block.
    """
    props = []
    for part in assertion.strip().split("endproperty"):
        part = part.strip()
        if part:
            props.append(part + " endproperty")
    assertion_block = "\n".join(props)
    
    mock_reasoning = generate_mock_reasoning(code)
    
    # Synthesize the requested structure
    has_sync = "posedge" in code or "negedge" in code
    edge_cases = "- Resets\n- Combinational loops" if not has_sync else "- Reset and Default states\n- Clock transitions"
    
    output = f"{mock_reasoning}\n\n"
    output += "1. Assertions\n"
    output += f"```systemverilog\n{assertion_block}\n```\n\n"
    output += "## Explanation\n"
    output += "- These properties check the main logical branches within the RTL.\n\n"
    output += "## Edge Cases Covered\n"
    output += f"{edge_cases}"

    return (
        f"### Example {index}\n\n"
        f"RTL Code:\n"
        f"```systemverilog\n{code.strip()}\n```\n\n"
        f"Assertions Output:\n"
        f"{output}"
    )


def build_prompt(
    query_rtl: str,
    retrieved_examples: list[dict],
    clock_hint: str | None = None,
) -> str:
    """
    Assemble the full LLM prompt from the system instructions,
    retrieved few-shot examples, and the user's RTL query.

    Args:
        query_rtl:           The RTL code the user wants assertions for.
        retrieved_examples:  Top-k records returned by retrieve().
        clock_hint:          Optional clock signal name (e.g. "posedge clk").
                             Provided when the user explicitly specifies it.

    Returns:
        A single string ready to be sent to an LLM API.
    """
    sections = []

    # 1. System instructions
    sections.append(SYSTEM_PROMPT)

    # 2. Few-shot examples from retrieval
    if retrieved_examples:
        sections.append(
            "\n\n"
            "REFERENCE EXAMPLES\n"
            "==================\n"
            "Study these examples carefully. They show the exact style \n"
            "and structure you must follow.\n"
        )
        for i, example in enumerate(retrieved_examples, start=1):
            sections.append(format_few_shot_example(
                index=i,
                code=example["Code"],
                assertion=example["Assertion"],
            ))

    # 3. Optional clock context
    if clock_hint:
        sections.append(
            f"\n\nCLOCK CONTEXT\n"
            f"=============\n"
            f"The design uses: `{clock_hint}`\n"
            f"Use this clock in every synchronous property.\n"
        )

    # 4. The actual user query
    sections.append(
        "\n\n"
        "YOUR TASK\n"
        "=========\n"
        "Analyze the following RTL, output your reasoning in an <analysis> block, \n"
        "and then generate the final output structured exactly as requested (1. Assertions, 2. Explanation, 3. Edge cases covered).\n\n"
        f"RTL Code:\n"
        f"```systemverilog\n{query_rtl.strip()}\n```\n\n"
        f"Assertions Output:\n"
    )

    return "\n".join(sections)


# ─────────────────────────────────────────────────────────────
# NATURAL LANGUAGE PROMPT COMPONENTS
# ─────────────────────────────────────────────────────────────

NL_SYSTEM_PROMPT = """\
You are an expert in SystemVerilog Assertions and hardware verification.

Convert the following natural language specification into SystemVerilog Assertions.

Instructions:
* Identify conditions, sequences, and timing behavior
* Use correct SVA syntax
* Assume clock and reset if needed
* Be precise and complete

REASONING STEP:
Before writing the final structure, you MUST output an <analysis> block where you extract:
<analysis>
  <timing>Expected timing (e.g. combinational vs synchronous)</timing>
  <condition>The triggering conditions</condition>
  <action>The expected outcome or sequence</action>
</analysis>

OUTPUT FORMAT:
Your final output MUST follow this exact structure after the analysis block:

<analysis>...</analysis>

1. Assertions
```systemverilog
property <PropertyName>;
  ...
endproperty
```

## Explanation
Briefly explain what each assertion checks.

## Edge Cases Covered
List the edge cases (e.g., reset, default assignments, mutual exclusion).
"""

def format_nl_few_shot_example(index: int, code: str, assertion: str) -> str:
    """Format an example for NL prompt (uses the RTL representation as context)."""
    props = []
    for part in assertion.strip().split("endproperty"):
        part = part.strip()
        if part:
            props.append(part + " endproperty")
    assertion_block = "\n".join(props)
    
    return (
        f"### Example {index}\n\n"
        f"Reference RTL Code:\n"
        f"```systemverilog\n{code.strip()}\n```\n\n"
        f"Assertions Output:\n"
        f"```systemverilog\n{assertion_block}\n```\n"
    )

def build_nl_prompt(
    query_nl: str,
    retrieved_examples: list[dict],
    clock_hint: str | None = None,
) -> str:
    """
    Assemble the full LLM prompt for Natural Language queries.
    """
    sections = []
    if retrieved_examples:
        sections.append(
            "Here are similar examples (RTL and Assertions) for structural reference:\n"
        )
        for i, example in enumerate(retrieved_examples, start=1):
            sections.append(format_nl_few_shot_example(
                index=i,
                code=example["Code"],
                assertion=example["Assertion"],
            ))

    if clock_hint:
        sections.append(f"Assume the design uses clock: `{clock_hint}`.\n")

    sections.append(
        "Now generate assertions for the following natural language description:\n"
        f"USER INPUT: {query_nl.strip()}\n"
    )

    return "\n".join(sections)



# ─────────────────────────────────────────────────────────────
# DEMO
# ─────────────────────────────────────────────────────────────

def run_demo():
    print("\n[1/3] Loading model and index ...")
    model = SentenceTransformer(MODEL_NAME)
    index, records = load_index()
    print(f"  Index: {index.ntotal:,} vectors ready.\n")

    # ── Demo A: Asynchronous if/else ──────────────────────────
    query_async = """\
if ( enable && data_valid ) begin
    output_reg = input_data;
    if ( mode_select == 2'b01 ) begin
        result = input_data + offset;
    end
    else begin
        result = input_data;
    end
end
else begin
    output_reg = 0;
end\
"""

    print("[2/3] Building prompt for asynchronous if/else RTL ...\n")
    examples_async = retrieve(
        query_async, model, index, records,
        top_k=3,
        filter_synchronous="False",   # prefer async examples
    )
    prompt_async = build_prompt(query_async, examples_async)

    _print_prompt(prompt_async, label="PROMPT A (Asynchronous if/else)")

    # ── Demo B: Synchronous case statement ────────────────────
    query_sync = """\
case ( state_reg )
   2'b00 : begin
     next_state <= IDLE;
     count <= 0;
   end
   2'b01 : begin
     next_state <= ACTIVE;
     count <= count + 1;
   end
   default : begin
     next_state <= ERROR;
   end
endcase\
"""

    print("[3/3] Building prompt for synchronous case statement ...\n")
    examples_sync = retrieve(
        query_sync, model, index, records,
        top_k=3,
        filter_synchronous="True",   # prefer sync examples
    )
    prompt_sync = build_prompt(
        query_sync,
        examples_sync,
        clock_hint="posedge clk",
    )

    _print_prompt(prompt_sync, label="PROMPT B (Synchronous case)")

    print("Done. Pass these prompts to an LLM in Step 4.\n")


def _print_prompt(prompt: str, label: str) -> None:
    """Print a prompt with a clear header and separator."""
    bar = "=" * 70
    print(bar)
    print(f"  {label}")
    print(bar)
    print(prompt)
    print(bar)
    print()


if __name__ == "__main__":
    run_demo()
