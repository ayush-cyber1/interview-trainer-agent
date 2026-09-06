/* ProfilePage.tsx — profile setup + resume upload + generation trigger */

import { useCallback, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { submitProfile, generatePrep } from '../api'
import type { GenerateResponse, ProfileData } from '../types'
import styles from './ProfilePage.module.css'
import { Upload, Sparkles, X, CheckCircle2 } from 'lucide-react'

const JOB_ROLES = [
  'Software Engineer',
  'Data Analyst',
  'Product Manager',
  'HR Specialist',
  'Sales Executive',
  'Other',
]

interface Props {
  onGenerated: (profile: ProfileData, results: GenerateResponse) => void
}

export default function ProfilePage({ onGenerated }: Props) {
  const navigate = useNavigate()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [name, setName] = useState('')
  const [level, setLevel] = useState<'Fresher' | 'Mid' | 'Senior'>('Fresher')
  const [role, setRole] = useState('Software Engineer')
  const [customRole, setCustomRole] = useState('')
  const [resumeFile, setResumeFile] = useState<File | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const [skills, setSkills] = useState<string[]>([])
  const [profileSaved, setProfileSaved] = useState(false)

  const [errors, setErrors] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState<'profile' | 'generate' | null>(null)
  const [apiError, setApiError] = useState('')

  const effectiveRole = role === 'Other' ? customRole : role

  function validate() {
    const e: Record<string, string> = {}
    if (!name.trim()) e.name = 'Please enter your name.'
    if (role === 'Other' && !customRole.trim()) e.customRole = 'Please enter your job role.'
    return e
  }

  async function handleSaveProfile(e: React.FormEvent) {
    e.preventDefault()
    const errs = validate()
    if (Object.keys(errs).length) { setErrors(errs); return }
    setErrors({})
    setApiError('')
    setLoading('profile')
    try {
      const res = await submitProfile(
        { name: name.trim(), experience_level: level, job_role: effectiveRole },
        resumeFile
      )
      setSkills(res.skills_extracted ?? [])
      setProfileSaved(true)
    } catch (err: any) {
      setApiError(err?.response?.data?.detail ?? 'Failed to save profile. Is the backend running?')
    } finally {
      setLoading(null)
    }
  }

  async function handleGenerate() {
    if (!profileSaved) { setApiError('Save your profile first.'); return }
    setApiError('')
    setLoading('generate')
    try {
      const profile: ProfileData = {
        name: name.trim(),
        experience_level: level,
        job_role: effectiveRole,
        skills,
      }
      const results = await generatePrep(profile)
      onGenerated(profile, results)
      navigate('/results')
    } catch (err: any) {
      setApiError(err?.response?.data?.detail ?? 'Generation failed. Check backend logs.')
    } finally {
      setLoading(null)
    }
  }

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) setResumeFile(file)
  }, [])

  return (
    <div className={`${styles.page} fade-in`}>
      <div className={styles.hero}>
        <h1 className={styles.title}>Set Up Your Profile</h1>
        <p className={styles.sub}>Tell us about yourself and your target role. Optionally upload your resume to get skill-aware questions.</p>
      </div>

      <form className={styles.card} onSubmit={handleSaveProfile} noValidate>
        {/* Name */}
        <div className={styles.field}>
          <label htmlFor="name" className={styles.label}>Your Name</label>
          <input
            id="name"
            className={`${styles.input} ${errors.name ? styles.inputError : ''}`}
            value={name}
            onChange={(e) => { setName(e.target.value); setErrors((p) => ({ ...p, name: '' })) }}
            placeholder="e.g. Alex Johnson"
          />
          {errors.name && <span className={styles.errMsg}>{errors.name}</span>}
        </div>

        {/* Experience Level */}
        <div className={styles.field}>
          <label className={styles.label}>Experience Level</label>
          <div className={styles.chips}>
            {(['Fresher', 'Mid', 'Senior'] as const).map((l) => (
              <button
                key={l}
                type="button"
                className={`${styles.chip} ${level === l ? styles.chipActive : ''}`}
                onClick={() => setLevel(l)}
              >
                {l}
              </button>
            ))}
          </div>
        </div>

        {/* Job Role */}
        <div className={styles.field}>
          <label htmlFor="role" className={styles.label}>Target Job Role</label>
          <select
            id="role"
            className={styles.select}
            value={role}
            onChange={(e) => setRole(e.target.value)}
          >
            {JOB_ROLES.map((r) => <option key={r}>{r}</option>)}
          </select>
          {role === 'Other' && (
            <input
              className={`${styles.input} ${errors.customRole ? styles.inputError : ''}`}
              style={{ marginTop: '10px' }}
              value={customRole}
              onChange={(e) => { setCustomRole(e.target.value); setErrors((p) => ({ ...p, customRole: '' })) }}
              placeholder="Enter your job role"
            />
          )}
          {errors.customRole && <span className={styles.errMsg}>{errors.customRole}</span>}
        </div>

        {/* Resume Upload */}
        <div className={styles.field}>
          <label className={styles.label}>Resume <span className={styles.optional}>(optional · PDF or DOCX)</span></label>
          <div
            className={`${styles.dropzone} ${dragOver ? styles.dropzoneActive : ''} ${resumeFile ? styles.dropzoneFilled : ''}`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.doc"
              style={{ display: 'none' }}
              onChange={(e) => setResumeFile(e.target.files?.[0] ?? null)}
            />
            {resumeFile ? (
              <div className={styles.fileInfo}>
                <CheckCircle2 size={20} color="var(--success)" />
                <span>{resumeFile.name}</span>
                <button
                  type="button"
                  className={styles.removeFile}
                  onClick={(e) => { e.stopPropagation(); setResumeFile(null) }}
                >
                  <X size={14} />
                </button>
              </div>
            ) : (
              <div className={styles.dropHint}>
                <Upload size={24} />
                <span>Drag & drop or <strong>browse</strong></span>
              </div>
            )}
          </div>
        </div>

        {/* Extracted Skills */}
        {skills.length > 0 && (
          <div className={styles.skillsBox}>
            <span className={styles.skillsLabel}>Skills detected from resume:</span>
            <div className={styles.skillTags}>
              {skills.map((s) => <span key={s} className={styles.tag}>{s}</span>)}
            </div>
          </div>
        )}

        {apiError && <div className={styles.apiError}>{apiError}</div>}

        <div className={styles.actions}>
          <button type="submit" className={styles.btnPrimary} disabled={!!loading}>
            {loading === 'profile' ? <span className="spin" style={{ display: 'inline-block', width: 18, height: 18, border: '2px solid #fff', borderTopColor: 'transparent', borderRadius: '50%' }} /> : null}
            {profileSaved ? 'Profile Saved ✓' : 'Save Profile'}
          </button>
          <button
            type="button"
            className={styles.btnAccent}
            disabled={!profileSaved || !!loading}
            onClick={handleGenerate}
          >
            {loading === 'generate'
              ? <><span className="spin" style={{ display: 'inline-block', width: 18, height: 18, border: '2px solid #fff', borderTopColor: 'transparent', borderRadius: '50%' }} /> Generating…</>
              : <><Sparkles size={16} /> Generate Questions</>
            }
          </button>
        </div>
      </form>
    </div>
  )
}
