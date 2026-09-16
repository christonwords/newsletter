export async function loadCollection(url, fetchImpl = fetch) {
  const response = await fetchImpl(url, { cache: "no-store" });
  if (!response.ok) throw new Error(`collection request failed: ${response.status}`);
  const items = await response.json();
  if (!Array.isArray(items)) throw new Error("collection data is invalid");
  return items;
}

const image = (item) => {
  const node = document.createElement("img");
  node.src = item.image;
  node.alt = item.title;
  node.loading = "lazy";
  node.decoding = "async";
  return node;
};

export function createDrumkitItem(item, className = "drumkit-item") {
  const link = document.createElement("a");
  link.className = className;
  link.href = item.url;
  link.target = "_blank";
  link.rel = "noreferrer";
  link.append(image(item));

  const label = document.createElement("span");
  label.textContent = item.title;
  link.append(label);
  return link;
}

export function createVstItem(item, className = "vst-item") {
  const figure = document.createElement("figure");
  figure.className = className;
  figure.append(image(item));

  const caption = document.createElement("figcaption");
  caption.textContent = item.title;
  figure.append(caption);
  return figure;
}

export async function renderDrumkits(container, { limit = Infinity } = {}) {
  const items = await loadCollection("/data/drumkits.json");
  container.replaceChildren(...items.slice(0, limit).map((item) => createDrumkitItem(item)));
  return items;
}

export async function renderVsts(container, { limit = Infinity } = {}) {
  const items = await loadCollection("/data/vsts.json");
  container.replaceChildren(...items.slice(0, limit).map((item) => createVstItem(item)));
  return items;
}
