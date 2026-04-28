export interface APIResponse<T> {
  success: boolean;
  message: string;
  data: T;
  error?: string | null;
}

export interface DataQualityBrief {
  overall_confidence: number;
  can_cite_as_municipal: boolean;
}

export interface ValidationIssue {
  code: string;
  severity: "blocking" | "warning" | string;
  field?: string | null;
  description: string;
  value_excerpt?: string | null;
}

export interface ValidationReport {
  passed: boolean;
  score: number;
  checks_run: number;
  checks_failed: number;
  blocking_count: number;
  warning_count: number;
  rule_version: string;
  issues: ValidationIssue[];
}

export interface Municipality {
  id: string;
  name: string;
  region?: string;
  profile?: string;
  economic_base?: string;
  notes?: string;
}

export interface Neighborhood {
  id: string;
  municipality_id: string;
  name: string;
}

export interface DataQualitySummary {
  overall_confidence: number;
  municipal_coverage_pct: number;
  state_coverage_pct: number;
  estimated_coverage_pct: number;
  can_cite_as_municipal: boolean;
  quality_label: string;
  methodology_disclaimer: string;
}

export interface EvidenceSummary {
  id: string;
  municipality_id: string;
  municipality_name: string;
  created_at: string;
  collection_method: string;
  data_quality: {
    overall_confidence: number;
    can_cite_as_municipal: boolean;
    quality_label: string;
  };
}

export interface EvidenceDetail extends EvidenceSummary {
  snapshot_version: string;
  expires_at?: string | null;
  data_quality: DataQualitySummary;
  sources_used: string[];
  geographic_fallbacks: string[];
}

export interface MessagingAxis {
  axis: string;
  message: string;
  rationale?: string;
  emotional_hook?: string;
  data_anchor?: string;
}

export interface StrategySection {
  executive_strategic: string;
  messaging_axes: MessagingAxis[];
  pain_points_ranked: string[];
  opportunities_ranked: string[];
  candidate_positioning: string;
  recommended_tone: string;
  risk_flags: string[];
  framing_suggestions: string[];
  communication_channels_priority: string[];
  ai_generated: boolean;
  latency_ms?: number | null;
}

export interface CriticalNeed {
  title: string;
  severity?: string;
  evidence?: string;
  urgency?: string;
  [key: string]: unknown;
}

export interface AnalysisSummary {
  id: string;
  municipality_id: string;
  evidence_record_id: string;
  created_at: string;
  status: string;
  objective?: string;
  executive_summary: string;
  data_quality: DataQualityBrief;
  validation: ValidationReport;
}

export interface AnalysisDetail extends AnalysisSummary {
  demographic_profile: Record<string, unknown>;
  economic_engine: Record<string, unknown>;
  infrastructure_gaps: Record<string, unknown>;
  critical_needs: CriticalNeed[];
  opportunities: string[];
  kpi_board: Record<string, unknown>;
  strategy_section: StrategySection;
}

export interface SpeechSection {
  title: string;
  content: string;
  persuasion_technique?: string;
}

export interface DurationVerification {
  target_minutes: number;
  estimated_minutes: number;
  lower_bound_minutes: number;
  upper_bound_minutes: number;
  within_tolerance: boolean;
  delta_minutes: number;
  delta_pct: number;
  words_per_minute: number;
  actual_word_count: number;
}

export interface SourceProcessingMeta {
  word_count: number;
  paragraph_count: number;
  segments_count: number;
  estimated_minutes: number;
  alpha_ratio: number;
  prompt_ready_word_count: number;
  segment_previews: string[];
}

export interface GenerationPlan {
  target_words: number;
  minimum_words: number;
  opening_words: number;
  closing_words: number;
  body_sections: number;
  body_section_words: number;
  batches: number[][];
}

export interface SpeechData {
  title?: string;
  speech_objective?: string;
  target_audience?: string;
  estimated_duration_minutes?: number;
  estimated_word_count?: number;
  opening?: string;
  body_sections?: SpeechSection[];
  closing?: string;
  full_text?: string;
  local_references?: string[];
  improvements_made?: string[];
  adaptation_notes?: string[];
  duration_verification?: DurationVerification;
  source_processing?: SourceProcessingMeta;
  generation_plan?: GenerationPlan;
  emotional_hooks?: string[];
  rational_hooks?: string[];
}

export interface SpeechSummary {
  id: string;
  municipality_id: string;
  analysis_run_id?: string;
  created_at: string;
  status: string;
  speech_type: "creation" | "adaptation" | "improvement";
  target_duration_minutes: number;
  target_word_count: number;
  actual_word_count: number;
  retry_count: number;
  parameter_hash: string;
  data_quality: DataQualityBrief;
  validation: ValidationReport;
}

export interface SpeechDetail extends SpeechSummary {
  speech_data: SpeechData;
  ai_generated: boolean;
  latency_ms?: number;
}

export type AnalysisRun = AnalysisDetail;
export type SpeechRun = SpeechDetail;