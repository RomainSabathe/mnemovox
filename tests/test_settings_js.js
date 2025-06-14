/**
 * @jest-environment jsdom
 */

// Mock HTML structure for testing
const html = `
<div id="toast-container"></div>
<form id="settings-form">
    <div class="form-group">
        <label for="default-model">Default Model:</label>
        <select id="default-model">
            <option value="tiny">Tiny</option>
            <option value="base">Base</option>
            <option value="small">Small</option>
            <option value="medium">Medium</option>
        </select>
    </div>
    
    <div class="form-group">
        <label for="default-language">Default Language:</label>
        <select id="default-language">
            <option value="auto">Auto Detect</option>
            <option value="en">English</option>
            <option value="fr">French</option>
        </select>
    </div>
    
    <button type="submit">Save Settings</button>
</form>
`;

describe("Settings JS", () => {
  beforeEach(() => {
    document.body.innerHTML = html;
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ default_model: "base", default_language: "en" }),
      })
    );
    
    // Trigger DOMContentLoaded event manually since require doesn't trigger it
    delete require.cache[require.resolve("../static/js/settings.js")];
    require("../static/js/settings.js");
    
    // Manually trigger DOMContentLoaded event
    const event = new Event('DOMContentLoaded');
    document.dispatchEvent(event);
  });

  afterEach(() => {
    jest.clearAllMocks();
    document.body.innerHTML = '';
  });

  it("submits settings and shows success toast", async () => {
    const form = document.querySelector("#settings-form");
    const modelSelect = form.querySelector("#default-model");
    const languageSelect = form.querySelector("#default-language");
    
    modelSelect.value = "medium";
    languageSelect.value = "en";

    // Create and dispatch submit event
    const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
    form.dispatchEvent(submitEvent);

    // Wait for async operations to complete
    await new Promise(resolve => setTimeout(resolve, 200));

    expect(global.fetch).toHaveBeenCalledWith("/api/settings", expect.objectContaining({
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        default_model: "medium",
        default_language: "en"
      })
    }));
    
    const toast = document.querySelector(".toast.success");
    expect(toast).toBeTruthy();
    expect(toast.textContent).toContain("Settings saved");
  });

  it("shows error toast on API failure", async () => {
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: false,
        json: () => Promise.resolve({ error: "Invalid settings" }),
      })
    );

    const form = document.querySelector("#settings-form");
    const modelSelect = form.querySelector("#default-model");
    const languageSelect = form.querySelector("#default-language");
    
    modelSelect.value = "medium";
    languageSelect.value = "en";

    // Create and dispatch submit event
    const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
    form.dispatchEvent(submitEvent);

    // Wait for async operations to complete
    await new Promise(resolve => setTimeout(resolve, 200));

    const toast = document.querySelector(".toast.error");
    expect(toast).toBeTruthy();
    expect(toast.textContent).toContain("Invalid settings");
  });
});
