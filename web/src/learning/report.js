// Final learning report: markdown builder and rubric.
//
// The builder is pure: every visible string comes from the `labels` object
// supplied by the caller (the UI passes t(...) results), so this module has no
// i18n or store dependency and can be tested directly in Node.
//
// The generated report starts as a skeleton with TODO prompts. The rubric only
// passes after the student replaces those prompts with real text, which keeps
// the final activity behaviour-based instead of a single button click.

export const REPORT_MARKER = '<!-- hivebr:learning-report -->'
// Same marker used by the IFMG template in ReportsPanel: the decorative banner
// is expanded only for preview/export, so the Markdown source stays readable.
export const IFMG_HEADER = '<!-- ifmg-header -->'
export const IDENTITY_START = '<!-- hivebr:report-identity -->'
export const IDENTITY_END = '<!-- /hivebr:report-identity -->'

export const RUBRIC_DEFAULTS = {
  // Words that are not part of the skeleton: tables, headings, images, HTML and
  // comments are ignored, so the student must write real prose.
  minWords: 300,
  sections: 5,
}

/** Words in prose lines only (no headings, tables, images, HTML or comments). */
export function proseWordCount(text) {
  const prose = String(text || '')
    .split(/\r?\n/)
    .filter((line) => {
      const trimmed = line.trim()
      if (!trimmed) return false
      if (trimmed.startsWith('#')) return false
      if (trimmed.startsWith('|')) return false
      if (trimmed.startsWith('![')) return false
      if (trimmed.startsWith('<')) return false
      if (/^[-:|\s]+$/.test(trimmed)) return false
      return true
    })
    .join(' ')
  return prose.split(/\s+/).filter((word) => /[\p{L}\p{N}]/u.test(word)).length
}

