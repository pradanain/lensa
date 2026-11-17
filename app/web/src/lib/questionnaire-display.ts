import type {Question} from './api'
import {number} from './utils'

export function questionNumber(field: Pick<Question,'question_text'>) {
  return field.question_text.match(/^\s*(\d+)(?=\s*[.a-zA-Z])/u)?.[1] || null
}

export function answerText(field: Question) {
  if(field.question_id === 'b1_p.nama_sls' && field.reference_label) return field.reference_label
  if(field.label_status === 'TEMPLATE_MULTI' && field.label) return field.label
  const quantity = field.converter === 'decimal' || field.display_format === 'number'
  if(quantity && (!field.parse_status || field.parse_status === 'VALID')) {
    return number(field.numeric_value ?? field.value)
  }
  const labelHasCode = field.value && field.label && (field.label === field.value || field.label.startsWith(field.value + '.') || field.label.startsWith(field.value + ' '))
  return field.label && field.value && !labelHasCode ? field.value + ' · ' + field.label : field.label || field.value || '—'
}
