/* api.ts — thin Axios wrapper for the backend */

import axios from 'axios'
import type { GenerateResponse, ProfileData } from './types'

const BASE = '/api'

export async function submitProfile(
  data: Omit<ProfileData, 'skills'>,
  resumeFile?: File | null
): Promise<{ skills_extracted: string[]; resume_warning?: string }> {
  const form = new FormData()
  form.append('name', data.name)
  form.append('experience_level', data.experience_level)
  form.append('job_role', data.job_role)
  if (resumeFile) form.append('resume', resumeFile)

  const res = await axios.post(`${BASE}/profile`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

export async function generatePrep(
  profile: ProfileData
): Promise<GenerateResponse> {
  const res = await axios.post(`${BASE}/generate`, {
    name: profile.name,
    experience_level: profile.experience_level,
    job_role: profile.job_role,
    skills: profile.skills,
  })
  return res.data
}

export async function checkHealth(): Promise<{
  status: string
  vector_store: string
  watsonx_configured: boolean
}> {
  const res = await axios.get(`${BASE}/health`)
  return res.data
}
