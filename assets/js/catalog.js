const toText = (value) => String(value ?? "").trim();

const normalizeBeat = (beat, order) => ({
  id: toText(beat.id || beat.slug || `beat-${order}`),
  slug: toText(beat.slug),
  title: toText(beat.title || beat.slug || "untitled").toLowerCase(),
  bpm: toText(beat.bpm),
  key: toText(beat.key).toLowerCase(),
  preview: toText(beat.preview),
  duration: Number(beat.duration || 30),
  order: Number.isInteger(beat.order) ? beat.order : order,
  peaks: Array.isArray(beat.peaks) ? beat.peaks.map(Number) : []
});

const withBaseUrl = (catalog, baseUrl) => ({
  ...catalog,
  beats: catalog.beats.map((beat) => ({
    ...beat,
    preview: /^(?:https?:)?\/\//.test(beat.preview) || beat.preview.startsWith("/")
      ? beat.preview
      : `${baseUrl}${beat.preview}`
  }))
});

export function normalizeCatalog(payload) {
  if (Array.isArray(payload)) {
    return {
      schemaVersion: 0,
      revision: "legacy",
      publishedAt: "",
      beats: payload.map(normalizeBeat)
    };
  }

  if (!payload || payload.schemaVersion !== 1 || !Array.isArray(payload.beats)) {
    throw new Error("unsupported catalog schema");
  }

  return {
    schemaVersion: 1,
    revision: toText(payload.revision),
    publishedAt: toText(payload.publishedAt),
    beats: payload.beats.map(normalizeBeat).sort((a, b) => a.order - b.order)
  };
}

export async function loadBeatCatalog(baseUrl = "/beats/", fetchImpl = fetch) {
  for (const filename of ["catalog.json", "beats.json"]) {
    const response = await fetchImpl(`${baseUrl}${filename}`, { cache: "no-store" });
    if (response.ok) return withBaseUrl(normalizeCatalog(await response.json()), baseUrl);
    if (response.status !== 404) throw new Error(`catalog request failed: ${response.status}`);
  }

  throw new Error("beat catalog is unavailable");
}

export function formatBeatMeta(beat) {
  return [beat.bpm ? `${beat.bpm} bpm` : "", beat.key].filter(Boolean).join(" / ") || "preview";
}
