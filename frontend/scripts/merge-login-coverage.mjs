import { readFileSync, statSync, writeFileSync } from 'node:fs'
import { relative, resolve, sep } from 'node:path'

const frontend = process.cwd()
const unitCoveredHelpers = new Set(['src/utils/loginValidation.ts', 'src/utils/loginErrors.ts'])

function readReport(file) {
  const records = new Map()
  for (const block of readFileSync(file, 'utf8').trim().split(/^end_of_record\r?$/m)) {
    const lines = block.trim().split(/\r?\n/)
    if (!lines[0]) continue
    const index = lines.findIndex((line) => line.startsWith('SF:'))
    if (index < 0) throw new Error('Missing source record in ' + file)
    const sourcePath = resolve(frontend, lines[index].slice(3))
    const source = relative(frontend, sourcePath).split(sep).join('/')
    if (!source.startsWith('src/') || !statSync(sourcePath).isFile() || records.has(source)) {
      throw new Error('Invalid or duplicate coverage path: ' + source)
    }
    lines[index] = 'SF:' + source
    records.set(source, lines)
  }
  if (!records.size) throw new Error('Empty coverage report: ' + file)
  return records
}

const unit = readReport('coverage/unit/lcov.info')
const components = readReport('coverage/components/lcov.info')
for (const source of ['src/auth/AuthContext.tsx', 'src/pages/LoginPage.tsx']) {
  if (!components.has(source)) throw new Error('Missing login component coverage: ' + source)
}
for (const source of unitCoveredHelpers) {
  if (!unit.has(source) || components.has(source)) {
    throw new Error('Invalid unit coverage ownership: ' + source)
  }
}

for (const [source, lines] of components) {
  const placeholder = unit.get(source)
  if (!placeholder?.includes('LH:0') ||
      !placeholder.includes('BRH:0') || !placeholder.includes('FNH:0') ||
      placeholder.some((line) => /^DA:\d+,[1-9]\d*/.test(line) || /^BRDA:[^,]+,[^,]+,[^,]+,[1-9]\d*/.test(line) || /^FNDA:[1-9]\d*/.test(line))) {
    throw new Error('Unexpected overlapping or missing coverage: ' + source)
  }
  unit.set(source, lines)
}

const lcov = [...unit.values()].map((lines) => [...lines, 'end_of_record'].join('\n')).join('\n')
writeFileSync('coverage/lcov.info', lcov + '\n')
console.log('Merged LCOV with ' + unit.size + ' source files and ' + components.size + ' Vitest modules.')
