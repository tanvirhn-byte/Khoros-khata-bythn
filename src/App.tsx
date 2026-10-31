import React, { useState } from 'react';
import { 
  FileText, Copy, Check, Download, Layers, ShieldCheck, 
  CheckCircle2, Play, Database, KeyRound, Users, Globe, Zap, Wallet, Sparkles, RefreshCw, WifiOff, Smartphone, Lock
} from 'lucide-react';
import phase18ReportText from '../public/phase18-report.txt?raw';
import phase17ReportText from '../public/phase17-report.txt?raw';
import phase14_16ReportText from '../public/phase14-15-16-report.txt?raw';
import phase13ReportText from '../public/phase13-report.txt?raw';
import phase12ReportText from '../public/phase12-report.txt?raw';
import phase11ReportText from '../public/phase11-report.txt?raw';
import phase10ReportText from '../public/phase10-report.txt?raw';
import premiumUiReportText from '../public/premium-ui-report.txt?raw';
import phase9ReportText from '../public/phase9-report.txt?raw';
import phase8ReportText from '../public/phase8-report.txt?raw';
import phase7ReportText from '../public/phase7-report.txt?raw';
import phase6ReportText from '../public/phase6-report.txt?raw';
import phase5ReportText from '../public/phase5-report.txt?raw';
import phase4ReportText from '../public/phase4-report.txt?raw';
import phase3ReportText from '../public/phase3-report.txt?raw';
import phase2ReportText from '../public/phase-report.txt?raw';
import auditText from '../public/AUDIT_REPORT.txt?raw';

