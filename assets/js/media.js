export function createMediaController({ previewAudio, backgroundAudio = null, onChange = () => {} }) {
  let activeBeat = null;
  let activePreview = "";

  const state = () => ({
    activeBeat,
    beatPlaying: !previewAudio.paused,
    backgroundPlaying: Boolean(backgroundAudio && !backgroundAudio.paused)
  });

  const emit = () => onChange(state());

  if (typeof previewAudio.addEventListener === "function") {
    previewAudio.addEventListener("ended", () => {
      activeBeat = null;
      emit();
    });
  }

  return {
    async toggleBeat(beat) {
      if (backgroundAudio) backgroundAudio.pause();

      if (activeBeat === beat.id && !previewAudio.paused) {
        previewAudio.pause();
      } else {
        if (activePreview !== beat.preview) {
          previewAudio.src = beat.preview;
          previewAudio.currentTime = 0;
          activePreview = beat.preview;
        }
        activeBeat = beat.id;
        await previewAudio.play();
      }

      emit();
    },

    async toggleBackground() {
      if (!backgroundAudio) return;
      previewAudio.pause();
      activeBeat = null;
      if (backgroundAudio.paused) await backgroundAudio.play();
      else backgroundAudio.pause();
      emit();
    },

    pauseAll() {
      previewAudio.pause();
      if (backgroundAudio) backgroundAudio.pause();
      activeBeat = null;
      emit();
    },

    getState: state
  };
}
