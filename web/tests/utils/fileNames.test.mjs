// Unit tests for file-name helpers shared by tabs and the Python worker.
import test from 'node:test'
import assert from 'node:assert/strict'
import {
  fileExtension, isPythonFile, normalizeFileName, safeFileName,
} from '../../src/utils/fileNames.js'

test('fileExtension returns the lower-case extension', () => {
  assert.equal(fileExtension('script.py'), '.py')
  assert.equal(fileExtension('DATA.CSV'), '.csv')
  assert.equal(fileExtension('notes.v2.json'), '.json')
  assert.equal(fileExtension('noext'), '')
  assert.equal(fileExtension(''), '')
})

test('isPythonFile accepts only .py (case-insensitive)', () => {
  assert.equal(isPythonFile('a.py'), true)
  assert.equal(isPythonFile('A.PY'), true)
  assert.equal(isPythonFile('a.json'), false)
  assert.equal(isPythonFile('a'), false)
})

test('normalizeFileName keeps helper extensions and defaults to .py', () => {
  assert.equal(normalizeFileName('helper.py'), 'helper.py')
  assert.equal(normalizeFileName('data.json'), 'data.json')
  assert.equal(normalizeFileName('report.csv'), 'report.csv')
  assert.equal(normalizeFileName('README'), 'README.py')
  assert.equal(normalizeFileName('dir/notes.txt'), 'notes.txt')
  assert.equal(normalizeFileName(''), 'user_script.py')
})

test('safeFileName sanitizes paths and keeps helper extensions', () => {
  assert.equal(safeFileName('my module.py'), 'my module.py')
  assert.equal(safeFileName('data.json'), 'data.json')
  assert.equal(safeFileName('dir/values.csv'), 'values.csv')
  assert.equal(safeFileName('a:b?.txt'), 'a_b_.txt')
  assert.equal(safeFileName('noext'), 'noext.py')
  assert.equal(safeFileName(''), 'user_script.py')
})