export default function App() {
  const [activeTab, setActiveTab] = useState<'app' | 'p18' | 'p17' | 'p14_16' | 'p13' | 'p12' | 'p11' | 'p10' | 'ui' | 'p9' | 'p8' | 'p7' | 'p6' | 'p5' | 'p4' | 'p3' | 'p2' | 'p1'>('p18');
  const [copied, setCopied] = useState(false);

  const getDoc = () => {
    switch (activeTab) {
      case 'p18':
        return {
          title: 'Full Project-Wide GitHub Repository Audit & Improvement Report (Phase 18)',
          file: 'phase18-report.txt',
          text: phase18ReportText
        };
      case 'p17':
        return {
          title: 'Phase 17: Comprehensive Android Application Testing & Verification Report',
          file: 'phase17-report.txt',
          text: phase17ReportText
        };
      case 'p14_16':
        return {
          title: 'Combined Master Report: Phase 14 (Security & Performance) + Phase 15 (Production Hosting) + Phase 16 (Capacitor Android)',
          file: 'phase14-15-16-report.txt',
          text: phase14_16ReportText
        };
      case 'p13':
        return {
          title: 'Phase 13: Existing Admin Panel Audit & Security Hardening Report',
          file: 'phase13-report.txt',
          text: phase13ReportText
        };
      case 'p12':
        return {
          title: 'Phase 12: Progressive Web App (PWA) Completion & Verification Report',
          file: 'phase12-report.txt',
          text: phase12ReportText
        };
      case 'p11':
        return {
          title: 'Phase 11: Offline Functionality, Status Popups & Admin Notices Report',
          file: 'phase11-report.txt',
          text: phase11ReportText
        };
      case 'p10':
        return {
          title: 'Phase 10: Online Synchronization & Multi-Device Consistency Report',
          file: 'phase10-report.txt',
          text: phase10ReportText
        };
      case 'ui':
        return {
          title: 'Premium UI/UX Transformation Report',
          file: 'premium-ui-report.txt',
          text: premiumUiReportText
        };
      case 'p9':
        return {
          title: 'Phase 9: Core Expense Tracker Verification Report',
          file: 'phase9-report.txt',
          text: phase9ReportText
        };
      case 'p8':
        return {
          title: 'Phase 8: Frontend & API Integration Report',
          file: 'phase8-report.txt',
          text: phase8ReportText
        };
      case 'p7':
        return {
          title: 'Phase 7: Backend API & CORS Hardening Report',
          file: 'phase7-report.txt',
          text: phase7ReportText
        };
      case 'p6':
        return {
          title: 'Phase 6: Multi-User Data Isolation Verification Report',
          file: 'phase6-report.txt',
          text: phase6ReportText
        };
      case 'p5':
        return {
          title: 'Phase 5: Authentication & Security Report',
          file: 'phase5-report.txt',
          text: phase5ReportText
        };
      case 'p4':
        return {
          title: 'Phase 4: Database Hardening Report',
          file: 'phase4-report.txt',
          text: phase4ReportText
        };
      case 'p3':
        return {
          title: 'Phase 3: Code Quality & Bug Fixes Report',
          file: 'phase3-report.txt',
          text: phase3ReportText
        };
      case 'p2':
        return {
          title: 'Phase 2: Corrected Architecture Report',
          file: 'phase-report.txt',
          text: phase2ReportText
        };
      case 'p1':
        return {
          title: 'Phase 1: Project Audit Report',
          file: 'AUDIT_REPORT.txt',
          text: auditText
        };
      default:
        return { title: '', file: '', text: '' };
    }
  };

  const { title: currentTitle, file: currentFileName, text: currentText } = getDoc();

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(currentText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      const textArea = document.createElement('textarea');
      textArea.value = currentText;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    }
  };

  const handleDownload = () => {
    const blob = new Blob([currentText], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = currentFileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const [downloadingZip, setDownloadingZip] = useState(false);

  const handleDownloadZip = async (e?: React.MouseEvent) => {
    if (e) e.preventDefault();
    setDownloadingZip(true);
    try {
      const response = await fetch('/khoros-source-by-tanvir.zip');
      const arrayBuffer = await response.arrayBuffer();
      const zipBlob = new Blob([arrayBuffer], { type: 'application/zip' });
      const url = URL.createObjectURL(zipBlob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'khoros source by tanvir.zip');
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      setTimeout(() => URL.revokeObjectURL(url), 3000);
    } catch {
      window.location.href = '/khoros-source-by-tanvir.zip';
    } finally {
      setTimeout(() => setDownloadingZip(false), 1500);
    }
  };

  return (
    <div className="min-h-screen bg-[#0A111D] text-[#E8EEF7] font-sans pb-10">
      {/* Header */}
      <header className="sticky top-0 z-30 bg-[#0F1B2D]/95 backdrop-blur-md border-b border-[#22314A] px-4 py-2.5 shadow-md">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-[#2DD4BF] to-[#14B8A6] text-[#0F1B2D] font-bold text-base flex items-center justify-center shadow-md">
              খ
            </div>
            <div>
              <h1 className="text-sm sm:text-base font-bold text-white leading-tight">খরচের খাতা</h1>
              <p className="text-[11px] text-[#2DD4BF] font-medium">Phase 18 Complete · Cloud APK Workflow Ready</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleDownloadZip}
              disabled={downloadingZip}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all bg-gradient-to-r from-[#2DD4BF] to-[#14B8A6] text-[#0F1B2D] shadow hover:opacity-90 cursor-pointer disabled:opacity-50"
              title="সম্পূর্ণ প্রজেক্ট সোর্স কোড ডাউনলোড করুন (ZIP)"
            >
              <Download className="w-3.5 h-3.5" />
              <span>{downloadingZip ? 'ডাউনলোড হচ্ছে…' : 'Download ZIP'}</span>
            </button>
            <span className="text-[11px] px-2.5 py-1 rounded-full bg-[#16301F] text-[#7BE0A0] border border-[#2D6A41] font-semibold">
              Ready
            </span>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-4xl mx-auto px-3.5 pt-3">
        {/* Navigation Tabs */}
        <div className="grid grid-cols-3 sm:grid-cols-9 gap-1 bg-[#121C2E] p-1.5 rounded-2xl border border-[#22314A] mb-3 text-center">
          <button
            onClick={() => { setActiveTab('p18'); setCopied(false); }}
            className={`flex items-center justify-center gap-1 py-1.5 px-1 rounded-xl text-[10px] sm:text-xs font-semibold transition-all ${
              activeTab === 'p18'
                ? 'bg-gradient-to-r from-[#2DD4BF] to-[#14B8A6] text-[#0F1B2D] shadow-md font-bold'
                : 'text-[#8CA0B8] hover:text-white'
            }`}
          >
            <Smartphone className="w-3.5 h-3.5 shrink-0" />
            <span className="truncate">Phase 18</span>
          </button>

          <button
            onClick={() => { setActiveTab('p17'); setCopied(false); }}
            className={`flex items-center justify-center gap-1 py-1.5 px-1 rounded-xl text-[10px] sm:text-xs font-semibold transition-all ${
              activeTab === 'p17'
                ? 'bg-gradient-to-r from-[#2DD4BF] to-[#14B8A6] text-[#0F1B2D] shadow-md font-bold'
                : 'text-[#8CA0B8] hover:text-white'
            }`}
          >
            <Smartphone className="w-3.5 h-3.5 shrink-0" />
            <span className="truncate">Phase 17</span>
          </button>

          <button
            onClick={() => { setActiveTab('p14_16'); setCopied(false); }}
            className={`flex items-center justify-center gap-1 py-1.5 px-1 rounded-xl text-[10px] sm:text-xs font-semibold transition-all ${
              activeTab === 'p14_16'
                ? 'bg-gradient-to-r from-[#2DD4BF] to-[#14B8A6] text-[#0F1B2D] shadow-md font-bold'
                : 'text-[#8CA0B8] hover:text-white'
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5 shrink-0" />
            <span className="truncate">Phase 14–16</span>
          </button>

          <button
            onClick={() => { setActiveTab('p13'); setCopied(false); }}
            className={`flex items-center justify-center gap-1 py-1.5 px-1 rounded-xl text-[10px] sm:text-xs font-semibold transition-all ${
              activeTab === 'p13'
                ? 'bg-gradient-to-r from-[#2DD4BF] to-[#14B8A6] text-[#0F1B2D] shadow-md font-bold'
                : 'text-[#8CA0B8] hover:text-white'
            }`}
          >
            <Lock className="w-3.5 h-3.5 shrink-0" />
            <span className="truncate">Phase 13</span>
          </button>

          <button
            onClick={() => { setActiveTab('p12'); setCopied(false); }}
            className={`flex items-center justify-center gap-1 py-1.5 px-1 rounded-xl text-[10px] sm:text-xs font-semibold transition-all ${
              activeTab === 'p12'
                ? 'bg-gradient-to-r from-[#2DD4BF] to-[#14B8A6] text-[#0F1B2D] shadow-md font-bold'
                : 'text-[#8CA0B8] hover:text-white'
            }`}
          >
            <Smartphone className="w-3.5 h-3.5 shrink-0" />
            <span className="truncate">Phase 12</span>
          </button>

          <button
            onClick={() => { setActiveTab('p11'); setCopied(false); }}
            className={`flex items-center justify-center gap-1 py-1.5 px-1 rounded-xl text-[10px] sm:text-xs font-semibold transition-all ${
              activeTab === 'p11'
                ? 'bg-gradient-to-r from-[#2DD4BF] to-[#14B8A6] text-[#0F1B2D] shadow-md font-bold'
                : 'text-[#8CA0B8] hover:text-white'
            }`}
          >
            <WifiOff className="w-3.5 h-3.5 shrink-0" />
            <span className="truncate">Phase 11</span>
          </button>

          <button
            onClick={() => { setActiveTab('p10'); setCopied(false); }}
            className={`flex items-center justify-center gap-1 py-1.5 px-1 rounded-xl text-[10px] sm:text-xs font-semibold transition-all ${
              activeTab === 'p10'
                ? 'bg-gradient-to-r from-[#2DD4BF] to-[#14B8A6] text-[#0F1B2D] shadow-md font-bold'
                : 'text-[#8CA0B8] hover:text-white'
            }`}
          >
            <RefreshCw className="w-3.5 h-3.5 shrink-0" />
            <span className="truncate">Phase 10</span>
          </button>

          <button
            onClick={() => { setActiveTab('ui'); setCopied(false); }}
            className={`flex items-center justify-center gap-1 py-1.5 px-1 rounded-xl text-[10px] sm:text-xs font-semibold transition-all ${
              activeTab === 'ui'
                ? 'bg-gradient-to-r from-[#2DD4BF] to-[#14B8A6] text-[#0F1B2D] shadow-md font-bold'
                : 'text-[#8CA0B8] hover:text-white'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5 shrink-0" />
            <span className="truncate">Premium UI</span>
          </button>

          <button
            onClick={() => { setActiveTab('app'); setCopied(false); }}
            className={`flex items-center justify-center gap-1 py-1.5 px-1 rounded-xl text-[10px] sm:text-xs font-semibold transition-all ${
              activeTab === 'app'
                ? 'bg-gradient-to-r from-[#2DD4BF] to-[#14B8A6] text-[#0F1B2D] shadow-md font-bold'
                : 'text-[#8CA0B8] hover:text-white'
            }`}
          >
            <Play className="w-3.5 h-3.5 shrink-0" />
            <span className="truncate">Live App</span>
          </button>

          <button
            onClick={() => { setActiveTab('p9'); setCopied(false); }}
            className={`flex items-center justify-center gap-1 py-1.5 px-1 rounded-xl text-[10px] sm:text-xs font-semibold transition-all ${
              activeTab === 'p9'
                ? 'bg-gradient-to-r from-[#2DD4BF] to-[#14B8A6] text-[#0F1B2D] shadow-md font-bold'
                : 'text-[#8CA0B8] hover:text-white'
            }`}
          >
            <Wallet className="w-3.5 h-3.5 shrink-0" />
            <span className="truncate">Phase 9</span>
          </button>

          <button
            onClick={() => { setActiveTab('p8'); setCopied(false); }}
            className={`flex items-center justify-center gap-1 py-1.5 px-1 rounded-xl text-[10px] sm:text-xs font-semibold transition-all ${
              activeTab === 'p8'
                ? 'bg-gradient-to-r from-[#2DD4BF] to-[#14B8A6] text-[#0F1B2D] shadow-md font-bold'
                : 'text-[#8CA0B8] hover:text-white'
            }`}
          >
            <Zap className="w-3.5 h-3.5 shrink-0" />
            <span className="truncate">Phase 8</span>
          </button>

          <button
            onClick={() => { setActiveTab('p7'); setCopied(false); }}
            className={`flex items-center justify-center gap-1 py-1.5 px-1 rounded-xl text-[10px] sm:text-xs font-semibold transition-all ${
              activeTab === 'p7'
                ? 'bg-gradient-to-r from-[#2DD4BF] to-[#14B8A6] text-[#0F1B2D] shadow-md font-bold'
                : 'text-[#8CA0B8] hover:text-white'
            }`}
          >
            <Globe className="w-3.5 h-3.5 shrink-0" />
            <span className="truncate">Phase 7</span>
          </button>

          <button
            onClick={() => { setActiveTab('p6'); setCopied(false); }}
            className={`flex items-center justify-center gap-1 py-1.5 px-1 rounded-xl text-[10px] sm:text-xs font-semibold transition-all ${
              activeTab === 'p6'
                ? 'bg-gradient-to-r from-[#2DD4BF] to-[#14B8A6] text-[#0F1B2D] shadow-md font-bold'
                : 'text-[#8CA0B8] hover:text-white'
            }`}
          >
            <Users className="w-3.5 h-3.5 shrink-0" />
            <span className="truncate">Phase 6</span>
          </button>

          <button
            onClick={() => { setActiveTab('p5'); setCopied(false); }}
            className={`flex items-center justify-center gap-1 py-1.5 px-1 rounded-xl text-[10px] sm:text-xs font-semibold transition-all ${
              activeTab === 'p5'
                ? 'bg-gradient-to-r from-[#2DD4BF] to-[#14B8A6] text-[#0F1B2D] shadow-md font-bold'
                : 'text-[#8CA0B8] hover:text-white'
            }`}
          >
            <KeyRound className="w-3.5 h-3.5 shrink-0" />
            <span className="truncate">Phase 5</span>
          </button>

          <button
            onClick={() => { setActiveTab('p4'); setCopied(false); }}
            className={`flex items-center justify-center gap-1 py-1.5 px-1 rounded-xl text-[10px] sm:text-xs font-semibold transition-all ${
              activeTab === 'p4'
                ? 'bg-gradient-to-r from-[#2DD4BF] to-[#14B8A6] text-[#0F1B2D] shadow-md font-bold'
                : 'text-[#8CA0B8] hover:text-white'
            }`}
          >
            <Database className="w-3.5 h-3.5 shrink-0" />
            <span className="truncate">Phase 4</span>
          </button>

          <button
            onClick={() => { setActiveTab('p3'); setCopied(false); }}
            className={`flex items-center justify-center gap-1 py-1.5 px-1 rounded-xl text-[10px] sm:text-xs font-semibold transition-all ${
              activeTab === 'p3'
                ? 'bg-gradient-to-r from-[#2DD4BF] to-[#14B8A6] text-[#0F1B2D] shadow-md font-bold'
                : 'text-[#8CA0B8] hover:text-white'
            }`}
          >
            <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
            <span className="truncate">Phase 3</span>
          </button>

          <button
            onClick={() => { setActiveTab('p2'); setCopied(false); }}
            className={`flex items-center justify-center gap-1 py-1.5 px-1 rounded-xl text-[10px] sm:text-xs font-semibold transition-all ${
              activeTab === 'p2'
                ? 'bg-gradient-to-r from-[#2DD4BF] to-[#14B8A6] text-[#0F1B2D] shadow-md font-bold'
                : 'text-[#8CA0B8] hover:text-white'
            }`}
          >
            <Layers className="w-3.5 h-3.5 shrink-0" />
            <span className="truncate">Phase 2</span>
          </button>

          <button
            onClick={() => { setActiveTab('p1'); setCopied(false); }}
            className={`flex items-center justify-center gap-1 py-1.5 px-1 rounded-xl text-[10px] sm:text-xs font-semibold transition-all ${
              activeTab === 'p1'
                ? 'bg-gradient-to-r from-[#2DD4BF] to-[#14B8A6] text-[#0F1B2D] shadow-md font-bold'
                : 'text-[#8CA0B8] hover:text-white'
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5 shrink-0" />
            <span className="truncate">Phase 1</span>
          </button>
        </div>

        {activeTab === 'app' ? (
          /* Live App View */
          <div className="bg-[#121C2E] border border-[#22314A] rounded-2xl overflow-hidden shadow-xl">
            <div className="bg-[#10192A] px-4 py-2 border-b border-[#22314A] flex items-center justify-between text-xs text-[#8CA0B8]">
              <span className="font-semibold text-[#99F6E4]">খরচের খাতা — Interactive Live App</span>
              <a 
                href="/khoroch/index.html" 
                target="_blank" 
                rel="noreferrer"
                className="text-[#2DD4BF] hover:underline"
              >
                Open Fullscreen ↗
              </a>
            </div>
            <iframe
              src="/khoroch/index.html"
              title="Khoroch er Khata Live"
              className="w-full h-[72vh] border-0 bg-[#0A111D]"
            />
          </div>
        ) : (
          /* Document Viewer */
          <>
            <div className="bg-[#121C2E] border border-[#22314A] rounded-2xl p-3.5 mb-3 shadow-lg">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
                <div>
                  <div className="flex items-center gap-1.5">
                    <FileText className="w-4 h-4 text-[#2DD4BF]" />
                    <h2 className="text-xs sm:text-sm font-bold text-white">{currentTitle}</h2>
                  </div>
                  <p className="text-[11px] text-[#8CA0B8] mt-0.5">
                    File: <code className="text-[#99F6E4] font-mono bg-[#0A111D] px-1 py-0.5 rounded">{currentFileName}</code>
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={handleCopy}
                    className="flex-1 sm:flex-none flex items-center justify-center gap-1 px-3 py-1.5 rounded-xl text-xs font-bold transition-all bg-[#1F6F8B] hover:bg-[#2585A6] text-white shadow"
                  >
                    {copied ? (
                      <>
                        <Check className="w-3.5 h-3.5 text-[#2DD4BF]" />
                        <span>কপি হয়েছে ✓</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5" />
                        <span>Copy Full Text</span>
                      </>
                    )}
                  </button>

                  <button
                    onClick={handleDownload}
                    className="flex-1 sm:flex-none flex items-center justify-center gap-1 px-3 py-1.5 rounded-xl text-xs font-bold transition-all bg-[#1b2a42] hover:bg-[#223554] text-[#E8EEF7] border border-[#2c3f5c]"
                  >
                    <Download className="w-3.5 h-3.5 text-[#2DD4BF]" />
                    <span>Download .txt</span>
                  </button>
                </div>
              </div>

              {copied && (
                <div className="mt-2.5 p-2 rounded-xl bg-[#16301F] border border-[#2D6A41] text-[#7BE0A0] text-[11px] flex items-center gap-2">
                  <Check className="w-3.5 h-3.5 shrink-0" />
                  <span>টেক্সটটি কপি হয়েছে! এখন আপনার চ্যাটে বা ডেভেলপারকে পেস্ট (Paste) করে দিন।</span>
                </div>
              )}
            </div>

            <div className="bg-[#0A111D] border border-[#22314A] rounded-2xl overflow-hidden shadow-inner">
              <div className="bg-[#10192A] px-4 py-2 border-b border-[#22314A] flex items-center justify-between text-xs text-[#8CA0B8]">
                <span className="font-mono">{currentFileName}</span>
                <span>UTF-8 Plain Text</span>
              </div>
              <div className="p-3.5 max-h-[62vh] overflow-y-auto">
                <pre className="font-mono text-[11px] sm:text-xs text-[#CBD5E1] whitespace-pre-wrap leading-relaxed select-text">
                  {currentText}
                </pre>
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
