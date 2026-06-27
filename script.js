const audio = document.querySelector("#background-audio");
const toggle = document.querySelector(".audio-toggle");

if (audio && toggle) {
  toggle.addEventListener("click", async () => {
    if (audio.paused) {
      try {
        audio.volume = 0.42;
        await audio.play();
        toggle.textContent = "sound on";
        toggle.setAttribute("aria-pressed", "true");
      } catch {
        toggle.textContent = "sound blocked";
      }
      return;
    }

    audio.pause();
    toggle.textContent = "sound off";
    toggle.setAttribute("aria-pressed", "false");
  });
}
