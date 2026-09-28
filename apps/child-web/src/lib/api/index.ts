import { config } from "@/src/config";
import type { LearningApi } from "./contracts";
import { HttpLearningApi } from "./http";
import { MockLearningApi } from "./mock";

let singleton: LearningApi | null = null;

export function getLearningApi(): LearningApi {
  if (!singleton) {
    singleton =
      config.apiMode === "http"
        ? new HttpLearningApi(
            config.apiBaseUrl,
            config.sessionResultPathTemplate
          )
        : new MockLearningApi();
  }
  return singleton;
}
