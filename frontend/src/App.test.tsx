import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";

describe("App", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo) => {
        const url = String(input);
        if (url.includes("/api/health")) {
          return {
            ok: true,
            json: async () => ({
              ok: true,
              model: "realesr-general-x4v3.onnx",
              device: "cpu",
              stub: false,
              model_scale: 4,
              load_error: null,
            }),
          } as Response;
        }
        return { ok: false, statusText: "not mocked" } as Response;
      }),
    );
  });

  it("renders the enhancer workflow", async () => {
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Pro Image Enhancer" })).toBeInTheDocument();
    expect(screen.getByText("Upload")).toBeInTheDocument();
    expect(screen.getByLabelText(/upload an image/i)).toBeInTheDocument();
    expect(await screen.findByText(/realesr-general-x4v3/i)).toBeInTheDocument();
  });
});
