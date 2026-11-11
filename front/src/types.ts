import type { components } from "./api/schema";

type Schemas = components["schemas"];

export type PromptResponse = Schemas["PromptResponse"];
export type PromptDetailResponse = Schemas["PromptDetailResponse"];
export type PromptVersionResponse = Schemas["PromptVersionResponse"];
export type CreatePromptRequest = Schemas["CreatePromptRequest"];
export type VersionDiffResponse = Schemas["VersionDiffResponse"];
export type DiffLineResponse = Schemas["DiffLineResponse"];

/** A prompt as shown on the dashboard: the summary plus its versions, when they could be loaded. */
export type PromptItem = Omit<PromptResponse, "content"> & {
  versions?: PromptVersionResponse[];
};

export const activeVersion = (prompt: PromptItem): PromptVersionResponse | undefined =>
  prompt.versions?.find((version) => version.is_active);
