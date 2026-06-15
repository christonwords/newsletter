const audio = document.querySelector("#background-audio");
const toggle = document.querySelector(".audio-toggle");
const ticker = document.querySelector(".ticker p");

if (ticker) {
  ticker.innerHTML += ticker.innerHTML;
}

if (audio && toggle) {
  toggle.addEventListener("click", async () => {
    if (audio.paused) {
      try {
        audio.volume = 0.42;
        await audio.play();
        toggle.textContent = "sound: on";
        toggle.setAttribute("aria-pressed", "true");
      } catch {
        toggle.textContent = "sound blocked";
      }
      return;
    }

    audio.pause();
    toggle.textContent = "sound: off";
    toggle.setAttribute("aria-pressed", "false");
  });
}

document.addEventListener("pointermove", (event) => {
  const x = (event.clientX / window.innerWidth - 0.5).toFixed(3);
  const y = (event.clientY / window.innerHeight - 0.5).toFixed(3);
  document.documentElement.style.setProperty("--drift-x", x);
  document.documentElement.style.setProperty("--drift-y", y);
});
