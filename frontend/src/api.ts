import type { Health, Job, OutputFormat, Scale } from "./types";

async function parseError(res: Response): Promise<string> {
  try {
    const body = await res.json();
    return body.detail || body.message || res.statusText;
  } catch {
    return res.statusText;
  }
}

export async function fetchHealth(): Promise<Health> {
  const res = await fetch("/api/health");
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function createJob(params: {
  file: File;
  scale: Scale;
  outputFormat: OutputFormat;
  confirm?: boolean;
}): Promise<Job> {
  const form = new FormData();
  form.append("file", params.file);
  form.append("scale", String(params.scale));
  form.append("output_format", params.outputFormat);
  form.append("confirm", params.confirm ? "true" : "false");
  const res = await fetch("/api/jobs", { method: "POST", body: form });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const error = new Error(body.detail || res.statusText) as Error & {
      needsConfirm?: boolean;
      status?: number;
    };
    error.needsConfirm = Boolean(body.needs_confirm) || res.status === 409;
    error.status = res.status;
    throw error;
  }
  return res.json();
}

export async function getJob(id: string): Promise<Job> {
  const res = await fetch(`/api/jobs/${id}`);
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function cancelJob(id: string): Promise<Job> {
  const res = await fetch(`/api/jobs/${id}/cancel`, { method: "POST" });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function deleteJob(id: string): Promise<void> {
  const res = await fetch(`/api/jobs/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(await parseError(res));
}

export function originalUrl(id: string) {
  return `/api/jobs/${id}/original`;
}

export function resultUrl(id: string) {
  return `/api/jobs/${id}/result`;
}
