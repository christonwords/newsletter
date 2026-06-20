const root = document.documentElement;
const orbit = document.querySelector(".glass-orbit");
const revealEls = document.querySelectorAll(".reveal");
const magnets = document.querySelectorAll(".magnetic");

document.addEventListener("pointermove", (event) => {
  const x = event.clientX;
  const y = event.clientY;
  const mx = x / window.innerWidth - 0.5;
  const my = y / window.innerHeight - 0.5;

  root.style.setProperty("--cursor-x", x);
  root.style.setProperty("--cursor-y", y);
  root.style.setProperty("--mx", mx.toFixed(3));
  root.style.setProperty("--my", my.toFixed(3));

  if (orbit) {
    orbit.style.setProperty("--tilt-x", mx.toFixed(3));
    orbit.style.setProperty("--tilt-y", my.toFixed(3));
  }
});

revealEls.forEach((el) => {
  const delay = el.dataset.delay;
  if (delay) {
    el.style.setProperty("--delay", `${delay}ms`);
  }
});

const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("visible");
        observer.unobserve(entry.target);
      }
    });
  },
  { threshold: 0.16 }
);

revealEls.forEach((el) => observer.observe(el));

magnets.forEach((button) => {
  button.addEventListener("pointermove", (event) => {
    const rect = button.getBoundingClientRect();
    const x = event.clientX - rect.left - rect.width / 2;
    const y = event.clientY - rect.top - rect.height / 2;
    button.style.transform = `translate(${x * 0.08}px, ${y * 0.12}px) scale(1.02)`;
  });

  button.addEventListener("pointerleave", () => {
    button.style.transform = "";
  });
});
