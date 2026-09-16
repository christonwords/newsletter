import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import test from "node:test";

const read = (path) => readFileSync(new URL(`../../${path}`, import.meta.url), "utf8");

test("homepage is the five-part living index", () => {
  const html = read("index.html");
  assert.match(html, /<h1[^>]*>christon<\/h1>/);
  assert.equal((html.match(/data-index-target=/g) || []).length, 5);
  assert.match(html, /assets\/css\/base\.css/);
  assert.match(html, /assets\/js\/home\.js/);
});

test("beat archive has search and one shared audio player", () => {
  const html = read("beats/index.html");
  assert.match(html, /id="beat-search"/);
  assert.equal((html.match(/<audio/g) || []).length, 1);
  assert.match(html, /assets\/js\/beats\.js/);
});

test("dedicated collection routes exist", () => {
  assert.equal(existsSync(new URL("../../drumkits/index.html", import.meta.url)), true);
  assert.equal(existsSync(new URL("../../vsts/index.html", import.meta.url)), true);
});

test("collection data includes every current asset", () => {
  const drumkits = JSON.parse(read("data/drumkits.json"));
  const vsts = JSON.parse(read("data/vsts.json"));
  assert.equal(drumkits.length, 5);
  assert.equal(vsts.length, 18);
  assert.equal(drumkits.at(-1).title, "beauty is swxg drumkit");
});

test("a2v has an explicit route back to the main index", () => {
  const html = read("a2v/index.html");
  assert.match(html, /class="back-to-index" href="\.\.\/">back to christon<\/a>/);
});
