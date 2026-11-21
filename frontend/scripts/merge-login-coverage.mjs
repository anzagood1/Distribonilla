import { readFileSync, statSync, writeFileSync } from 'node:fs'
import { relative, resolve, sep } from 'node:path'

const frontend = process.cwd()
const expectedComponents = new Set([
  'src/auth/AuthContext.tsx',
  'src/components/UserMenu.tsx',
  'src/pages/LoginPage.tsx',
])

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
if (components.size !== expectedComponents.size) throw new Error('Missing login component coverage')

for (const [source, lines] of components) {
  const placeholder = unit.get(source)
  if (!expectedComponents.has(source) || !placeholder?.includes('LH:0') ||
      !placeholder.includes('BRH:0') || !placeholder.includes('FNH:0') ||
      !lines.some((line) => /^LH:[1-9]\d*$/.test(line))) {
    throw new Error('Unexpected overlapping or missing coverage: ' + source)
  }
  unit.set(source, lines)
}

const lcov = [...unit.values()].map((lines) => [...lines, 'end_of_record'].join('\n')).join('\n')
writeFileSync('coverage/lcov.info', lcov + '\n')
console.log('Merged LCOV with ' + unit.size + ' source files and both login components.')
