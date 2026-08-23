import type { Config } from "tailwindcss";
// Reuse Module 1's tokens exactly rather than redefining them here.
import designSystemConfig from "./src/design-system/tailwind.config";

const config: Config = {
  presets: [designSystemConfig],
  content: [
    "./src/**/*.{ts,tsx}",
    "../design-system/src/**/*.{ts,tsx}", // picks up classes used inside imported components
  ],
};

export default config;
