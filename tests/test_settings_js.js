/**
 * @jest-environment jsdom
 */
import fs from "fs";
import path from "path";
import { fireEvent } from "@testing-library/dom";
import "@testing-library/jest-dom";

const html = fs.readFileSync(
  path.resolve(__dirname, "../templates/settings.html"),
  "utf8"
);

describe("Settings JS", () => {
  beforeEach(() => {
    document.body.innerHTML = html;
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ default_model: "base", default_language: "en" }),
      })
    );
    require("../static/js/settings.js");
  });

  it("submits settings and shows success toast", async () => {
    const form = document.querySelector("#settings-form");
    form.querySelector("#default-model").value = "medium";
    form.querySelector("#default-language").value = "en";

    await fireEvent.submit(form);

    expect(global.fetch).toHaveBeenCalledWith("/api/settings", expect.any(Object));
    const toast = document.querySelector(".toast.success");
    expect(toast).toBeInTheDocument();
    expect(toast).toHaveTextContent("Settings saved");
  });
});
