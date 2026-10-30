#!/usr/bin/env node
// Copy the study crawler's instrumentation library into ./vendor/crawl/ so that ConsentCheck can be released and run
// outside the study checkout. Run inside the checkout:  node tools/vendor_lib.js [--dest DIR]
// Copies crawl/lib/{rawcdp,instrument,inject,vendors,probes}.js and the two data files they read
// (crawl/vendor_endpoints.json, crawl/cmp_signatures.json), keeping their relative layout.
const fs = require('fs');
const path = require('path');
const E = require('../lib/env');
const i = process.argv.indexOf('--dest');
const dest = path.resolve(i > 0 ? process.argv[i + 1] : path.join(E.HERE, 'vendor', 'crawl'));
const src = path.join(E.STUDY, 'crawl');
fs.mkdirSync(path.join(dest, 'lib'), { recursive: true });
const files = ['lib/rawcdp.js', 'lib/instrument.js', 'lib/inject.js', 'lib/vendors.js', 'lib/probes.js', 'vendor_endpoints.json', 'cmp_signatures.json'];
for (const f of files) fs.copyFileSync(path.join(src, f), path.join(dest, f));
fs.writeFileSync(path.join(dest, 'SOURCE.txt'), `Copied from the study checkout (crawl/) on ${new Date().toISOString()} by tools/vendor_lib.js.\nDo not edit here; change crawl/lib in the study and copy again.\n`);
console.log(`copied ${files.length} files to ${dest}; set CONSENTCHECK_CRAWL_LIB=${path.join(dest, 'lib')} or keep it at ./vendor/crawl/lib`);
