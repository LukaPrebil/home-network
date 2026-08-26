/*
 * Extract the TIGO optimizer module map from the TIGO EI layout page.
 *
 * Paste into the browser devtools console with the equipment list open. Builds
 * the MODULES string for vault_tigo_modules and copies it to the clipboard.
 * Prints validation counts only, never the serials, so the summary can be
 * shared without disclosing hardware identifiers.
 *
 * Cards carry two .equipment-label spans: the panel position lives in
 * .title-row, the barcode serial in the trailing .type-row. Selecting on the
 * class alone conflates them.
 */
(() => {
  const cards = [...document.querySelectorAll('.title-row')]
    .map((row) => row.parentElement)
    .filter((card) => /pv module/i.test(card.querySelector('.equipment-badge')?.textContent || ''));

  const rows = cards.map((card) => {
    const position = card.querySelector('.title-row .equipment-label')?.textContent.trim() || '';
    const labels = [...card.querySelectorAll('.type-row .equipment-label')];
    const serial = labels.at(-1)?.textContent.trim() || '';
    return { position, serial };
  });

  const parsed = [];
  const problems = [];

  for (const { position, serial } of rows) {
    const m = position.match(/^([A-Za-z]+)(\d+)$/);
    if (!m) { problems.push(`unparseable position: ${position || '(empty)'}`); continue; }
    if (!/^[0-9A-Z]-[0-9A-Z]{7}$/.test(serial)) { problems.push(`bad serial format at ${position}`); continue; }
    parsed.push({ string: m[1].toUpperCase(), index: Number(m[2]), serial });
  }

  parsed.sort((a, b) => a.string.localeCompare(b.string) || a.index - b.index);

  const dupSerial = new Set();
  const dupName = new Set();
  const seenSerial = new Set();
  const seenName = new Set();
  for (const p of parsed) {
    const name = p.string + p.index;
    if (seenSerial.has(p.serial)) dupSerial.add(name);
    if (seenName.has(name)) dupName.add(name);
    seenSerial.add(p.serial);
    seenName.add(name);
  }

  const perString = parsed.reduce((acc, p) => ({ ...acc, [p.string]: (acc[p.string] || 0) + 1 }), {});

  /* NAME must not repeat the string letter: the bridge composes the entity
     name as STRING + NAME, so A:1: yields A1 while A:A1: would yield AA1. */
  const modules = parsed.map((p) => `${p.string}:${p.index}:${p.serial}`).join(', ');

  console.log('--- paste this summary back, it contains no serials ---');
  console.log('cards found:      ', cards.length);
  console.log('parsed ok:        ', parsed.length);
  console.log('per string:       ', JSON.stringify(perString));
  console.log('duplicate serials:', dupSerial.size ? [...dupSerial] : 'none');
  console.log('duplicate names:  ', dupName.size ? [...dupName] : 'none');
  console.log('problems:         ', problems.length ? problems : 'none');
  console.log('missing indices:  ', JSON.stringify(
    Object.fromEntries(Object.keys(perString).map((s) => {
      const have = new Set(parsed.filter((p) => p.string === s).map((p) => p.index));
      return [s, [...Array(15).keys()].map((i) => i + 1).filter((i) => !have.has(i))];
    })),
  ));

  try { copy(modules); console.log('\nMODULES string copied to clipboard.'); }
  catch { console.log('\nclipboard unavailable; the string is the return value below.'); }

  return modules;
})();
