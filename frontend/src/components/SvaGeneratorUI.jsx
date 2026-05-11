import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus, vs } from 'react-syntax-highlighter/dist/esm/styles/prism';

// ─── Utility: strip LLM internal XML tags ────────────────────────────────────
function cleanLLMOutput(raw) {
  if (!raw) return '';
  let cleaned = raw.replace(/<(think|analysis|reasoning|thinking|chain_of_thought|internal)[^>]*>[\s\S]*?<\/\1>/gi, '');
  cleaned = cleaned.replace(/<\/?[a-zA-Z][a-zA-Z0-9_-]*(\s[^>]*)?\/?\>/g, '');
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n');
  return cleaned.trim();
}

// ─── Agent pipeline steps ─────────────────────────────────────────────────────
const AGENTS = [
  { key: 'rag',        label: 'RAG',      icon: '1', desc: 'Retrieving context'    },
  { key: 'generator',  label: 'Generate', icon: '2', desc: 'Generating assertions' },
  { key: 'summarizer', label: 'Summarize',icon: '3', desc: 'Summarizing results'   },
];

// ─── Horizontal Agent Timeline ────────────────────────────────────────────────
function AgentTimeline({ agentStates, isDarkMode }) {
  return (
    <div className="w-full flex flex-col gap-3">
      {/* Node row with connectors */}
      <div className="flex flex-row items-center">
        {AGENTS.map((agent, i) => {
          const s         = agentStates[agent.key] || 'idle';
          const isRunning  = s === 'running';
          const isDone     = s === 'done';
          const isRetrying = s === 'retrying';

          return (
            <React.Fragment key={agent.key}>
              <motion.div
                animate={isRunning ? { scale: [1, 1.1, 1] } : {}}
                transition={{ repeat: Infinity, duration: 1.3, ease: 'easeInOut' }}
                className={`w-9 h-9 rounded-full flex-shrink-0 flex items-center justify-center text-sm font-semibold
                  border-2 transition-all duration-300
                  ${isDone     ? (isDarkMode ? 'bg-white border-white text-zinc-950'           : 'bg-zinc-950 border-zinc-950 text-white') : ''}
                  ${isRunning  ? (isDarkMode ? 'bg-zinc-800 border-white text-white shadow-md' : 'bg-white border-zinc-950 text-zinc-950 shadow-md') : ''}
                  ${isRetrying ? (isDarkMode ? 'bg-amber-900/30 border-amber-500 text-amber-400' : 'bg-amber-50 border-amber-400 text-amber-700') : ''}
                  ${s === 'idle' ? (isDarkMode ? 'bg-zinc-900 border-zinc-800 text-zinc-600'  : 'bg-white border-zinc-200 text-zinc-300') : ''}
                `}
              >
                {isDone ? '✓' : agent.icon}
              </motion.div>

              {i < AGENTS.length - 1 && (
                <div className={`flex-1 h-0.5 mx-3 rounded-full overflow-hidden ${isDarkMode ? 'bg-zinc-800' : 'bg-zinc-200'}`}>
                  <motion.div
                    className={`h-full rounded-full ${isDarkMode ? 'bg-white' : 'bg-zinc-950'}`}
                    initial={{ width: '0%' }}
                    animate={{ width: isDone ? '100%' : '0%' }}
                    transition={{ duration: 0.4, ease: 'easeInOut' }}
                  />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* Label + badge row */}
      <div className="flex flex-row">
        {AGENTS.map((agent) => {
          const s          = agentStates[agent.key] || 'idle';
          const isRunning  = s === 'running';
          const isDone     = s === 'done';
          const isRetrying = s === 'retrying';
          const isActive   = isDone || isRunning || isRetrying;

          return (
            <div key={agent.key} className="flex-1 flex flex-col items-center gap-1">
              <span className={`text-xs font-semibold text-center transition-colors duration-200
                ${isActive ? (isDarkMode ? 'text-white' : 'text-zinc-900') : (isDarkMode ? 'text-zinc-600' : 'text-zinc-400')}`}>
                {agent.label}
              </span>
              {isRunning && (
                <span className={`text-[9px] font-bold uppercase tracking-widest px-1.5 py-0.5 rounded-full animate-pulse border
                  ${isDarkMode ? 'bg-zinc-800 border-zinc-700 text-zinc-300' : 'bg-zinc-100 border-zinc-200 text-zinc-500'}`}>
                  Running
                </span>
              )}
              {isRetrying && (
                <span className={`text-[9px] font-bold uppercase tracking-widest px-1.5 py-0.5 rounded-full border
                  ${isDarkMode ? 'bg-amber-900/30 border-amber-800/50 text-amber-400' : 'bg-amber-50 border-amber-200 text-amber-600'}`}>
                  Refining
                </span>
              )}
              {isDone && (
                <span className={`text-[9px] font-bold uppercase tracking-widest px-1.5 py-0.5 rounded-full border
                  ${isDarkMode ? 'bg-emerald-900/30 border-emerald-800/50 text-emerald-400' : 'bg-emerald-50 border-emerald-200 text-emerald-600'}`}>
                  Done
                </span>
              )}
            </div>
          );
        })}
      </div>
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

  const syntaxTheme = isDarkMode ? vscDarkPlus : vs;
  const mapLanguage = (lang) => {
    if (!lang) return 'text';
    if (lang.toLowerCase() === 'systemverilog') return 'verilog';
    return lang;
  };

  return (
    <div className={`rounded-xl overflow-hidden border my-3 transition-colors duration-300 shadow-sm
      ${isDarkMode ? 'border-zinc-800 bg-[#1e1e1e]' : 'border-zinc-200 bg-[#ffffff]'}`}>
      {language && (
        <div className={`flex items-center justify-between px-4 py-2.5 border-b transition-colors duration-300
          ${isDarkMode ? 'bg-[#181818] border-zinc-800' : 'bg-zinc-50 border-zinc-200'}`}>
          <span className={`text-[11px] font-bold uppercase tracking-widest
            ${isDarkMode ? 'text-zinc-400' : 'text-zinc-500'}`}
            style={{ fontFamily: "Consolas, Monaco, 'Andale Mono', 'Ubuntu Mono', monospace" }}>
            {language}
          </span>
          <button
            onClick={handleCopy}
            className={`text-[11px] font-medium px-2.5 py-1 rounded-md transition-colors
              ${isDarkMode ? 'text-zinc-400 hover:text-zinc-200 hover:bg-white/10' : 'text-zinc-500 hover:text-zinc-800 hover:bg-zinc-950/5'}`}
          >
            {copied ? 'Copied' : 'Copy'}
          </button>
        </div>
      )}
      <SyntaxHighlighter
        language={mapLanguage(language)}
        style={syntaxTheme}
        customStyle={{
          margin: 0,
          padding: '1.25rem',
          fontSize: '13px',
          backgroundColor: 'transparent',
          fontVariantLigatures: 'none'
        }}
        codeTagProps={{
          style: { 
            fontFamily: "Consolas, Monaco, 'Andale Mono', 'Ubuntu Mono', monospace",
            fontVariantLigatures: 'none'
          }
        }}
      >
        {children}
      </SyntaxHighlighter>
    </div>
  );
}

// ─── Markdown renderer components ────────────────────────────────────────────
const getMdComponents = (isDarkMode) => ({
  code({ className, children, node, ...props }) {
    const match = /language-(\w+)/.exec(className || '');
    const isInline = !match && !String(children).includes('\n');

    if (isInline) {
      return (
        <code className={`text-[13px] px-1.5 py-0.5 rounded-md border transition-colors duration-300
          ${isDarkMode ? 'bg-zinc-800 border-zinc-700 text-zinc-300' : 'bg-zinc-100 border-zinc-200 text-zinc-800'}`}
          style={{ fontFamily: "Consolas, Monaco, 'Andale Mono', 'Ubuntu Mono', monospace", fontVariantLigatures: 'none' }}
          {...props}>
          {children}
        </code>
      );
    }
    const lang = match ? match[1] : '';
    return <CodeBlock language={lang} isDarkMode={isDarkMode}>{String(children).trimEnd()}</CodeBlock>;
  },
  p({ children })          { return <p className={`text-[14px] leading-relaxed mb-3 last:mb-0 ${isDarkMode ? 'text-zinc-300' : 'text-zinc-700'}`}>{children}</p>; },
  h1({ children })         { return <h1 className={`text-lg font-bold mt-5 mb-2 tracking-tight ${isDarkMode ? 'text-white' : 'text-zinc-900'}`} style={{ fontFamily: 'Funnel Display, sans-serif' }}>{children}</h1>; },
  h2({ children })         { return <h2 className={`text-base font-semibold mt-4 mb-2 tracking-tight ${isDarkMode ? 'text-zinc-100' : 'text-zinc-800'}`} style={{ fontFamily: 'Funnel Display, sans-serif' }}>{children}</h2>; },
  h3({ children })         { return <h3 className={`text-sm font-semibold mt-3 mb-1.5 ${isDarkMode ? 'text-zinc-200' : 'text-zinc-800'}`}>{children}</h3>; },
  ul({ children })         { return <ul className={`list-disc list-outside pl-5 space-y-1.5 text-[14px] mb-3 ${isDarkMode ? 'text-zinc-300' : 'text-zinc-700'}`}>{children}</ul>; },
  ol({ children })         { return <ol className={`list-decimal list-outside pl-5 space-y-1.5 text-[14px] mb-3 ${isDarkMode ? 'text-zinc-300' : 'text-zinc-700'}`}>{children}</ol>; },
  li({ children })         { return <li className="leading-relaxed pl-0.5">{children}</li>; },
  strong({ children })     { return <strong className={`font-semibold ${isDarkMode ? 'text-white' : 'text-zinc-900'}`}>{children}</strong>; },
  em({ children })         { return <em className={`italic ${isDarkMode ? 'text-zinc-400' : 'text-zinc-600'}`}>{children}</em>; },
  blockquote({ children }) { return <blockquote className={`border-l-[3px] pl-4 py-0.5 my-3 italic ${isDarkMode ? 'border-zinc-700 text-zinc-400' : 'border-zinc-300 text-zinc-500'}`}>{children}</blockquote>; },
  hr()                     { return <hr className={`border-0 border-t my-4 ${isDarkMode ? 'border-zinc-800' : 'border-zinc-200'}`} />; },
  table({ children })      { return <div className={`overflow-x-auto my-3 rounded-lg border ${isDarkMode ? 'border-zinc-800' : 'border-zinc-200'}`}><table className={`w-full text-sm ${isDarkMode ? 'text-zinc-300' : 'text-zinc-700'}`}>{children}</table></div>; },
  th({ children })         { return <th className={`px-4 py-2.5 text-left font-semibold border-b ${isDarkMode ? 'bg-zinc-900 border-zinc-800 text-zinc-200' : 'bg-zinc-50 border-zinc-200 text-zinc-800'}`}>{children}</th>; },
  td({ children })         { return <td className={`px-4 py-2.5 border-b ${isDarkMode ? 'border-zinc-800' : 'border-zinc-100'}`}>{children}</td>; },
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
  const [history,      setHistory]      = useState([]);
  const [isHistoryOpen,setIsHistoryOpen]= useState(false);
  const [agentStates,  setAgentStates]  = useState({});
  const abortRef = useRef(null);

  const fetchHistory = async () => {
    try {
      const res = await fetch('http://localhost:8000/history');
      if (res.ok) setHistory(await res.json());
    } catch (e) {
      console.error('Failed to fetch history', e);
    }
  };

  useEffect(() => { fetchHistory(); }, []);

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
            if (payload.agent !== 'critic') updateAgent(payload.agent, payload.status);
          } else if (event === 'result') {
            setAgentStates({ rag: 'done', generator: 'done', summarizer: 'done' });
            setOutput({
              assertions:  cleanLLMOutput(payload.assertions),
              explanation: cleanLLMOutput(payload.explanation),
              summary:     cleanLLMOutput(payload.summary),
            });
            fetchHistory();
          } else if (event === 'error') {
            setErrorStatus(payload.message);
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
      assertions:  item.assertions,
      explanation: item.explanation,
      summary:     item.summary,
    });
    setAgentStates({});
    setErrorStatus('');
    setActiveTab('assertions');
    setIsHistoryOpen(false);
  };

  const isDone = !isGenerating && output !== null;
  const hasAgentActivity = Object.keys(agentStates).length > 0;
  const mdRenderers = getMdComponents(isDarkMode);

  const tabs = [
    { key: 'assertions',  label: 'Assertions',  content: output?.assertions  },
    { key: 'explanation', label: 'Explanation', content: output?.explanation },
    { key: 'summary',     label: 'Summary',     content: output?.summary     },
  ].filter(t => t.content?.trim());

  const bgStyle = !isDarkMode
    ? { fontFamily: 'Funnel Display, sans-serif', backgroundColor: '#ffffff', backgroundImage: 'radial-gradient(circle, rgb(255,255,255) 0%, rgb(228,241,255) 100%)' }
    : { fontFamily: 'Funnel Display, sans-serif' };

  return (
    <div
      className={`min-h-screen flex flex-col lg:flex-row transition-colors duration-500 ${isDarkMode ? 'bg-[#0f1115]' : ''}`}
      style={bgStyle}
    >
      {/* ── History Sidebar ── */}
      <AnimatePresence>
        {isHistoryOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              onClick={() => setIsHistoryOpen(false)}
              className="fixed inset-0 bg-black/20 z-40 backdrop-blur-sm"
            />
            <motion.div
              initial={{ x: '-100%' }} animate={{ x: 0 }} exit={{ x: '-100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className={`fixed top-0 left-0 bottom-0 w-80 shadow-2xl z-50 flex flex-col transition-colors duration-300
                ${isDarkMode ? 'bg-[#141414] border-r-[3px] border-[oklch(0.34_0.05_73.64)]' : 'bg-white border-r border-zinc-200'}`}
            >
              <div className={`flex items-center justify-between p-5 border-b transition-colors duration-300
                ${isDarkMode ? 'bg-[#1c1c1c] border-zinc-800' : 'bg-zinc-50 border-zinc-100'}`}>
                <h2 className={`text-lg font-bold ${isDarkMode ? 'text-white' : 'text-zinc-900'}`}
                  style={{ fontFamily: 'Funnel Display, sans-serif' }}>
                  Request History
                </h2>
                <button onClick={() => setIsHistoryOpen(false)}
                  className={`p-1 font-bold ${isDarkMode ? 'text-zinc-500 hover:text-zinc-300' : 'text-zinc-400 hover:text-zinc-700'}`}>
                  ✕
                </button>
              </div>
              <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
                {history.length === 0 ? (
                  <p className={`text-sm text-center mt-10 ${isDarkMode ? 'text-zinc-600' : 'text-zinc-400'}`}>
                    No history found.
                  </p>
                ) : history.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => loadHistoryItem(item)}
                    className={`text-left p-3 rounded-xl border transition-all flex flex-col gap-2
                      ${isDarkMode ? 'bg-zinc-900 border-zinc-800 hover:border-zinc-600' : 'bg-white border-zinc-200 hover:border-zinc-400 hover:shadow-sm'}`}
                  >
                    <div className="flex justify-between items-center w-full">
                      <span className="text-xs font-semibold uppercase text-zinc-500 tracking-wider">
                        {item.input_type === 'rtl' ? 'RTL' : 'NL'}
                      </span>
                      <span className={`text-[10px] ${isDarkMode ? 'text-zinc-600' : 'text-zinc-400'}`}>
                        {new Date(item.timestamp).toLocaleString()}
                      </span>
                    </div>
                    <p className={`text-sm line-clamp-2 leading-relaxed ${isDarkMode ? 'text-zinc-400' : 'text-zinc-700'}`}
                      style={{ fontFamily: item.input_type === 'rtl' ? "'Intel One Mono', monospace" : "'Funnel Display', sans-serif" }}>
                      {item.content.length > 100 ? item.content.slice(0, 100) + '…' : item.content}
                    </p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border
                        ${item.lint_clean
                          ? (isDarkMode ? 'bg-emerald-900/30 border-emerald-800/50 text-emerald-400' : 'bg-emerald-100 border-emerald-200 text-emerald-700')
                          : (isDarkMode ? 'bg-amber-900/30 border-amber-800/50 text-amber-400'    : 'bg-amber-100 border-amber-200 text-amber-700')}`}>
                        {item.lint_clean ? 'Lint Passed' : 'Lint Failed'}
                      </span>
                      <span className={`text-[10px] font-medium ${isDarkMode ? 'text-zinc-600' : 'text-zinc-500'}`}>
                        {item.attempts} attempt{item.attempts !== 1 && 's'}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* ── LEFT PANEL — input & pipeline ── */}
      <div className={`w-full lg:w-1/2 flex-shrink-0 lg:sticky lg:top-0 lg:h-screen lg:overflow-y-auto
        flex flex-col px-8 py-10 transition-colors duration-300
        ${isDarkMode ? 'border-r border-zinc-800' : 'border-r border-zinc-200'}`}>

        {/* Top bar: history + theme toggle */}
        <div className="flex items-center justify-between mb-10">
          <button
            onClick={() => setIsHistoryOpen(true)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold border transition-colors
              ${isDarkMode ? 'bg-zinc-800 border-zinc-700 text-zinc-300 hover:bg-zinc-700' : 'bg-white border-zinc-200 text-zinc-700 hover:bg-zinc-50'}`}
          >
            History
          </button>
          <button
            onClick={() => setIsDarkMode(!isDarkMode)}
            className={`w-9 h-9 flex items-center justify-center rounded-lg border transition-colors
              ${isDarkMode ? 'bg-zinc-800 border-zinc-700 text-zinc-300 hover:bg-zinc-700' : 'bg-white border-zinc-200 text-zinc-600 hover:bg-zinc-50'}`}
            title={isDarkMode ? 'Light mode' : 'Dark mode'}
          >
            {isDarkMode ? (
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="M4.93 4.93l1.41 1.41"/>
                <path d="M17.66 17.66l1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/>
                <path d="M4.93 19.07l1.41-1.41"/><path d="M17.66 6.34l1.41-1.41"/>
              </svg>
            ) : (
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>
              </svg>
            )}
          </button>
        </div>

        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
          className="mb-8"
        >
          <h1
            className={`text-5xl font-bold tracking-tight mb-2 transition-colors duration-300 ${isDarkMode ? 'text-white' : 'text-zinc-950'}`}
            style={{ fontFamily: 'Funnel Display, sans-serif' }}
          >
            VERIGEN
          </h1>
          <p className={`text-sm font-normal tracking-wide transition-colors duration-300 ${isDarkMode ? 'text-zinc-400' : 'text-zinc-500'}`}>
            Multi-agent SystemVerilog Assertion generation
          </p>
          <p className={`text-xs font-normal tracking-wide mt-0.5 transition-colors duration-300 ${isDarkMode ? 'text-zinc-600' : 'text-zinc-400'}`}>
            RAG · Generate · Summarize
          </p>
        </motion.div>

        {/* Input controls */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.08, ease: 'easeOut' }}
          className="flex flex-col gap-5 flex-1"
        >
          {/* Mode Toggle */}
          <div className={`flex gap-1 p-1 rounded-xl border w-fit transition-colors duration-300
            ${isDarkMode ? 'bg-[#1a1a1a] border-zinc-800' : 'bg-zinc-100 border-zinc-200'}`}>
            {['rtl', 'natural_language'].map(mode => (
              <button
                key={mode}
                onClick={() => setInputMode(mode)}
                className={`px-5 py-2 rounded-lg text-sm font-medium transition-all duration-200
                  ${inputMode === mode
                    ? (isDarkMode ? 'bg-zinc-800 text-white shadow-sm border border-zinc-700' : 'bg-white text-zinc-900 shadow-sm border border-zinc-200')
                    : (isDarkMode ? 'text-zinc-500 hover:text-zinc-300' : 'text-zinc-500 hover:text-zinc-800')}`}
              >
                {mode === 'rtl' ? 'RTL Mode' : 'Natural Language'}
              </button>
            ))}
          </div>

          {/* Input Textarea */}
          <div className={`rounded-2xl overflow-hidden transition-all duration-300
            ${isDarkMode ? 'bg-[#0a0a0a] border-[3px] border-[oklch(0.34_0.05_73.64)] shadow-[0_0_10px_rgba(255,255,255,0.05)]' : 'bg-white border border-zinc-200 shadow-lg'}`}>
            <div className={`flex items-center gap-3 px-4 py-3 border-b transition-colors duration-300
              ${isDarkMode ? 'border-zinc-800/80 bg-[#141414]' : 'border-zinc-100 bg-zinc-50'}`}>
              <span className={`font-mono text-sm font-bold ${isDarkMode ? 'text-emerald-400' : 'text-emerald-600'}`}>
                {inputMode === 'rtl' ? '>_' : '~$'}
              </span>
              <span className={`text-[11px] font-semibold uppercase tracking-widest font-mono
                ${isDarkMode ? 'text-zinc-400' : 'text-zinc-500'}`}>
                {inputMode === 'rtl' ? 'SystemVerilog' : 'Natural Language'}
              </span>
            </div>
            <textarea
              value={inputValue}
              onChange={e => setInputValue(e.target.value)}
              placeholder={inputMode === 'rtl' ? 'Paste your SystemVerilog RTL code here…' : 'Describe the hardware behaviour in plain English…'}
              className={`w-full px-4 py-4 bg-transparent text-[13px] outline-none resize-none min-h-[200px] leading-relaxed transition-colors duration-300
                ${isDarkMode ? 'text-zinc-300 placeholder-zinc-600' : 'text-zinc-800 placeholder-zinc-400'}`}
              style={{ fontFamily: "'Intel One Mono', monospace" }}
              spellCheck="false"
            />
          </div>

          {/* Buttons */}
          <div className="flex gap-3">
            <motion.button
              whileHover={{ scale: 1.015 }} whileTap={{ scale: 0.985 }}
              onClick={handleGenerate}
              disabled={!inputValue.trim() || isGenerating}
              className={`flex-1 py-3 rounded-xl text-sm font-semibold tracking-wide transition-all duration-200 flex items-center justify-center gap-3
                ${!inputValue.trim() || isGenerating
                  ? (isDarkMode ? 'bg-zinc-800 text-zinc-500 cursor-not-allowed border border-zinc-700' : 'bg-zinc-100 text-zinc-400 cursor-not-allowed border border-zinc-200')
                  : (isDarkMode ? 'bg-white text-zinc-950 shadow-md hover:bg-zinc-100' : 'bg-zinc-950 text-white shadow-md hover:bg-zinc-800')}`}
            >
              {isGenerating ? (
                <>
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ repeat: Infinity, duration: 0.9, ease: 'linear' }}
                    className={`w-4 h-4 border-2 rounded-full ${isDarkMode ? 'border-zinc-600 border-t-zinc-950' : 'border-white/30 border-t-white'}`}
                  />
                  Generating…
                </>
              ) : 'Generate Assertions'}
            </motion.button>

            {isDone && (
              <motion.button
                whileHover={{ scale: 1.015 }} whileTap={{ scale: 0.985 }}
                onClick={handleGenerate}
                className={`px-5 py-3 rounded-xl text-sm font-semibold border transition-all shadow-sm
                  ${isDarkMode ? 'bg-zinc-900 border-zinc-700 text-zinc-300 hover:bg-zinc-800' : 'bg-white border-zinc-200 text-zinc-700 hover:bg-zinc-50 hover:border-zinc-400'}`}
              >
                Regenerate
              </motion.button>
            )}
          </div>

          {/* Pipeline timeline */}
          <AnimatePresence>
            {(isGenerating || (isDone && hasAgentActivity)) && (
              <motion.div
                key="timeline"
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.3 }}
                className={`rounded-2xl p-5 overflow-hidden transition-all duration-300
                  ${isDarkMode ? 'bg-[#141414] border-[3px] border-[oklch(0.34_0.05_73.64)]' : 'bg-white border border-zinc-200 shadow-sm'}`}
              >
                <div className="flex items-center gap-2 mb-4">
                  <div className={`w-1.5 h-1.5 rounded-full ${isGenerating ? (isDarkMode ? 'bg-white animate-pulse' : 'bg-zinc-950 animate-pulse') : 'bg-emerald-500'}`} />
                  <span className={`text-[10px] font-semibold uppercase tracking-widest ${isDarkMode ? 'text-zinc-500' : 'text-zinc-500'}`}>
                    {isGenerating ? 'Pipeline Running' : 'Pipeline Complete'}
                  </span>
                </div>
                <AgentTimeline agentStates={agentStates} isDarkMode={isDarkMode} />
              </motion.div>
            )}
          </AnimatePresence>

          {/* Error */}
          <AnimatePresence>
            {errorStatus && (
              <motion.div
                initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
                className={`rounded-xl border p-4 text-sm font-medium whitespace-pre-wrap leading-relaxed
                  ${isDarkMode ? 'bg-red-950/40 border-red-900/50 text-red-400' : 'bg-red-50 border-red-200 text-red-700'}`}
              >
                {errorStatus}
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      </div>

      {/* ── RIGHT PANEL — results ── */}
      <div className="flex-1 flex flex-col px-8 py-10 min-h-screen overflow-y-auto">
        <AnimatePresence mode="wait">
          {!output ? (
            /* Empty state */
            <motion.div
              key="empty"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="flex-1 flex flex-col items-center justify-center gap-2 text-center py-20"
            >
              <p className={`text-sm font-semibold ${isDarkMode ? 'text-zinc-500' : 'text-zinc-400'}`}>
                Results will appear here
              </p>
              <p className={`text-xs ${isDarkMode ? 'text-zinc-700' : 'text-zinc-300'}`}>
                Enter RTL code or a hardware description and generate
              </p>
            </motion.div>
          ) : (
            /* Results panel */
            <motion.div
              key="results"
              initial={{ opacity: 0, x: 16 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 16 }}
              transition={{ duration: 0.4, ease: 'easeOut' }}
              className="flex flex-col gap-0"
            >
              {/* Panel header */}
              <div className={`flex items-center justify-between px-6 py-4 rounded-t-2xl border-b transition-colors duration-300
                ${isDarkMode ? 'bg-[#1c1c1c] border-zinc-800' : 'bg-zinc-50 border-zinc-100'}`}>
                <div className="flex items-center gap-2.5">
                  <div className={`w-2 h-2 rounded-full ${isDarkMode ? 'bg-white' : 'bg-zinc-950'}`} />
                  <h2 className={`text-sm font-semibold ${isDarkMode ? 'text-white' : 'text-zinc-900'}`}
                    style={{ fontFamily: 'Funnel Display, sans-serif' }}>
                    Generated Assertions
                  </h2>
                </div>
                <button
                  onClick={() => navigator.clipboard.writeText(tabs.find(t => t.key === activeTab)?.content || '')}
                  className={`text-xs font-semibold px-3 py-1.5 rounded-lg border transition-all active:scale-95
                    ${isDarkMode ? 'bg-zinc-800 border-zinc-700 text-zinc-300 hover:text-white hover:border-zinc-500' : 'bg-white border-zinc-200 text-zinc-500 hover:text-zinc-900 hover:border-zinc-400'}`}
                >
                  Copy
                </button>
              </div>

              {/* Tabs */}
              <div className={`flex gap-1 px-5 pt-4 pb-0 border-x transition-colors duration-300
                ${isDarkMode ? 'border-zinc-800 bg-[#141414]' : 'border-zinc-200 bg-white'}`}>
                {tabs.map(tab => (
                  <button
                    key={tab.key}
                    onClick={() => setActiveTab(tab.key)}
                    className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all duration-150
                      ${activeTab === tab.key
                        ? (isDarkMode ? 'bg-white text-zinc-950' : 'bg-zinc-950 text-white')
                        : (isDarkMode ? 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50' : 'text-zinc-500 hover:text-zinc-800 hover:bg-zinc-100')}`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              {/* Tab content */}
              <div className={`rounded-b-2xl border transition-colors duration-300
                ${isDarkMode ? 'border-zinc-800 bg-[#141414]' : 'border-zinc-200 bg-white'}`}>
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
                        <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdRenderers}>
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
    </div>
  );
};

export default SvaGeneratorUI;
