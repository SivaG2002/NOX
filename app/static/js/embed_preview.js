const sample = {
  streamer: "samplecreator",
  title: "Building a new speedrun route",
  game: "Just Chatting",
  platform: "Twitch",
  url: "https://example.com/watch",
  viewers: "1,024",
  start_time: "Just now",
};

function renderTemplate(value) {
  return Object.entries(sample).reduce(
    (text, [key, replacement]) => text.replaceAll(`{${key}}`, replacement),
    value || ""
  );
}

function refreshPreview() {
  const title = document.querySelector("[data-preview='title']");
  const description = document.querySelector("[data-preview='description']");
  const color = document.querySelector("[data-preview='color']");
  const footer = document.querySelector("[data-preview='footer']");
  const author = document.querySelector("[data-preview='author']");

  document.getElementById("preview-title").textContent = renderTemplate(title.value);
  document.getElementById("preview-description").textContent = renderTemplate(description.value);
  document.getElementById("preview-accent").style.background = color.value || "#e53935";
  document.getElementById("preview-footer").textContent = renderTemplate(footer.value);
  document.getElementById("preview-author").textContent = renderTemplate(author.value) || "Twitch Live";
}

document.querySelectorAll("#embed-form input, #embed-form textarea").forEach((input) => {
  input.addEventListener("input", refreshPreview);
});

refreshPreview();

