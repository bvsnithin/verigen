import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const SvaGeneratorUI = () => {
  const [inputMode, setInputMode] = useState('rtl');
  const [inputValue, setInputValue] = useState('');
  const [output, setOutput] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [errorStatus, setErrorStatus] = useState('');

  const handleGenerate = async () => {
    if (!inputValue.trim()) return;
    setIsGenerating(true);
    setErrorStatus('');
    setOutput(null);

    try {
      const response = await fetch('http://localhost:8000/generate_assertions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          input_type: inputMode, 
          content: inputValue 
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      let assertions = "";
      let explanation = "";
      let edgeCases = "";

      // Parse the backend response
      if (typeof data.assertions === 'string') assertions = data.assertions;
      else if (typeof data.sva === 'string') assertions = data.sva;
      else if (typeof data.response === 'string') assertions = data.response;
      else if (typeof data === 'string') assertions = data;
      else assertions = JSON.stringify(data, null, 2);

      explanation = data.explanation || data.explanations || "";
      edgeCases = data.edge_cases || data.edgeCases || "";

      setOutput({
        assertions,
        explanation,
        edgeCases
      });

    } catch (error) {
      console.error("Failed to generate assertions:", error);
      setErrorStatus(`Error: Backend connection failed. Make sure the python backend is running. Details: ${error.message}`);
    } finally {
      setIsGenerating(false);
    }
  };

  const getPlaceholder = () => {
    return inputMode === 'rtl' 
      ? "Paste your SystemVerilog RTL code here..."
      : "Describe the behavior in plain English...";
  };

  return (
    <div className="min-h-screen w-full bg-gradient-to-br from-[#f5f3ff] via-[#ffffff] to-[#ede9fe] flex flex-col justify-center items-center py-12 px-4 relative overflow-hidden font-raleway text-slate-800">
      


      {/* Header Container */}
      <motion.div 
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
        className="z-10 text-center mb-10 w-full max-w-5xl"
      >
        <h1 className="text-4xl md:text-5xl font-semibold tracking-tight text-slate-900 mb-3">
          SVA <span className="bg-gradient-to-r from-purple-600 to-[#e81cff] bg-clip-text text-transparent">Generator</span>
        </h1>
        <p className="text-slate-500 font-medium tracking-wide">
          Intelligent SystemVerilog Assertion generation.
        </p>
      </motion.div>

      {/* Main Glassmorphism Card */}
      <motion.div 
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, delay: 0.1, ease: "easeOut" }}
        className="z-10 w-full max-w-5xl bg-white/10 backdrop-blur-[60px] border border-white/40 shadow-[0_30px_60px_-15px_rgba(0,0,0,0.3)] rounded-[32px] p-6 md:p-10 flex flex-col gap-8 relative overflow-hidden"
      >
        {/* Subtle inner highlight to enhance the glass edge */}
        <div className="absolute inset-0 rounded-[32px] border border-white/60 pointer-events-none"></div>

        {/* Segmented Control / Input Mode Toggle */}
        <div className="flex justify-center relative z-20">
          <div className="bg-white/50 backdrop-blur-md p-1.5 rounded-2xl border border-white/50 shadow-[0_4px_12px_rgba(0,0,0,0.1)] flex space-x-1">
            <button
              onClick={() => setInputMode('rtl')}
              className={`px-8 py-2.5 rounded-xl text-sm font-semibold transition-all duration-300 ${
                inputMode === 'rtl'
                  ? 'bg-white/80 text-purple-700 shadow-[0_2px_10px_rgba(0,0,0,0.05)] border border-white/60'
                  : 'text-slate-500 hover:text-slate-700 hover:bg-white/40'
              }`}
            >
              RTL Mode
            </button>
            <button
              onClick={() => setInputMode('natural_language')}
              className={`px-8 py-2.5 rounded-xl text-sm font-semibold transition-all duration-300 ${
                inputMode === 'natural_language'
                  ? 'bg-white/80 text-purple-700 shadow-[0_2px_10px_rgba(0,0,0,0.05)] border border-white/60'
                  : 'text-slate-500 hover:text-slate-700 hover:bg-white/40'
              }`}
            >
              Natural Language Mode
            </button>
          </div>
        </div>

        {/* Dynamic Input Box */}
        <div className="relative group z-20">
          <div className="relative flex flex-col bg-white/60 backdrop-blur-xl rounded-3xl border-2 border-purple-400 shadow-[inset_0_2px_8px_rgba(0,0,0,0.02)] focus-within:border-purple-500 overflow-hidden min-h-[220px] transition-colors duration-300">
            <div className="px-6 py-4 border-b border-white/40 bg-white/30 flex items-center justify-between">
              <span className="text-[13px] font-bold text-purple-800/80 uppercase tracking-widest flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full shadow-sm ${inputMode === 'rtl' ? 'bg-indigo-400' : 'bg-fuchsia-400'}`}></div>
                Input ({inputMode === 'rtl' ? 'SystemVerilog' : 'English'})
              </span>
            </div>
            <textarea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder={getPlaceholder()}
              className="flex-grow w-full p-6 bg-transparent text-base font-medium text-slate-700 placeholder-slate-400/70 outline-none resize-none align-top focus:ring-0"
              spellCheck="false"
            />
          </div>
        </div>

        {/* Generate Button */}
        <div className="flex justify-center relative z-20">
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={handleGenerate}
            disabled={!inputValue.trim() || isGenerating}
            className={`
              relative px-12 py-4 rounded-2xl font-semibold text-base tracking-wide
              transition-all duration-300 outline-none
              ${!inputValue.trim() || isGenerating
                ? 'opacity-50 cursor-not-allowed bg-slate-200/50 text-slate-400 shadow-none' 
                : 'bg-gradient-to-r from-purple-500 to-indigo-500 text-white shadow-lg shadow-purple-500/30 hover:shadow-xl hover:shadow-purple-500/40 ring-1 ring-purple-500/50'
              }
            `}
          >
            <span className="relative flex items-center justify-center gap-3">
              {isGenerating ? (
                <>
                  <motion.div 
                    animate={{ rotate: 360 }}
                    transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
                    className="w-5 h-5 border-[3px] border-white/30 border-t-white rounded-full"
                  />
                  Generating...
                </>
              ) : (
                'Generate Assertions'
              )}
            </span>
          </motion.button>
        </div>

        {/* Error State */}
        <AnimatePresence>
          {errorStatus && (
            <motion.div 
              initial={{ opacity: 0, height: 0, y: -10 }}
              animate={{ opacity: 1, height: 'auto', y: 0 }}
              exit={{ opacity: 0, height: 0, y: -10 }}
              className="relative z-20 text-red-600 text-sm font-medium text-center bg-red-50/80 backdrop-blur-md p-4 rounded-2xl border border-red-200 shadow-sm"
            >
              {errorStatus}
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      {/* Output Panel Container */}
      <AnimatePresence>
        {output && (
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            transition={{ duration: 0.6, ease: "easeOut", delay: 0.1 }}
            className="z-10 w-full max-w-5xl mt-8 mb-12"
          >
            <div className="bg-white/10 backdrop-blur-[60px] border border-white/40 shadow-[0_30px_60px_-15px_rgba(0,0,0,0.3)] rounded-[32px] p-6 md:p-10 flex flex-col gap-8 relative overflow-hidden">
              <div className="absolute inset-0 rounded-[32px] border border-white/40 pointer-events-none"></div>

              <div className="flex items-center justify-between border-b border-white/40 pb-5 relative z-20">
                <h2 className="text-xl font-bold text-slate-800 flex items-center gap-3">
                  <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.5)]"></div>
                  Result Output
                </h2>
                <button 
                  onClick={() => navigator.clipboard.writeText(output.assertions)}
                  className="text-sm font-semibold text-purple-700 bg-white/60 hover:bg-white backdrop-blur-md px-5 py-2.5 rounded-xl transition-all border border-white/50 shadow-sm hover:shadow active:scale-95"
                >
                  Copy Assertions
                </button>
              </div>

              {/* 1. Assertions Section */}
              <div className="flex flex-col relative z-20">
                <h3 className="text-[13px] font-bold text-slate-500 uppercase tracking-widest mb-3">1. Assertions</h3>
                <div className="bg-white/60 backdrop-blur-md rounded-2xl border border-white/50 p-6 shadow-[inset_0_2px_8px_rgba(0,0,0,0.02)] overflow-x-auto">
                  <pre className="text-[14px] font-mono text-slate-800 whitespace-pre-wrap leading-relaxed">
                    {output.assertions || "// No assertions generated."}
                  </pre>
                </div>
              </div>

              {/* 2. Explanation Section */}
              {(output.explanation) && (
                <div className="flex flex-col relative z-20">
                  <h3 className="text-[13px] font-bold text-slate-500 uppercase tracking-widest mb-3">2. Explanation</h3>
                  <div className="bg-purple-50/50 backdrop-blur-md rounded-2xl border border-purple-100/60 text-slate-700 p-6 leading-relaxed text-[15px] font-medium shadow-[inset_0_2px_8px_rgba(0,0,0,0.02)]">
                    {output.explanation.split('\n').map((line, i) => (
                      <span key={i}>{line}<br/></span>
                    ))}
                  </div>
                </div>
              )}

              {/* 3. Edge Cases Section */}
              {(output.edgeCases) && (
                <div className="flex flex-col relative z-20">
                  <h3 className="text-[13px] font-bold text-slate-500 uppercase tracking-widest mb-3">3. Edge Cases</h3>
                  <div className="bg-fuchsia-50/50 backdrop-blur-md rounded-2xl border border-fuchsia-100/60 text-slate-700 p-6 leading-relaxed text-[15px] font-medium shadow-[inset_0_2px_8px_rgba(0,0,0,0.02)]">
                    {output.edgeCases.split('\n').map((line, i) => (
                      <span key={i}>{line}<br/></span>
                    ))}
                  </div>
                </div>
              )}

            </div>
          </motion.div>
        )}
      </AnimatePresence>

    </div>
  );
};

export default SvaGeneratorUI;
