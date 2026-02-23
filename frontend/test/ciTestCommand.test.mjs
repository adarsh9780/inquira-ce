import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

test("frontend npm test script does not require forwarded --run arg", () => {
  const __filename = fileURLToPath(import.meta.url);
  const __dirname = path.dirname(__filename);
  const pkgPath = path.resolve(__dirname, "..", "package.json");
  const pkg = JSON.parse(fs.readFileSync(pkgPath, "utf8"));
  const testScript = pkg?.scripts?.test ?? "";

  assert.equal(typeof testScript, "string");
  assert.match(testScript, /node\s+--test/);
  assert.doesNotMatch(testScript, /\s--run(\s|$)/);
});
