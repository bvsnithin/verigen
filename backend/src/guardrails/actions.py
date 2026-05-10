import os
import re

from ollama import Client

_RTL_PATTERN = re.compile(
    r"\b(module|endmodule|always|assign|wire|reg|logic|input|output|inout|"
    r"posedge|negedge|parameter|localparam|generate|endgenerate|property|"
    r"sequence|assert|assume|cover|clocking|endclocking|interface|endinterface|"
    r"typedef|enum|struct|systemverilog|verilog|rtl|hdl|fpga|asic|assertion|"
    r"sva|flip.?flop|latch|register|fsm|state.?machine|clock|reset)\b",
    re.IGNORECASE,
)

_CLASSIFICATION_PROMPT = (
    "You are a domain classifier for VeriGen, a SystemVerilog assertion generator.\n"
    "Determine if the following input is related to: RTL code, hardware design, "
    "SystemVerilog, Verilog, digital circuits, FPGAs, ASICs, or hardware verification.\n"
    "Reply with YES or NO only — no explanation.\n\n"
    "Input: {user_input}"
)


async def check_input_domain(context: dict) -> bool:
    user_input = context.get("user_message", "")

    # Fast path: RTL/hardware keyword present
    if _RTL_PATTERN.search(user_input):
        return True

    # LLM-based check for natural language or ambiguous inputs
    api_key = os.environ.get("OLLAMA_API_KEY", "")
    client = Client(
        host="https://ollama.com",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    try:
        response = client.chat(
            "qwen3-coder-next",
            messages=[{
                "role": "user",
                "content": _CLASSIFICATION_PROMPT.format(user_input=user_input[:500]),
            }],
            stream=False,
        )
        answer = response["message"]["content"].strip().upper()
        return answer.startswith("YES")
    except Exception:
        return True  # fail open — don't block legitimate requests on LLM errors
