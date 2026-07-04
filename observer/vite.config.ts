import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The observer reads the repo's contracts and content directly — JSON Schema
// is the source of truth on both sides of the boundary (Ajv here, pydantic
// mirrors on the Python side). fs.allow lets dev-server imports reach them.
export default defineConfig({
  plugins: [react()],
  server: {
    fs: { allow: [".."] },
  },
  test: {
    environment: "node",
  },
});
