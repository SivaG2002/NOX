(() => {
  // Sync custom user limits for size presets
  const syncPresets = (presetSelect, customLimitInput) => {
    if (!presetSelect || !customLimitInput) return;

    const syncCustomLimit = () => {
      const selected = presetSelect.options[presetSelect.selectedIndex];
      const isCustom = presetSelect.value === "custom";
      customLimitInput.disabled = !isCustom;
      if (!isCustom && selected?.dataset.limit) {
        customLimitInput.value = selected.dataset.limit;
      }
    };

    presetSelect.addEventListener("change", syncCustomLimit);
    syncCustomLimit();
  };

  // Sync main form presets
  const mainPreset = document.getElementById("voice-size-preset");
  const mainCustomLimit = document.getElementById("voice-custom-limit");
  syncPresets(mainPreset, mainCustomLimit);

  // Sync edit modal presets
  const editPreset = document.getElementById("editTriggerSizePreset");
  const editCustomLimit = document.getElementById("editTriggerCustomLimit");
  syncPresets(editPreset, editCustomLimit);

  // Handle edit modal population
  const editModal = document.getElementById("editTriggerModal");
  if (editModal) {
    editModal.addEventListener("show.bs.modal", (event) => {
      const button = event.relatedTarget;
      if (!button) return;

      const triggerId = button.dataset.triggerId;
      const triggerChannelName = button.dataset.triggerChannelName;
      const triggerCategoryId = button.dataset.triggerCategoryId;
      const triggerUserLimit = button.dataset.triggerUserLimit;
      const triggerSizePreset = button.dataset.triggerSizePreset;
      const triggerTemplate = button.dataset.triggerTemplate;
      const triggerEnabled = button.dataset.triggerEnabled === "true";

      // Update form action to point to the correct trigger
      const form = editModal.querySelector("#editTriggerForm");
      form.action = `/dashboard/${window.location.pathname.split("/")[2]}/voice-triggers/${triggerId}/update`;

      // Populate fields
      document.getElementById("editTriggerName").value = triggerChannelName;
      document.getElementById("editTriggerCategory").value = triggerCategoryId || "";
      document.getElementById("editTriggerSizePreset").value = triggerSizePreset;
      document.getElementById("editTriggerTemplate").value = triggerTemplate;
      document.getElementById("editTriggerEnabled").checked = triggerEnabled;

      // Sync custom limit based on preset
      if (triggerSizePreset !== "custom") {
        const selected = document.getElementById("editTriggerSizePreset").options[
          document.getElementById("editTriggerSizePreset").selectedIndex
        ];
        if (selected?.dataset.limit) {
          document.getElementById("editTriggerCustomLimit").value = selected.dataset.limit;
        }
      } else {
        document.getElementById("editTriggerCustomLimit").value = triggerUserLimit;
      }

      // Sync disabled state
      syncPresets(editPreset, editCustomLimit);
    });
  }
})();

