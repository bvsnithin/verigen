import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

// ─── Utility: strip LLM internal XML tags ────────────────────────────────────
function cleanLLMOutput(raw) {
  if (!raw) return '';
  let cleaned = raw.replace(/<(analysis|reasoning|thinking|chain_of_thought|internal)[^>]*>[\s\S]*?<\/\1>/gi, '');
  cleaned = cleaned.replace(/<\/?[a-zA-Z][a-zA-Z0-9_-]*(\s[^>]*)?\/?\>/g, '');
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n');
  return cleaned.trim();
}

// ─── Agent pipeline steps ─────────────────────────────────────────────────────
const AGENTS = [
  { key: 'rag',       label: 'RAG',       icon: '1', desc: 'Retrieving context'    },
  { key: 'generator', label: 'Generate',  icon: '2', desc: 'Generating assertions' },
  { key: 'summarizer',label: 'Summarize', icon: '3', desc: 'Summarizing results'   },
];

// ─── AgentTimeline ────────────────────────────────────────────────────────────
function AgentTimeline({ agentStates, done, isDarkMode }) {
  return (
    <div className="w-full flex flex-col gap-4">
      {AGENTS.map((agent, i) => {
        const s = agentStates[agent.key] || 'idle';
        const isRunning  = s === 'running';
        const isDone     = s === 'done';
        const isRetrying = s === 'retrying';
        const isIdle     = s === 'idle';

        return (
          <div key={agent.key} className="flex items-start gap-4">
            {/* Node */}
            <div className="flex flex-col items-center gap-1 flex-shrink-0">
              <motion.div
                animate={isRunning ? { scale: [1, 1.1, 1] } : {}}
                transition={{ repeat: Infinity, duration: 1.3, ease: 'easeInOut' }}
                className={`
                  w-10 h-10 rounded-full flex items-center justify-center text-base
                  border-2 transition-all duration-300
                  ${isDone ? (isDarkMode ? 'bg-white border-white text-zinc-950' : 'bg-zinc-950 border-zinc-950 text-white') : ''}
                  ${isRunning ? (isDarkMode ? 'bg-zinc-800 border-white text-white shadow-md' : 'bg-white border-zinc-950 text-zinc-950 shadow-md') : ''}
                  ${isRetrying ? (isDarkMode ? 'bg-amber-900/30 border-amber-500 text-amber-400' : 'bg-amber-50 border-amber-400 text-amber-700') : ''}
                  ${isIdle ? (isDarkMode ? 'bg-zinc-900 border-zinc-800 text-zinc-600' : 'bg-white border-zinc-200 text-zinc-300') : ''}
                `}
              >
                {isDone ? 'OK' : agent.icon}
              </motion.div>
              {i < AGENTS.length - 1 && (
                <div className={`w-0.5 h-6 rounded-full mt-1 ${isDarkMode ? 'bg-zinc-800' : 'bg-zinc-200'}`}>
                  <motion.div
                    className={`w-full rounded-full ${isDarkMode ? 'bg-white' : 'bg-zinc-950'}`}
                    initial={{ height: '0%' }}
                    animate={{ height: isDone ? '100%' : '0%' }}
                    transition={{ duration: 0.4, ease: 'easeInOut' }}
                  />
                </div>
              )}
            </div>

            {/* Label + status */}
            <div className="pt-1.5 flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className={`text-sm font-semibold transition-colors duration-200
                  ${isDone ? (isDarkMode ? 'text-white' : 'text-zinc-900') : isRunning ? (isDarkMode ? 'text-white' : 'text-zinc-900') : (isDarkMode ? 'text-zinc-500' : 'text-zinc-400')}`}>
                  {agent.label}
                </span>
                {isRunning && (
                  <span className={`text-[10px] font-semibold uppercase tracking-widest px-2 py-0.5 rounded-full animate-pulse border
                    ${isDarkMode ? 'bg-zinc-800 border-zinc-700 text-zinc-300' : 'bg-zinc-100 border-zinc-200 text-zinc-500'}`}>
                    Running
                  </span>
                )}
                {isRetrying && (
                  <span className={`text-[10px] font-semibold uppercase tracking-widest px-2 py-0.5 rounded-full border
                    ${isDarkMode ? 'bg-amber-900/30 border-amber-800/50 text-amber-400' : 'bg-amber-50 border-amber-200 text-amber-600'}`}>
                    Refining
                  </span>
                )}
                {isDone && (
                  <span className={`text-[10px] font-semibold uppercase tracking-widest px-2 py-0.5 rounded-full border
                    ${isDarkMode ? 'bg-emerald-900/30 border-emerald-800/50 text-emerald-400' : 'bg-emerald-50 border-emerald-200 text-emerald-600'}`}>
                    Done
                  </span>
                )}
              </div>
              <p className={`text-xs mt-0.5 transition-colors duration-200
                ${isIdle ? (isDarkMode ? 'text-zinc-600' : 'text-zinc-300') : (isDarkMode ? 'text-zinc-400' : 'text-zinc-500')}`}>
                {agent.desc}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── Code Block ───────────────────────────────────────────────────────────────
function CodeBlock({ children, language, isDarkMode }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(children);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={`rounded-xl overflow-hidden border my-3 transition-colors duration-300 ${isDarkMode ? 'border-zinc-800 bg-[#0a0a0a]' : 'border-zinc-200 bg-[#111111]'}`}>
      {language && (
        <div className={`flex items-center justify-between px-4 py-2.5 border-b transition-colors duration-300 ${isDarkMode ? 'bg-[#141414] border-zinc-800' : 'bg-[#1a1a1a] border-zinc-800'}`}>
          <span className="text-[11px] font-bold text-zinc-400 uppercase tracking-widest"
            style={{ fontFamily: "'Intel One Mono', monospace" }}>
            {language}
          </span>
          <button
            onClick={handleCopy}
            className="text-[11px] font-medium text-zinc-500 hover:text-zinc-200 transition-colors
              px-2.5 py-1 rounded-md hover:bg-white/10"
          >
            {copied ? 'Copied' : 'Copy'}
          </button>
        </div>
      )}
      <pre className="p-5 overflow-x-auto text-[13px] text-zinc-200 leading-relaxed"
        style={{ fontFamily: "'Intel One Mono', monospace" }}>
        <code>{children}</code>
      </pre>
    </div>
  );
}

// ─── Markdown renderer map ────────────────────────────────────────────────────
const getMdComponents = (isDarkMode) => ({
  code({ inline, className, children }) {
    const lang = (className || '').replace('language-', '');
    if (inline) {
      return (
        <code className={`text-[13px] px-1.5 py-0.5 rounded-md border transition-colors duration-300
          ${isDarkMode ? 'bg-zinc-800 border-zinc-700 text-zinc-300' : 'bg-zinc-100 border-zinc-200 text-zinc-800'}`}
          style={{ fontFamily: "'Intel One Mono', monospace" }}>
          {children}
        </code>
      );
    }
    return <CodeBlock language={lang} isDarkMode={isDarkMode}>{String(children).trimEnd()}</CodeBlock>;
  },
  p({ children })         { return <p className={`text-[15px] leading-relaxed mb-3 last:mb-0 transition-colors duration-300 ${isDarkMode ? 'text-zinc-300' : 'text-zinc-700'}`}>{children}</p>; },
  h1({ children })        { return <h1 className={`text-xl font-bold mt-5 mb-2 tracking-tight transition-colors duration-300 ${isDarkMode ? 'text-white' : 'text-zinc-900'}`} style={{ fontFamily: 'Funnel Display, sans-serif' }}>{children}</h1>; },
  h2({ children })        { return <h2 className={`text-lg font-semibold mt-4 mb-2 tracking-tight transition-colors duration-300 ${isDarkMode ? 'text-zinc-100' : 'text-zinc-800'}`} style={{ fontFamily: 'Funnel Display, sans-serif' }}>{children}</h2>; },
  h3({ children })        { return <h3 className={`text-base font-semibold mt-3 mb-1.5 transition-colors duration-300 ${isDarkMode ? 'text-zinc-200' : 'text-zinc-800'}`}>{children}</h3>; },
  ul({ children })        { return <ul className={`list-disc list-outside pl-5 space-y-1.5 text-[15px] mb-3 transition-colors duration-300 ${isDarkMode ? 'text-zinc-300' : 'text-zinc-700'}`}>{children}</ul>; },
  ol({ children })        { return <ol className={`list-decimal list-outside pl-5 space-y-1.5 text-[15px] mb-3 transition-colors duration-300 ${isDarkMode ? 'text-zinc-300' : 'text-zinc-700'}`}>{children}</ol>; },
  li({ children })        { return <li className="leading-relaxed pl-0.5">{children}</li>; },
  strong({ children })    { return <strong className={`font-semibold transition-colors duration-300 ${isDarkMode ? 'text-white' : 'text-zinc-900'}`}>{children}</strong>; },
  em({ children })        { return <em className={`italic transition-colors duration-300 ${isDarkMode ? 'text-zinc-400' : 'text-zinc-600'}`}>{children}</em>; },
  blockquote({ children }){ return <blockquote className={`border-l-[3px] pl-4 py-0.5 my-3 italic transition-colors duration-300 ${isDarkMode ? 'border-zinc-700 text-zinc-400' : 'border-zinc-300 text-zinc-500'}`}>{children}</blockquote>; },
  hr()                    { return <hr className={`border-0 border-t my-4 transition-colors duration-300 ${isDarkMode ? 'border-zinc-800' : 'border-zinc-200'}`} />; },
  table({ children })     { return <div className={`overflow-x-auto my-3 rounded-lg border transition-colors duration-300 ${isDarkMode ? 'border-zinc-800' : 'border-zinc-200'}`}><table className={`w-full text-sm transition-colors duration-300 ${isDarkMode ? 'text-zinc-300' : 'text-zinc-700'}`}>{children}</table></div>; },
  th({ children })        { return <th className={`px-4 py-2.5 text-left font-semibold border-b transition-colors duration-300 ${isDarkMode ? 'bg-zinc-900 border-zinc-800 text-zinc-200' : 'bg-zinc-50 border-zinc-200 text-zinc-800'}`}>{children}</th>; },
  td({ children })        { return <td className={`px-4 py-2.5 border-b transition-colors duration-300 ${isDarkMode ? 'border-zinc-800' : 'border-zinc-100'}`}>{children}</td>; },
});

// ─── Main component ───────────────────────────────────────────────────────────
const SvaGeneratorUI = () => {
  const [isDarkMode,   setIsDarkMode]   = useState(false);
  const [inputMode,    setInputMode]    = useState('rtl');
  const [inputValue,   setInputValue]   = useState('');
  const [output,       setOutput]       = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [errorStatus,  setErrorStatus]  = useState('');
  const [activeTab,    setActiveTab]    = useState('assertions');
  
  // History State
  const [history, setHistory] = useState([]);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);

  // Per-agent status: 'idle' | 'running' | 'done' | 'retrying'
  const [agentStates,  setAgentStates]  = useState({});
  const abortRef = useRef(null);

  const fetchHistory = async () => {
    try {
      const response = await fetch('http://localhost:8000/history');
      if (response.ok) {
        setHistory(await response.json());
      }
    } catch (error) {
      console.error("Failed to fetch history", error);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const updateAgent = (agent, status) =>
    setAgentStates(prev => ({ ...prev, [agent]: status }));

  const handleGenerate = async () => {
    if (!inputValue.trim()) return;

    setIsGenerating(true);
    setErrorStatus('');
    setOutput(null);
    setActiveTab('assertions');
    setAgentStates({});

    try {
      const controller = new AbortController();
      abortRef.current = controller.signal;

      const response = await fetch('http://localhost:8000/generate_assertions/stream', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ input_type: inputMode, content: inputValue }),
        signal:  controller.signal,
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

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

          if (event === 'agent_event') {
            // The 'critic' agent is filtered out — never shown in the UI
            if (payload.agent !== 'critic') {
              updateAgent(payload.agent, payload.status);
            }
          } else if (event === 'result') {
            // Mark all visible agents done
            setAgentStates({ rag: 'done', generator: 'done', summarizer: 'done' });
            setOutput({
              assertions:  cleanLLMOutput(payload.assertions),
              explanation: cleanLLMOutput(payload.explanation),
              summary:     cleanLLMOutput(payload.summary),
            });
            fetchHistory(); // Refresh history with new entry
          } else if (event === 'error') {
            setErrorStatus(`Error: ${payload.message}`);
          }
        }
      }
    } catch (error) {
      if (error.name !== 'AbortError') {
        setErrorStatus(
          `Backend connection failed. Make sure the Python server is running on port 8000.\n\nDetails: ${error.message}`
        );
      }
    } finally {
      setIsGenerating(false);
    }
  };

  const loadHistoryItem = (item) => {
    setInputMode(item.input_type);
    setInputValue(item.content);
    setOutput({
      assertions: item.assertions,
      explanation: item.explanation,
      summary: item.summary,
    });
    setAgentStates({});
    setErrorStatus('');
    setActiveTab('assertions');
    setIsHistoryOpen(false); // Close sidebar after selecting
  };

  const getPlaceholder = () =>
    inputMode === 'rtl'
      ? 'Paste your SystemVerilog RTL code here...'
      : 'Describe the hardware behaviour in plain English...';

  const isDone = !isGenerating && output !== null;

  // Build tabs — only show non-empty sections
  const tabs = [
    { key: 'assertions',  label: 'Assertions',  content: output?.assertions  },
    { key: 'explanation', label: 'Explanation', content: output?.explanation },
    { key: 'summary',     label: 'Summary',     content: output?.summary     },
  ].filter(t => t.content?.trim());

  const hasAgentActivity = Object.keys(agentStates).length > 0;
  const mdRenderers = getMdComponents(isDarkMode);

  return (
    <div
      className={`min-h-screen w-full flex flex-col items-center py-16 px-4 relative transition-colors duration-500 ${isDarkMode ? 'bg-[#0f1115]' : ''}`}
      style={!isDarkMode ? {
        fontFamily: 'Inter, sans-serif',
        backgroundColor: '#ffffff',
        backgroundImage: 'radial-gradient(circle, rgb(255, 255, 255) 0%, rgb(228 241 255) 100%)'
      } : {
        fontFamily: 'Inter, sans-serif'
      }}
    >
      {/* ── Theme Toggle Button ── */}
      <button
        onClick={() => setIsDarkMode(!isDarkMode)}
        className={`absolute top-6 right-6 flex items-center justify-center w-10 h-10 rounded-lg shadow-sm transition-colors z-10 border ${
          isDarkMode 
            ? 'bg-zinc-800 border-zinc-700 text-zinc-300 hover:bg-zinc-700 hover:text-white' 
            : 'bg-white border-zinc-200 text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900'
        }`}
        title={isDarkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
      >
        {isDarkMode ? (
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="4" />
            <path d="M12 2v2" />
            <path d="M12 20v2" />
            <path d="M4.93 4.93l1.41 1.41" />
            <path d="M17.66 17.66l1.41 1.41" />
            <path d="M2 12h2" />
            <path d="M20 12h2" />
            <path d="M4.93 19.07l1.41-1.41" />
            <path d="M17.66 6.34l1.41-1.41" />
          </svg>
        ) : (
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
          </svg>
        )}
      </button>

      {/* ── History Toggle Button ── */}
      <button
        onClick={() => setIsHistoryOpen(true)}
        className={`absolute top-6 left-6 flex items-center gap-2 px-4 py-2 rounded-lg shadow-sm text-sm font-semibold transition-colors z-10 border ${
          isDarkMode 
            ? 'bg-zinc-800 border-zinc-700 text-zinc-300 hover:bg-zinc-700' 
            : 'bg-white border-zinc-200 text-zinc-700 hover:bg-zinc-50'
        }`}
      >
        <span className="text-lg">History</span> 
      </button>

      {/* ── History Sidebar ── */}
      <AnimatePresence>
        {isHistoryOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsHistoryOpen(false)}
              className="fixed inset-0 bg-black/20 z-40 backdrop-blur-sm"
            />
            <motion.div
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className={`fixed top-0 left-0 bottom-0 w-80 shadow-2xl z-50 flex flex-col transition-colors duration-300 ${
                isDarkMode ? 'bg-[#141414] border-r-[3px] border-[oklch(0.34_0.05_73.64)] shadow-[0_0_10px_rgba(255,255,255,0.05)]' : 'bg-white border-r border-zinc-200'
              }`}
            >
              <div className={`flex items-center justify-between p-5 border-b transition-colors duration-300 ${
                isDarkMode ? 'bg-[#1c1c1c] border-zinc-800' : 'bg-zinc-50 border-zinc-100'
              }`}>
                <h2 className={`text-lg font-bold flex items-center gap-2 ${isDarkMode ? 'text-white' : 'text-zinc-900'}`} style={{ fontFamily: 'Funnel Display, sans-serif' }}>
                  Request History
                </h2>
                <button onClick={() => setIsHistoryOpen(false)} className={`p-1 font-bold ${isDarkMode ? 'text-zinc-500 hover:text-zinc-300' : 'text-zinc-400 hover:text-zinc-700'}`}>
                  ✕
                </button>
              </div>
              <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
                {history.length === 0 ? (
                  <p className={`text-sm text-center mt-10 ${isDarkMode ? 'text-zinc-600' : 'text-zinc-400'}`}>No history found.</p>
                ) : (
                  history.map((item) => (
                    <button
                      key={item.id}
                      onClick={() => loadHistoryItem(item)}
                      className={`text-left p-3 rounded-xl border transition-all flex flex-col gap-2 ${
                        isDarkMode 
                          ? 'bg-zinc-900 border-zinc-800 hover:border-zinc-600' 
                          : 'bg-white border-zinc-200 hover:border-zinc-400 hover:shadow-sm'
                      }`}
                    >
                      <div className="flex justify-between items-center w-full">
                        <span className="text-xs font-semibold uppercase text-zinc-500 tracking-wider">
                          {item.input_type === 'rtl' ? 'RTL' : 'NL'}
                        </span>
                        <span className={`text-[10px] ${isDarkMode ? 'text-zinc-600' : 'text-zinc-400'}`}>
                          {new Date(item.timestamp).toLocaleString()}
                        </span>
                      </div>
                      <p className={`text-sm line-clamp-2 leading-relaxed ${isDarkMode ? 'text-zinc-400' : 'text-zinc-700'}`} style={{ fontFamily: item.input_type === 'rtl' ? "'Intel One Mono', monospace" : 'Inter, sans-serif' }}>
                        {item.content.length > 100 ? item.content.slice(0, 100) + '...' : item.content}
                      </p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                          item.lint_clean 
                            ? (isDarkMode ? 'bg-emerald-900/30 border-emerald-800/50 text-emerald-400' : 'bg-emerald-100 border-emerald-200 text-emerald-700')
                            : (isDarkMode ? 'bg-amber-900/30 border-amber-800/50 text-amber-400' : 'bg-amber-100 border-amber-200 text-amber-700')
                        }`}>
                          {item.lint_clean ? 'Lint Passed' : 'Lint Failed'}
                        </span>
                        <span className={`text-[10px] font-medium ${isDarkMode ? 'text-zinc-600' : 'text-zinc-500'}`}>
                          {item.attempts} attempt{item.attempts !== 1 && 's'}
                        </span>
                      </div>
                    </button>
                  ))
                )}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* ── Header ── */}
      <motion.div
        initial={{ opacity: 0, y: -16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.55, ease: 'easeOut' }}
        className="text-center mb-12 w-full max-w-3xl mt-4"
      >
        <h1
          className={`text-5xl md:text-6xl font-bold tracking-tight mb-3 transition-colors duration-300 ${isDarkMode ? 'text-white' : 'text-zinc-950'}`}
          style={{ fontFamily: 'Funnel Display, sans-serif' }}
        >
          VERIGEN
        </h1>
        <p className={`text-base font-normal tracking-wide transition-colors duration-300 ${isDarkMode ? 'text-zinc-400' : 'text-zinc-500'}`}>
          Multi-agent SystemVerilog Assertion generation
        </p>
        <p className={`text-base font-normal tracking-wide transition-colors duration-300 mt-1 ${isDarkMode ? 'text-zinc-500' : 'text-zinc-400'}`}>
          RAG · Generate · Summarize
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
        <div className={`flex gap-1 p-1 rounded-xl border w-fit self-center transition-colors duration-300 ${
          isDarkMode ? 'bg-[#1a1a1a] border-zinc-800' : 'bg-zinc-100 border-zinc-200'
        }`}>
          {['rtl', 'natural_language'].map(mode => (
            <button
              key={mode}
              onClick={() => setInputMode(mode)}
              className={`px-6 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                inputMode === mode
                  ? (isDarkMode ? 'bg-zinc-800 text-white shadow-sm border border-zinc-700' : 'bg-white text-zinc-900 shadow-sm border border-zinc-200')
                  : (isDarkMode ? 'text-zinc-500 hover:text-zinc-300' : 'text-zinc-500 hover:text-zinc-800')
              }`}
            >
              {mode === 'rtl' ? 'RTL Mode' : 'Natural Language'}
            </button>
          ))}
        </div>

        {/* Input Area */}
        <div className={`rounded-2xl overflow-hidden transition-all duration-300 ${isDarkMode ? 'bg-[#0a0a0a] border-[3px] border-[oklch(0.34_0.05_73.64)] shadow-[0_0_10px_rgba(255,255,255,0.05)]' : 'bg-white border border-zinc-200 shadow-lg'}`}>
          <div className={`flex items-center gap-3 px-5 py-3.5 border-b transition-colors duration-300 ${isDarkMode ? 'border-zinc-800/80 bg-[#141414]' : 'border-zinc-100 bg-zinc-50'}`}>
            <span className={`font-mono text-sm font-bold opacity-90 ${isDarkMode ? 'text-emerald-400' : 'text-emerald-600'}`}>
              {inputMode === 'rtl' ? '>_' : '~$'}
            </span>
            <span className={`text-[11px] font-semibold uppercase tracking-widest font-mono ${isDarkMode ? 'text-zinc-400' : 'text-zinc-500'}`}>
              {inputMode === 'rtl' ? 'SystemVerilog' : 'Natural Language'}
            </span>
          </div>
          <textarea
            id="sva-input"
            value={inputValue}
            onChange={e => setInputValue(e.target.value)}
            placeholder={getPlaceholder()}
            className={`w-full px-5 py-5 bg-transparent text-[14px] outline-none resize-none min-h-[220px] leading-relaxed transition-colors duration-300 ${
              isDarkMode 
                ? 'text-zinc-300 placeholder-zinc-600 selection:bg-emerald-500/30' 
                : 'text-zinc-800 placeholder-zinc-400 selection:bg-emerald-500/20'
            }`}
            style={{ fontFamily: "'Intel One Mono', monospace" }}
            spellCheck="false"
          />
        </div>

        {/* Generate / Regenerate Buttons */}
        <div className="flex justify-center gap-3">
          <motion.button
            id="generate-btn"
            whileHover={{ scale: 1.015 }}
            whileTap={{ scale: 0.985 }}
            onClick={handleGenerate}
            disabled={!inputValue.trim() || isGenerating}
            className={`px-10 py-3.5 rounded-xl text-sm font-semibold tracking-wide
              transition-all duration-200 flex items-center gap-3 ${
              !inputValue.trim() || isGenerating
                ? (isDarkMode ? 'bg-zinc-800 text-zinc-500 cursor-not-allowed border border-zinc-700' : 'bg-zinc-100 text-zinc-400 cursor-not-allowed border border-zinc-200')
                : (isDarkMode ? 'bg-white text-zinc-950 shadow-md hover:bg-zinc-100 active:scale-[0.99]' : 'bg-zinc-950 text-white shadow-md hover:shadow-lg hover:bg-zinc-800 active:scale-[0.99]')
            }`}
          >
            {isGenerating ? (
              <>
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ repeat: Infinity, duration: 0.9, ease: 'linear' }}
                  className={`w-4 h-4 border-2 rounded-full ${isDarkMode ? 'border-zinc-300/30 border-t-zinc-950' : 'border-white/25 border-t-white'}`}
                />
                Generating…
              </>
            ) : (
              'Generate Assertions'
            )}
          </motion.button>

          {/* Show Regenerate button if we are looking at an already-generated output */}
          {isDone && (
            <motion.button
              whileHover={{ scale: 1.015 }}
              whileTap={{ scale: 0.985 }}
              onClick={handleGenerate}
              className={`px-6 py-3.5 rounded-xl text-sm font-semibold tracking-wide border transition-all shadow-sm flex items-center gap-2 ${
                isDarkMode
                  ? 'bg-zinc-900 border-zinc-700 text-zinc-300 hover:bg-zinc-800 hover:border-zinc-600'
                  : 'bg-white border-zinc-200 text-zinc-700 hover:bg-zinc-50 hover:border-zinc-400'
              }`}
            >
              Regenerate
            </motion.button>
          )}
        </div>

        {/* Agent Timeline */}
        <AnimatePresence>
          {(isGenerating || (isDone && hasAgentActivity)) && (
            <motion.div
              key="timeline"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.3 }}
              className={`rounded-2xl p-6 overflow-hidden transition-all duration-300 ${
                isDarkMode ? 'bg-[#141414] border-[3px] border-[oklch(0.34_0.05_73.64)] shadow-[0_0_10px_rgba(255,255,255,0.05)]' : 'bg-white border border-zinc-200 shadow-sm'
              }`}
            >
              <div className="flex items-center gap-2 mb-5">
                <div className={`w-2 h-2 rounded-full ${isGenerating ? (isDarkMode ? 'bg-white animate-pulse' : 'bg-zinc-950 animate-pulse') : 'bg-emerald-500'}`} />
                <span className={`text-xs font-semibold uppercase tracking-widest ${isDarkMode ? 'text-zinc-500' : 'text-zinc-500'}`}>
                  {isGenerating ? 'Pipeline Running' : 'Pipeline Complete'}
                </span>
              </div>
              <AgentTimeline agentStates={agentStates} done={isDone} isDarkMode={isDarkMode} />
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
              className={`rounded-xl border p-4 text-sm font-medium whitespace-pre-wrap leading-relaxed ${
                isDarkMode ? 'bg-red-950/40 border-red-900/50 text-red-400' : 'bg-red-50 border-red-200 text-red-700'
              }`}
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
            <div className={`rounded-2xl overflow-hidden transition-all duration-300 ${
              isDarkMode ? 'bg-[#141414] border-[3px] border-[oklch(0.34_0.05_73.64)] shadow-[0_0_10px_rgba(255,255,255,0.05)]' : 'bg-white border border-zinc-200 shadow-sm'
            }`}>

              {/* Panel Header */}
              <div className={`flex items-center justify-between px-6 py-4 border-b transition-colors duration-300 ${
                isDarkMode ? 'bg-[#1c1c1c] border-zinc-800' : 'bg-zinc-50 border-zinc-100'
              }`}>
                <div className="flex items-center gap-2.5">
                  <div className={`w-2 h-2 rounded-full ${isDarkMode ? 'bg-white' : 'bg-zinc-950'}`} />
                  <h2
                    className={`text-base font-semibold ${isDarkMode ? 'text-white' : 'text-zinc-900'}`}
                    style={{ fontFamily: 'Funnel Display, sans-serif' }}
                  >
                    Generated Result
                  </h2>
                </div>
                <button
                  id="copy-result-btn"
                  onClick={() =>
                    navigator.clipboard.writeText(
                      tabs.find(t => t.key === activeTab)?.content || ''
                    )
                  }
                  className={`text-xs font-semibold px-3.5 py-1.5 rounded-lg transition-all shadow-sm active:scale-95 border ${
                    isDarkMode 
                      ? 'bg-zinc-800 border-zinc-700 text-zinc-300 hover:text-white hover:border-zinc-500' 
                      : 'bg-white border-zinc-200 text-zinc-500 hover:text-zinc-900 hover:border-zinc-400'
                  }`}
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
                      id={`tab-${tab.key}`}
                      onClick={() => setActiveTab(tab.key)}
                      className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                        activeTab === tab.key
                          ? (isDarkMode ? 'bg-white text-zinc-950' : 'bg-zinc-950 text-white')
                          : (isDarkMode ? 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50' : 'text-zinc-500 hover:text-zinc-800 hover:bg-zinc-100')
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
                        components={mdRenderers}
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
