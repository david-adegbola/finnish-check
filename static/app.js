// The only JavaScript in the app: the "Load sample ads" button and the "Hide Finnish required" filter.

const loadButton = document.getElementById("load-samples");
if (loadButton) {
  loadButton.addEventListener("click", async () => {
    const status = document.getElementById("samples-status");
    try {
      const response = await fetch("/samples");
      const samples = await response.json();
      // One ad per block, separated by a line of three dashes, as the form expects
      document.getElementById("ads_text").value = samples.map(s => s.text).join("\n---\n");
      const skills = document.getElementById("skills");
      if (!skills.value.trim()) skills.value = "Python, SQL, Excel, QGIS, communication, laboratory work";
      status.textContent = `${samples.length} sample ads loaded.`;
    } catch (error) {
      status.textContent = "Couldn't load the sample ads.";
    }
  });
}

const hideRequired = document.getElementById("hide-required");
if (hideRequired) {
  hideRequired.addEventListener("change", () => {
    document.querySelectorAll("#results tbody tr").forEach(row => {
      row.classList.toggle("hidden", hideRequired.checked && row.dataset.level === "required");
    });
  });
}
