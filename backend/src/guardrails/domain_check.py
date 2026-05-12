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

_REJECTION = (
    "I'm VeriGen, a SystemVerilog assertion generator. I can only help with "
    "RTL code analysis and assertion generation. Please provide RTL code or a "
    "hardware design specification."
)

_PROMPT = (
    "Is the following input related to RTL code, hardware design, SystemVerilog, "
    "Verilog, digital circuits, FPGAs, ASICs, or hardware verification? "
    "Reply YES or NO only.\n\nInput: {user_input}"
)


async def check_input_domain(user_input: str) -> tuple[bool, str]:
    """
    Returns (allowed, rejection_message).
    Fast regex for RTL keywords; LLM fallback for natural language.
    Fails open on errors so legitimate requests are never blocked.
    """
    if _RTL_PATTERN.search(user_input):
        return True, ""

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
                "content": _PROMPT.format(user_input=user_input[:500]),
            }],
            stream=False,
        )
        answer = response["message"]["content"].strip().upper()
        return (True, "") if answer.startswith("YES") else (False, _REJECTION)
    except Exception:
        return False, _REJECTION
