export const SCALES = [2, 4, 6, 8, 10] as const;
export type Scale = (typeof SCALES)[number];
export type OutputFormat = "PNG" | "TIFF";

export type JobStatus =
  | "queued"
  | "running"
  | "cancelling"
  | "cancelled"
  | "completed"
  | "failed";

export interface Verification {
  ok: boolean;
  actual_format: string | null;
  actual_width: number | null;
  actual_height: number | null;
  original_width: number;
  original_height: number;
  scale_x: number | null;
  scale_y: number | null;
  matches_requested_scale: boolean;
  format_matches_request: boolean;
  cropped: boolean;
  orientation: string;
  summary: string;
  message: string;
  requested_scale: number;
  requested_format: string;
  model?: string;
  device?: string;
}

export interface Job {
  id: string;
  status: JobStatus;
  progress: number;
  message: string;
  error: string | null;
  scale: number;
  output_format: OutputFormat;
  original_name: string;
  original_width: number;
  original_height: number;
  verification: Verification | null;
  warning: string | null;
}

export interface Health {
  ok: boolean;
  model: string;
  device: string;
  stub: boolean;
  model_scale: number;
  load_error: string | null;
}

export function expectedOutputSize(width: number, height: number, scale: number) {
  return { width: width * scale, height: height * scale };
}
