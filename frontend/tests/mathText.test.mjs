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
  assert.deepEqual(
    mathValues('(-\\frac{3}{2})^2\\times8'),
    ['(-\\frac{3}{2})^{2}', '\\times'],
  )
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

test('renders subscripts and fractions with nested subscripts', () => {
  const text = '已知a_{1}=3,a_{2}=\\frac{1}{1-a_{1}},a_{3}=\\frac{1}{1-a_{2}},a_{4}=\\frac{1}{1-a_{3}},…，依此类推，则a_{2027}等于____'
  assert.deepEqual(
    mathValues(text),
    [
      'a_{1}',
      'a_{2}',
      '\\frac{1}{1-a_{1}}',
      'a_{3}',
      '\\frac{1}{1-a_{2}}',
      'a_{4}',
      '\\frac{1}{1-a_{3}}',
      'a_{2027}',
    ],
  )
})

test('supports bare subscripts, combined sub/superscripts, and unicode subscripts', () => {
  assert.deepEqual(mathValues('a_1 + a_2 + x_i'), ['a_{1}', 'a_{2}', 'x_{i}'])
  assert.deepEqual(mathValues('a_{1}^2 + x_1^2'), ['a_{1}^{2}', 'x_{1}^{2}'])
  assert.equal(normalizeMathSource('已知 a₁ = 3，且 a₂ = 1'), '已知 a_{1} = 3，且 a_{2} = 1')
  assert.deepEqual(mathValues('已知 a₁ = 3，且 a₂ = 1'), ['a_{1}', 'a_{2}'])
})

test('renders nested fraction synchronous fallback and upgrades with KaTeX', async () => {
  const rendered = renderMathHtml('a_{2}=\\frac{1}{1-a_{1}}')
  assert.equal(rendered.html, 'a_2=(1)/(1-a_1)')
  assert.equal(rendered.hasMath, true)
  assert.ok(rendered.upgrade)
  const upgraded = await rendered.upgrade()
  assert.ok(upgraded.includes('katex'))
  assert.ok(!upgraded.includes('math-fallback'))
})

