import json
import re
import subprocess
import sys

# find char codes they are matched with Python's (?u)\\w

match = re.compile(r'(?u)\w')
begin = -1

ranges = []
singles = []

for i in range(65536):
    # 0xd800-0xdfff is surrogate pair area. skip this.
    if not match.match(chr(i)) and not (0xd800 <= i <= 0xdfff):
        if begin == -1:
            begin = i
    elif begin != -1:
        if begin + 1 == i:
            singles.append(begin)
        else:
            ranges.append((begin, i - 1))
        begin = -1


# fold json within almost 80 chars per line
def fold(jsonData, splitter):
    code = json.dumps(jsonData)
    lines = []
    while True:
        if len(code) < 71:
            lines.append('        ' + code)
            break
        index = code.index(splitter, 70)
        lines.append('        ' + code[:index + len(splitter)])
        code = code[index + len(splitter):]
    lines[0] = lines[0][8:]
    return '\n'.join(lines)


# JavaScript code
js_src = '''
var splitChars = (function() {
    var result = {};
    var singles = %s;
    var i, j, start, end;
    for (i = 0; i < singles.length; i++) {
        result[singles[i]] = true;
    }
    var ranges = %s;
    for (i = 0; i < ranges.length; i++) {
        start = ranges[i][0];
        end = ranges[i][1];
        for (j = start; j <= end; j++) {
            result[j] = true;
        }
    }
    return result;
})();

function splitQuery(query) {
    var result = [];
    var start = -1;
    for (var i = 0; i < query.length; i++) {
        if (splitChars[query.charCodeAt(i)]) {
            if (start !== -1) {
                result.push(query.slice(start, i));
                start = -1;
            }
        } else if (start === -1) {
            start = i;
        }
    }
    if (start !== -1) {
        result.push(query.slice(start));
    }
    return result;
}
''' % (fold(singles, ','), fold(ranges, '],'))

js_test_src = '''
// This is regression test for https://github.com/sphinx-doc/sphinx/issues/3150
// generated by compat_regexp_generator.py
// it needs node.js for testing
var assert = require('assert');

%s

console.log("test splitting English words")
assert.deepEqual(['Hello', 'World'], splitQuery('   Hello    World   '));
console.log('   ... ok\\n')

console.log("test splitting special characters")
assert.deepEqual(['Pin', 'Code'], splitQuery('Pin-Code'));
console.log('   ... ok\\n')

console.log("test splitting Chinese characters")
assert.deepEqual(['Hello', 'from', '中国', '上海'], splitQuery('Hello from 中国 上海'));
console.log('   ... ok\\n')

console.log("test splitting Emoji(surrogate pair) characters. It should keep emojis.")
assert.deepEqual(['😁😁'], splitQuery('😁😁'));
console.log('   ... ok\\n')

console.log("test splitting umlauts. It should keep umlauts.")
assert.deepEqual(
    ['Löschen', 'Prüfung', 'Abändern', 'ærlig', 'spørsmål'],
    splitQuery('Löschen Prüfung Abändern ærlig spørsmål'));
console.log('   ... ok\\n')

''' % js_src

python_src = '''\
"""Provides Python compatible word splitter to JavaScript

DO NOT EDIT. This is generated by utils/jssplitter_generator.py
"""

splitter_code = """
%s
"""
''' % js_src

with open('../sphinx/search/jssplitter.py', 'w') as f:
    f.write(python_src)

with open('./regression_test.js', 'w') as f:
    f.write(js_test_src)

print("starting test...")
result = subprocess.call(['node', './regression_test.js'])
sys.exit(result)
