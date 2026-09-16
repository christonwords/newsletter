import assert from "node:assert/strict";
import test from "node:test";

import { createDisclosureController } from "../../assets/js/home.js";

test("opens one index panel at a time", () => {
  const changes = [];
  const controller = createDisclosureController({
    ids: ["beats", "drumkits", "vsts"],
    onChange: (state) => changes.push(state)
  });

  controller.open("beats");
  controller.open("drumkits");

  assert.equal(controller.current(), "drumkits");
  assert.deepEqual(changes.at(-1), { openId: "drumkits" });
});

test("clicking the open panel closes it", () => {
  const controller = createDisclosureController({ ids: ["beats"] });
  controller.toggle("beats");
  controller.toggle("beats");
  assert.equal(controller.current(), "");
});

test("ignores unknown panel ids", () => {
  const controller = createDisclosureController({ ids: ["beats"] });
  controller.open("contact");
  assert.equal(controller.current(), "");
});
