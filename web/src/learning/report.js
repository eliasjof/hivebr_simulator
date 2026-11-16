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

export const RUBRIC_DEFAULTS = {
  // Words that are not part of the skeleton: tables, headings, images and
  // comments are ignored, so the student must write real prose.
  minWords: 300,
  sections: 7,
}

/** Words in prose lines only (no headings, tables, images, comments). */
export function proseWordCount(text) {
  const prose = String(text || '')
    .split(/\r?\n/)
    .filter((line) => {
      const trimmed = line.trim()
      if (!trimmed) return false
      if (trimmed.startsWith('#')) return false
      if (trimmed.startsWith('|')) return false
      if (trimmed.startsWith('![')) return false
      if (trimmed.startsWith('<!--')) return false
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

/**
 * Builds the final report skeleton.
 *
 * labels: { title, identification, student, group, date, summary, activities,
 *           results, figures, difficulties, conclusion, todo, none,
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
  lines.push('', `# ${label('title')}`, '')

  lines.push(`## ${label('identification')}`, '')
  lines.push(tableRow(['', '']))
  lines.push(tableRow(['---', '---']))
  lines.push(tableRow([label('student'), studentName]))
  lines.push(tableRow([label('group'), groupName]))
  lines.push(tableRow([label('date'), day]))
  lines.push('')

  lines.push(`## ${label('summary')}`, '')
  lines.push(label('todo'))
  lines.push('')

  lines.push(`## ${label('activities')}`, '')
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

  lines.push(`## ${label('results')}`, '')
  const byTrack = new Map()
  for (const row of rows) {
    const track = row.track || label('none')
    if (!byTrack.has(track)) byTrack.set(track, [])
    byTrack.get(track).push(row)
  }
  for (const [track, list] of byTrack) {
    lines.push(`### ${track}`, '')
    for (const row of list) lines.push(`- ${row.title} (${row.stars ?? 0}/3, ${row.xp ?? 0} XP)`)
    lines.push('')
  }
  lines.push(label('todo'))
  lines.push('')

  lines.push(`## ${label('figures')}`, '')
  if (captures.length) {
    for (const capture of captures) {
      lines.push(`![${capture.name || capture.id}](capture:${capture.id})`)
    }
  } else {
    lines.push(label('none'))
  }
  lines.push('')

  lines.push(`## ${label('difficulties')}`, '')
  lines.push(label('todo'))
  lines.push('')

  lines.push(`## ${label('conclusion')}`, '')
  lines.push(label('todo'))
  lines.push('')

  return lines.join('\n')
}

/**
 * Rewrites only the identification table of an existing report, so a student
 * who fixes their name or class after generating the report does not lose the
 * text they already wrote. Returns the content unchanged when the heading is
 * missing.
 */
export function updateReportIdentification(content, {
  labels = {},
  studentName = '',
  groupName = '',
  date = new Date(),
} = {}) {
  const text = String(content || '')
  const label = (key) => String(labels[key] ?? key)
  const heading = `## ${label('identification')}`
  const start = text.indexOf(heading)
  if (start < 0) return text

  const next = text.indexOf('\n## ', start + heading.length)
  const end = next < 0 ? text.length : next + 1
  const day = date instanceof Date ? date.toISOString().slice(0, 10) : String(date)
  const block = [
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

  return text.slice(0, start) + block + text.slice(end)
}
