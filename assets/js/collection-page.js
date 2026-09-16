import { renderDrumkits, renderVsts } from "./collections.js";

const init = async () => {
  const grid = document.querySelector("#collection-grid");
  try {
    if (document.body.dataset.collection === "drumkits") await renderDrumkits(grid);
    else await renderVsts(grid);
  } catch {
    grid.textContent = "this collection could not load.";
  }
};

init();
