"""
main.py
=======
The main entry point for the VeriGen SVA Generator.
Use this script to generate SystemVerilog Assertions (SVA) from RTL snippets.

Usage:
    python main.py
"""

import os
from src.pipeline import SVAGeneratorPipeline

def main():
    print("=" * 70)
    print(" VeriGen: AI-Powered SVA Generator (Step 7 Pipeline)")
    print("=" * 70)

    # Initialize the engine (loads model and indexes only once)
    pipeline = SVAGeneratorPipeline(top_k=3)

    # Example RTL input
    rtl_input = """\
always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        valid_out <= 1'b0;
        data_out  <= 8'h00;
    end else if (enable) begin
        valid_out <= 1'b1;
        data_out  <= data_in + offset;
    end else begin
        valid_out <= 1'b0;
    end
end\
"""

    print("\n[INPUT] Target RTL Code:")
    print("-" * 30)
    print(rtl_input)
    print("-" * 30)

    print("\n[PROCESS] Generating Assertions with RAG & Reasoning ...\n")

    # Generate assertions
    try:
        pipeline.generate_assertions(
            rtl_code=rtl_input,
            clock_hint="posedge clk",
            synchronous_filter="True"
        )
    except Exception as e:
        print(f"\n[ERROR] Failed to generate assertions: {e}")
        if "OLLAMA_API_KEY" not in os.environ:
            print("Tip: Make sure OLLAMA_API_KEY is set in your .env file.")

    print("\n" + "=" * 70)
    print(" Done.")
    print("=" * 70)

if __name__ == "__main__":
    main()
