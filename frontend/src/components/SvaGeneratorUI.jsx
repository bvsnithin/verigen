import React, { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

// ─── Utility: strip LLM internal XML tags from output ────────────────────────
// The LLM sometimes emits <analysis>...</analysis> or similar internal reasoning
// blocks. We strip any XML-like tags and their content before rendering.
function cleanLLMOutput(raw) {
  if (!raw) return '';
  // Remove block-level XML tags like <analysis>...</analysis> (including content)
  let cleaned = raw.replace(/<(analysis|reasoning|thinking|chain_of_thought|internal)[^>]*>[\s\S]*?<\/\1>/gi, '');
  // Remove any remaining stray XML tags (self-closing or otherwise)
  cleaned = cleaned.replace(/<\/?[a-zA-Z][a-zA-Z0-9_-]*(\s[^>]*)?\/?>/g, '');
  // Collapse 3+ blank lines into 2
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n');
  return cleaned.trim();
}

// ─── Progress Steps ───────────────────────────────────────────────────────────

const STEPS = [
  { key: 'classify', label: 'Classify' },
  { key: 'retrieve', label: 'Retrieve' },
  { key: 'prompt',   label: 'Prompt'   },
  { key: 'generate', label: 'Generate' },
];

const MSG_TO_STEP = {
  'Classifying':       'classify',
  'Loading knowledge': 'classify',
  'Retrieving':        'retrieve',
  'Building reasoning':'prompt',
  'Generating':        'generate',
};

function resolveStep(message) {
  for (const [substr, step] of Object.entries(MSG_TO_STEP)) {
    if (message.includes(substr)) return step;
  }
  return null;
}

function ProgressTracker({ statusMsg, done }) {
  const activeStep = resolveStep(statusMsg);
  const activeIdx  = STEPS.findIndex(s => s.key === activeStep);

  return (
    <div className="w-full flex flex-col gap-5">
      {/* Status line */}
      <div className="flex items-center gap-3">
        <motion.div
          animate={{ rotate: done ? 0 : 360 }}
          transition={{ repeat: done ? 0 : Infinity, duration: 1.1, ease: 'linear' }}
          className={`w-4 h-4 border-2 rounded-full flex-shrink-0 transition-colors duration-300 ${
            done ? 'border-black' : 'border-zinc-300 border-t-black'
          }`}
        />
        <span className="text-sm font-medium text-zinc-600 tracking-tight truncate">
          {statusMsg}
        </span>
      </div>

      {/* Step nodes + connectors */}
      <div className="flex items-start gap-0">
        {STEPS.map((step, i) => {
          const isCompleted = done || i < activeIdx;
          const isActive    = !done && i === activeIdx;

          return (
            <React.Fragment key={step.key}>
              <div className="flex flex-col items-center gap-2 flex-shrink-0 w-20">
                <motion.div
                  animate={isActive ? { scale: [1, 1.12, 1] } : {}}
                  transition={{ repeat: Infinity, duration: 1.3, ease: 'easeInOut' }}
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold border-2 transition-all duration-300 ${
                    isCompleted
                      ? 'bg-black border-black text-white'
                      : isActive
                      ? 'bg-white border-black text-black shadow-[0_0_0_3px_rgba(0,0,0,0.08)]'
                      : 'bg-white border-zinc-200 text-zinc-400'
                  }`}
                >
                  {isCompleted ? '✓' : i + 1}
                </motion.div>
                <span className={`text-[10px] text-center leading-tight font-semibold uppercase tracking-wider transition-colors duration-300 ${
                  isCompleted ? 'text-black' :
                  isActive    ? 'text-zinc-700' : 'text-zinc-400'
                }`}>
                  {step.label}
                </span>
              </div>

              {i < STEPS.length - 1 && (
                <div className="flex-1 h-0.5 mt-4 mx-1 rounded-full overflow-hidden bg-zinc-150 border border-zinc-200">
                  <motion.div
                    className="h-full bg-black rounded-full"
                    initial={{ width: '0%' }}
                    animate={{ width: isCompleted ? '100%' : isActive ? '45%' : '0%' }}
                    transition={{ duration: 0.45, ease: 'easeInOut' }}
                  />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}

// ─── Code Block ───────────────────────────────────────────────────────────────

function CodeBlock({ children, language }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(children);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="rounded-xl overflow-hidden border border-zinc-200 bg-[#111111] my-3">
      {language && (
        <div className="flex items-center justify-between px-4 py-2.5 bg-[#1a1a1a] border-b border-zinc-800">
          <span className="text-[11px] font-bold text-zinc-400 uppercase tracking-widest" style={{ fontFamily: 'JetBrains Mono, monospace' }}>
            {language}
          </span>
          <button
            onClick={handleCopy}
            className="text-[11px] font-medium text-zinc-500 hover:text-zinc-200 transition-colors px-2.5 py-1 rounded-md hover:bg-white/10"
          >
            {copied ? '✓ Copied' : 'Copy'}
          </button>
        </div>
      )}
      <pre className="p-5 overflow-x-auto text-[13px] text-zinc-200 leading-relaxed" style={{ fontFamily: 'JetBrains Mono, monospace' }}>
        <code>{children}</code>
      </pre>
    </div>
  );
}

// ─── Markdown Renderers ───────────────────────────────────────────────────────

const mdComponents = {
  code({ inline, className, children }) {
    const lang = (className || '').replace('language-', '');
    if (inline) {
      return (
        <code
          className="bg-zinc-100 text-zinc-800 text-[13px] px-1.5 py-0.5 rounded-md border border-zinc-200"
          style={{ fontFamily: 'JetBrains Mono, monospace' }}
        >
          {children}
        </code>
      );
    }
    return <CodeBlock language={lang}>{String(children).trimEnd()}</CodeBlock>;
  },
  p({ children }) {
    return <p className="text-[15px] text-zinc-700 leading-relaxed mb-3 last:mb-0">{children}</p>;
  },
  h1({ children }) {
    return <h1 className="text-xl font-bold text-zinc-900 mt-5 mb-2 tracking-tight" style={{ fontFamily: 'Funnel Display, sans-serif' }}>{children}</h1>;
  },
  h2({ children }) {
    return <h2 className="text-lg font-semibold text-zinc-800 mt-4 mb-2 tracking-tight" style={{ fontFamily: 'Funnel Display, sans-serif' }}>{children}</h2>;
  },
  h3({ children }) {
    return <h3 className="text-base font-semibold text-zinc-800 mt-3 mb-1.5">{children}</h3>;
  },
  ul({ children }) {
    return <ul className="list-disc list-outside pl-5 space-y-1.5 text-[15px] text-zinc-700 mb-3">{children}</ul>;
  },
  ol({ children }) {
    return <ol className="list-decimal list-outside pl-5 space-y-1.5 text-[15px] text-zinc-700 mb-3">{children}</ol>;
  },
  li({ children }) {
    return <li className="leading-relaxed pl-0.5">{children}</li>;
  },
  strong({ children }) {
    return <strong className="font-semibold text-zinc-900">{children}</strong>;
  },
  em({ children }) {
    return <em className="italic text-zinc-600">{children}</em>;
  },
  blockquote({ children }) {
    return (
      <blockquote className="border-l-[3px] border-zinc-300 pl-4 py-0.5 my-3 text-zinc-500 italic">
        {children}
      </blockquote>
    );
  },
  hr() {
    return <hr className="border-0 border-t border-zinc-200 my-4" />;
  },
  table({ children }) {
    return (
      <div className="overflow-x-auto my-3 rounded-lg border border-zinc-200">
        <table className="w-full text-sm text-zinc-700">{children}</table>
      </div>
    );
  },
  th({ children }) {
    return <th className="px-4 py-2.5 text-left font-semibold text-zinc-800 bg-zinc-50 border-b border-zinc-200">{children}</th>;
  },
  td({ children }) {
    return <td className="px-4 py-2.5 border-b border-zinc-100">{children}</td>;
  },
};

// ─── Main Component ───────────────────────────────────────────────────────────

const SvaGeneratorUI = () => {
  const [inputMode,     setInputMode]     = useState('rtl');
  const [inputValue,    setInputValue]    = useState('');
  const [output,        setOutput]        = useState(null);
  const [isGenerating,  setIsGenerating]  = useState(false);
  const [statusMsg,     setStatusMsg]     = useState('');
  const [errorStatus,   setErrorStatus]   = useState('');
  const [activeTab,     setActiveTab]     = useState('assertions');
  const abortRef = useRef(null);

  const handleGenerate = async () => {
    if (!inputValue.trim()) return;

    setIsGenerating(true);
    setErrorStatus('');
    setOutput(null);
    setStatusMsg('Connecting to pipeline...');
    setActiveTab('assertions');

    try {
      const response = await fetch('http://localhost:8000/generate_assertions/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ input_type: inputMode, content: inputValue }),
        signal: abortRef.current,
      });

      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

      const reader  = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer    = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const messages = buffer.split('\n\n');
        buffer = messages.pop();

        for (const msg of messages) {
          if (!msg.trim()) continue;

          const lines    = msg.split('\n');
          const evtLine  = lines.find(l => l.startsWith('event:'));
          const dataLine = lines.find(l => l.startsWith('data:'));
          if (!evtLine || !dataLine) continue;

          const event   = evtLine.replace('event:', '').trim();
          const payload = JSON.parse(dataLine.replace('data:', '').trim());

          if (event === 'status') {
            setStatusMsg(payload.message);
          } else if (event === 'result') {
            setStatusMsg('Done!');
            setOutput({
              assertions:  cleanLLMOutput(payload.assertions),
              explanation: cleanLLMOutput(payload.explanation),
            });
          } else if (event === 'error') {
            setErrorStatus(`Error: ${payload.message}`);
          }
        }
      }
    } catch (error) {
      if (error.name !== 'AbortError') {
        console.error('Failed to generate assertions:', error);
        setErrorStatus(`Backend connection failed. Make sure the Python server is running on port 8000.\n\nDetails: ${error.message}`);
      }
    } finally {
      setIsGenerating(false);
    }
  };

  const getPlaceholder = () =>
    inputMode === 'rtl'
      ? 'Paste your SystemVerilog RTL code here...'
      : 'Describe the hardware behaviour in plain English...';

  const isDone = !isGenerating && output !== null;

  const tabs = [
    { key: 'assertions',  label: 'Assertions',  content: output?.assertions  },
    { key: 'explanation', label: 'Explanation',  content: output?.explanation },
  ].filter(t => t.content?.trim());

  // ── render ──────────────────────────────────────────────────────────────────
  return (
    <div
      className="min-h-screen w-full bg-white flex flex-col items-center py-16 px-4"
      style={{ fontFamily: 'Inter, sans-serif' }}
    >
      {/* ── Header ── */}
      <motion.div
        initial={{ opacity: 0, y: -16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.55, ease: 'easeOut' }}
        className="text-center mb-12 w-full max-w-3xl"
      >
        <h1
          className="text-5xl md:text-6xl font-bold tracking-tight text-zinc-950 mb-3"
          style={{ fontFamily: 'Funnel Display, sans-serif' }}
        >
          SVA Generator
        </h1>
        <p className="text-zinc-400 text-base font-normal tracking-wide">
          Intelligent SystemVerilog Assertion generation — RAG + LLM powered.
        </p>
      </motion.div>

      {/* ── Main Card ── */}
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.55, delay: 0.08, ease: 'easeOut' }}
        className="w-full max-w-3xl flex flex-col gap-6"
      >
        {/* Mode Toggle */}
        <div className="flex gap-1 p-1 bg-zinc-100 rounded-xl border border-zinc-200 w-fit self-center">
          {['rtl', 'natural_language'].map(mode => (
            <button
              key={mode}
              onClick={() => setInputMode(mode)}
              className={`px-6 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                inputMode === mode
                  ? 'bg-white text-zinc-900 shadow-sm border border-zinc-200'
                  : 'text-zinc-500 hover:text-zinc-800'
              }`}
            >
              {mode === 'rtl' ? 'RTL Mode' : 'Natural Language'}
            </button>
          ))}
        </div>

        {/* Input Area */}
        <div className="bg-white rounded-2xl border border-zinc-200 shadow-sm overflow-hidden">
          {/* Toolbar */}
          <div className="flex items-center gap-2.5 px-5 py-3.5 border-b border-zinc-100 bg-zinc-50">
            <div className={`w-2 h-2 rounded-full ${inputMode === 'rtl' ? 'bg-zinc-800' : 'bg-zinc-400'}`} />
            <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-widest">
              {inputMode === 'rtl' ? 'SystemVerilog Input' : 'Natural Language Input'}
            </span>
          </div>
          <textarea
            value={inputValue}
            onChange={e => setInputValue(e.target.value)}
            placeholder={getPlaceholder()}
            className="w-full px-5 py-5 bg-transparent text-[15px] text-zinc-800 placeholder-zinc-300 outline-none resize-none min-h-[220px] leading-relaxed"
            style={{ fontFamily: inputMode === 'rtl' ? 'JetBrains Mono, monospace' : 'Inter, sans-serif' }}
            spellCheck="false"
          />
        </div>

        {/* Generate Button */}
        <div className="flex justify-center">
          <motion.button
            whileHover={{ scale: 1.015 }}
            whileTap={{ scale: 0.985 }}
            onClick={handleGenerate}
            disabled={!inputValue.trim() || isGenerating}
            className={`px-10 py-3.5 rounded-xl text-sm font-semibold tracking-wide transition-all duration-200 flex items-center gap-3 ${
              !inputValue.trim() || isGenerating
                ? 'bg-zinc-100 text-zinc-400 cursor-not-allowed border border-zinc-200'
                : 'bg-zinc-950 text-white shadow-md hover:shadow-lg hover:bg-zinc-800 active:scale-[0.99]'
            }`}
          >
            {isGenerating ? (
              <>
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ repeat: Infinity, duration: 0.9, ease: 'linear' }}
                  className="w-4 h-4 border-2 border-white/25 border-t-white rounded-full"
                />
                Generating...
              </>
            ) : (
              'Generate Assertions'
            )}
          </motion.button>
        </div>

        {/* Progress Tracker */}
        <AnimatePresence>
          {(isGenerating || (isDone && statusMsg)) && (
            <motion.div
              key="progress"
              initial={{ opacity: 0, height: 0, marginTop: 0 }}
              animate={{ opacity: 1, height: 'auto', marginTop: 0 }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.3 }}
              className="bg-white rounded-2xl border border-zinc-200 shadow-sm p-6 overflow-hidden"
            >
              <ProgressTracker statusMsg={statusMsg} done={isDone} />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Error State */}
        <AnimatePresence>
          {errorStatus && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 font-medium whitespace-pre-wrap leading-relaxed"
            >
              {errorStatus}
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      {/* ── Output Panel ── */}
      <AnimatePresence>
        {output && (
          <motion.div
            initial={{ opacity: 0, y: 32 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 16 }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
            className="w-full max-w-3xl mt-8 mb-16"
          >
            <div className="bg-white rounded-2xl border border-zinc-200 shadow-sm overflow-hidden">

              {/* Panel Header */}
              <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-100 bg-zinc-50">
                <div className="flex items-center gap-2.5">
                  <div className="w-2 h-2 rounded-full bg-zinc-950" />
                  <h2
                    className="text-base font-semibold text-zinc-900"
                    style={{ fontFamily: 'Funnel Display, sans-serif' }}
                  >
                    Generated Result
                  </h2>
                </div>
                <button
                  onClick={() =>
                    navigator.clipboard.writeText(
                      activeTab === 'assertions' ? output.assertions : output.explanation
                    )
                  }
                  className="text-xs font-semibold text-zinc-500 hover:text-zinc-900 bg-white border border-zinc-200 hover:border-zinc-400 px-3.5 py-1.5 rounded-lg transition-all shadow-sm active:scale-95"
                >
                  Copy
                </button>
              </div>

              {/* Tabs */}
              {tabs.length > 1 && (
                <div className="flex gap-1 px-6 pt-4">
                  {tabs.map(tab => (
                    <button
                      key={tab.key}
                      onClick={() => setActiveTab(tab.key)}
                      className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                        activeTab === tab.key
                          ? 'bg-zinc-950 text-white'
                          : 'text-zinc-500 hover:text-zinc-800 hover:bg-zinc-100'
                      }`}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>
              )}

              {/* Tab Content */}
              <AnimatePresence mode="wait">
                {tabs.map(tab =>
                  activeTab === tab.key ? (
                    <motion.div
                      key={tab.key}
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -6 }}
                      transition={{ duration: 0.2 }}
                      className="p-6"
                    >
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={mdComponents}
                      >
                        {tab.content}
                      </ReactMarkdown>
                    </motion.div>
                  ) : null
                )}
              </AnimatePresence>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default SvaGeneratorUI;
