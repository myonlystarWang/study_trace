import assert from 'node:assert/strict'
import test from 'node:test'

import {
  DEFAULT_FALLBACK_SUBJECTS,
  cleanTaskContent,
  splitInlineItems,
  isNoiseLine,
  matchSubjectHeader,
  parseHomeworkText
} from '../src/utils/homeworkParser.js'

test('cleans leading bullet points, numbers, and combinations', () => {
  assert.equal(cleanTaskContent('1. 计算 P29, 30 (打印的)'), '计算 P29, 30 (打印的)')
  assert.equal(cleanTaskContent('* 1. 计算'), '计算')
  assert.equal(cleanTaskContent('① 预习古诗'), '预习古诗')
  assert.equal(cleanTaskContent('（1） 订正错题'), '订正错题')
  assert.equal(cleanTaskContent('一、 背诵课文'), '背诵课文')
  assert.equal(cleanTaskContent('- 练习册P10'), '练习册P10')
  assert.equal(cleanTaskContent('• 词语听写'), '词语听写')
  // Keeps internal numbers intact
  assert.equal(cleanTaskContent('第5课词语 1+1'), '第5课词语 1+1')
  assert.equal(cleanTaskContent('P20 1, 3, 4, 5 (练习册)'), 'P20 1, 3, 4, 5 (练习册)')
})

test('intelligently splits inline sequential list items while preserving non-list items', () => {
  // Sequential list items on the same line
  assert.deepEqual(
    splitInlineItems('1. 发的作文题 2. 在发的四线三格上写自己字帖的内容。'),
    ['发的作文题', '在发的四线三格上写自己字帖的内容。']
  )
  assert.deepEqual(
    splitInlineItems('1、背诵课文 2、生字1+1 3、预习第5课'),
    ['背诵课文', '生字1+1', '预习第5课']
  )
  assert.deepEqual(
    splitInlineItems('① 背诵古诗 ② 默写生字'),
    ['背诵古诗', '默写生字']
  )

  // Non-list items must NOT be split
  assert.deepEqual(
    splitInlineItems('P20 1, 3, 4, 5  P21 10  P22 2  P23 5  P24 2 (练习册)'),
    ['P20 1, 3, 4, 5  P21 10  P22 2  P23 5  P24 2 (练习册)']
  )
  assert.deepEqual(
    splitInlineItems('第5课词语 1+1'),
    ['第5课词语 1+1']
  )
  assert.deepEqual(
    splitInlineItems('订练习册 P33~P43, P48~50'),
    ['订练习册 P33~P43, P48~50']
  )
})

test('identifies noise lines such as dates and notification greetings', () => {
  assert.equal(isNoiseLine('9月23日'), true)
  assert.equal(isNoiseLine('9月23日 (周三)'), true)
  assert.equal(isNoiseLine('2026-09-23 今日作业'), true)
  assert.equal(isNoiseLine('【今日作业】'), true)
  assert.equal(isNoiseLine('各位家长好：'), true)
  assert.equal(isNoiseLine('*   语文： 第5课词语 1+1'), false)
})

test('matches subject header with bullets, colons, brackets and standalone lines', () => {
  const m1 = matchSubjectHeader('*   语文： 第5课词语 1+1', DEFAULT_FALLBACK_SUBJECTS)
  assert.notEqual(m1, null)
  assert.equal(m1.subject.name, '语文')
  assert.equal(m1.remainder, '第5课词语 1+1')

  const m2 = matchSubjectHeader('*   数学：', DEFAULT_FALLBACK_SUBJECTS)
  assert.notEqual(m2, null)
  assert.equal(m2.subject.name, '数学')
  assert.equal(m2.remainder, '')

  const m3 = matchSubjectHeader('【英语】 1. 听写单词', DEFAULT_FALLBACK_SUBJECTS)
  assert.notEqual(m3, null)
  assert.equal(m3.subject.name, '英语')
  assert.equal(m3.remainder, '1. 听写单词')

  const m4 = matchSubjectHeader('1. 计算 P29, 30 (打印的)', DEFAULT_FALLBACK_SUBJECTS)
  assert.equal(m4, null)
})

test('parses full homework text with markdown bullets and subtasks', () => {
  const rawInput = `9月23日
*   语文： 第5课词语 1+1
*   数学：
    1. 计算 P29, 30 (打印的)
    2. 订周测卷 (活页纸上)
    3. 订练习册 P33~P43, P48~50
*   英语： 1. 发的作文题 2. 在发的四线三格上写自己字帖的内容。
*   生物： P20 1, 3, 4, 5  P21 10  P22 2  P23 5  P24 2 (练习册)`

  const result = parseHomeworkText(rawInput, DEFAULT_FALLBACK_SUBJECTS)
  assert.equal(result.groups.length, 4)
  assert.equal(result.unassigned.length, 0)

  const groupChinese = result.groups.find((g) => g.subject.name === '语文')
  assert.deepEqual(groupChinese.items, ['第5课词语 1+1'])

  const groupMath = result.groups.find((g) => g.subject.name === '数学')
  assert.deepEqual(groupMath.items, [
    '计算 P29, 30 (打印的)',
    '订周测卷 (活页纸上)',
    '订练习册 P33~P43, P48~50'
  ])

  const groupEnglish = result.groups.find((g) => g.subject.name === '英语')
  assert.deepEqual(groupEnglish.items, [
    '发的作文题',
    '在发的四线三格上写自己字帖的内容。'
  ])

  const groupBio = result.groups.find((g) => g.subject.name === '生物')
  assert.deepEqual(groupBio.items, [
    'P20 1, 3, 4, 5  P21 10  P22 2  P23 5  P24 2 (练习册)'
  ])
})
