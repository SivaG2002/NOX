(() => {
  const preset = document.getElementById("voice-size-preset");
  const customLimit = document.getElementById("voice-custom-limit");

  if (!preset || !customLimit) {
    return;
  }

  const syncCustomLimit = () => {
    const selected = preset.options[preset.selectedIndex];
    const isCustom = preset.value === "custom";
    customLimit.disabled = !isCustom;
    if (!isCustom && selected?.dataset.limit) {
      customLimit.value = selected.dataset.limit;
    }
  };

  preset.addEventListener("change", syncCustomLimit);
  syncCustomLimit();
})();
