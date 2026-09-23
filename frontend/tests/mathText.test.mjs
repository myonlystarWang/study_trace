import assert from 'node:assert/strict'
import test from 'node:test'

import { buildSegments, normalizeMathSource, renderMathHtml } from '../src/utils/mathText.js'

const mathValues = (text) => buildSegments(text)
  .filter((part) => part.type === 'math')
  .map((part) => part.value)

test('renders multi-symbol and parenthesized exponent bases from OCR', () => {
  assert.deepEqual(
    mathValues('m^2 + (a+b+cd)m + (cd)^2027'),
    ['m^{2}', '(cd)^{2027}'],
  )
  assert.deepEqual(mathValues('（cd）^2027'), ['(cd)^{2027}'])
})

test('normalizes Unicode superscripts from keyboard and OCR output', () => {
  assert.equal(normalizeMathSource('若 m² = 4，且 x⁻² = 1'), '若 m^2 = 4，且 x^-2 = 1')
  assert.deepEqual(mathValues('m² + (cd)²'), ['m^{2}', '(cd)^{2}'])
})

test('keeps elementary expressions inside a parenthesized exponent', () => {
  assert.deepEqual(mathValues('x^(2n-1) + y^{n+1}'), ['x^{2n-1}', 'y^{n+1}'])
})

test('keeps the synchronous fallback readable while KaTeX loads', () => {
  const rendered = renderMathHtml('(cd)^2027')
  assert.equal(rendered.html, '(cd)^2027')
  assert.equal(rendered.hasMath, true)
})
