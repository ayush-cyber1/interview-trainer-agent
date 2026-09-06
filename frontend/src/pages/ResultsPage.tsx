/* ResultsPage.tsx — displays generated Q&A, tabs, readiness chart */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  RadialBarChart, RadialBar, PolarAngleAxis,
  ResponsiveContainer, Tooltip
} from 'recharts'
import type { GenerateResponse, ProfileData, QuestionItem } from '../types'
import styles from './ResultsPage.module.css'
import { ChevronDown, ChevronUp, Download, RotateCcw, Lightbulb, BookOpen } from 'lucide-react'

interface Props {
  profile: ProfileData
  results: GenerateResponse
}

function QuestionCard({ item, index }: { item: QuestionItem; index: number }) {
  const [open, setOpen] = useState(false)
  return (
    <div className={styles.qcard}>
      <button className={styles.qtrigger} onClick={() => setOpen((p) => !p)}>
        <span className={styles.qnum}>{String(index + 1).padStart(2, '0')}</span>
        <span className={styles.qtext}>{item.question}</span>
        {open ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
      </button>
      {open && (
        <div className={styles.qbody}>
          <div className={styles.qsection}>
            <span className={styles.qsectionTitle}><BookOpen size={14} /> Model Answer</span>
            <p className={styles.qanswer}>{item.model_answer}</p>
          </div>
          <div className={styles.qtip}>
            <Lightbulb size={14} />
            <span><strong>Tip:</strong> {item.tip}</span>
          </div>
        </div>
      )}
    </div>
  )
}

function downloadPrepSheet(profile: ProfileData, results: GenerateResponse) {
  const lines: string[] = [
    `INTERVIEW PREP SHEET`,
    `Generated: ${new Date().toLocaleString()}`,
    `Candidate: ${profile.name}  |  Role: ${profile.job_role}  |  Level: ${profile.experience_level}`,
    ``,
    `═══════════════════════ TECHNICAL QUESTIONS ════════════════════════`,
    ...results.technical.map((q, i) => [
      ``,
      `Q${i + 1}. ${q.question}`,
      `Answer: ${q.model_answer}`,
      `Tip: ${q.tip}`,
    ].join('\n')),
    ``,
    `══════════════════════ BEHAVIORAL QUESTIONS ════════════════════════`,
    ...results.behavioral.map((q, i) => [
      ``,
      `Q${i + 1}. ${q.question}`,
      `Answer: ${q.model_answer}`,
      `Tip: ${q.tip}`,
    ].join('\n')),
    ``,
    `══════════════════════ READINESS ASSESSMENT ════════════════════════`,
    `Score: ${results.readiness.score}/10`,
    ``,
    `Recommendations:`,
    ...results.readiness.recommendations.map((r, i) => `  ${i + 1}. ${r}`),
  ]

  const blob = new Blob([lines.join('\n')], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `prep-sheet-${profile.name.replace(/\s+/g, '-')}.txt`
  a.click()
  URL.revokeObjectURL(url)
}

export default function ResultsPage({ profile, results }: Props) {
  const navigate = useNavigate()
  const [tab, setTab] = useState<'technical' | 'behavioral'>('technical')

  const scoreData = [{ name: 'Score', value: results.readiness.score * 10, fill: '#4f46e5' }]

  return (
    <div className={`${styles.page} fade-in`}>
      {/* Header */}
      <div className={styles.pageHeader}>
        <div>
          <h1 className={styles.title}>Your Interview Prep</h1>
          <p className={styles.sub}>{profile.name} · {profile.job_role} · {profile.experience_level}</p>
        </div>
        <div className={styles.headerActions}>
          <button className={styles.btnOutline} onClick={() => navigate('/profile')}>
            <RotateCcw size={15} /> Retry
          </button>
          <button className={styles.btnPrimary} onClick={() => downloadPrepSheet(profile, results)}>
            <Download size={15} /> Download Prep Sheet
          </button>
        </div>
      </div>

      {/* Summary row */}
      <div className={styles.summaryRow}>
        {/* Readiness gauge */}
        <div className={styles.gaugeCard}>
          <h3 className={styles.cardTitle}>Readiness Score</h3>
          <div className={styles.gauge}>
            <ResponsiveContainer width="100%" height={160}>
              <RadialBarChart
                cx="50%" cy="80%"
                innerRadius="60%"
                outerRadius="100%"
                startAngle={180}
                endAngle={0}
                data={scoreData}
              >
                <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
                <RadialBar dataKey="value" cornerRadius={8} background={{ fill: '#e0e7ff' }} />
                <Tooltip formatter={(v: number) => [`${v / 10}/10`, 'Readiness']} />
              </RadialBarChart>
            </ResponsiveContainer>
            <div className={styles.gaugeLabel}>
              <span className={styles.gaugeScore}>{results.readiness.score}</span>
              <span className={styles.gaugeMax}>/10</span>
            </div>
          </div>
        </div>

        {/* Recommendations */}
        <div className={styles.recCard}>
          <h3 className={styles.cardTitle}>Preparation Recommendations</h3>
          <ul className={styles.recList}>
            {results.readiness.recommendations.map((r, i) => (
              <li key={i} className={styles.recItem}>
                <span className={styles.recBullet}>{i + 1}</span>
                <span>{r}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Stats */}
        <div className={styles.statsCard}>
          <h3 className={styles.cardTitle}>Question Breakdown</h3>
          <div className={styles.statsGrid}>
            <div className={styles.statBox} style={{ background: '#eef0ff' }}>
              <span className={styles.statNum}>{results.technical.length}</span>
              <span className={styles.statLbl}>Technical</span>
            </div>
            <div className={styles.statBox} style={{ background: '#f0fdf4' }}>
              <span className={styles.statNum}>{results.behavioral.length}</span>
              <span className={styles.statLbl}>Behavioral</span>
            </div>
            <div className={styles.statBox} style={{ background: '#fff7ed' }}>
              <span className={styles.statNum}>{results.technical.length + results.behavioral.length}</span>
              <span className={styles.statLbl}>Total</span>
            </div>
          </div>
          {profile.skills.length > 0 && (
            <div className={styles.skillsUsed}>
              <span className={styles.skillsUsedLabel}>Skills used:</span>
              <div className={styles.skillTags}>
                {profile.skills.slice(0, 6).map((s) => <span key={s} className={styles.tag}>{s}</span>)}
                {profile.skills.length > 6 && <span className={styles.tagMore}>+{profile.skills.length - 6}</span>}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Tab panel */}
      <div className={styles.tabPanel}>
        <div className={styles.tabs}>
          <button
            className={`${styles.tab} ${tab === 'technical' ? styles.tabActive : ''}`}
            onClick={() => setTab('technical')}
          >
            Technical Questions <span className={styles.tabBadge}>{results.technical.length}</span>
          </button>
          <button
            className={`${styles.tab} ${tab === 'behavioral' ? styles.tabActive : ''}`}
            onClick={() => setTab('behavioral')}
          >
            Behavioral Questions <span className={styles.tabBadge}>{results.behavioral.length}</span>
          </button>
        </div>

        <div className={styles.qList}>
          {(tab === 'technical' ? results.technical : results.behavioral).map((q, i) => (
            <QuestionCard key={i} item={q} index={i} />
          ))}
        </div>
      </div>
    </div>
  )
}