/** Rubric checks shared by the activity goal and the UI checklist. */
export function reportRubric(content, goal = {}) {
  const text = String(content || '')
  const minWords = goal.minWords ?? RUBRIC_DEFAULTS.minWords
  const sections = goal.sections ?? RUBRIC_DEFAULTS.sections
  const headings = (text.match(/^##\s+\S/gm) || []).length
  const words = proseWordCount(text)
  const checks = [
    { id: 'marker', ok: text.includes(REPORT_MARKER) },
    { id: 'sections', ok: headings >= sections },
    { id: 'words', ok: words >= minWords },
    { id: 'no_todo', ok: !/\bTODO\b/.test(text) },
  ]
  return { ok: checks.every((check) => check.ok), checks, words, headings }
}

function tableRow(cells) {
  return `| ${cells.join(' | ')} |`
}

function escapeHtml(text) {
  return String(text ?? '').replace(/[&<>"']/g, (char) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]
  ))
}

/**
 * IFMG identification table. It is delimited by markers so the profile sync can
 * rewrite only this block and keep everything the student wrote.
 */
function identityLines({ labels = {}, studentName = '', groupName = '', day = '' }) {
  const label = (key) => escapeHtml(labels[key] ?? key)
  const value = (text) => escapeHtml(text ?? '')
  return [
    IDENTITY_START,
    '<table>',
    `  <tr><td style="width:26%;color:#1e4d2e;font-weight:600;">${label('date')}</td><td>${value(day)}</td></tr>`,
    `  <tr><td style="color:#1e4d2e;font-weight:600;">${label('professor')}</td><td>${value(labels.notInformed)}</td></tr>`,
    `  <tr><td style="color:#1e4d2e;font-weight:600;">${label('subject')}</td><td>${value(labels.subjectValue)}</td></tr>`,
    `  <tr><td style="color:#1e4d2e;font-weight:600;">${label('group')}</td><td>${value(groupName)}</td></tr>`,
    `  <tr><td style="color:#1e4d2e;font-weight:600;">${label('student')}</td><td>${value(studentName)}</td></tr>`,
    '</table>',
    IDENTITY_END,
  ]
}

/**
 * Builds the final report skeleton following the IFMG academic model:
 * institutional header, identification table and five numbered sections.
 *
 * labels: { title, professor, subject, subjectValue, notInformed, student,
 *           group, date, introduction, development, resultsDiscussion,
 *           activities, results, figures, conclusion, references, todo, none,
 *           level, activity, stars, xp }
 * rows:   [{ level, track, title, stars, xp }]
 */
export function buildLearningReport({
  labels = {},
  rows = [],
  captures = [],
  date = new Date(),
  studentName = '',
  groupName = '',
} = {}) {
  const label = (key) => String(labels[key] ?? key)
  const lines = []
  const day = date instanceof Date ? date.toISOString().slice(0, 10) : String(date)

  lines.push(REPORT_MARKER)
  lines.push(IFMG_HEADER)
  lines.push('')
  lines.push(...identityLines({ labels, studentName, groupName, day }))
  lines.push('', `# ${label('title')}`, '')

  lines.push(`## 1) ${label('introduction')}`, '')
  lines.push(label('todo'))
  lines.push('')

  lines.push(`## 2) ${label('development')}`, '')
  lines.push(label('todo'))
  lines.push('')

  lines.push(`## 3) ${label('resultsDiscussion')}`, '')
  lines.push(`### ${label('activities')}`, '')
  lines.push(tableRow([label('level'), label('activity'), label('stars'), label('xp')]))
  lines.push(tableRow(['---:', '---', '---:', '---:']))
  for (const row of rows) {
    lines.push(tableRow([
      row.level ?? '',
      row.title ?? '',
      `${row.stars ?? 0}/3`,
      `${row.xp ?? 0} XP`,
    ]))
  }
  if (!rows.length) lines.push(tableRow([label('none'), '', '', '']))
  lines.push('')

  lines.push(`### ${label('results')}`, '')
  const byTrack = new Map()
  for (const row of rows) {
    const track = row.track || label('none')
    if (!byTrack.has(track)) byTrack.set(track, [])
    byTrack.get(track).push(row)
  }
  for (const [track, list] of byTrack) {
    lines.push(`#### ${track}`, '')
    for (const row of list) lines.push(`- ${row.title} (${row.stars ?? 0}/3, ${row.xp ?? 0} XP)`)
    lines.push('')
  }
  lines.push(label('todo'))
  lines.push('')

  lines.push(`### ${label('figures')}`, '')
  if (captures.length) {
    for (const capture of captures) {
      lines.push(`![${capture.name || capture.id}](capture:${capture.id})`)
    }
  } else {
    lines.push(label('none'))
  }
  lines.push('')

  lines.push(`## 4) ${label('conclusion')}`, '')
  lines.push(label('todo'))
  lines.push('')

  lines.push(`## 5) ${label('references')}`, '')
  lines.push(label('todo'))
  lines.push('')

  return lines.join('\n')
}

/**
 * Rewrites only the identification block of an existing report, so a student
 * who fixes their name or class after generating the report does not lose the
 * text they already wrote. Supports the IFMG block and the old `## Identificação`
 * heading used by reports generated before the template change.
 */
export function updateReportIdentification(content, {
  labels = {},
  studentName = '',
  groupName = '',
  date = new Date(),
} = {}) {
  const text = String(content || '')
  const day = date instanceof Date ? date.toISOString().slice(0, 10) : String(date)
  const block = identityLines({ labels, studentName, groupName, day }).join('\n')

  const start = text.indexOf(IDENTITY_START)
  if (start >= 0) {
    const end = text.indexOf(IDENTITY_END, start)
    if (end >= 0) {
      return text.slice(0, start) + block + text.slice(end + IDENTITY_END.length)
    }
  }

  // Legacy report: markdown identification table under its own heading.
  const label = (key) => String(labels[key] ?? key)
  const heading = `## ${label('identification')}`
  const headingAt = text.indexOf(heading)
  if (headingAt < 0) return text

  const next = text.indexOf('\n## ', headingAt + heading.length)
  const end = next < 0 ? text.length : next + 1
  const legacy = [
    heading,
    '',
    tableRow(['', '']),
    tableRow(['---', '---']),
    tableRow([label('student'), studentName]),
    tableRow([label('group'), groupName]),
    tableRow([label('date'), day]),
    '',
    '',
  ].join('\n')

  return text.slice(0, headingAt) + legacy + text.slice(end)
}
