// Unit tests for the YAML config editor find/replace helpers.
import test from 'node:test'
import assert from 'node:assert/strict'
import {
  findMatches, nextMatchIndex, replaceAllMatches, escapeRegExp,
} from '../../src/utils/findReplace.js'

test('findMatches returns every occurrence, case-insensitive by default', () => {
  assert.deepEqual(findMatches('Robot robot ROBOT', 'robot'), [0, 6, 12])
  assert.deepEqual(findMatches('Robot robot', 'robot', true), [6])
  assert.deepEqual(findMatches('abc', ''), [])
  assert.deepEqual(findMatches('abc', 'z'), [])
})

test('nextMatchIndex searches forward from the end of the selection and wraps', () => {
  const m = [0, 6, 12]
  assert.equal(nextMatchIndex(m, { start: 0, end: 0, dir: 1 }), 0)
  assert.equal(nextMatchIndex(m, { start: 7, end: 12, dir: 1 }), 12)
  assert.equal(nextMatchIndex(m, { start: 13, end: 15, dir: 1 }), 0)
  assert.equal(nextMatchIndex(m, { start: 6, end: 11, dir: -1 }), 0)
  assert.equal(nextMatchIndex(m, { start: 0, end: 0, dir: -1 }), 12)
  assert.equal(nextMatchIndex([], { dir: 1 }), -1)
})

test('replaceAllMatches replaces every match and counts them', () => {
  assert.deepEqual(
    replaceAllMatches('a-b-A-b', 'b', 'B'),
    { text: 'a-B-A-B', count: 2 },
  )
  assert.deepEqual(
    replaceAllMatches('a-b-A-b', 'b', 'B', true),
    { text: 'a-B-A-B', count: 2 },
  )
  assert.deepEqual(
    replaceAllMatches('a-b-A-b', 'A', 'X', true),
    { text: 'a-b-X-b', count: 1 },
  )
  assert.deepEqual(replaceAllMatches('abc', 'z', 'x'), { text: 'abc', count: 0 })
})

test('replaceAllMatches treats regex metacharacters literally', () => {
  assert.deepEqual(
    replaceAllMatches('a.b a.b', '.', '$'),
    { text: 'a$b a$b', count: 2 },
  )
  assert.equal(escapeRegExp('a.b*c'), 'a\\.b\\*c')
})
