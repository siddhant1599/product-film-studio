const root = document.querySelector("#root");
const fps = Number(root.dataset.fps);
const duration = Number(root.dataset.duration);
const reveal = Number(root.dataset.revealFrame) / fps;
const canvas = document.querySelector("#plates");
const context = canvas.getContext("2d", { alpha: false });
const plates = Array.from({ length: Number(root.dataset.frames) }, (_, i) => {
  const img = new Image();
  img.src = "assets/plates/" + String(i).padStart(6, "0") + ".webp";
  return img;
});

let previous = -1;
function draw(time) {
  const index = Math.min(plates.length - 1, Math.max(0, Math.floor(time * fps + 1e-6)));
  const image = plates[index];
  if (index !== previous && image.complete && image.naturalWidth) {
    context.drawImage(image, 0, 0, canvas.width, canvas.height);
    previous = index;
  }
}

const timeline = gsap.timeline({ paused: true, onUpdate: () => draw(timeline.time()) });
timeline.to("#accent", { scaleX: 1, duration: Math.min(0.24, duration - reveal), ease: "power4.out" }, reveal);
timeline.set({}, {}, duration);
window.__timelines = { main: timeline };
window.__hf = window.__hf || {};
window.__hf.buildReady = window.__hf.buildReady || {};
window.__hf.buildReady.plates = Promise.all(plates.map(image => image.decode())).then(() => draw(timeline.time()));
