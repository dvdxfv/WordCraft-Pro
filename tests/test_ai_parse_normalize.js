'use strict';
// Unit tests for _sanitizeAIParseRules normalization logic.
// Mirrors the function from web/index.html — keep in sync when the function changes.

function _sanitizeAIParseRules(o) {
  if (!o || typeof o !== 'object' || Array.isArray(o)) return {};
  if ((o.lineSpacingMode == null || o.lineSpacingValue == null) && o.lineHeight != null) {
    const lh = parseFloat(o.lineHeight);
    if (isFinite(lh)) {
      if (lh >= 1.0 && lh <= 5.0) {
        o.lineSpacingMode = 'multiple';
        o.lineSpacingValue = lh;
      } else if (lh >= 6 && lh <= 100) {
        o.lineSpacingMode = 'exact';
        o.lineSpacingValue = lh;
      }
    }
  }
  const lh = parseFloat(o.lineHeight);
  if (!isFinite(lh) || lh < 1.0 || lh > 5.0) o.lineHeight = null;
  if (o.lineSpacingMode == null && o.lineSpacingValue != null) {
    const sv = parseFloat(o.lineSpacingValue);
    if (isFinite(sv)) {
      if (sv >= 1.0 && sv <= 5.0) o.lineSpacingMode = 'multiple';
      else if (sv >= 6 && sv <= 100) o.lineSpacingMode = 'exact';
    }
  }
  if (o.lineSpacingMode === 'multiple') {
    const sv = parseFloat(o.lineSpacingValue);
    if (!isFinite(sv) || sv < 1.0 || sv > 5.0) o.lineSpacingValue = null;
  } else if (o.lineSpacingMode === 'exact') {
    const sv = parseFloat(o.lineSpacingValue);
    if (!isFinite(sv) || sv < 6 || sv > 100) o.lineSpacingValue = null;
  } else {
    o.lineSpacingMode = null;
    o.lineSpacingValue = null;
  }
  return o;
}

let passed = 0, failed = 0;
function check(desc, actual, expected) {
  if (actual === expected) {
    console.log(`  PASS  ${desc}`);
    passed++;
  } else {
    console.error(`  FAIL  ${desc}: expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
    failed++;
  }
}

// lineHeight: 1.5 → multiple
{
  const r = _sanitizeAIParseRules({ lineHeight: 1.5 });
  check('lineHeight=1.5 → mode=multiple', r.lineSpacingMode, 'multiple');
  check('lineHeight=1.5 → value=1.5', r.lineSpacingValue, 1.5);
  check('lineHeight=1.5 → lineHeight preserved (display)', r.lineHeight, 1.5);
}

// lineHeight: 20 → exact (was the bug: 20 > 5 got cleared before mapping)
{
  const r = _sanitizeAIParseRules({ lineHeight: 20 });
  check('lineHeight=20 → mode=exact', r.lineSpacingMode, 'exact');
  check('lineHeight=20 → value=20', r.lineSpacingValue, 20);
  check('lineHeight=20 → lineHeight cleared (out of display range)', r.lineHeight, null);
}

// lineSpacingValue=1.5, mode absent → infer multiple
{
  const r = _sanitizeAIParseRules({ lineSpacingValue: 1.5 });
  check('lineSpacingValue=1.5 no mode → mode=multiple', r.lineSpacingMode, 'multiple');
  check('lineSpacingValue=1.5 no mode → value=1.5', r.lineSpacingValue, 1.5);
}

// lineSpacingValue=20, mode absent → infer exact
{
  const r = _sanitizeAIParseRules({ lineSpacingValue: 20 });
  check('lineSpacingValue=20 no mode → mode=exact', r.lineSpacingMode, 'exact');
  check('lineSpacingValue=20 no mode → value=20', r.lineSpacingValue, 20);
}

// Explicit mode+value should not be overridden by lineHeight
{
  const r = _sanitizeAIParseRules({ lineHeight: 1.5, lineSpacingMode: 'exact', lineSpacingValue: 20 });
  check('explicit mode=exact not overridden', r.lineSpacingMode, 'exact');
  check('explicit value=20 not overridden', r.lineSpacingValue, 20);
}

// Invalid mode string → both nulled
{
  const r = _sanitizeAIParseRules({ lineSpacingMode: 'invalid', lineSpacingValue: 1.5 });
  check('invalid mode → mode=null', r.lineSpacingMode, null);
  check('invalid mode → value=null', r.lineSpacingValue, null);
}

// lineHeight out of both ranges → no mapping, both null
{
  const r = _sanitizeAIParseRules({ lineHeight: 200 });
  check('lineHeight=200 (out of range) → mode=null', r.lineSpacingMode, null);
  check('lineHeight=200 (out of range) → value=null', r.lineSpacingValue, null);
  check('lineHeight=200 → lineHeight cleared', r.lineHeight, null);
}

console.log(`\n${passed} passed, ${failed} failed`);
if (failed > 0) process.exit(1);
