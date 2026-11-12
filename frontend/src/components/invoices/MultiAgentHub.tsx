"use client";

import React, { useState, useEffect } from "react";
import {
  Sparkles,
  Bot,
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  FileSearch,
  Building2,
  GitCompare,
  Clock,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  HelpCircle,
  Check,
  Percent,
  Layers,
  ArrowRight,
  ExternalLink,
  ShieldCheck,
} from "lucide-react";
import { api } from "@/services/api";
import {
  MultiAgentAnalysisReport,
  AgentExecutionLogResponse,
  Invoice,
} from "@/types";
import { formatCurrency, formatDateTime } from "@/lib/utils";

interface MultiAgentHubProps {
  invoice: Invoice;
  onInvoiceUpdated?: () => void;
}

export const MultiAgentHub: React.FC<MultiAgentHubProps> = ({
  invoice,
  onInvoiceUpdated,
}) => {
  const [analysis, setAnalysis] = useState<MultiAgentAnalysisReport | null>(null);
  const [logs, setLogs] = useState<AgentExecutionLogResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [running, setRunning] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [showLogs, setShowLogs] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<"overview" | "lines" | "telemetry">("overview");

  const fetchAnalysisData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [report, execLogs] = await Promise.all([
        api.getInvoiceAnalysis(invoice.id).catch(() => null),
        api.getAgentLogs(invoice.id).catch(() => []),
      ]);
      setAnalysis(report);
      setLogs(execLogs);
    } catch (err: any) {
      console.error("Error fetching agent analysis:", err);
      setError(err.message || "Failed to load agent analysis");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (invoice?.id) {
      fetchAnalysisData();
    }
  }, [invoice?.id]);

  const handleRunAnalysis = async () => {
    try {
      setRunning(true);
      setError(null);
      const report = await api.analyzeInvoice(invoice.id);
      setAnalysis(report);
      const updatedLogs = await api.getAgentLogs(invoice.id).catch(() => []);
      setLogs(updatedLogs);
      if (onInvoiceUpdated) {
        onInvoiceUpdated();
      }
    } catch (err: any) {
      console.error("Agent analysis execution failed:", err);
      setError(err.message || "Agent execution failed");
    } finally {
      setRunning(false);
    }
  };

  const getRecommendationBadge = (rec?: string) => {
    switch (rec?.toUpperCase()) {
      case "APPROVE":
        return {
          bg: "bg-emerald-50 border-emerald-300 text-emerald-800",
          pill: "bg-emerald-500 text-white",
          icon: <CheckCircle2 className="h-5 w-5 text-emerald-600" />,
          title: "Recommended for Human Approval",
        };
      case "REJECT":
        return {
          bg: "bg-rose-50 border-rose-300 text-rose-800",
          pill: "bg-rose-500 text-white",
          icon: <XCircle className="h-5 w-5 text-rose-600" />,
          title: "Recommended for Rejection / Return",
        };
      case "REVIEW":
      default:
        return {
          bg: "bg-amber-50 border-amber-300 text-amber-800",
          pill: "bg-amber-500 text-white",
          icon: <AlertTriangle className="h-5 w-5 text-amber-600" />,
          title: "Manual Officer Review Required",
        };
    }
  };

  const getRiskCategoryBadge = (category?: string, score?: string | number) => {
    const num = Number(score || 0);
    switch (category?.toUpperCase()) {
      case "CRITICAL":
        return {
          bg: "bg-rose-100 text-rose-900 border-rose-300",
          barColor: "bg-rose-600",
          label: "CRITICAL RISK",
        };
      case "HIGH":
        return {
          bg: "bg-rose-50 text-rose-800 border-rose-200",
          barColor: "bg-rose-500",
          label: "HIGH RISK",
        };
      case "MEDIUM":
        return {
          bg: "bg-amber-50 text-amber-800 border-amber-200",
          barColor: "bg-amber-500",
          label: "MEDIUM RISK",
        };
      case "LOW":
      default:
        return {
          bg: "bg-emerald-50 text-emerald-800 border-emerald-200",
          barColor: "bg-emerald-500",
          label: "LOW RISK",
        };
    }
  };

  const badgeInfo = getRecommendationBadge(analysis?.recommendation);
  const riskInfo = getRiskCategoryBadge(analysis?.risk_category, analysis?.risk_score);

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
      {/* Top Header */}
      <div className="p-5 sm:p-6 bg-gradient-to-r from-slate-900 via-slate-800 to-indigo-950 text-white flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="flex items-start space-x-3.5">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-500/20 border border-indigo-400/30 text-indigo-300 shadow-inner flex-shrink-0">
            <Bot className="h-6 w-6" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-base font-bold tracking-tight text-white flex items-center space-x-2">
                <span>Autonomous AP Intelligence Hub</span>
                <span className="text-[10px] uppercase font-mono font-bold px-2 py-0.5 rounded-full bg-indigo-500/30 text-indigo-200 border border-indigo-400/30">
                  Phase 3 Multi-Agent
                </span>
              </h3>
            </div>
            <p className="text-xs text-slate-300 mt-1 max-w-2xl leading-relaxed">
              Five collaborative AI agents sequentially analyze invoice text, verify vendor credentials, execute 3-way PO/GRN matching, detect overbilling and fraud, and provide recommendation for human sign-off.
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2.5 flex-shrink-0">
          <button
            onClick={handleRunAnalysis}
            disabled={running}
            className={`inline-flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-bold shadow-md transition ${
              running
                ? "bg-indigo-400 text-white cursor-wait"
                : analysis
                ? "bg-white/10 hover:bg-white/20 text-white border border-white/20 backdrop-blur"
                : "bg-indigo-500 hover:bg-indigo-600 text-white shadow-indigo-500/30"
            }`}
          >
            <RefreshCw className={`h-3.5 w-3.5 ${running ? "animate-spin" : ""}`} />
            <span>{running ? "Agents Executing..." : analysis ? "Re-Run AI Analysis" : "Run Multi-Agent Analysis"}</span>
          </button>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="m-6 p-4 rounded-xl border border-rose-200 bg-rose-50 text-xs text-rose-800 flex items-center space-x-2.5">
          <AlertTriangle className="h-4 w-4 text-rose-600 flex-shrink-0" />
          <span className="font-medium">{error}</span>
        </div>
      )}

      {/* Running skeleton */}
      {running && (
        <div className="p-8 text-center space-y-4">
          <div className="inline-flex items-center justify-center p-3 rounded-2xl bg-indigo-50 border border-indigo-100 text-indigo-600 animate-pulse">
            <Sparkles className="h-8 w-8 animate-spin" />
          </div>
          <div>
            <h4 className="text-sm font-bold text-slate-900">Agents in Sequential Deliberation...</h4>
            <p className="text-xs text-slate-500 mt-1">
              InvoiceUnderstanding → VendorVerification → ThreeWayMatching → FraudRisk → ApprovalRecommendation
            </p>
          </div>
        </div>
      )}

      {/* Empty State: Analysis not yet performed */}
      {!loading && !running && !analysis && (
        <div className="p-8 sm:p-12 text-center space-y-5">
          <div className="inline-flex items-center justify-center h-14 w-14 rounded-2xl bg-slate-100 text-slate-500 border border-slate-200">
            <Sparkles className="h-7 w-7 text-indigo-500" />
          </div>
          <div className="max-w-md mx-auto space-y-2">
            <h4 className="text-base font-bold text-slate-900">No Multi-Agent Analysis Generated</h4>
            <p className="text-xs text-slate-500 leading-relaxed">
              Trigger the automated pipeline to have specialized agents analyze document validity, cross-examine the vendor master, calculate PO & GRN line variances, and compute the composite fraud score.
            </p>
          </div>
          <div>
            <button
              onClick={handleRunAnalysis}
              className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold shadow-md shadow-indigo-600/20 transition"
            >
              <Bot className="h-4 w-4" />
              <span>Launch 5-Agent Pipeline Now</span>
            </button>
          </div>
        </div>
      )}

      {/* Analyzed Report Content */}
      {!running && analysis && (
        <div className="p-5 sm:p-6 space-y-6">
          {/* Executive Synthesis Banner */}
          <div className={`rounded-2xl border p-5 sm:p-6 ${badgeInfo.bg} shadow-sm space-y-4`}>
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 pb-4 border-b border-black/5">
              <div className="flex items-start space-x-3.5">
                <div className="mt-0.5">{badgeInfo.icon}</div>
                <div>
                  <div className="flex items-center space-x-2">
                    <span className={`px-2.5 py-0.5 rounded-full font-mono text-[11px] font-bold ${badgeInfo.pill}`}>
                      {analysis.recommendation}
                    </span>
                    <h4 className="text-sm font-bold tracking-tight">{badgeInfo.title}</h4>
                    <span className="text-[11px] font-semibold opacity-75">
                      • Confidence: {Number(analysis.approval_recommendation?.confidence || 0)}%
                    </span>
                  </div>
                  <p className="text-xs mt-1 leading-relaxed opacity-90 max-w-3xl">
                    {analysis.approval_recommendation?.executive_summary || "Multi-agent evaluation completed."}
                  </p>
                </div>
              </div>

              {/* Risk Gauge Box */}
              <div className="flex items-center space-x-4 bg-white/70 backdrop-blur p-3.5 rounded-xl border border-black/5 flex-shrink-0">
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-[11px] font-bold text-slate-700">
                    <span>Fraud & Risk Score</span>
                    <span className="font-mono">{Number(analysis.risk_score || 0)}/100</span>
                  </div>
                  <div className="w-32 h-2 rounded-full bg-slate-200 overflow-hidden">
                    <div
                      className={`h-full ${riskInfo.barColor} transition-all duration-500`}
                      style={{ width: `${Math.min(100, Math.max(0, Number(analysis.risk_score || 0)))}%` }}
                    />
                  </div>
                  <div className="flex items-center justify-between text-[10px]">
                    <span className={`font-bold px-1.5 py-0.2 rounded border ${riskInfo.bg}`}>
                      {riskInfo.label}
                    </span>
                    <span className="text-slate-500 font-mono text-[9px]">
                      {analysis.fraud_risk?.risk_factors?.length || 0} factors
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Quick Unresolved Issues Banner if any */}
            {analysis.unresolved_issues && analysis.unresolved_issues.length > 0 && (
              <div className="bg-white/80 backdrop-blur rounded-xl p-3 border border-black/5 space-y-1.5">
                <div className="flex items-center space-x-2 text-xs font-bold text-rose-900">
                  <AlertTriangle className="h-3.5 w-3.5 text-rose-600 flex-shrink-0" />
                  <span>Unresolved Issues Requiring Action ({analysis.unresolved_issues.length})</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] text-slate-700">
                  {analysis.unresolved_issues.map((issue, idx) => (
                    <div key={idx} className="flex items-start space-x-1.5">
                      <span className="text-rose-500 font-bold">•</span>
                      <span>{issue}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Sub-Tabs / View Switcher */}
          <div className="flex items-center space-x-2 border-b border-slate-200 pb-2">
            <button
              onClick={() => setActiveTab("overview")}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                activeTab === "overview"
                  ? "bg-slate-900 text-white shadow-sm"
                  : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              Agents Synthesis (5 Agents)
            </button>
            <button
              onClick={() => setActiveTab("lines")}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                activeTab === "lines"
                  ? "bg-slate-900 text-white shadow-sm"
                  : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              3-Way Line Matches ({analysis.matching?.line_matches?.length || 0})
            </button>
            <button
              onClick={() => setActiveTab("telemetry")}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                activeTab === "telemetry"
                  ? "bg-slate-900 text-white shadow-sm"
                  : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              Execution Telemetry ({logs.length} Logs)
            </button>
          </div>

          {/* TAB 1: 5 Specialized Agent Cards */}
          {activeTab === "overview" && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {/* Agent 1: Invoice Understanding */}
              <div className="bg-slate-50/70 rounded-xl border border-slate-200 p-4 space-y-3.5 flex flex-col justify-between">
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <div className="p-1.5 rounded-lg bg-sky-100 text-sky-700">
                        <FileSearch className="h-4 w-4" />
                      </div>
                      <span className="text-xs font-bold text-slate-900">Invoice Understanding</span>
                    </div>
                    <span
                      className={`text-[10px] font-bold font-mono px-2 py-0.5 rounded-full border ${
                        analysis.understanding?.status === "PASSED"
                          ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                          : analysis.understanding?.status === "WARNING"
                          ? "bg-amber-50 text-amber-700 border-amber-200"
                          : "bg-rose-50 text-rose-700 border-rose-200"
                      }`}
                    >
                      {analysis.understanding?.status || "UNKNOWN"}
                    </span>
                  </div>

                  <p className="text-[11px] text-slate-600 leading-relaxed">
                    {analysis.understanding?.summary}
                  </p>

                  <div className="space-y-1.5 pt-2 border-t border-slate-200/60 text-[11px]">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-500">Extraction Confidence:</span>
                      <span className="font-mono font-bold text-slate-800">
                        {Number(analysis.understanding?.confidence_score || 0)}%
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-slate-500">Tax Structure:</span>
                      <span className="font-semibold text-slate-800">
                        {analysis.understanding?.tax_type?.replace(/_/g, " ")}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-slate-500">Math Reconciliation:</span>
                      <span
                        className={`font-semibold ${
                          analysis.understanding?.math_reconciled ? "text-emerald-700" : "text-amber-700"
                        }`}
                      >
                        {analysis.understanding?.math_reconciled ? "Reconciled" : "Variance Detected"}
                      </span>
                    </div>
                  </div>
                </div>

                {analysis.understanding?.missing_fields?.length > 0 && (
                  <div className="pt-2 border-t border-slate-200/60">
                    <span className="text-[10px] font-bold text-amber-800">Missing Fields: </span>
                    <span className="text-[10px] text-slate-600">
                      {analysis.understanding.missing_fields.join(", ")}
                    </span>
                  </div>
                )}
              </div>

              {/* Agent 2: Vendor Verification */}
              <div className="bg-slate-50/70 rounded-xl border border-slate-200 p-4 space-y-3.5 flex flex-col justify-between">
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <div className="p-1.5 rounded-lg bg-teal-100 text-teal-700">
                        <Building2 className="h-4 w-4" />
                      </div>
                      <span className="text-xs font-bold text-slate-900">Vendor Verification</span>
                    </div>
                    <span
                      className={`text-[10px] font-bold font-mono px-2 py-0.5 rounded-full border ${
                        analysis.vendor_verification?.status === "VERIFIED"
                          ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                          : analysis.vendor_verification?.status === "UNKNOWN_VENDOR"
                          ? "bg-rose-50 text-rose-700 border-rose-200"
                          : "bg-amber-50 text-amber-700 border-amber-200"
                      }`}
                    >
                      {analysis.vendor_verification?.status || "UNKNOWN"}
                    </span>
                  </div>

                  <p className="text-[11px] text-slate-600 leading-relaxed">
                    {analysis.vendor_verification?.summary}
                  </p>

                  <div className="space-y-1.5 pt-2 border-t border-slate-200/60 text-[11px]">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-500">Vendor Master Match:</span>
                      <span className="font-semibold text-slate-800">
                        {analysis.vendor_verification?.legal_name || "Unmatched"}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-slate-500">GSTIN Match:</span>
                      <span
                        className={`font-semibold ${
                          analysis.vendor_verification?.gstin_matched ? "text-emerald-700" : "text-rose-700"
                        }`}
                      >
                        {analysis.vendor_verification?.gstin_matched ? "Matched Registered ID" : "Mismatch / Missing"}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-slate-500">Banking Remittance:</span>
                      <span
                        className={`font-semibold ${
                          analysis.vendor_verification?.has_bank_details ? "text-emerald-700" : "text-amber-700"
                        }`}
                      >
                        {analysis.vendor_verification?.has_bank_details ? "Bank Account on File" : "No Bank Details"}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-200/60">
                  <div className="text-[10px] text-slate-500 flex items-center justify-between">
                    <span>Vendor Status:</span>
                    <span
                      className={`font-bold ${
                        analysis.vendor_verification?.is_active ? "text-emerald-700" : "text-rose-700"
                      }`}
                    >
                      {analysis.vendor_verification?.is_active ? "Active University Vendor" : "Inactive / Unregistered"}
                    </span>
                  </div>
                </div>
              </div>

              {/* Agent 3: Three-Way Matching */}
              <div className="bg-slate-50/70 rounded-xl border border-slate-200 p-4 space-y-3.5 flex flex-col justify-between">
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <div className="p-1.5 rounded-lg bg-indigo-100 text-indigo-700">
                        <GitCompare className="h-4 w-4" />
                      </div>
                      <span className="text-xs font-bold text-slate-900">3-Way PO & GRN Match</span>
                    </div>
                    <span
                      className={`text-[10px] font-bold font-mono px-2 py-0.5 rounded-full border ${
                        analysis.matching?.match_status === "FULL_MATCH"
                          ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                          : analysis.matching?.match_status === "NO_PO"
                          ? "bg-purple-50 text-purple-700 border-purple-200"
                          : "bg-amber-50 text-amber-700 border-amber-200"
                      }`}
                    >
                      {analysis.matching?.match_status || "UNKNOWN"}
                    </span>
                  </div>

                  <p className="text-[11px] text-slate-600 leading-relaxed">
                    {analysis.matching?.summary}
                  </p>

                  <div className="space-y-1.5 pt-2 border-t border-slate-200/60 text-[11px]">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-500">Purchase Order:</span>
                      <span className="font-mono font-semibold text-slate-800">
                        {analysis.matching?.po_number || "None Linked (Direct Spend)"}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-slate-500">GRN Records:</span>
                      <span className="font-mono text-slate-800">
                        {analysis.matching?.grn_numbers?.length
                          ? analysis.matching.grn_numbers.join(", ")
                          : "None Linked"}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-slate-500">Total Variance:</span>
                      <span
                        className={`font-mono font-bold ${
                          Number(analysis.matching?.total_variance || 0) === 0
                            ? "text-emerald-700"
                            : "text-amber-700"
                        }`}
                      >
                        {formatCurrency(Number(analysis.matching?.total_variance || 0))}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-200/60">
                  <div className="flex items-center justify-between text-[10px]">
                    <span className="text-slate-500">Line Items Checked:</span>
                    <span className="font-mono font-bold text-slate-800">
                      {analysis.matching?.line_matches?.length || 0} Lines
                    </span>
                  </div>
                </div>
              </div>

              {/* Agent 4: Fraud & Risk Detection */}
              <div className="bg-slate-50/70 rounded-xl border border-slate-200 p-4 space-y-3.5 flex flex-col justify-between">
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <div className="p-1.5 rounded-lg bg-rose-100 text-rose-700">
                        <ShieldAlert className="h-4 w-4" />
                      </div>
                      <span className="text-xs font-bold text-slate-900">Fraud & Risk Engine</span>
                    </div>
                    <span className={`text-[10px] font-bold font-mono px-2 py-0.5 rounded-full border ${riskInfo.bg}`}>
                      {riskInfo.label} ({Number(analysis.risk_score || 0)})
                    </span>
                  </div>

                  <p className="text-[11px] text-slate-600 leading-relaxed">
                    {analysis.fraud_risk?.summary}
                  </p>

                  <div className="space-y-1.5 pt-2 border-t border-slate-200/60 text-[11px]">
                    <div className="text-[10px] font-bold text-slate-700 uppercase tracking-wider">
                      Assessed Risk Factors ({analysis.fraud_risk?.risk_factors?.length || 0}):
                    </div>
                    {analysis.fraud_risk?.risk_factors && analysis.fraud_risk.risk_factors.length > 0 ? (
                      <div className="space-y-1 max-h-24 overflow-y-auto">
                        {analysis.fraud_risk.risk_factors.map((rf, idx) => (
                          <div key={idx} className="flex items-center justify-between text-[10px] bg-white p-1 rounded border border-slate-200">
                            <span className="truncate max-w-[170px] text-slate-700">{rf.factor.replace(/_/g, " ")}</span>
                            <span className="font-mono font-bold text-rose-600">+{rf.score_impact} pts</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="p-2 rounded bg-emerald-50 text-emerald-800 text-[10px] font-medium text-center">
                        ✓ All 7 security and duplicate dimensions cleared
                      </div>
                    )}
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-200/60">
                  <div className="text-[10px] text-slate-600">
                    <span className="font-semibold">Action: </span>
                    <span>{analysis.fraud_risk?.recommended_action}</span>
                  </div>
                </div>
              </div>

              {/* Agent 5: Approval Recommendation & Human Checklist */}
              <div className="bg-slate-50/70 rounded-xl border border-slate-200 p-4 space-y-3.5 flex flex-col justify-between md:col-span-2">
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <div className="p-1.5 rounded-lg bg-indigo-100 text-indigo-700">
                        <ShieldCheck className="h-4 w-4" />
                      </div>
                      <span className="text-xs font-bold text-slate-900">
                        Officer Recommendation & Action Checklist
                      </span>
                    </div>
                    <span className={`text-[10px] font-bold font-mono px-2.5 py-0.5 rounded-full border ${badgeInfo.pill}`}>
                      {analysis.recommendation}
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {/* Key reasons */}
                    <div className="space-y-1.5">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-700">
                        Key Synthesis Reasons:
                      </span>
                      <ul className="space-y-1 text-[11px] text-slate-600">
                        {analysis.approval_recommendation?.key_reasons?.map((reason, idx) => (
                          <li key={idx} className="flex items-start space-x-1.5">
                            <span className="text-indigo-500 font-bold">•</span>
                            <span>{reason}</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    {/* Action checklist for accounts officer */}
                    <div className="space-y-1.5">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-700">
                        Account Officer Checklist:
                      </span>
                      <ul className="space-y-1.5 text-[11px] text-slate-700 bg-white p-2.5 rounded-lg border border-slate-200">
                        {analysis.approval_recommendation?.action_checklist?.map((item, idx) => (
                          <li key={idx} className="flex items-start space-x-2">
                            <input
                              type="checkbox"
                              defaultChecked={analysis.recommendation === "APPROVE"}
                              className="mt-0.5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500/20"
                            />
                            <span className="leading-tight text-slate-700">{item}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-200/60 flex items-center justify-between text-[10px] text-slate-500">
                  <div className="flex items-center space-x-1.5">
                    <CheckCircle2 className="h-3.5 w-3.5 text-indigo-600" />
                    <span>Human in the loop: Decision authority rests with University Finance Officers.</span>
                  </div>
                  <span className="font-mono">Analysis: {formatDateTime(analysis.analyzed_at)}</span>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: Itemized Line Matches Table */}
          {activeTab === "lines" && (
            <div className="border border-slate-200 rounded-xl overflow-hidden">
              <div className="p-3.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
                <div>
                  <h4 className="text-xs font-bold text-slate-900">3-Way Line Matching Detail</h4>
                  <p className="text-[11px] text-slate-500">
                    Reconciliation between Invoiced Lines, Purchase Order Lines, and Warehouse Goods Receipt
                  </p>
                </div>
                <span className="text-xs font-mono font-bold text-slate-700">
                  Total Variance: {formatCurrency(Number(analysis.matching?.total_variance || 0))}
                </span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-slate-100/60 text-slate-500 font-semibold border-b border-slate-200">
                      <th className="py-2 px-3">#</th>
                      <th className="py-2 px-3">Description</th>
                      <th className="py-2 px-3 text-right">PO Qty</th>
                      <th className="py-2 px-3 text-right">GRN Acc.</th>
                      <th className="py-2 px-3 text-right">Inv Qty</th>
                      <th className="py-2 px-3 text-right">PO Price</th>
                      <th className="py-2 px-3 text-right">Inv Price</th>
                      <th className="py-2 px-3 text-right">Price Var</th>
                      <th className="py-2 px-3 text-center">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {analysis.matching?.line_matches && analysis.matching.line_matches.length > 0 ? (
                      analysis.matching.line_matches.map((line, idx) => (
                        <tr key={idx} className="hover:bg-slate-50/50">
                          <td className="py-2.5 px-3 font-mono text-slate-400">{line.line_number}</td>
                          <td className="py-2.5 px-3 font-medium text-slate-800">{line.description}</td>
                          <td className="py-2.5 px-3 text-right font-mono text-slate-600">
                            {line.po_quantity !== null ? Number(line.po_quantity) : "N/A"}
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono text-slate-600">
                            {line.grn_accepted_quantity !== null ? Number(line.grn_accepted_quantity) : "N/A"}
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono font-bold text-slate-800">
                            {Number(line.invoice_quantity)}
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono text-slate-600">
                            {line.po_unit_price !== null ? formatCurrency(Number(line.po_unit_price)) : "N/A"}
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono font-bold text-slate-800">
                            {formatCurrency(Number(line.invoice_unit_price))}
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono">
                            <span
                              className={`font-bold ${
                                Number(line.price_variance) === 0
                                  ? "text-emerald-700"
                                  : Number(line.price_variance) > 0
                                  ? "text-rose-600"
                                  : "text-blue-600"
                              }`}
                            >
                              {formatCurrency(Number(line.price_variance))}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-center">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                                line.status === "MATCHED"
                                  ? "bg-emerald-100 text-emerald-800"
                                  : line.status === "PRICE_VARIANCE"
                                  ? "bg-amber-100 text-amber-800"
                                  : line.status === "QUANTITY_VARIANCE"
                                  ? "bg-rose-100 text-rose-800"
                                  : "bg-slate-100 text-slate-700"
                              }`}
                            >
                              {line.status}
                            </span>
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={9} className="py-6 text-center text-slate-400 text-xs">
                          No line items to match against PO lines.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 3: Execution Telemetry & Logs */}
          {activeTab === "telemetry" && (
            <div className="border border-slate-200 rounded-xl overflow-hidden space-y-3">
              <div className="p-3.5 bg-slate-50 border-b border-slate-200">
                <h4 className="text-xs font-bold text-slate-900">Database Execution Logs (`agent_execution_logs`)</h4>
                <p className="text-[11px] text-slate-500">
                  Granular agent telemetry including execution duration, status, and input/output payload summaries
                </p>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-slate-100/60 text-slate-500 font-semibold border-b border-slate-200">
                      <th className="py-2 px-3">Agent Name</th>
                      <th className="py-2 px-3 text-center">Status</th>
                      <th className="py-2 px-3 text-right">Duration</th>
                      <th className="py-2 px-3">Summary / Output</th>
                      <th className="py-2 px-3 text-right">Timestamp</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
                    {logs && logs.length > 0 ? (
                      logs.map((log) => (
                        <tr key={log.id} className="hover:bg-slate-50/50">
                          <td className="py-2 px-3 font-bold text-slate-900">{log.agent_name}</td>
                          <td className="py-2 px-3 text-center">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                log.execution_status === "SUCCESS"
                                  ? "bg-emerald-100 text-emerald-800"
                                  : "bg-rose-100 text-rose-800"
                              }`}
                            >
                              {log.execution_status}
                            </span>
                          </td>
                          <td className="py-2 px-3 text-right text-slate-600">
                            {log.execution_duration ? `${log.execution_duration}s` : "N/A"}
                          </td>
                          <td className="py-2 px-3 font-sans text-xs text-slate-700 max-w-md truncate">
                            {log.output_summary || log.error_message || "Execution completed"}
                          </td>
                          <td className="py-2 px-3 text-right text-slate-400">
                            {formatDateTime(log.created_at)}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={5} className="py-6 text-center text-slate-400 font-sans text-xs">
                          No execution logs found for this invoice.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};