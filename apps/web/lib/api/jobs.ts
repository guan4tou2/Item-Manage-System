import type { paths } from "@ims/api-types"
import { apiFetch } from "./client"

export type JobStatus = paths["/api/jobs/{job_name}/status"]["get"]["responses"]["200"]["content"]["application/json"]
export type JobRunResult = paths["/api/jobs/{job_name}/run"]["post"]["responses"]["200"]["content"]["application/json"]

export async function getJobStatus(
  jobName: string,
  accessToken: string | null,
): Promise<JobStatus> {
  const res = await apiFetch(`/jobs/${jobName}/status`, { accessToken })
  return (await res.json()) as JobStatus
}
